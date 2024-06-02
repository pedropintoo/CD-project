import http.server as http_server
import logging
import json
from queue import Queue
from threading import Thread

class HTTPRequestHandler(http_server.BaseHTTPRequestHandler):

    request_queue = None
    response_queue = None
    logger = None
    stats = None
    network = None

    # Suppress http console output
    def log_message(self, format, *args):
        return
    
    def do_POST(self):

        if self.path.endswith("/solve"):
            length = int(self.headers.get('Content-Length'))
            data = self.rfile.read(length).decode('utf8')
            
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()

            tasks = json.loads(data)['tasks']
            self.logger.warning(f"HTTP request for {data} tasks. - " + str(self.prev_data)) # new thread
            
            # send request to p2p
            self.request_queue.put(tasks)

            # wait for response
            response = self.response_queue.get(block=True)
            self.logger.debug(f"HTTP response.")

            self.wfile.write((response + "\n").encode("utf8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found\n")    

    def do_GET(self):
        if self.path.endswith("/stats"):
            self.send_response(200)
            self.send_header('Content-type','application/json')
            self.end_headers()
            
            self.wfile.write((json.dumps(self.stats) + "\n").encode("utf8"))
        elif self.path.endswith("/network"):
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            
            self.wfile.write((json.dumps(self.network) + "\n").encode("utf8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found\n")    



class HTTPServerThread(Thread):
    def __init__(self, logger, host, port, stats, network):
        Thread.__init__(self)
        self.logger = logger
        self.host = host
        self.port = port

        self.stats = stats
        self.network = network

        # Generate request and response http queues
        self.request_queue = Queue()
        self.response_queue = Queue()

        HTTPRequestHandler.request_queue = self.request_queue
        HTTPRequestHandler.response_queue = self.response_queue
        HTTPRequestHandler.logger = self.logger
        HTTPRequestHandler.stats = self.stats
        HTTPRequestHandler.network = self.network

        self.logger.info("HTTP Server started http://%s:%s" % (host, port))
        self.server = http_server.HTTPServer(
            server_address=(host, port),
            RequestHandlerClass=HTTPRequestHandler,
        )
        

    def run(self):
        self.server.serve_forever()    
