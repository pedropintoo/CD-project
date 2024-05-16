import logging
import os

class Logger:

    def __init__(self, identifierName: str, logFile: str = None):
        self.log = logging.getLogger(identifierName)
        CustomFormatter().setup(self.log)

        self.log.addHandler(logging.FileHandler(logFile))


    def error(self, errorMsg):
        self.log.error(errorMsg)

    def info(self, infoMsg):
        self.log.info(infoMsg)

    def debug(self, debugMsg):
        self.log.debug(debugMsg)      

    def warning(self, warningMsg):
        self.log.warning(warningMsg)

    def critical(self, criticalMsg):
        self.log.critical(criticalMsg)
            

class CustomFormatter(logging.Formatter):

    colors = {
        'DEBUG': '\x1b[38;20m',   # Gray
        'INFO': '\033[38;2;33;213;33m',    # Green
        'WARNING': '\033[93m',    # Yellow
        'ERROR': '\033[91m',      # Red
        'CRITICAL': '\033[1;31m'  # Dark Red
    }

    reset = '\033[0m'
    fmt = '%(name)s %(levelname)-8s %(message)s'

    def format(self, record):
        color = self.colors.get(record.levelname, self.reset)
        formatter = logging.Formatter(color + self.fmt + self.reset)
        return formatter.format(record)

    def setup(self, logger):
        logger.propagate = False
        
        if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(self)
            logger.setLevel(logging.DEBUG)
            logger.addHandler(console_handler)