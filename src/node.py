import selectors
import time
import queue
from utils.logger import Logger
from src.http_server import HTTPServerThread
from src.p2p_server import P2PServerThread
import pickle


class Node:
    def __init__(self, host, http_port, p2p_port, anchor, handicap):

        self.logger = Logger(f"[{host}]", f"logs/{host}.log")
        self.selector = selectors.DefaultSelector()

        self.stats = {"all" : {"solved": 0, "validations": 0}, "nodes": []}
        self.network = {}

        self.http_server = HTTPServerThread(self.logger, host, http_port, self.stats, self.network)
        self.p2p_server = P2PServerThread(self.logger, host, p2p_port, anchor, handicap, self.network)

        # this variable is only for testing purposes ONLY! (to be removed)
        if (anchor != None):
            self.anchor_temp_conn = self.p2p_server.connect(anchor.split(":")[0], anchor.split(":")[1])

        self.isHandlingHTTP = False
            
        
    def run(self):
        self.http_server.start()
        self.p2p_server.start()

        # testing purposes ONLY! (to be removed)
        # while True:
        #     try:
        #         http_response = self.http_server.request_queue.get(block=False, )
        #     except queue.Empty:
        #         pass
        #     else:
        #         self.isHandlingHTTP = True
        #         self.anchor_temp_conn.send(http_response.encode("utf8"))

        #     try:
        #         p2p_response = self.p2p_server.request_queue.get(block=False)
        #     except queue.Empty:
        #         pass
        #     else:
        #         if self.isHandlingHTTP:
        #             self.isHandlingHTTP = False
        #             self.stats["all"]["solved"] += 1
        #             self.logger.debug("P2P response.")
        #             self.http_server.response_queue.put(p2p_response["data"].decode("utf8"))
        #         else:
        #             self.logger.debug("P2P response.")
        #             p2p_response["conn"].send(p2p_response["data"])
                    
        while not self.done:
            output, addr = self.p2p_server.request_queue.get(block=False) 
            if output is not None:
                self.logger.info("O: %s", output)
                # `HELLO` , `JOIN_REQUEST`, `JOIN_REPLY`, `SOLVE_REQUEST`, `SOLVE_REPLY`
                
                if output["method"] == "HELLO":
                    for node in output["args"]["nodesList"]:
                        # Check if node is already known
                        if self.network.get(node["host"] + ":" + str(node["port"])) is None:
                            sock = self.p2p_server.connect(node["host"], node["port"])
                            self.network[node["host"] + ":" + str(node["port"])] = sock    
                            
                elif output["method"] == "JOIN_REQUEST":
                    self.all_nodes_known(output)
                elif output["method"] == "JOIN_REPLY":
                    for node in output["args"]["nodesList"]:
                        sock = self.p2p_server.connect(node["host"], node["port"])
                        P2PProtocol.send_hello(sock, output["args"]["nodesList"])
                elif output["method"] == "SOLVE_REQUEST":
                    self.execute_task(output) # and send reply
                elif output["method"] == "SOLVE_REPLY":
                    self.send_tasks(output) # save and send tasks                                      

