from src.http_server import HTTPServerThread
#from src.p2p_server import P2PServer


class Node:
    def __init__(self, host, http_port, p2p_port, anchor, handicap):
        self.http_server = HTTPServerThread(host, http_port)
        #self.p2p_server = P2PServer()
        
        pass

    def run(self):
        self.http_server.run()
        #self.p2p_server.run()
    