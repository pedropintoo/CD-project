import time
from typing import Dict, List, Tuple, NamedTuple, Deque
from socket import socket

class Worker:
    def __init__(self, host_port: str, socket: socket, smoothing_factor: float = 0.50, task_size_factor: float = 0.75):
        self.worker_address = host_port
        self.network = {}
        self.socket = socket

        # stats
        self.stats = {"address": host_port, "validations": 0}
        self.pending_stats = {"address": host_port, "validations": 0, "internal_validations": 0, "external_validations": 0, "uncommitted_validations": 0}

        # availability
        self.Alive = True       # false when worker is dead ( it means that the worker is not responding or socket was closed )
        self.isAvailable = True # false when worker is working

        # flooding response time
        self.last_flooding_received = time.time()

        # task response time
        self.last_task_sended = time.time()
        self.task_response_time = 10.0   # Exponential Moving Average response time

        # response time factor
        self.smoothing_factor = smoothing_factor

        # worker task size
        self.task_size = 1000
        self.task_size_factor = task_size_factor

    def start_task(self):
        """Worker start a task."""
        self.isAvailable = False
        self.last_task_sended = time.time()

    def flooding_received(self):  
        """Worker give signs of aliveness.""" 
        self.Alive = True
        print(f"Worker {self.worker_address} is alive. {self.task_response_time}")
        self.last_flooding_received = time.time()

    def task_done(self):  
        """Worker give signs of aliveness.""" 
        self.isAvailable = True
        self.update_task_response_time()

    def update_task_response_time(self):
        """Update the task response time given a new response."""
        elapsed_time = time.time() - self.last_task_sended
        self.last_task_sended = time.time()
        self.task_response_time = (self.smoothing_factor * elapsed_time +
                                    (1 - self.smoothing_factor) * self.task_response_time)
        
        if self.task_size == 0:
            self.task_size = 1 

        # limit task_response_time to task_size_factor with task_size
        self.task_size = int(self.task_size * (self.task_size_factor / self.task_response_time))
        # print(f"TASK : {self.task_size}, {self.task_size_factor} {self.task_response_time}")

    def isFloodingTimeout(self):
        if self.Alive == False:
            return True

        # Recalculate
        elapsed_time = time.time() - self.last_flooding_received
        if elapsed_time > 6: # TODO: thing about this limit value (and others...)
            self.Alive = False

        return not self.Alive
    
    def isTaskTimeout(self):
        elapsed_time = time.time() - self.last_task_sended
        return elapsed_time > 100 * self.task_response_time

    def crash(self):
        """Crash the worker"""
        self.Alive = False
        self.isAvailable = True # for future reconnection
        self.update_task_response_time()

class TaskID(NamedTuple):
    sudoku_id: int
    start: int
    end: int

    def __str__(self):
        return f"{self.sudoku_id}[{self.start}-{self.end}]"

    def parse(task_id: str):
        """Parse a task id from a string."""
        sudoku_id, start, end = task_id.split("[")[0], task_id.split("[")[1].split("-")[0], task_id.split("-")[1][:-1] # remove the last char ']'
        return TaskID(sudoku_id, int(start), int(end))

    def get_start_end(self):
        return self.start, self.end

class Task:
    def __init__(self, task_id: TaskID, worker: Worker, tries_limit: int = 1):
        self.task_id = task_id
        
        self.worker = worker
        worker.start_task()
        
        # Limit retries of the task
        self.tries = 0
        self.tries_limit = tries_limit

    def has_timed_out(self) -> bool:
        """Check if the task has exceeded its time limit."""
        return not self.worker.Alive or self.worker.isTaskTimeout()

    def has_exceeded_tries(self) -> bool:
        """Check if the task has exceeded its retry limit."""
        return self.tries >= self.tries_limit

    def retry(self):
        """Increment the number of tries."""
        self.tries += 1

