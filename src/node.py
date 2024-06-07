import selectors, time, socket, queue, pickle, sys
from threading import Lock
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
            }
        }

        
        self.network = {}
        
        self.isHandlingHTTP = False

        self.handicap = handicap

        self.last_flooding = time.time()
        self.TIME_TO_FLOODING = 3 # in seconds

        self.http_server = HTTPServer(self.logger, host, http_port, self.stats, self.network, max_threads)
        self.p2p_server = P2PServer(self.logger, host, p2p_port)
        self.internal_solved_queue = queue.Queue() # 
        self.solving_locker = Lock()

        # Workers & Tasks Manager (load balancer)
        self.wtManager = WTManager(self.logger)
        self.myWork = self.wtManager.add_worker(self.p2p_server.replyAddress, socket=None) # add itself as a worker
        self.myWork.Alive = False           # it is not alive, it is the node itself!
        self.myWork.smoothing_factor = 0.9 # TODO: !!!
        self.myWork.task_done()

        self.solverConfig = SudokuAlgorithm(logger= self.logger, handicap = self.handicap)
    

    def connectWorker(self, host_port) -> Worker:
        """Connect to a peer."""
        try:
            self.logger.debug(f"Connecting to {host_port}")

            # create a socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host_port.split(":")[0], int(host_port.split(":")[1])))
            sock.setblocking(False)

            # get worker
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

    def updateSumStats(self):
        """Update Stats."""
        isChanged = False
        for baseName in ["solved", "invalid"]:
            new_value = self.pending_stats["all"][baseName] + self.pending_stats["all"]["internal_"+baseName] + self.pending_stats["all"]["external_"+baseName]
            if new_value != self.stats["all"][baseName]:
                self.stats["all"][baseName] = new_value
                isChanged = True

        for worker in self.wtManager.workersDict.values():
            new_value = worker.pending_stats["validations"] + worker.pending_stats["internal_validations"] + worker.pending_stats["external_validations"]
            if new_value != worker.stats["validations"]:
                worker.stats["validations"] = new_value
                isChanged = True

        return isChanged        
        # TODO: herself stats

    def commitPendingStats(self):
        """Commit Pending Stats."""
        
        for baseName in ["solved", "invalid"]:
            self.pending_stats["all"]["internal_"+baseName] = self.pending_stats["all"]["uncommitted_"+baseName]
            self.pending_stats["all"]["uncommitted_"+baseName] = 0

        for worker in self.wtManager.workersDict.values():
            worker.pending_stats["internal_validations"] = worker.pending_stats["uncommitted_validations"]
            worker.pending_stats["uncommitted_validations"] = 0
        # TODO: herself stats

    def updateWithReceivedStats(self, stats):
        """Update Stats with Received Stats."""
        
        for baseName in ["solved", "invalid"]:
            myBaseValue = self.pending_stats["all"][baseName] # from pending stats
            baseValueReceived = stats["all"][baseName]
            incrementedValueReceived = stats["all"]["internal_"+baseName]

            if baseValueReceived > myBaseValue:
                self.pending_stats["all"][baseName] = baseValueReceived
                self.pending_stats["all"]["internal_"+baseName] = 0
                self.pending_stats["all"]["external_"+baseName] = incrementedValueReceived
                self.pending_stats["numberOfResults"] = -1
            elif baseValueReceived == myBaseValue:                
                self.pending_stats["all"]["external_"+baseName] += incrementedValueReceived 
        
        for st_info in stats["nodes"]:
            host_port = st_info["address"]
            
            worker = self.wtManager.workersDict.get(host_port)
            if worker is None:
                worker = self.wtManager.add_worker(host_port, socket=None) # not connected yet. Is dead with high probability!
                worker.Alive = False

            myWorkerBaseValue = worker.pending_stats["validations"]
            baseValueReceived = st_info["validations"]
            incrementedValueReceived = st_info["internal_validations"]

            if baseValueReceived > myWorkerBaseValue:
                worker.pending_stats["validations"] = baseValueReceived
                worker.pending_stats["internal_validations"] = 0
                worker.pending_stats["external_validations"] = incrementedValueReceived   
                self.pending_stats["numberOfResults"] = -1 
            elif baseValueReceived == myWorkerBaseValue:
                worker.pending_stats["external_validations"] += incrementedValueReceived

        # TODO: herself stats

        self.pending_stats["numberOfResults"] += 1 # In case of `-1` the value will be 0, otherwise it will be incremented
        
    def updateWithConfirmedStats(self, stats, host_port): 
        """Update Stats with Confirmed Stats."""
        for baseName in ["solved", "invalid"]:
            myBaseValue = self.pending_stats["all"][baseName] + self.pending_stats["all"]["internal_"+baseName] + self.pending_stats["all"]["external_"+baseName]
            baseValueReceived = stats["all"][baseName]
            self.stats["all"][baseName] = myBaseValue

            if baseValueReceived > myBaseValue:
                self.stats["all"][baseName] = baseValueReceived
                self.logger.critical(f"Update {baseName} to [{self.stats['all'][baseName]}].")
            elif baseValueReceived < myBaseValue:
                self.logger.critical(f"Discard {baseName} [{baseValueReceived}] from {host_port}.") # TODO: remove # host_port is only for logging!

            self.pending_stats["all"][baseName] = self.stats["all"][baseName]
            self.pending_stats["all"]["internal_"+baseName] = 0
            self.pending_stats["all"]["external_"+baseName] = 0 # Not update uncommitted.
            self.pending_stats["all"]["numberOfResults"] = 0

        for st_info in stats["nodes"]:
            host_port = st_info["address"]
            
            worker = self.wtManager.workersDict.get(host_port)
            if worker is None:
                worker = self.wtManager.add_worker(host_port, socket=None)

            myWorkerBaseValue = worker.pending_stats["validations"] + worker.pending_stats["internal_validations"] + worker.pending_stats["external_validations"]
            baseValueReceived = st_info["validations"]
            worker.stats["validations"] = myWorkerBaseValue

            if baseValueReceived > myWorkerBaseValue:
                worker.stats["validations"] = baseValueReceived
                self.logger.critical(f"Update validations to [{worker.stats['validations']}].")
            elif baseValueReceived < myWorkerBaseValue:
                self.logger.critical(f"Discard validations [{baseValueReceived}] from {host_port}.") # TODO: remove 

            worker.pending_stats["validations"] = worker.stats["validations"]
            worker.pending_stats["internal_validations"] = 0
            worker.pending_stats["external_validations"] = 0 # Not update uncommitted.
            worker.pending_stats["numberOfResults"] = 0

        # TODO: herself stats

    def getWorkerStats(self):
        """Get worker stats."""
        return list(map(lambda worker: {"address": worker.worker_address, "validations": worker.pending_stats["validations"], "internal_validations": worker.pending_stats["internal_validations"]}, self.wtManager.workersDict.values()))

    def updateNetwork(self):
        """Update network dict."""
        self.network.clear()
        for worker in self.wtManager.get_alive_workers():
            self.network[worker.worker_address] = worker.network


    def updateWorkersStats(self):
        """Update workers stats."""
        workers_stats = []
        total_validations = 0
        for worker in self.wtManager.workersDict.values():
            workers_stats.append(worker.stats)
            total_validations += worker.stats["validations"]
        self.stats["nodes"] = sorted(workers_stats, key=lambda x: x["validations"], reverse=True)
        self.stats["all"]["validations"] = total_validations
        # TODO: herself stats

    def isAlone(self):
        """Check if the node is alone."""
        return len(self.wtManager.get_alive_workers()) == 0

    def doTasksInDispatcher(self):
        """Do tasks in dispatcher."""

        if self.p2p_server.request_queue.empty and self.wtManager.has_tasks():
            max_factor = 0.5
            task_size_factor = max_factor
 
            p2p_time = self.p2p_server.get_average_request()/200
            if p2p_time <= max_factor:
                task_size_factor = p2p_time

            self.myWork.task_size_factor = task_size_factor
            
            # self.logger.warning(self.p2p_server.get_average_request())
            task = self.wtManager.get_task_to_worker(self.myWork)
            task_id = task.task_id

            self.wtManager.working_tasks[task_id] = task # only for updates

            # Create SudokuJob object
            sudoku_job = SudokuJob(self.wtManager.current_sudoku.sudoku, task_id.start, task_id.end, self.solverConfig)
            
            # Execute the task using SudokuJob
            solution = sudoku_job.solve()

            if solution is not None:
                self.logger.info(f"Sudoku is valid. [by Dispatcher]")


            self.wtManager.finish_task(task_id, solution) 

            validations = task_id.end - task_id.start # update flooding stats
            self.myWork.pending_stats["uncommitted_validations"] += validations

    def setupNextRound(self):  
        self.pending_stats = {  
            "numberOfResults": 0,
            "all": {
                "solved": self.stats["all"]["solved"], "internal_solved": 0, "external_solved": 0, "uncommitted_solved": self.pending_stats["all"]["uncommitted_solved"],
                "invalid": self.stats["all"]["invalid"], "internal_invalid": 0, "external_invalid": 0, "uncommitted_invalid": self.pending_stats["all"]["uncommitted_invalid"]
            }
        }    
        for worker in self.wtManager.workersDict.values():
            worker.pending_stats = {
                "validations": worker.stats["validations"], "internal_validations": 0, "external_validations": 0, "uncommitted_validations": worker.pending_stats["uncommitted_validations"]
            } 


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
                # TODO: kill the node! Also when CTRL-C this must kill the node...
                    

