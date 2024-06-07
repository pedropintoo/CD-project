import http.server as http_server
import socketserver, socket, json
from queue import Queue
from threading import Lock, Thread
from src.sudoku_algorithm import SudokuAlgorithm
from src.utils.serializer_xml import dict_to_xml, parse_xml

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
        with self.locker:  
            if self.path.endswith("/solve"):
                try:
                    length = int(self.headers.get('Content-Length'))
                    data = self.rfile.read(length).decode('utf8')

                    content_type = self.headers.get('Content-Type', 'application/json')
                    
                    if 'application/xml' in content_type:
                        # Try to parse the XML data
                        sudoku = parse_xml(data)['sudoku']
                        self.logger.critical("XML")
                        self.logger.critical(sudoku)
                    else:
                        # Try to parse the JSON data
                        sudoku = json.loads(data)['sudoku']
                        self.logger.critical(sudoku)
 
                    self.logger.warning(f"HTTP request for {sudoku}.")
                    
                    # Put the request in the queue
                    self.request_queue.put(sudoku)

                    # Wait for the response
                    response = self.response_queue.get(block=True)
                    self.logger.debug(f"HTTP response.")
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()

                    self.wfile.write(((f"\n\n\033[92m{'Solved!!'}\033[00m \n" + str(SudokuAlgorithm(response))) if response is not None else f"\n\n\033[91m{'Not found!'}\033[00m" + "\n").encode("utf8"))
                
                # Handle JSON errors    
                except (json.JSONDecodeError, KeyError) as e:
                    self.send_response(400)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    
                    error_message = f"Invalid request format: {str(e)}\n"
                    self.wfile.write(error_message.encode("utf8"))
                    
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"404 Not Found\n")
    
    def do_GET(self):
        # Handle the stats request
        if self.path.endswith("/stats"):
            self._handle_get_request(self.stats)
            
        # Handle the network request
        elif self.path.endswith("/network"):
            self._handle_get_request(self.network)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found\n")

    def _handle_get_request(self, data):
        content_type = self.headers.get('Content-Type', 'application/json')
        if 'application/xml' in content_type:
            self.send_response(200)
            self.send_header('Content-type', 'application/xml')
            self.end_headers()
            response_data = dict_to_xml(data)
            self.wfile.write(response_data.encode('utf8'))
        else:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response_data = json.dumps(data, indent=4) + "\n"
            self.wfile.write(response_data.encode("utf8"))


class HTTPServerThread(Thread):
    def __init__(self, logger, addr, sock, locker, request_queue, response_queue, stats, network):
        Thread.__init__(self)
        self.daemon = True # Exit when main thread exits
        self.logger = logger
        self.addr = addr
        self.sock = sock
        self.locker = locker
        self.stats = stats
        self.network = network

        self.request_queue = request_queue
        self.response_queue = response_queue

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
    def __init__(self, logger, host, port, stats, network, max_threads):
        self.logger = logger
        self.addr = (host, int(port))
        self.stats = stats
        self.network = network
        self.locker = Lock()

        self.max_threads = max_threads

        # Generate request and response http queues (THREAD SAFE!!)
        self.request_queue = Queue()
        self.response_queue = Queue()

        # One socket for all threads
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.addr)
        self.sock.listen(5)
    
    def start(self):
        self.logger.info("HTTP Server started http://%s:%s" % self.addr)
        threads_count = "" # For debugging
        
        for i in range(self.max_threads):
            try:
                HTTPServerThread(self.logger, self.addr, self.sock, self.locker, self.request_queue, self.response_queue, self.stats, self.network)
                threads_count += f"\033[92m{'.'}\033[00m" # green
            except Exception as e:
                threads_count += f"\033[91m{'X'}\033[00m" # red

        self.logger.debug("HTTP threads: [" + threads_count + "]")