# Dynamic Splitter of Sudoku
class SudokuDynamicSplitter:
    def __init__(self, sudoku: str, sudoku_id: int):
        self.sudoku = sudoku
        self.sudoku_id = sudoku_id
        self.solution = None
        
        _emptyCells = self._count_zeros(sudoku)
        if _emptyCells == 0:
            self.start = 0
            self.end = 0
            self.solution = sudoku
        else:
            self.start = int(_emptyCells * '1')
            self.end = int("1" + _emptyCells * '0')

    def get_splitted_task_id(self, task_size: int) -> TaskID:
        """Get a task of a given size."""
        if self.start + task_size <= self.end:
            task_range_start = self.start
            self.start += task_size
            return TaskID(self.sudoku_id, task_range_start, self.start)
        
        task = TaskID(self.sudoku_id, self.start, self.end)
        self.start = self.end
        return task

    def _count_zeros(self, matrix) -> int:
        count = 0
        for row in matrix:
            for element in row:
                if element == 0:
                    count += 1
        return count

    def has_tasks(self) -> bool:
        return self.start < self.end    

# Workers & Tasks Manager (load balancer)
class WTManager:
    def __init__(self, logger):
        # workers manager
        self.workersDict: Dict[str, Worker] = {}

        self.sudoku_id = 0
        self.current_sudoku : SudokuDynamicSplitter = None

        # tasks manager
        self.pending_tasks_queue: List[TaskID] = [] # TaskID, ..
        self.working_tasks: Dict[TaskID, Task] = {} # TaskID -> Task

        self.logger = logger  

    def get_task_to_worker(self, worker: Worker) -> Task:
        """Get the task to assign to a worker."""
        task_size = worker.task_size
        
        if self.current_sudoku.has_tasks():
            task_id = self.current_sudoku.get_splitted_task_id(task_size)
            return Task(task_id, worker)

        task_id = self.pending_tasks_queue[0]
        if task_id.end - task_id.start <= task_size:
            # this task was abandoned by another worker
            self.pending_tasks_queue.remove(task_id)
            return Task(task_id, worker) 
        else:
            task_id = self.pending_tasks_queue.pop(0)
            
            new_task_id = TaskID(task_id.sudoku_id, task_id.start, task_id.start + task_size)
            old_task_id = TaskID(task_id.sudoku_id, task_id.start + task_size, task_id.end)
            self.pending_tasks_queue.insert(0, old_task_id)
            return Task(new_task_id, worker)


    def update_worker_flooding(self, worker):
        """Update the worker flooding time."""
        worker.flooding_received()
        isWorking = False
        if worker.isAvailable == False:
            for task in self.working_tasks.values():
                if task.worker == worker:
                    isWorking = True
            if not isWorking:
                worker.task_done() 
                self.logger.info("UPDATE WORKER FLOODING: Worker is available again.") # with low probability!       

    def add_pending_task(self, sudoku: str):
        """Add a task to the pending queue."""
        
        self.sudoku_id += 1 
        self.current_sudoku = SudokuDynamicSplitter(sudoku, self.sudoku_id)

    def add_worker(self, host_port: str, socket: socket) -> Worker:
        """Create and add a worker to the workers list."""
        worker = Worker(host_port, socket)
        self.workersDict[host_port] = worker
        return worker

    def finish_task(self, task_id: TaskID, solution: str = None):
        """Remove a task from the working list."""
        task = self.working_tasks.get(task_id)
        if task is not None:
            task.worker.task_done()
            del self.working_tasks[task_id]
        else:
            try:
                if task_id in self.pending_tasks_queue:
                    self.pending_tasks_queue.remove(task_id) # the responser is a dead worker
            except ValueError:
                pass # the task was already done

        if solution is not None:
            self.current_sudoku.solution = solution
            
            # remove the sudoku from other workers 
            working_copy = self.working_tasks.copy()
            for t in working_copy.keys():
                if t.sudoku_id == task_id.sudoku_id:
                    self.working_tasks[t].worker.task_done() # worker is available again
                    del self.working_tasks[t]    
            
            pending_copy = self.pending_tasks_queue.copy()
            for t in pending_copy:
                if t.sudoku_id == task_id.sudoku_id:
                    self.pending_tasks_queue.remove(t)    

    def isDone(self) -> bool:
        """Check if all tasks are done."""
        return self.current_sudoku.solution is not None or (not self.current_sudoku.has_tasks() and not self.has_pending_tasks() and not self.has_working_tasks())

    def has_pending_tasks(self) -> bool:
        """Check if there are pending tasks."""
        return len(self.pending_tasks_queue) > 0

    def has_working_tasks(self) -> bool:
        """Check if there are working tasks."""
        return len(self.working_tasks) > 0

    def has_tasks(self) -> bool:
        """Check if there are tasks available."""
        return (self.has_pending_tasks() or self.current_sudoku.has_tasks())

    def kill_worker(self, host_port: str, close_socket = True):
        """Kill a worker."""
        worker = self.workersDict.get(host_port)
        worker.crash()

        # close the socket if connection to worker fail!
        if close_socket:
            worker.socket.close()
            worker.socket = None
        
        # unsign every task of the dead worker
        tasks_copy = list(self.working_tasks.values()).copy() # must be a copy because we are deleting elements!
        for task in tasks_copy:
            if task.worker == worker:
                self.unassign_task(task) 

    def unassign_task(self, task: Task):
        """Remove a task from the working list and add it back to the pending queue."""
        self.pending_tasks_queue.append(task.task_id)
        task.worker.crash()
        del self.working_tasks[task.task_id]

    def get_ready_workers(self) -> List[Worker]:
        """Get the list of ready workers."""
        return [worker for worker in self.workersDict.values() if worker.isAvailable and worker.Alive]

    def get_alive_workers(self) -> List[Worker]:
        """Get the list of alive workers."""
        return [worker for worker in self.workersDict.values() if worker.Alive]
    
    def get_alive_workers_address(self) -> List[str]:
        """Get the list of alive workers addresses."""
        return [worker.worker_address for worker in self.get_alive_workers()]

    def checkWorkersFloodingTimeouts(self):
        """Check for workers that have timed out."""
        for worker in self.get_alive_workers():
            if worker.isFloodingTimeout():
                # we do not kill the socket! we just mark the worker as dead
                self.logger.warning(f"Worker {worker.worker_address} is sleeping. [Flooding Timeout]")
                self.kill_worker(worker.worker_address, close_socket=False)

    def checkTasksTimeouts(self) -> list[Task]:
        """Check for tasks that have timed out and handle retries."""        
        # tasks to retry
        retry_tasks = []
        tasks_copy = list(self.working_tasks.values()).copy() # must be a copy because we are deleting elements!
        for task in tasks_copy:
            if task.has_timed_out():
                if task.has_exceeded_tries():
                    self.logger.warning(f"Task {task.task_id} has timed out. [Exceeded Retries]")
                    # task expired
                    self.kill_worker(task.worker)
                else:
                    retry_tasks.append(task) # client must retry !!
                    task.retry()

        return retry_tasks   

    def get_best_worker(self) -> Worker:
        """Get the worker with the lowest task response time."""
        best_worker = None
        for worker in self.get_ready_workers():
            if best_worker is None or worker.task_response_time < best_worker.task_response_time:
                best_worker = worker
        return best_worker

    def get_tasks_to_send(self) -> List[Task]:
        """Get new tasks with associated workers."""
        new_work_tasks = []

        worker = self.get_best_worker() # if None: no workers available
        
        while self.has_tasks() and worker is not None:
            task = self.get_task_to_worker(worker) # from pending tasks or sudoku queue (splitted task)
            task_id = task.task_id

            self.working_tasks[task_id] = task
            new_work_tasks.append(task)

            worker = self.get_best_worker() # get the next best worker

        return new_work_tasks


    

        


