import selectors, time, socket, queue, pickle, sys
from src.p2p_loadbalancer import WTManager, Worker, TaskID
from src.p2p_server import P2PServer
from src.http_server import HTTPServer
from src.utils.logger import Logger
from src.p2p_protocol import P2PProtocol 
from src.sudoku_job import SudokuJob
from src.sudoku_algorithm import SudokuAlgorithm

class Node:
    def __init__(self, host, http_port, p2p_port, anchor, handicap, max_threads):

        self.logger = Logger(f"[{host}]", f"logs/{host}.log")
        self.selector = selectors.DefaultSelector()
        self.anchor = anchor # uniform format 'host:port'

        self.stats = {
            "all": {
                "solved": 0, 
                "invalid": 0, 
                "validations": 0 # sum of nodes validations
            },
            "nodes": [
                # { "address": "host:port", "validations": 0}, ..
            ]
        }
        
        self.pending_stats = {  
            "numberOfResults": 0,
            "all": {
                "solved": 0, "internal_solved": 0, "external_solved": 0, "uncommitted_solved": 0,
                "invalid": 0, "internal_invalid": 0, "external_invalid": 0, "uncommitted_invalid": 0, 
                "validations": 0, "internal_validations": 0, "external_validations": 0, "uncommitted_validations": 0 # TODO: remove validations and use sum of nodes validations
            },
            "nodes": [
                # { "address": "host:port", "validations": 0, "internal_validations": 0, "external_validations": 0, "uncommitted_validations": 0}, ..
            ]    
        }

        
        self.network = {}
        
        self.isHandlingHTTP = False

        self.handicap = handicap

        self.last_flooding = time.time()
        self.TIME_TO_FLOODING = 3 # in seconds

        self.http_server = HTTPServer(self.logger, host, http_port, self.stats, self.network, max_threads)
        self.p2p_server = P2PServer(self.logger, host, p2p_port)

        # Workers & Tasks Manager (load balancer)
        self.wtManager = WTManager(self.logger)
        
        self.solverConfig = SudokuAlgorithm(logger= self.logger, handicap = self.handicap)

    

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

    def isToSendFlooding(self):
        """Check if it is time to send a flooding message."""
        return (time.time() - self.last_flooding) > self.TIME_TO_FLOODING

    def updateSumStats(self, baseName=None, updateNodes=False):
        """Update Stats."""
        self.stats["all"][baseName] = self.pending_stats["all"][baseName] + self.pending_stats["all"]["internal_"+baseName] + self.pending_stats["all"]["external_"+baseName]
        # TODO: nodes stats

    def commitPendingStats(self, baseName=None, commitNodes=False):
        """Commit Pending Stats."""
        # stat = self.pending_stats["all"][baseName] ???
        self.pending_stats["all"]["internal_"+baseName] = self.pending_stats["all"]["uncommitted_"+baseName]
        self.pending_stats["all"]["uncommitted_"+baseName] = 0
        # TODO: nodes stats

    def updateWithReceivedStats(self, stats, baseName=None, updateNodes=False):
        """Update Stats with Received Stats."""
        myBaseValue = self.pending_stats["all"][baseName] # from pending stats
        baseValueReceived = stats["all"][baseName]
        incrementedValueReceived = stats["all"]["internal_"+baseName]

        if baseValueReceived > myBaseValue:
            self.pending_stats["all"][baseName] = baseValueReceived
            self.pending_stats["all"]["internal_"+baseName] = 0
            self.pending_stats["all"]["external_"+baseName] = incrementedValueReceived
            self.pending_stats["numberOfResults"] = 0
        elif baseValueReceived < myBaseValue:
            self.pending_stats["numberOfResults"] += 1
        else:
            self.pending_stats["numberOfResults"] += 1
            self.pending_stats["all"]["external_"+baseName] += incrementedValueReceived 
        
        # TODO: nodes stats

    def updateWithConfirmedStats(self, stats, host_port, baseName=None, updateNodes=False):
        """Update Stats with Confirmed Stats."""
        myBaseValue = self.pending_stats["all"][baseName] + self.pending_stats["all"]["internal_"+baseName] + self.pending_stats["all"]["external_"+baseName]
        baseValueReceived = stats["all"][baseName]

        if baseValueReceived > myBaseValue:
            self.stats["all"][baseName] = baseValueReceived
            self.logger.critical(f"Update {baseName} to [{self.stats['all'][baseName]}].")
        elif baseValueReceived < myBaseValue:
            self.logger.critical(f"Discard {baseName} [{baseValueReceived}] from {host_port}.")

        self.pending_stats["all"][baseName] = self.stats["all"][baseName]
        self.pending_stats["all"]["internal_"+baseName] = 0
        self.pending_stats["all"]["external_"+baseName] = 0 # not the uncommitted !!!
        self.pending_stats["all"]["numberOfResults"] = 0
        # TODO: nodes stats

    def updateNetwork(self):
        """Update network dict."""
        self.network.clear()
        for worker in self.wtManager.get_alive_workers():
            self.network[worker.worker_address] = worker.network

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
                # TODO: kill the node!


