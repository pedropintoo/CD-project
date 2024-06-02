import http.server as http_server
import socketserver, socket, json, time
from queue import Queue
from threading import Lock, Thread

HTTP_THREAD_COUNT = 20

class HTTPRequestHandler(http_server.BaseHTTPRequestHandler):
    request_queue = None
    response_queue = None
    logger = None
    stats = None
    network = None
    locker = None

    # Suppress http console output (can be removed for debugging)
    def log_message(self, format, *args):
        return

    def do_POST(self):
        with self.locker: # TODO: (remove this)
            if self.path.endswith("/solve"):
                length = int(self.headers.get('Content-Length'))
                data = self.rfile.read(length).decode('utf8')
                
                self.send_response(200)
                self.send_header('Content-type','text/html')
                self.end_headers()

                tasks = json.loads(data)['tasks']
                self.logger.warning(f"HTTP request for {tasks} tasks.")
                
                # Send request to p2p
                self.request_queue.put(tasks)

                time.sleep(5)

                # Wait for response
                #response = self.response_queue.get(block=True)
                self.logger.debug(f"HTTP response.")

                self.wfile.write(("response" + "\n").encode("utf8"))
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
    def __init__(self, logger, addr, sock, locker, stats, network):
        Thread.__init__(self)
        self.daemon = True # Exit when main thread exits
        self.logger = logger
        self.addr = addr
        self.sock = sock
        self.locker = locker
        self.stats = stats
        self.network = network

        # Generate request and response http queues
        self.request_queue = Queue()
        self.response_queue = Queue()

        self.start() # Start the thread
        

    def run(self):
        HTTPRequestHandler.request_queue = self.request_queue
        HTTPRequestHandler.response_queue = self.response_queue
        HTTPRequestHandler.logger = self.logger
        HTTPRequestHandler.stats = self.stats
        HTTPRequestHandler.network = self.network
        HTTPRequestHandler.locker = self.locker

        self.server = http_server.HTTPServer(self.addr, HTTPRequestHandler, False) # Start the server

        # Prevent the HTTP server from re-binding every handler.
        # https://stackoverflow.com/questions/46210672/
        self.server.socket = self.sock
        self.server.server_bind = self.server_close = lambda self: None
        ##

        self.server.serve_forever()    


class HTTPServer():
    def __init__(self, logger, host, port, stats, network):
        self.logger = logger
        self.addr = (host, int(port))
        self.stats = stats
        self.network = network
        self.locker = Lock()

        # One socket for all threads
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.addr)
        self.sock.listen(5)
    
    def start(self):
        self.logger.info("HTTP Server started http://%s:%s" % self.addr)
        threads_count = "" # For debugging
        
        for i in range(HTTP_THREAD_COUNT):
            try:
                HTTPServerThread(self.logger, self.addr, self.sock, self.locker, self.stats, self.network)
                threads_count += f"\033[92m{'.'}\033[00m" # green
            except Exception as e:
                threads_count += f"\033[91m{'X'}\033[00m" # red


        self.logger.debug("HTTP Threads ready: [" + threads_count + "]")
