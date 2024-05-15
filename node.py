#!/usr/bin/env python3

import argparse
from src.http_server import HTTPServer
#from src.p2p_server import P2PServer


class Node:
    def __init__(self, http_port, p2p_port, anchor, handicap):
        self.http_server = HTTPServer(http_port)
        #self.p2p_server = P2PServer()
        
        pass
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog='node.py',
                    description='Start in node in the network')
    
    parser.add_argument("-p", "--http_port", type=int, help="HTTP port to listen on", default=8000)
    parser.add_argument("-s", "--p2p_port", type=int, help="P2P port to listen on", default=7000)
    parser.add_argument("-a", "--anchor", type=str, help="Anchor P2P node to connect to", default="localhost:7000")
    parser.add_argument("-d", "--handicap", type=int, help="Handicap for the node", default=0)

    args = parser.parse_args()

    node = Node(args.http_port, args.p2p_port, args.anchor, args.handicap)
    #node.start()


