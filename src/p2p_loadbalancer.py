import time
from typing import Dict, List
from socket import socket

class Worker:
    def __init__(self, host_port: str, socket: socket, smoothing_factor: float = 0.50):
        self.worker_address = host_port
        self.socket = socket

        # availability
        self.Alive = True       # false when worker is dead ( it means that the worker is not responding or socket was closed )
        self.isAvailable = True # false when worker is working

        # hello response time
        self.isFirstHello = True
        self.last_hello_received = time.time()
        self.hello_response_time = 10.0  # Exponential Moving Average response time 

        # task response time
        self.isFirstTask = True
        self.last_task_sended = time.time()
        self.task_response_time = 10.0   # Exponential Moving Average response time

        # response time factor
        self.smoothing_factor = smoothing_factor # TODO: increase when worker gets older (more stable)

    def start_task(self):
        """Worker start a task."""
        self.isAvailable = False
        self.last_task_sended = time.time()

    def hello_received(self):  
        """Worker give signs of aliveness.""" 
        self.Alive = True
        self.update_hello_response_time()

    def task_done(self):  
        """Worker give signs of aliveness.""" 
        self.isAvailable = True
        self.update_task_response_time()

    def update_hello_response_time(self):
        """Update the hello response time given a new response."""
        elapsed_time = time.time() - self.last_hello_received
        if self.isFirstHello:
            self.hello_response_time = elapsed_time
            self.isFirstHello = False
        else:
            self.hello_response_time = (self.smoothing_factor * elapsed_time +
                                      (1 - self.smoothing_factor) * self.hello_response_time)
    
    def update_task_response_time(self):
        """Update the task response time given a new response."""
        elapsed_time = time.time() - self.last_hello_received
        if self.isFirstTask:
            self.task_response_time = elapsed_time
            self.isFirstTask = False
        else:
            self.task_response_time = (self.smoothing_factor * elapsed_time +
                                      (1 - self.smoothing_factor) * self.task_response_time)

    def checkHelloTimeout(self):
        if self.Alive == False:
            return False

        # Recalculate
        elapsed_time = time.time() - self.last_signal
        if elapsed_time > 5 * self.hello_response_time: # TODO: thing about this limit value
            self.Alive = False
        
        return self.Alive
    
    def checkTaskTimeout(self):
        elapsed_time = time.time() - self.last_task_sended
        return elapsed_time > 2 * self.task_response_time

    def crash(self):
        """Crash the worker"""
        self.Alive = False
        self.isAvailable = True # for future reconnection
        self.last_hello_received = time.time()
        self.last_task_sended = time.time()


class Task:
    def __init__(self, task_id: int, worker: Worker, tries_limit: int = 1):
        self.task_id = task_id
        
        self.worker = worker
        worker.start_task()
        
        # Limit retries of the task
        self.tries = 0
        self.tries_limit = tries_limit

    def has_timed_out(self) -> bool:
        """Check if the task has exceeded its time limit."""
        return not self.worker.Alive or self.worker.checkTaskTimeout()

    def has_exceeded_tries(self) -> bool:
        """Check if the task has exceeded its retry limit."""
        return self.tries >= self.tries_limit

    def retry(self):
        """Increment the number of tries."""
        self.tries += 1


# Workers & Tasks Manager (load balancer)
class WTManager:
    def __init__(self):
        # workers manager
        self.workersDict: Dict[str, Worker] = {}

        # tasks manager
        self.pending_tasks_queue: List[int] = []
        self.working_tasks: Dict[int, Task] = {}

    def add_pending_task(self, task_id: int):
        """Add a task to the pending queue."""
        self.pending_tasks_queue.append(task_id)

    def finish_task(self, task_id: int):
        """Remove a task from the working list."""
        task = self.working_tasks.get(int(task_id)) 
        
        if task is not None:
            task.worker.task_done()
            del self.working_tasks[task_id]
        else:
            try:
                if task_id in self.pending_tasks_queue:
                    self.pending_tasks_queue.remove(task_id) # the responser is a dead worker
            except ValueError:
                pass 

    def isDone(self) -> bool:
        """Check if all tasks are done."""
        return not self.has_pending_tasks() and not self.has_working_tasks()

    def has_pending_tasks(self) -> bool:
        """Check if there are pending tasks."""
        return len(self.pending_tasks_queue) > 0

    def has_working_tasks(self) -> bool:
        """Check if there are working tasks."""
        return len(self.working_tasks) > 0

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

    def checkWorkersHelloTimeouts(self):
        """Check for workers that have timed out."""
        for worker in self.get_alive_workers():
            if not worker.checkAlive():
                # we do not kill the socket! we just mark the worker as dead
                self.kill_worker(worker.worker_address, close_socket=False)

    def checkTasksTimeouts(self) -> list[Task]:
        """Check for tasks that have timed out and handle retries."""        
        # tasks to retry
        retry_tasks = []
        tasks_copy = list(self.working_tasks.values()).copy() # must be a copy because we are deleting elements!
        for task in tasks_copy:
            if task.has_timed_out():
                if task.has_exceeded_tries():
                    # task expired
                    self.unassign_task(task) # add to pending queue
                else:
                    retry_tasks.append(task) # client must retry !!

        return retry_tasks   

    def get_best_worker(self) -> Worker:
        """Get the worker with the lowest EMA response time."""
        best_worker = None
        for worker in self.get_ready_workers():
            if best_worker is None or worker.ema_response_time < best_worker.ema_response_time: # TODO: worker response time! 
                best_worker = worker
        return best_worker

    def get_tasks_to_send(self) -> List[Task]:
        """Get new tasks with associated workers."""
        new_work_tasks = []
        pending = self.pending_tasks_queue.copy()

        worker = self.get_best_worker() # if None: no workers available
        
        while self.has_pending_tasks() and worker is not None:
            task_id = self.pending_tasks_queue.pop(0)
            task = Task(task_id, worker)
            new_work_tasks.append(task)
            self.working_tasks[task_id] = task

        return new_work_tasks



    

        


