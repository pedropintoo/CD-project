import time
from typing import Dict, List
from socket import socket

class Worker:
    def __init__(self, host_port: str, socket: socket, smoothing_factor: float = 0.50):
        self.worker_address = host_port
        self.socket = socket

        # availability
        self.available = True
        self.isTheFirstResponse = True

        # response time
        self.ema_response_time = 0.0  # Exponential Moving Average response time
        self.smoothing_factor = smoothing_factor # TODO: increase when worker gets older (more stable)


    def update_ema_response_time(self, response_time: float):
        """Update the EMA response time given a new response time."""
        if self.isTheFirstResponse:
            self.ema_response_time = response_time
            self.isTheFirstResponse = False
        else:
            self.ema_response_time = (self.smoothing_factor * response_time +
                                      (1 - self.smoothing_factor) * self.ema_response_time)


class Task:
    def __init__(self, task_id: int, worker: Worker, time_limit: int = 10, tries_limit: int = 3):
        self.task_id = task_id
        self.worker = worker
        worker.available = False
        self.start_time = time.time()
        self.tries = 0
        
        # Limit parameters
        self.time_limit = time_limit
        self.tries_limit = tries_limit

    def has_timed_out(self) -> bool:
        """Check if the task has exceeded its time limit."""
        return time.time() - self.start_time > self.time_limit

    def has_exceeded_tries(self) -> bool:
        """Check if the task has exceeded its retry limit."""
        return self.tries >= self.tries_limit

    def retry(self):
        """Increment the number of tries and reset the start time."""
        self.tries += 1
        now = time.time()
        self.worker.update_ema_response_time( now - self.start_time )
        self.start_time = now   
        
    def end(self):
        """End the task."""
        self.worker.available = True
        now = time.time()
        self.worker.update_ema_response_time( now - self.start_time )

# Workers & Tasks Manager (load balancer)
class WTManager:
    def __init__(self):
        # workers manager
        self.socketsDict: Dict[str, socket] = {} # {'host:port': socket}
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

    def isDone(self) -> bool:
        """Check if all tasks are done."""
        return not self.has_pending_tasks() and not self.has_working_tasks()

    def has_pending_tasks(self) -> bool:
        """Check if there are pending tasks."""
        return len(self.pending_tasks_queue) > 0

    def has_working_tasks(self) -> bool:
        """Check if there are working tasks."""
        return len(self.working_tasks) > 0

    def unassign_task(self, task: Task):
        """Remove a task from the working list and add it back to the pending queue."""
        task.end() # update worker
        self.pending_tasks_queue.append(task.task_id)
        del self.working_tasks[task.task_id]

    def checkTimeouts(self) -> list[Task]:
        """Check for tasks that have timed out and handle retries."""
        timeout_tasks = []

        for task in list(self.working_tasks.values()):
            if task.has_timed_out():
                if task.has_exceeded_tries():
                    self.unassign_task(task) # add to pending queue
                else:
                    timeout_tasks.append(task) # client must retry !!

        return timeout_tasks   

    def get_best_worker(self) -> Worker:
        """Get the worker with the lowest EMA response time."""
        best_worker = None
        for worker in self.workersDict.values():
            if worker.available and (best_worker is None or worker.ema_response_time < best_worker.ema_response_time):
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

    

        


