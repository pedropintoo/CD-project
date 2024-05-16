import selectors
from utils.logger import Logger
import time
from src.http_server import HTTPServerThread
#from src.p2p_server import P2PServer


class Node:
    def __init__(self, host, http_port, p2p_port, anchor, handicap):

        self.logger = Logger(f"[{host}:{http_port}]", f"logs/{host}_{http_port}.log")
        self.selector = selectors.DefaultSelector()

        self.http_server = HTTPServerThread(self.logger, host, http_port)
        self.p2p_server = P2PServerSelector(self.logger, host, p2p_port, anchor, handicap)

    def run(self):
        self.http_server.start()
        self.p2p_server.start()

        while True:
            response = self.http_server.response_queue.get()

            if response:
                self.http_server.request_queue.put(response)
