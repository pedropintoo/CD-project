import socket
import selectors
from threading import Thread
from queue import Queue
from src.utils.network import create_socket

class P2PServerThread(Thread):
    def __init__(self, logger, host, port, anchor, handicap, network):
        Thread.__init__(self)
        self.logger = logger
        self._host = host
        self._port = port
        self.network = network
        
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

        # JOIN_REQUEST first message
        if self.anchor:
            sock = self.connect(self.anchor.split(":")[0], self.anchor.split(":")[1])

            P2PProtocol.send_join_request(sock)


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
            self.logger.debug(f"Connecting to {host}:{port}")

            # create a socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, int(port)))
            sock.setblocking(False)

            # Register the socket to the selector
            self.selector.register(sock, selectors.EVENT_READ, self.handle_requests)
            
            # Store the socket in the network
            self.network[host + ":" + str(port)] = sock

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

