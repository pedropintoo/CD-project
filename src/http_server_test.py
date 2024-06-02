from concurrent.futures import ThreadPoolExecutor
from http_server import HTTPServerThread
from utils.logger import Logger
import time

port = 8080
host = "localhost"

logger = Logger(f"[{host}]", f"logs/{host}.log")

server = HTTPServerThread(logger, host, port, None, None)
server.start()

while True:
    time.sleep(0.1)



