import time
from functools import wraps
from collections import deque
from threading import Lock

def time_execution(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Execution time for {func.__name__}: {end_time - start_time} seconds")
        return result
    return wrapper

threshold = 5
recent_requests = deque()

def rate_limited(base_delay=0.5, interval=10):
    def decorator(func):
        lock = Lock()

        def wrapper(*args, **kwargs):
            with lock:
                current_time = time.time()
                recent_requests.append(current_time)
                num_requests = len([t for t in recent_requests if current_time - t < interval])

                print(f"Number of requests in the last {interval} seconds: {num_requests}")

                if num_requests > threshold:
                    delay = base_delay * (num_requests - threshold + 1)  # Increase delay based on excess requests
                    time.sleep(delay)

            return func(*args, **kwargs)

        return wrapper

    return decorator

# Example usage
@time_execution
@rate_limited()
def do_work():
    print("Work in progress...")
    time.sleep(0.1)

if __name__ == "__main__":
    for _ in range(10000):
        do_work()
