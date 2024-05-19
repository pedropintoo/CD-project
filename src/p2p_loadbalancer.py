import time
from typing import Dict, List
from socket import socket

class Task:
    def __init__(self, task_id: int, worker_address: str, time_limit: int = 10, tries_limit: int = 3):
        self.task_id = task_id
        self.worker_address = worker_address
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
        self.start_time = time.time()    

class WorkersManager:
    def __init__(self):        
        self.socketsDict: Dict[str, socket] = {} # {'host:port': socket}


class TaskManager:
    def __init__(self, workersManager):
        self.workersManager = workersManager
        self.pending_tasks_queue: List[int] = []
        self.working_tasks: Dict[int, Task] = {}

    def add_pending_task(self, task_id: int):
        """Add a task to the pending queue."""
        self.pending_tasks_queue.append(task_id)

    def has_pending_tasks(self) -> bool:
        """Check if there are pending tasks."""
        return len(self.pending_tasks_queue) > 0

    def assign_task(self, task: Task) -> int:
        """Assign a task to a worker."""
        task_id = self.pending_tasks_queue.pop()  
        task = Task(task_id, worker_address)
        self.working_tasks[task_id] = task
        return task_id

    def unassign_task(self, task_id: int):
        """Remove a task from the working list and add it back to the pending queue."""
        self.pending_tasks_queue.append(task_id)
        del self.working_tasks[task_id]

    def checkTimeouts(self) -> list[Task]:
        """Check for tasks that have timed out and handle retries."""
        timeout_tasks = []

        for task_id, task in list(self.working_tasks.items()):
            if task.has_timed_out():
                if task.has_exceeded_tries():
                    self.unassign_task(task_id) # add to pending queue
                else:
                    timeout_tasks.append(task) # client must retry !!

        return timeout_tasks       

