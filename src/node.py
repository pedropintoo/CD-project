import selectors
import time
import socket
import queue
import pickle
from src.p2p_loadbalancer import WTManager, Worker
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

        # Workers & Tasks Manager (load balancer)
        self.wtManager = WTManager() 


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
        try:
            P2PProtocol.send_msg(sock, msg)
            self.logger.debug(f"P2P-sent: {msg.data['command']}")  
        except Exception as e:
            self.logger.error(f"Failed to send message. {e}")

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
            self.wtManager.socketsDict[self.anchor] = sock
            self.wtManager.workersDict[self.anchor] = Worker(self.anchor, sock)
            
            msg = P2PProtocol.join_request(self.p2p_server.replyAddress)
            self.send_msg(sock, msg)

######### Main loop
        while True:
            
            # get http request (if any)                
            try:
                http_request = self.http_server.request_queue.get(block=False) 
            except queue.Empty:
                http_request = None

            # get p2p request (if any)
            try:
                p2p_request = self.p2p_server.request_queue.get(block=False)  
            except queue.Empty:
                p2p_request = None    
            

            # Handle http requests (if any)
            if http_request is not None:
                self.logger.debug(f"HTTP: Requested {http_request} tasks.")
                self.isHandlingHTTP = True
                number_of_tasks = int(http_request)
                
                # Add tasks to the pending queue
                for i in range(number_of_tasks):
                    self.wtManager.add_pending_task(i)
      
            # Handle p2p requests (if any)     
            if p2p_request is not None:
                data = p2p_request.data # get data attribute from the message
                self.logger.debug(f"P2P-received: {data['command']}")
                
                # Switch from the command
                if data["command"] == "HELLO":
                    host_port = data["replyAddress"]

                    # Add the node that sent the hello message to the network
                    if self.wtManager.socketsDict.get(host_port) is None:
                        sock = self.connect(host_port)
                        self.wtManager.socketsDict[host_port] = sock   
                        self.wtManager.workersDict[host_port] = Worker(host_port, sock)

                    # Add nodes that current node does not have
                    for host_port in data["args"]["nodesList"]:
                        # Skip if the node is the same as the current node
                        if host_port == self.p2p_server.replyAddress:
                            continue

                        if self.wtManager.socketsDict.get(host_port) is None:
                            sock = self.connect(host_port)
                            self.wtManager.socketsDict[host_port] = sock 
                            self.wtManager.workersDict[host_port] = Worker(host_port, sock)   
                            
                elif data["command"] == "JOIN_REQUEST":
                    host_port = data["replyAddress"]
                    sock = self.connect(host_port) 
                    self.wtManager.socketsDict[host_port] = sock
                    self.wtManager.workersDict[host_port] = Worker(host_port, sock)

                    # reply with the list of nodes
                    msg = P2PProtocol.join_reply(nodesList=list(self.wtManager.socketsDict.keys()))
                    self.send_msg(sock, msg)

                elif data["command"] == "JOIN_REPLY":
                    nodesList = data["args"]["nodesList"].copy() # list of nodes to send in hello message
                    nodesList.remove(self.p2p_server.replyAddress) 
                    nodesList.append(self.anchor)

                    # Send hello message for each node
                    for host_port in nodesList:

                        if host_port == self.anchor:
                            sock = self.wtManager.socketsDict.get(host_port) # already connected
                        else:
                            sock = self.connect(host_port) 
                            self.wtManager.socketsDict[host_port] = sock
                            self.wtManager.workersDict[host_port] = Worker(host_port, sock)

                        msg = P2PProtocol.hello(self.p2p_server.replyAddress, nodesList) 
                        self.send_msg(sock, msg)

                elif data["command"] == "SOLVE_REQUEST":
                    task_id = data["args"]["task_id"]
                    self.execute_task(task_id) # TODO: sudoku task

                    host_port = data["replyAddress"]

                    # Send the reply
                    sock = self.wtManager.socketsDict.get(host_port)
                    msg = P2PProtocol.solve_reply(self.p2p_server.replyAddress, task_id)
                    self.send_msg(sock, msg)
                    
                elif data["command"] == "SOLVE_REPLY":
                    # Store the task as solved
                    task_id = data["args"]["task_id"]
                    self.wtManager.finish_task(task_id) 
                        
            if not self.isHandlingHTTP:
                continue
            
            # Manage tasks assignments and timeouts (if any)    
            
            # check if completed
            if self.wtManager.isDone():
                self.isHandlingHTTP = False
                self.http_server.response_queue.put("task done!")
                self.logger.debug("HTTP: Task done!")
            else:
            # manage tasks assignments and timeouts
                timeout_tasks = self.wtManager.checkTimeouts() # tasks that have timed out

                # Retry tasks
                if len(timeout_tasks) > 0:
                    for task in timeout_tasks:
                        msg = P2PProtocol.solve_request(self.p2p_server.replyAddress, task.task_id)
                        self.send_msg(sock=self.wtManager.socketsDict[task.worker.worker_address], msg=msg)
                        task.retry()
                        self.logger.debug(f"P2P: Retrying task to {task.worker.worker_address} [{task.worker.ema_response_time}]")
     
                tasks_to_work = self.wtManager.get_tasks_to_work() # Get new tasks with associated workers

                # Assign new tasks
                for task in tasks_to_work:
                    msg = P2PProtocol.solve_request(self.p2p_server.replyAddress, task.task_id)
                    self.send_msg(sock=self.wtManager.socketsDict[task.worker.worker_address], msg=msg)
                    self.logger.debug(f"P2P: Assigning task {task.task_id} to {task.worker.worker_address} [{task.worker.ema_response_time}]")


                    
    # next_task = self.next_task() # Find the next task_id to be send

    # if next_task is not None:
    #     self.http_tasks[next_task] = 0 # sent

    #     host_port = data["replyAddress"]
    #     sock = self.wtManager.socketsDict.get(host_port)

    #     msg = P2PProtocol.solve_request(self.p2p_server.replyAddress, next_task)
    #     self.send_msg(sock, msg)   