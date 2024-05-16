#!/usr/bin/env python3
import argparse
import utils.network as utils_network
from src.node import Node

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog='node.py',
                    description='Start in node in the network')
    
    parser.add_argument("-p", "--http_port", type=int, help="HTTP port to listen on", default=8000)
    parser.add_argument("-s", "--p2p_port", type=int, help="P2P port to listen on", default=7000)
    parser.add_argument("-a", "--anchor", type=str, help="Anchor P2P node to connect to", default=None)
    parser.add_argument("-d", "--handicap", type=int, help="Handicap for the node", default=0)
    parser.add_argument("-l", "--localhost", action="store_true", help="Run on localhost", default=False)

    args = parser.parse_args()

    if args.localhost:
        host = "localhost"
    else:
        host = utils_network.get_ip_address()

    node = Node(host, args.http_port, args.p2p_port, args.anchor, args.handicap)
    node.run()


	