######### Main loop
        while True:
            if self.isToSendFlooding():
                # commit the pending stats and define uncommitted as 0
                self.commitPendingStats()
                
                for worker in self.wtManager.get_alive_workers():
                    self.logger.debug(f"P2P: Sending flooding consensus to {worker.worker_address}.")
                    worker_stats = self.getWorkerStats()
                    msg = P2PProtocol.flooding_hello(self.p2p_server.replyAddress, list(self.wtManager.get_alive_workers_address()), self.pending_stats.copy(), worker_stats)
                    self.send_msg(worker, msg)
                self.last_flooding = time.time()

                self.updateWorkersStats()
                self.updateNetwork()

            self.wtManager.checkWorkersFloodingTimeouts() # kill inactive workers (if any)   

            # get solved sudokus (if any)
            try:
                solved_reply = self.internal_solved_queue.get(block=False)
            except queue.Empty:
                solved_reply = None

            # get http request (if any)
            try:
                http_request = self.http_server.request_queue.get(block=False)
                if http_request is not None: 
                    self.logger.debug(f"HTTP: Requested {http_request} tasks.")
                    # self.myWork.task_response_time = 0.1 # TODO: check this
            except queue.Empty:
                http_request = None

            # get p2p request (if any)
            try:
                p2p_request = self.p2p_server.request_queue.get(block=False)  
            except queue.Empty:
                p2p_request = None 
            

            # Handle reply solved sudokus requests (if any)
            if solved_reply is not None:
                task_id = solved_reply["task_id"]
                host_port = solved_reply["replyAddress"]
                solution = solved_reply["solution"]

                worker = self.wtManager.workersDict.get(host_port)

                if solution is not "INVALID":
                    self.logger.debug(f"Sudoku is valid.")
                    msg = P2PProtocol.solve_reply(self.p2p_server.replyAddress, task_id, solution)
                else:
                    self.logger.debug(f"Sudoku is invalid.")
                    msg = P2PProtocol.solve_reply(self.p2p_server.replyAddress, task_id)    
                
                # Send the reply
                self.send_msg(worker, msg)

            # Handle http requests (if any)
            if http_request is not None:
                self.logger.debug(f"HTTP: Requested {http_request} tasks.")
                self.isHandlingHTTP = True

                sudoku = http_request
                print(sudoku)
                self.wtManager.add_pending_task(sudoku)                  
      
            # Handle p2p requests (if any)     
            if p2p_request is not None:
                self.p2p_server.update_average_request()
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

                        self.wtManager.update_worker_flooding(worker)

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

                    self.updateWithReceivedStats(stats)

                elif data["command"] == "FLOODING_CONFIRMATION":
                    # update baseValue if someone has a higher value (or higher round)
                    host_port = data["replyAddress"]
                    stats = data["args"]["stats"]
                   
                    # host_port is only for logging!
                    self.updateWithConfirmedStats(stats, host_port)

                elif data["command"] == "JOIN_REQUEST":
                    host_port = data["replyAddress"]

                    worker = self.connectWorker(host_port)
                    self.wtManager.kill_worker(host_port, close_socket=False) # kill the worker if it is already connected
                    worker.flooding_received() # if the worker is not new it is a reconnection!
                    # worker.task_done() # TODO: check this

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

                        if worker is not None:
                            worker_stats = self.getWorkerStats() # normally this stats are all zeros...
                            msg = P2PProtocol.flooding_hello(self.p2p_server.replyAddress, aliveNodes, self.pending_stats.copy(), worker_stats)
                            self.send_msg(worker, msg)

                elif data["command"] == "SOLVE_REQUEST":                    
                    task_id = data["args"]["task_id"]
                    sudoku = data["args"]["sudoku"]
                    host_port = data["replyAddress"]
                    
                    self.logger.critical(f"Task {task_id} received from {host_port}.")
                    start, end = task_id.get_start_end()
        
                    # Create SudokuJob object
                    sudoku_job = SudokuJob(sudoku, start, end, self.solverConfig)
                    
                    # Execute the task using SudokuJob
                    solution = sudoku_job.run(self.solving_locker, self.internal_solved_queue, task_id, host_port)

                    # worker = self.wtManager.workersDict.get(host_port)

                    # if solution is not None:
                    #     self.logger.debug(f"Sudoku is valid.")
                    #     msg = P2PProtocol.solve_reply(self.p2p_server.replyAddress, task_id, solution)
                    # else:
                    #     self.logger.debug(f"Sudoku is invalid.")
                    #     msg = P2PProtocol.solve_reply(self.p2p_server.replyAddress, task_id)    
                    
                    # # Send the reply
                    # self.send_msg(worker, msg)
                    
                elif data["command"] == "SOLVE_REPLY":
                    # Store the task as solved
                    task_id = data["args"]["task_id"]
                    solution = data["args"]["solution"]
                    host_port = data["replyAddress"]
                    worker = self.wtManager.workersDict.get(host_port)

                    self.wtManager.finish_task(task_id, solution) 

                    validations = task_id.end - task_id.start
                    # # update flooding stats
                    worker.pending_stats["uncommitted_validations"] += validations
                    self.logger.critical(f"Increment validations on worker {worker.worker_address}.")


            # I will send the confirmation only when I receive the result from all ALIVE nodes 
            if (len(self.wtManager.get_alive_workers()) > 0 and self.pending_stats["numberOfResults"] >= len(self.wtManager.get_alive_workers())):
                # update the stats with the pending stats
                isChanged = self.updateSumStats()  

                if isChanged:
                    self.logger.warning(f"[{self.stats['all']['solved']}, {self.stats['all']['invalid']}, {self.stats['all']['validations'] }]")

                # broadcast the confirmation
                for worker in self.wtManager.get_alive_workers():
                    msg = P2PProtocol.flooding_confirmation(self.p2p_server.replyAddress, self.stats.copy())
                    self.send_msg(worker, msg)
                
                # setup for the next round
                self.setupNextRound()
                self.updateWorkersStats()
            elif self.isAlone():
                # update the stats with the pending stats
                isChanged = self.updateSumStats()
                if isChanged:
                    self.logger.warning(f"[{self.stats['all']['solved']}, {self.stats['all']['invalid']}, {self.stats['all']['validations'] }]")
                # setup for the next round
                self.setupNextRound()
                self.updateWorkersStats()


            if not self.isHandlingHTTP:
                continue
            
            # Manage tasks assignments and timeouts (if any)    
            
            # check if completed
            if self.wtManager.isDone():
                self.isHandlingHTTP = False
                if self.wtManager.current_sudoku.solution is not None:
                    # TODO: must select the client to send the response (for now only one client is supported)
                    solution = self.wtManager.current_sudoku.solution 
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
                    sudoku = self.wtManager.current_sudoku.sudoku
                    msg = P2PProtocol.solve_request(self.p2p_server.replyAddress, task.task_id, sudoku)
                    
                    # send the tasks to the worker
                    self.send_msg(task.worker, msg)
                    self.logger.warning(f"P2P: Retrying task to {task.worker.worker_address} [{task.worker.task_response_time}]")
     
                tasks_to_send = self.wtManager.get_tasks_to_send() # tasks to work, with the best workers

                # Send tasks
                for task in tasks_to_send:
                    # build the tasks
                    sudoku = self.wtManager.current_sudoku.sudoku
                    msg = P2PProtocol.solve_request(self.p2p_server.replyAddress, task.task_id, sudoku)

                    # send the tasks to the worker
                    self.send_msg(task.worker, msg)
                    self.logger.debug(f"P2P: Assigning task {task.task_id} to {task.worker.worker_address} [{task.worker.task_response_time},{task.worker.task_size}]")


                # Do some tasks (if any)
                self.doTasksInDispatcher()