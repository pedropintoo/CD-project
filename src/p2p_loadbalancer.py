import time
from typing import Dict, List
from socket import socket

class Worker:
    def __init__(self, host_port: str, socket: socket, smoothing_factor: float = 0.50):
        self.worker_address = host_port
        self.socket = socket

        # availability
        self.last_signal = time.time()
        self.Alive = True
        self.isAvailable = True
        self.isTheFirstResponse = True

        # response time
        self.ema_response_time = 10.0  # Exponential Moving Average response time TODO: this initial value is arbitrary!
        self.smoothing_factor = smoothing_factor # TODO: increase when worker gets older (more stable)


    def update_ema_response_time(self, response_time: float):
        """Update the EMA response time given a new response time."""
        if self.isTheFirstResponse:
            self.ema_response_time = response_time
            self.isTheFirstResponse = False
        else:
            self.ema_response_time = (self.smoothing_factor * response_time +
                                      (1 - self.smoothing_factor) * self.ema_response_time)

    def alive_signal(self):  
        """Worker give signs of aliveness.""" 
        self.Alive = True
        self.last_signal = time.time()

    def isAlive(self):
        if self.Alive == False:
            return False

        # Recalculate
        now = time.time()
        elapsed_time = (now - self.last_signal)
        if elapsed_time > 10: # TODO: thing about this limit value
            self.Alive = False
        
        return self.Alive
    
    def crash(self):
        """Crash the worker -> worker is not alive."""
        self.Alive = False
        self.isAvailable = True # for future reconnection



class Task:
    def __init__(self, task_id: int, worker: Worker, tries_limit: int = 1):
        self.task_id = task_id
        self.worker = worker
        worker.isAvailable = False
        self.start_time = time.time()
        self.tries = 0
        
        # Limit parameters
        self.tries_limit = tries_limit

    def has_timed_out(self) -> bool:
        """Check if the task has exceeded its time limit."""
        return time.time() - self.start_time > (self.worker.ema_response_time*2)

    def has_exceeded_tries(self) -> bool:
        """Check if the task has exceeded its retry limit."""
        return self.tries >= self.tries_limit

    def retry(self):
        """Increment the number of tries and reset the start time."""
        self.tries += 1
        now = time.time()
        #self.worker.update_ema_response_time( now - self.start_time )
        self.start_time = now   
        
    def end(self):
        """End the task."""
        self.worker.isAvailable = True
        now = time.time()
        self.worker.update_ema_response_time( now - self.start_time )


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
            task.end() # update worker
            del self.working_tasks[task_id]
        else:
            try:
                self.pending_tasks_queue.remove(task_id) # the responser is a dead worker TODO: actualize the worker!!!
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

    def kill_worker(self, host_port: str):
        """Kill a worker."""
        worker = self.workersDict.get(host_port)
        worker.crash()
        if worker.socket is not None:
            worker.socket.close()
        worker.socket = None
        
        tasks = list(self.working_tasks.values()).copy()
        for task in tasks:
            if task.worker == worker:
                self.unassign_task(task)

    def unassign_task(self, task: Task):
        """Remove a task from the working list and add it back to the pending queue."""
        self.pending_tasks_queue.append(task.task_id)
        del self.working_tasks[task.task_id]

    def get_alive_workers(self) -> List[Worker]:
        """Get the list of alive workers."""
        return [worker for worker in self.workersDict.values() if worker.Alive]
    
    def get_alive_workers_address(self) -> List[str]:
        """Get the list of alive workers addresses."""
        return [worker.worker_address for worker in self.get_alive_workers()]

    def checkWorkersTimeouts(self):
        """Check for workers that not make signal of aliveness and handle retries."""
        for worker in self.get_alive_workers():
            if not worker.isAlive() and not worker.socket is not None:
                self.kill_worker(worker.worker_address)

    def checkTasksTimeouts(self) -> list[Task]:
        """Check for tasks that have timed out and handle retries."""        
        # tasks
        timeout_tasks = []
        for task in list(self.working_tasks.values()):
            if task.has_timed_out():
                if task.has_exceeded_tries():
                    # task expired
                    self.unassign_task(task) # add to pending queue
                else:
                    timeout_tasks.append(task) # client must retry !!

        return timeout_tasks   

    def get_best_worker(self) -> Worker:
        """Get the worker with the lowest EMA response time."""
        best_worker = None
        for worker in self.get_alive_workers():
            if worker.isAvailable and (best_worker is None or worker.ema_response_time < best_worker.ema_response_time):
                best_worker = worker
        return best_worker

    def get_tasks_to_work(self) -> List[Task]:
        """Get new tasks with associated workers."""
        new_tasks = []
        pending = self.pending_tasks_queue.copy()
        for task_id in pending:
            worker = self.get_best_worker()
            if worker is not None:
                task = Task(task_id, worker)
                new_tasks.append(task)
                self.working_tasks[task_id] = task
                self.pending_tasks_queue.remove(task_id)
            else:
                break

        return new_tasks



    

        


