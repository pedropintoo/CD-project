import socket
import selectors
from threading import Thread

class P2PServerThread(Thread):
    def __init__(self, logger, host, port, anchor, handicap):
        Thread.__init__(self)
        self.logger = logger
        self._host = host
        self._port = port

        self.anchor = anchor
        self.handicap = handicap
        self.selector = selectors.DefaultSelector()
        
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


    ############## Handlers ##############      

    def handle_new_connection(self, sock, mask):
        """Handle new client connection."""
        conn, addr = sock.accept()
        # Client socket
        conn.setblocking(False)

        # Handle future data from this client  
        self.sel.register(conn, mask, self.handle_requests)              
        
    def handle_requests(self, conn, mask):
        """Handle incoming data."""
        data = conn.recv(1024)
        if data:
            self.logger.debug(f"Received {data} from {conn.getpeername()}")
            conn.send(data)
        else:
            self.sel.unregister(conn)
            conn.close()

