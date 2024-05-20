import socket
import selectors
from threading import Thread
from queue import Queue
from src.p2p_protocol import P2PProtocol

class P2PServerThread(Thread):
    def __init__(self, logger, host, port):
        Thread.__init__(self)
        self.logger = logger
        self.replyAddress = f"{host}:{port}"
                
        # Generate request p2p queue
        self.request_queue = Queue()

        self.selector = selectors.DefaultSelector()
        
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1) # Reuse address
        self._socket.bind((host, port))
        self._socket.listen(100)
        self._socket.setblocking(False)

    def run(self):
        """Run until canceled."""

        self.logger.info(f"P2P Server started {self.replyAddress}")
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
        """Handle new client socket."""
        socket, addr = sock.accept()
        # Client socket
        socket.setblocking(False)

        self.logger.debug(f"P2P: New connection from {addr}")

        # Handle future data from this client  
        self.selector.register(socket, mask, self.handle_requests)              
        
    def handle_requests(self, sock, mask):
        """Handle incoming data."""
        message = P2PProtocol.recv_msg(sock)
        
        # Client disconnected
        if message == None:
            self.logger.debug(f"Client {sock.getpeername()} disconnected.")
            self.selector.unregister(sock)
            sock.close()
            return
        
        #self.logger.debug(f"Received message {message} from {sock.getpeername()}")

        self.request_queue.put(message)


