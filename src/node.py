from src.http_server import HTTPServer
#from src.p2p_server import P2PServer


class Node:
    def __init__(self, logger, host, http_port, p2p_port, anchor, handicap):
        self.logger = logger
        self.http_server = HTTPServer(logger, host, http_port)
        #self.p2p_server = P2PServer()
        
        pass

    def run(self):
        self.http_server.run()
        #self.p2p_server.run()
    