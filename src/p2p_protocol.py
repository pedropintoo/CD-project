class Message:
    """Message Type."""

    def __init__(self, command: str):
        self.data = {"command":command}

    def __repr__(self):
        return json.dumps(self.data)

