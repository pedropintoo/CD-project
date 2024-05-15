import http.server as http_server
from threading import Thread
import time
import queue

class HTTPProtocol(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()

        message = "Hello, World! Here is a POST response"

        time.sleep(2)

        self.wfile.write(bytes(message, "utf8"))

class HTTPServerThread:
    def __init__(self, host, port):
        self._host = host
        self._port = port

    def run(self):
        self.server = http_server.HTTPServer(
            server_address=(self.host, self.port),
            RequestHandlerClass=self.request_handler,
        )
        self.server.requests = self.requests_queue
        self.server.responses = self.responses_queue
        self.server.handler_attributes = self.handler_attributes
        self.server.timeout = self.timeout
        self.server.interval = self.interval
        nothing = lambda msg: None
        self.server.log_callback = (
            self.logger.debug if self.logger else nothing
        )
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()




