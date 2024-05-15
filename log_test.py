from utils.logger import Logger

logger = Logger("Logger", "logs/teste.log")
logger.error("This is an error message")
logger.info("This is an info message")
logger.debug("This is a debug message")
logger.warning("This is a warning message")
logger.critical("This is a critical message")
logger = Logger("Logger", "log.txt")
logger.error("This is an error message")
logger.info("This is an info message")
logger.debug("This is a debug message")
logger.warning("This is a warning message")
logger.critical("This is a critical message")          