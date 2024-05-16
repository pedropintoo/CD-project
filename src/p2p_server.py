import socket
import selectors
from threading import Thread
from queue import Queue

class P2PServerThread(Thread):
    def __init__(self, logger, host, port, anchor, handicap):
        Thread.__init__(self)
        self.logger = logger
        self._host = host
        self._port = port

        self.anchor = anchor
        self.handicap = handicap
        self.selector = selectors.DefaultSelector()

        # Generate request p2p queue
        self.request_queue = Queue()
        
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1) # Reuse address
        self._socket.bind((self._host, self._port))
        self._socket.listen(100)
        self._socket.setblocking(False)

    def run(self):
        """Run until canceled."""

        self.logger.info("P2P Server started %s:%s" % (self._host, self._port))
        self.selector.register(self._socket, selectors.EVENT_READ, self.handle_new_connection)

        while True:
            # Wait for events
            events = self.selector.select()
            # Handle events
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)   

    def connect(self, host, port):
        """Connect to a peer."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.logger.debug(f"Connecting to {host}:{port}")
            sock.connect((host, int(port)))
            sock.setblocking(False)
            self.selector.register(sock, selectors.EVENT_READ, self.handle_requests)
            return sock
        except Exception as e:
            self.logger.error(f"Failed to connect to {host}:{port}. {e}")
            return None

    ############## Handlers ##############      

    def handle_new_connection(self, sock, mask):
        """Handle new client connection."""
        conn, addr = sock.accept()
        # Client socket
        conn.setblocking(False)

        # Handle future data from this client  
        self.selector.register(conn, mask, self.handle_requests)              
        
    def handle_requests(self, conn, mask):
        """Handle incoming data."""
        data = conn.recv(1024)
        if data:
            self.logger.debug(f"Received {data} from {conn.getpeername()}")
            self.request_queue.put({"conn": conn, "data": data})
        else:
            self.sel.unregister(conn)
            conn.close()

