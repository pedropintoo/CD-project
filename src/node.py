import selectors
import time
import socket
import queue
import pickle
from src.p2p_server import P2PServerThread
from src.http_server import HTTPServerThread
from src.utils.logger import Logger
from src.p2p_protocol import P2PProtocol 


class Node:
    def __init__(self, host, http_port, p2p_port, anchor, handicap):

        self.logger = Logger(f"[{host}]", f"logs/{host}.log")
        self.selector = selectors.DefaultSelector()
        self.anchor = anchor

        self.stats = {"all" : {"solved": 0, "validations": 0}, "nodes": []}
        self.network = {}
        self.socketsDict = {} # {'host-port': socket}
        
        self.http_tasks = {} 
        self.isDone = False
        self.isHandlingHTTP = False

        self.http_server = HTTPServerThread(self.logger, host, http_port, self.stats, self.network)
        self.p2p_server = P2PServerThread(self.logger, host, p2p_port, handicap, self.socketsDict)

        


    def connect(self, host, port):
        """Connect to a peer."""
        try:
            self.logger.debug(f"Connecting to {host}:{port}")

            # create a socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, int(port)))
            sock.setblocking(False)

            # Register the socket to the selector
            self.p2p_server.selector.register(sock, selectors.EVENT_READ, self.p2p_server.handle_requests)

            return sock

        except Exception as e:
            self.logger.error(f"Failed to connect to {host}:{port}. {e}")
            return None   

    def next_task(self):
        """Find the next task to be send."""
        return next((task_id for task_id, state in self.http_tasks.items() if state == -1), None)    

    # request is {'command': 'SOLVE_REQUEST', 'task': task_id}
    def execute_task(self, request):
        """Execute the task and send the reply."""
        task_id = request["task"]

        self.logger.info(f"Task {task_id} is being executed... {i}%")
        # Execute the task
        for i in range(task_id*10, task_id*10+10):
            time.sleep(0.5)
            
        
    def run(self):
        """Run the node."""
        self.http_server.start()
        self.p2p_server.start()

        # Connect to anchor (if any)
        if self.anchor:
            anchor_host = self.anchor.split(":")[0]
            anchor_port = self.anchor.split(":")[1]
            sock = self.connect(anchor_host, anchor_port) # create connection and store in socketsDict
            self.socketsDict[anchor_host + "-" + anchor_port] = sock

            self.logger.info(f"Connected to: {anchor_host}:{anchor_port}")
            msg = P2PProtocol.join_request()
            P2PProtocol.send_msg(sock, msg)

        # Main loop
        while True:

            try:
                http_response = self.http_server.request_queue.get(block=False)
            except queue.Empty:
                http_response = None
            
            if http_response is not None:
                self.isHandlingHTTP = True
                self.isDone = False
                self.http_tasks = {i: -1 for i in range(int(http_response))}
                self.logger.info(f"HTTP: {http_response}")
                
                task_counter = 0
                for host_port, sock in self.socketsDict:
                    msg = P2PProtocol.solve_request(request["args"]["nodesList"])
                    P2PProtocol.send_msg(sock, msg)
                    self.http_tasks[task_counter] = 0
                    task_counter += 1                    
            
            
            try:
                request, addr = self.p2p_server.request_queue.get(block=False) 
            except queue.Empty:
                request = None
                   
            if request is not None:
                data = request.data
                self.logger.info(f"P2P: {data}")
                
                if data["command"] == "HELLO":
                    for node in data["args"]["nodesList"]: # [host-port, host-port, ...]
                        host = node.split("-")[0]
                        port = node.split("-")[1]

                        # Check if socketsDict has the socket -> {'host-port': socket}
                        if self.socketsDict.get(node) is None:
                            sock = self.connect(host, port)
                            self.socketsDict[host + "-" + port] = sock    
                            
                elif data["command"] == "JOIN_REQUEST":
                    host = addr[0]
                    port = addr[1]

                    print(self.socketsDict.values())

                    sock = self.connect(host, port) 
                    self.socketsDict[host + "-" + str(port)] = sock

                    msg = P2PProtocol.join_reply(list(self.socketsDict.keys()))
                    P2PProtocol.send_msg(sock, msg)
                    
                elif data["command"] == "JOIN_REPLY":
                    for node in data["args"]["nodesList"]: # [host-port, host-port, ...]
                        host = node.split("-")[0]
                        port = node.split("-")[1] 

                        # Check if socketsDict has the socket -> {'host-port': socket}
                        if self.socketsDict.get(node) is not None:
                            P2PProtocol.hello(self.socketsDict.get(node), data["args"]["nodesList"])
                        else:  
                            sock = self.connect(host, port) 
                            self.socketsDict[host + "-" + port] = sock

                            msg = P2PProtocol.hello(data["args"]["nodesList"])
                            P2PProtocol.send_msg(sock, msg)
                        
                elif data["command"] == "SOLVE_REQUEST":
                    self.execute_task(addr, data) # and send reply

                    # Send the reply
                    msg = P2PProtocol.solve_reply(task_id)
                    host_port = addr[0] + "-" + str(addr[1])
                    sock = self.socketsDict.get(host_port)
                    P2PProtocol.send_msg(sock, msg)
                    
                elif data["command"] == "SOLVE_REPLY":
                    # Update http_tasks -> {task_id: state, ...} -1: to be send, 0: send, 1: received
                    task_id = data["args"]["task_id"]
                    self.http_tasks[task_id] = 1

                    next_task = self.next_task() # Find the task_id in http_tasks to be send
                    if next_task is not None:
                        msg = P2PProtocol.solve_request(next_task)
                        # Check if socketsDict has the socket -> {'host-port': socket}
                        host_port = addr[0] + "-" + str(addr[1])
                        P2PProtocol.send_msg(self.socketsDict.get(host_port), msg)
                    else:
                        self.isDone = True        
                        

            if self.isHandlingHTTP:
                if self.isDone:
                    self.http_server.response_queue.put("done")
                    self.isHandlingHTTP = False
                else:
                    self.logger.info("Waiting for tasks to be solved...")
                    # TODO: checkTimeout()

                    