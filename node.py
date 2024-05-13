from src.http_server import HTTPServer
from src.p2p_server import P2PServer

class Node:
    def __init__(self):
        self.p2p_server = P2PServer()
        self.http_server = HTTPServer()

    

