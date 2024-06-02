from http_server import HTTPServer
from utils.logger import Logger
import time

port = 8080
host = "localhost"

logger = Logger(f"[{host}]", f"logs/{host}.log")

server = HTTPServer(logger, host, port, None, None)
server.start()

while True:
    time.sleep(0.1)



