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

        # self.stats = {"all" : {"solved": 0, "validations": 0}, "nodes": []}
        self.stats = {"baseValue": 0}
        self.flooding_round = 0
        self.incrementedValue = 0
        self.pending_stats = {"baseValue": 0, "incrementedValue": 0, "totalIncrementedValue": 0, "numberOfResults": 0}
        
        self.network = {}
        
        self.isHandlingHTTP = False

        self.handicap = handicap

        self.last_flooding = time.time()
        self.TIME_TO_FLOODING = 2 # in seconds

        self.http_server = HTTPServerThread(self.logger, host, http_port, self.stats, self.network)
        self.p2p_server = P2PServerThread(self.logger, host, p2p_port)

        # Workers & Tasks Manager (load balancer)
        self.wtManager = WTManager(self.logger) 


    def connectWorker(self, host_port) -> Worker:
        """Connect to a peer."""
        try:
            self.logger.debug(f"Connecting to {host_port}")

            # create a socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host_port.split(":")[0], int(host_port.split(":")[1])))
            sock.setblocking(False)

            worker = self.wtManager.workersDict.get(host_port)
            if worker is not None:
                if worker.socket is not None:
                    worker.socket.close()
                worker.socket = sock # reconnect the socket
            else:
                worker = self.wtManager.add_worker(host_port, sock)

            return worker

        except Exception as e:
            self.logger.debug(f"Failed to connect to {host_port}.")
            return None 

    def send_msg(self, worker, msg):
        """Send a message through a socket."""
        host_port = worker.worker_address
        sock = worker.socket
        if sock is None:
            return

        try:
            P2PProtocol.send_msg(sock, msg)
            self.logger.debug(f"P2P-sent: {msg.data['command']}")  
        except Exception as e:
            self.logger.error(f"Worker {host_port} is dead ({msg.data['command']}).")
            self.wtManager.kill_worker(host_port, close_socket=True) # the worker is dead, kill the socket!

    # DEMO propose
    def execute_task(self, task_id):
        """Execute the task and send the reply."""
        for i in range(task_id*10, task_id*10+10):
            time.sleep(self.handicap)
            

    def isToSendFlooding(self):
        """Check if it is time to send a flooding message."""
        return (time.time() - self.last_flooding) > self.TIME_TO_FLOODING

    def run(self):
        """Run the node."""
        self.http_server.start()
        self.p2p_server.start()

        # Connect to anchor (if any)
        if self.anchor:
            worker = self.connectWorker(self.anchor) # create connection and store in workersDict
            
            if worker is not None: # if the connection was successful
                msg = P2PProtocol.join_request(self.p2p_server.replyAddress)
                self.send_msg(worker, msg)
            else:
                self.logger.warning(f"Failed to connect to anchor {self.anchor}.")

