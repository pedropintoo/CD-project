import selectors
import time
import socket
import queue
import pickle
from src.p2p_loadbalancer import WorkersManager, TaskManager
from src.p2p_server import P2PServerThread
from src.http_server import HTTPServerThread
from src.utils.logger import Logger
from src.p2p_protocol import P2PProtocol 

class Node:
    def __init__(self, host, http_port, p2p_port, anchor, handicap):

        self.logger = Logger(f"[{host}]", f"logs/{host}.log")
        self.selector = selectors.DefaultSelector()
        self.anchor = anchor # uniform format 'host:port'

        self.stats = {"all" : {"solved": 0, "validations": 0}, "nodes": []}
        self.network = {}
        
        self.http_tasks = {} 
        self.isHandlingHTTP = False

        self.http_server = HTTPServerThread(self.logger, host, http_port, self.stats, self.network)
        self.p2p_server = P2PServerThread(self.logger, host, p2p_port, handicap)

        self.workersManager = WorkersManager()
        self.taskManager = TaskManager(self.workersManager)


    def connect(self, host_port):
        """Connect to a peer."""
        try:
            self.logger.debug(f"Connecting to {host_port}")

            # create a socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host_port.split(":")[0], int(host_port.split(":")[1])))
            sock.setblocking(False)

            # Register the socket to the selector
            self.p2p_server.selector.register(sock, selectors.EVENT_READ, self.p2p_server.handle_requests)

            return sock

        except Exception as e:
            self.logger.error(f"Failed to connect to {host_port}. {e}")
            return None 

    def send_msg(self, sock, msg):
        """Send a message through a socket."""
        P2PProtocol.send_msg(sock, msg)
        self.logger.debug(f"P2P-sent: {msg.data['command']}")          

    def next_task(self):
        """Find the next task to be send."""
        return next((task_id for task_id, state in self.http_tasks.items() if state == -1), None)    

    # request is {'command': 'SOLVE_REQUEST', 'task': task_id}
    def execute_task(self, task_id):
        """Execute the task and send the reply."""
        for i in range(task_id*10, task_id*10+10):
            time.sleep(0.1)
            
        
    def run(self):
        """Run the node."""
        self.http_server.start()
        self.p2p_server.start()

        # Connect to anchor (if any)
        if self.anchor:
            sock = self.connect(self.anchor) # create connection and store in socketsDict
            self.workersManager.socketsDict[self.anchor] = sock
            
            msg = P2PProtocol.join_request(self.p2p_server.replyAddress)
            self.send_msg(sock, msg)

        # Main loop
        while True:

            try:
                http_response = self.http_server.request_queue.get(block=False)
            except queue.Empty:
                http_response = None
            
            if http_response is not None:
                self.isHandlingHTTP = True
                self.http_tasks = {i: -1 for i in range(int(http_response))} # start tasks structure
                self.logger.debug(f"HTTP: {http_response}")
                
                task_id = 0
                for sock in self.workersManager.socketsDict.values():
                    self.http_tasks[task_id] = 0 # sent
                      
                    msg = P2PProtocol.solve_request(self.p2p_server.replyAddress, task_id)
                    self.send_msg(sock, msg)

                    task_id += 1 
                                     
            try:
                request = self.p2p_server.request_queue.get(block=False) 
            except queue.Empty:
                request = None
                   
            if request is not None:
                data = request.data

                self.logger.debug(f"P2P-received: {data['command']}")
                
                if data["command"] == "HELLO":
                    if self.workersManager.socketsDict.get(data["replyAddress"]) is None:
                        host_port = data["replyAddress"]
                        sock = self.connect(host_port)
                        self.workersManager.socketsDict[host_port] = sock   

                    for host_port in data["args"]["nodesList"]: # [host:port, host:port, ...]
                        
                        # Skip if the node is the same as the current node
                        if host_port == self.p2p_server.replyAddress:
                            continue

                        if self.workersManager.socketsDict.get(host_port) is None:
                            sock = self.connect(host_port)
                            self.workersManager.socketsDict[host_port] = sock    
                            
                elif data["command"] == "JOIN_REQUEST":
                    host_port = data["replyAddress"]

                    sock = self.connect(host_port) 
                    self.workersManager.socketsDict[host_port] = sock

                    msg = P2PProtocol.join_reply(nodesList=list(self.workersManager.socketsDict.keys()))
                    self.send_msg(sock, msg)


                elif data["command"] == "JOIN_REPLY":
                    nodesList = data["args"]["nodesList"].copy() # prepare the list of nodes to send in hello message
                    nodesList.remove(self.p2p_server.replyAddress) 
                    nodesList.append(self.anchor)

                    for host_port in data["args"]["nodesList"]: # [host:port, host:port, ...]
                        
                        # Skip if the node is the same as the current node
                        if host_port == self.p2p_server.replyAddress:
                            continue
                        
                        # print (f"Connecting to {host_port} my address is {self.p2p_server.replyAddress}")
                        # print (f"list of sockets {data['args']['nodesList']}")

                        # send hello message for each node
                        sock = self.connect(host_port) 
                        self.workersManager.socketsDict[host_port] = sock

                        msg = P2PProtocol.hello(self.p2p_server.replyAddress, nodesList) 
                        self.send_msg(sock, msg)


                elif data["command"] == "SOLVE_REQUEST":
                    task_id = data["args"]["task_id"]
                    self.execute_task(task_id) # execute

                    host_port = data["replyAddress"]

                    # Send the reply
                    sock = self.workersManager.socketsDict.get(host_port)

                    msg = P2PProtocol.solve_reply(self.p2p_server.replyAddress, task_id)
                    self.send_msg(sock, msg)
                    
                elif data["command"] == "SOLVE_REPLY": # http_tasks -> {task_id: state, ...}, state = -1: to be send, 0: send, 1: received
                    task_id = data["args"]["task_id"]
                    self.http_tasks[task_id] = 1

                    next_task = self.next_task() # Find the next task_id to be send

                    if next_task is not None:
                        self.http_tasks[next_task] = 0 # sent

                        host_port = data["replyAddress"]
                        sock = self.workersManager.socketsDict.get(host_port)

                        msg = P2PProtocol.solve_request(self.p2p_server.replyAddress, next_task)
                        self.send_msg(sock, msg)    
                        

            if self.isHandlingHTTP:
                if all(state == 1 for state in self.http_tasks.values()):
                    self.http_server.response_queue.put("done")
                    self.isHandlingHTTP = False
                else:
                    timeout_tasks = self.taskManager.checkTimeouts()

                    # Retry tasks
                    if len(timeout_tasks) > 0:
                        for task in timeout_tasks:
                            msg = P2PProtocol.solve_request(self.p2p_server.replyAddress, task.task_id)
                            self.send_msg(self.workersManager.socketsDict[task.worker_address], msg)
                            task.retry()

                    # new_tasks = self.taskManager.get_tasks_to_work() # Get new tasks with associated workers

                    # # Assign new tasks
                    # for task in new_tasks:
                    #     msg = P2PProtocol.solve_request(self.p2p_server.replyAddress, task.task_id)
                    #     self.send_msg(self.workersManager.socketsDict[task.worker_address], msg)

                    #     self.taskManager.add_working_task(task)


                    