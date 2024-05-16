class P2PServerSelector:
    def __init__(self, logger, host, port, anchor, handicap):
        self.logger = logger
        self.host = host
        self.port = port
        self.anchor = anchor
        self.handicap = handicap
        self.selector = selectors.DefaultSelector()
    
    def start(self):

        self.logger.info(f"P2P Server started {host}:{port}")
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen(5)
        self.server.setblocking(False)
        self.selector.register(self.server, selectors.EVENT_READ, handle_new_connection)