######### Main loop
        while True:
            # TODO: flooding protocol
            if self.isToSendFlooding():
                self.pending_stats["incrementedValue"] = self.incrementedValue
                
                for worker in self.wtManager.get_alive_workers():
                    self.logger.debug(f"P2P: Sending flooding consensus to {worker.worker_address} [{self.pending_stats['baseValue']}, {self.pending_stats['incrementedValue']}]")
                    msg = P2PProtocol.flooding_result(self.p2p_server.replyAddress, self.pending_stats["baseValue"], self.pending_stats["incrementedValue"])
                    self.send_msg(worker, msg)
                self.last_flooding = time.time()

                self.incrementedValue = 0

            self.wtManager.checkWorkersFloodingTimeouts() # kill inactive workers (if any)   


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

                # DEMO propose
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

                    worker = self.wtManager.workersDict.get(host_port)
                    # Add or update the node that sent the hello message
                    if worker is None:
                        self.connectWorker(host_port)
                    else:
                        if worker.socket == None:
                            # worker was dead and socket must be reconnected
                            self.connectWorker(host_port)

                    # TODO: to be removed  
                    # Add nodes that current node does not have
                    for host_port in data["args"]["nodesList"]:
                        # Skip if the node is the same as the current node
                        if host_port == self.p2p_server.replyAddress:
                            continue

                        if self.wtManager.workersDict.get(host_port) is None:
                            self.connectWorker(host_port)
                            
                elif data["command"] == "JOIN_REQUEST":
                    host_port = data["replyAddress"]

                    worker = self.connectWorker(host_port)
                    worker.flooding_received() # if the worker is not new it is a reconnection!

                    # reply with the list of nodes
                    msg = P2PProtocol.join_reply(nodesList=list(self.wtManager.get_alive_workers_address()))
                    self.send_msg(worker, msg)

                elif data["command"] == "JOIN_REPLY":
                    nodesList = data["args"]["nodesList"].copy() # list of nodes to send in hello message
                    nodesList.remove(self.p2p_server.replyAddress) # himself b# ELE NUMA SEGUNDA RECONECAO PODE ESTAR MORTO E NAO APARECE AQU!
                    nodesList.append(self.anchor) # how send the join reply

                    # Send hello message for each node
                    for host_port in nodesList:

                        if host_port == self.anchor:
                            worker = self.wtManager.workersDict.get(host_port) # already connected
                        else:
                            worker = self.connectWorker(host_port)

                        msg = P2PProtocol.hello(self.p2p_server.replyAddress, nodesList) 
                        self.send_msg(worker, msg)

                elif data["command"] == "SOLVE_REQUEST":
                    task_id = data["args"]["task_id"]
                    self.execute_task(task_id) # DEMO propose
                    # TODO: this must be done with a time limit!!!

                    host_port = data["replyAddress"]

                    # Send the reply
                    worker = self.wtManager.workersDict.get(host_port)
                    msg = P2PProtocol.solve_reply(self.p2p_server.replyAddress, task_id)
                    self.send_msg(worker, msg)
                    
                elif data["command"] == "SOLVE_REPLY":
                    # Store the task as solved
                    task_id = data["args"]["task_id"]
                    self.wtManager.finish_task(task_id) 
                    # update flooding stats
                    self.incrementedValue += 1
                    self.logger.critical("INCREASE ONE!!!")
            
                elif data["command"] == "FLOODING_RESULT":
                    baseValueReceived = data["baseValue"]
                    incrementedValueReceived = data["incrementedValue"]
                    # roundReceived = data["round"]
                    
                    self.pending_stats["baseValue"] = max(self.pending_stats["baseValue"], baseValueReceived)
                    
                    self.pending_stats["numberOfResults"] += 1
                    self.pending_stats["totalIncrementedValue"] += incrementedValueReceived  

                    worker = self.wtManager.workersDict.get(data["replyAddress"])
                    worker.flooding_received() # update the last flooding time
                    
                    self.logger.debug(f"P2P: Flooding result received. [{baseValueReceived}, {incrementedValueReceived}]")
                    self.logger.warning(f"[{self.pending_stats['baseValue']}, {self.incrementedValue}, {self.pending_stats['totalIncrementedValue'] }]")
                    
                elif data["command"] == "FLOODING_CONFIRMATION":
                    # update baseValue if someone has a higher value (or higher round)
                    baseValueReceived = data["baseValue"]
                    
                    # TODO: check if round has been confirmed

                    self.stats["baseValue"] = max(self.pending_stats["baseValue"], baseValueReceived)

                    self.pending_stats = {"baseValue": self.stats["baseValue"], "incrementedValue": 0, "totalIncrementedValue": 0, "numberOfResults": 0}    
                

            # only when I receive the result from all ALIVE nodes I will send the confirmation
            if len(self.wtManager.get_alive_workers()) > 0 and self.pending_stats["numberOfResults"] >= len(self.wtManager.get_alive_workers()):
                self.stats["baseValue"] = self.pending_stats["baseValue"] + self.pending_stats["totalIncrementedValue"] + self.pending_stats["incrementedValue"]
                
                self.logger.critical(f"[{self.pending_stats['baseValue']}, {self.pending_stats['incrementedValue']}, {self.pending_stats['totalIncrementedValue']}]")

                # broadcast the confirmation
                for worker in self.wtManager.get_alive_workers():
                    msg = P2PProtocol.flooding_confirmation(self.p2p_server.replyAddress, self.stats["baseValue"])
                    self.send_msg(worker, msg)
                
                # setup for the next round
                self.pending_stats = {"baseValue": self.stats["baseValue"], "incrementedValue": 0, "totalIncrementedValue": 0, "numberOfResults": 0}
                
                # self.flooding_round += 1
            

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
                retry_tasks = self.wtManager.checkTasksTimeouts() # tasks to retry, the timeout ones were all in the pending queue!

                # Retry tasks
                for task in retry_tasks:
                    # build the tasks again
                    msg = P2PProtocol.solve_request(self.p2p_server.replyAddress, task.task_id)
                    
                    # send the tasks to the worker
                    self.send_msg(task.worker, msg)
                    self.logger.warning(f"P2P: Retrying task to {task.worker.worker_address} [{task.worker.task_response_time}]")
     
                tasks_to_send = self.wtManager.get_tasks_to_send() # tasks to work, with the best workers

                # Send tasks
                for task in tasks_to_send:
                    # build the tasks
                    msg = P2PProtocol.solve_request(self.p2p_server.replyAddress, task.task_id)

                    # send the tasks to the worker
                    self.send_msg(task.worker, msg)
                    self.logger.debug(f"P2P: Assigning task {task.task_id} to {task.worker.worker_address} [{task.worker.task_response_time}]")


                    