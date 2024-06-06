import uuid
from queue import Queue
from threading import Lock

class Broker:
    def __init__(self):
        self.request_queues = {}
        self.response_queues = {}
        self.request_map = {}
        self.lock = Lock()

    def generate_request_id(self):
        return str(uuid.uuid4())

    def submit_request(self, request_id, request):
        with self.lock:
            self.request_queues[request_id] = Queue()
            self.response_queues[request_id] = Queue()
            self.request_map[request_id] = self.request_queues[request_id]
        
        # Add the request to the appropriate queue
        self.request_queues[request_id].put(request)

    def get_response(self, request_id):
        # Wait for the response in the appropriate queue
        return self.response_queues[request_id].get(block=True)

    def receive_from_server(self, response, request_id):
        # Put the response in the appropriate queue
        if request_id in self.response_queues:
            self.response_queues[request_id].put(response)
            # Clean up the queues after response is processed
            with self.lock:
                del self.request_queues[request_id]
                del self.response_queues[request_id]
                del self.request_map[request_id]
