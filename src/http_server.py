import http.server as http_server
from threading import Thread
import time
import queue

class HTTPRequestHandler(http_server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()

        message = "Hello, World! Here is a POST response"

        time.sleep(2)

        self.wfile.write(bytes(message, "utf8"))

class HTTPServer:
    def __init__(self, logger, host, port):
        self._host: str = host
        self._port: int = port
        self.logger = logger
        self.server = None

    def run(self):
        self.logger.info("Starting HTTP server on %s:%d" % (self._host, self._port))
        self.server = http_server.HTTPServer(
            server_address=(self._host, self._port),
            RequestHandlerClass=HTTPRequestHandler,
        )
        self.server.serve_forever()





