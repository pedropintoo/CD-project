import http.server as http_server
from queue import Queue
import logging
from threading import Thread

class HTTPRequestHandler(http_server.BaseHTTPRequestHandler):

    request_queue = None
    response_queue = None
    logger = None

    def do_POST(self):

        if self.path.endswith("/solve"):
            length = int(self.headers.get('content-length'))
            data = self.rfile.read(length).decode('utf8')

            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            
            self.logger.debug("HTTP request.")
            # send request to p2p
            self.response_queue.put(data)

            # wait for response
            response = self.request_queue.get(block=True)
            self.logger.debug(f"HTTP response.")

            self.wfile.write((response + "\n").encode("utf8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found\n")    



class HTTPServerThread(Thread):
    def __init__(self, logger, host, port):
        Thread.__init__(self)
        self.logger = logger
        self._host = host
        self._port = port

        # Generate request and response http queues
        self.request_queue = Queue()
        self.response_queue = Queue()

        HTTPRequestHandler.request_queue = self.request_queue
        HTTPRequestHandler.response_queue = self.response_queue
        HTTPRequestHandler.logger = self.logger

        self.logger.info("HTTP Server started http://%s:%s" % (host, port))
        self.server = http_server.HTTPServer(
            server_address=(host, port),
            RequestHandlerClass=HTTPRequestHandler,
        )
        

    def run(self):
        self.server.serve_forever()    