######### Main loop
        while True:
            if self.isToSendFlooding():
                # commit the pending stats and define uncommitted as 0
                self.commitPendingStats("solved") 
                self.commitPendingStats("invalid")
                self.commitPendingStats("validations")
                
                for worker in self.wtManager.get_alive_workers():
                    self.logger.debug(f"P2P: Sending flooding consensus to {worker.worker_address}.")
                    msg = P2PProtocol.flooding_hello(self.p2p_server.replyAddress, list(self.wtManager.get_alive_workers_address()), self.pending_stats.copy())
                    self.send_msg(worker, msg)
                self.last_flooding = time.time()

                self.updateNetwork()

            self.wtManager.checkWorkersFloodingTimeouts() # kill inactive workers (if any)   


            # get http request (if any)
            try:
                http_request = self.http_server.request_queue.get(block=False)
                if http_request is not None: 
                    self.logger.debug(f"HTTP: Requested {http_request} tasks.")
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

                sudoku = http_request
                print(sudoku)
                self.wtManager.add_pending_task(sudoku)                  
      
            # Handle p2p requests (if any)     
            if p2p_request is not None:
                data = p2p_request.data # get data attribute from the message
                self.logger.debug(f"P2P-received: {data['command']}")
                
                # Switch from the command received
                if data["command"] == "FLOODING_HELLO":
                    #### update the network
                    host_port = data["replyAddress"]
                    aliveNodes = data["args"]["aliveNodes"]

                    worker = self.wtManager.workersDict.get(host_port)
                    # Add or update the node that sent the flooding message
                    if worker is None:
                        worker = self.connectWorker(host_port)
                    else:
                        if worker.socket == None:
                            # worker was dead and socket must be reconnected
                            self.connectWorker(host_port)
                        worker.flooding_received() # update the last flooding time

                    worker.network = aliveNodes # update worker network

                    # Add nodes that current node does not have
                    for host_port in aliveNodes:
                        # Skip if the node is the same as the current node
                        if host_port == self.p2p_server.replyAddress:
                            continue

                        if self.wtManager.workersDict.get(host_port) is None:
                            self.connectWorker(host_port)        

                    #### updating the stats
                    stats = data["args"]["stats"]

                    self.updateWithReceivedStats(stats, baseName="solved")
                    self.updateWithReceivedStats(stats, baseName="invalid")
                    self.updateWithReceivedStats(stats, baseName="validations")

                    self.logger.warning(f"[{self.pending_stats['all']['solved']}, {self.pending_stats['all']['uncommitted_solved']}, {self.pending_stats['all']['external_solved'] }]")

                elif data["command"] == "FLOODING_CONFIRMATION":
                    # update baseValue if someone has a higher value (or higher round)
                    host_port = data["replyAddress"]
                    stats = data["args"]["stats"]
                   
                    
                    # host_port is only for logging!
                    self.updateWithConfirmedStats(stats, host_port, "solved")
                    self.updateWithConfirmedStats(stats, host_port, "invalid")
                    self.updateWithConfirmedStats(stats, host_port, "validations")

                    

                elif data["command"] == "JOIN_REQUEST":
                    host_port = data["replyAddress"]

                    worker = self.connectWorker(host_port)
                    worker.flooding_received() # if the worker is not new it is a reconnection!

                    # reply with the list of nodes
                    msg = P2PProtocol.join_reply(aliveNodes=list(self.wtManager.get_alive_workers_address()))
                    self.send_msg(worker, msg)

                elif data["command"] == "JOIN_REPLY":
                    aliveNodes = data["args"]["aliveNodes"].copy() # list of nodes to send in next flooding
                    aliveNodes.remove(self.p2p_server.replyAddress) # himself
                    aliveNodes.append(self.anchor) # how send the join reply

                    # Send flooding hello message for each node
                    for host_port in aliveNodes:

                        if host_port == self.anchor:
                            worker = self.wtManager.workersDict.get(host_port) # already connected
                        else:
                            worker = self.connectWorker(host_port)

                        msg = P2PProtocol.flooding_hello(self.p2p_server.replyAddress, aliveNodes, self.pending_stats.copy())
                        self.send_msg(worker, msg)

                elif data["command"] == "SOLVE_REQUEST":                    
                    task_id = data["args"]["task_id"]
                    sudoku = data["args"]["sudoku"]
                    host_port = data["replyAddress"]
                    
                    self.logger.critical(f"Task {task_id} received from {host_port}.")
                    start, end = task_id.get_start_end()
        
                    # Create SudokuJob object
                    sudoku_job = SudokuJob(sudoku, start, end, self.solverConfig)
                    
                    # Execute the task using SudokuJob (TODO: maybe thread this)
                    solution = sudoku_job.run()

                    worker = self.wtManager.workersDict.get(host_port)

                    if solution is not None:
                        self.logger.debug(f"Sudoku is valid.")
                        msg = P2PProtocol.solve_reply(self.p2p_server.replyAddress, task_id, solution)
                    else:
                        self.logger.debug(f"Sudoku is invalid.")
                        msg = P2PProtocol.solve_reply(self.p2p_server.replyAddress, task_id)    
                    
                    # Send the reply
                    self.send_msg(worker, msg)
                    
                elif data["command"] == "SOLVE_REPLY":
                    # Store the task as solved
                    task_id = data["args"]["task_id"]
                    solution = data["args"]["solution"]
                    # worker = task_id.worker WRONG!!! task_id not have worker!

                    self.wtManager.finish_task(task_id, solution) 

                    validations = task_id.end - task_id.start
                    # # update flooding stats
                    # worker.validations += validations
                    self.pending_stats["all"]["uncommitted_validations"] += validations
                    self.logger.critical(f"Increment validations on worker {worker.worker_address}.")


            # I will send the confirmation only when I receive the result from all ALIVE nodes 
            if len(self.wtManager.get_alive_workers()) > 0 and self.pending_stats["numberOfResults"] >= len(self.wtManager.get_alive_workers()):
                # update the stats with the pending stats
                self.updateSumStats("solved")
                self.updateSumStats("invalid")
                self.updateSumStats("validations")                 
                
                # broadcast the confirmation
                for worker in self.wtManager.get_alive_workers():
                    msg = P2PProtocol.flooding_confirmation(self.p2p_server.replyAddress, self.stats.copy())
                    self.send_msg(worker, msg)
                
                # setup for the next round
                self.pending_stats = {  
                    "numberOfResults": 0,
                    "all": {
                        "solved": self.stats["all"]["solved"], "internal_solved": 0, "external_solved": 0, "uncommitted_solved": self.pending_stats["all"]["uncommitted_solved"],
                        "invalid": self.stats["all"]["invalid"], "internal_invalid": 0, "external_invalid": 0, "uncommitted_invalid": self.pending_stats["all"]["uncommitted_invalid"],
                        "validations": self.stats["all"]["validations"], "internal_validations": 0, "external_validations": 0, "uncommitted_validations": self.pending_stats["all"]["uncommitted_validations"] # TODO: remove validations and use sum of nodes validations
                    },
                    "nodes": [
                        # { "address": "host:port", "validations": 0, "internal_validations": 0, "external_validations": 0, "uncommitted_validations": 0}, ..
                    ]
                }            

            if not self.isHandlingHTTP:
                continue
            
            # Manage tasks assignments and timeouts (if any)    
            
            # check if completed
            if self.wtManager.isDone():
                self.isHandlingHTTP = False
                if len(self.wtManager.solutionsDict) > 0:
                    # TODO: must select the client to send the response (for now only one client is supported)
                    solution = self.wtManager.solutionsDict.popitem()[1] # the first element is the sudoku_id solved!
                    self.logger.info(f"HTTP: Task done! {solution}")
                    self.http_server.response_queue.put(solution)
                    self.pending_stats["all"]["uncommitted_solved"] += 1
                else:    
                    self.http_server.response_queue.put(None)
                    self.logger.debug("HTTP: Task done! [No solution]")
                    self.pending_stats["all"]["uncommitted_invalid"] += 1
            else:
            # manage tasks assignments and timeouts
                retry_tasks = self.wtManager.checkTasksTimeouts() # tasks to retry, the timeout ones were all in the pending queue!

                # Retry tasks
                for task in retry_tasks:
                    # build the tasks again
                    sudoku = self.wtManager.get_sudoku(task.task_id)
                    msg = P2PProtocol.solve_request(self.p2p_server.replyAddress, task.task_id, sudoku)
                    
                    # send the tasks to the worker
                    self.send_msg(task.worker, msg)
                    self.logger.warning(f"P2P: Retrying task to {task.worker.worker_address} [{task.worker.task_response_time}]")
     
                tasks_to_send = self.wtManager.get_tasks_to_send() # tasks to work, with the best workers

                # Send tasks
                for task in tasks_to_send:
                    # build the tasks
                    sudoku = self.wtManager.get_sudoku(task.task_id)
                    msg = P2PProtocol.solve_request(self.p2p_server.replyAddress, task.task_id, sudoku)

                    # send the tasks to the worker
                    self.send_msg(task.worker, msg)
                    self.logger.debug(f"P2P: Assigning task {task.task_id} to {task.worker.worker_address} [{task.worker.task_response_time}]")


                    