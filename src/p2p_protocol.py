from socket import socket
import pickle

class Message:
    """Message Type."""

    def __init__(self, command: str):
        self.data = {"command":command}

    def to_bytes(self) -> bytes:
        print(self.data)
        return pickle.dumps(self.data)

class HelloMessage(Message):
    """Message to say hello to the P2P network."""

    def __init__(self, nodesList: list):
        super().__init__("HELLO")
        self.data["args"] = {"nodesList": nodesList}

class JoinRequestMessage(Message):
    """Message to join the P2P network."""
    
    def __init__(self):
        super().__init__("JOIN_REQUEST")

class JoinReplyMessage(Message):
    """Message to replay to a joining node."""
    
    def __init__(self, nodesList: list):
        super().__init__("JOIN_REPLY")
        self.data["args"] = {"nodesList": nodesList}

class SolveRequestMessage(Message):
    """Message to request to solve a task."""
    
    def __init__(self, task_id: int):
        super().__init__("SOLVE_REQUEST")
        self.data["task"] = task_id

class SolveReplyMessage(Message):
    """Message to reply a solve request."""
    
    def __init__(self, task_id: int):
        super().__init__("SOLVE_REPLY")
        self.data["task"] = task_id


class P2PProtocol:
    """P2P Protocol."""
    
    @classmethod
    def hello(cls, nodesList: list) -> HelloMessage:
        """Creates a HelloMessage object."""
        return HelloMessage(nodesList)
    
    @classmethod
    def join_request(cls) -> JoinRequestMessage:
        """Creates a JoinRequestMessage object."""
        return JoinRequestMessage()

    @classmethod
    def join_reply(cls, nodesList: list) -> JoinReplyMessage:
        """Creates a JoinReplyMessage object."""
        return JoinReplyMessage(nodesList)

    @classmethod
    def solve_request(cls, task_id: int) -> SolveRequestMessage:
        """Creates a SolveRequestMessage object."""
        return SolveRequestMessage(task_id)
    
    @classmethod
    def solve_reply(cls, task_id: int) -> SolveRequestMessage:
        """Creates a SolveRequestMessage object."""
        return SolveRequestMessage(task_id)


    @classmethod
    def send_msg(cls, socket: socket, msg: Message):
        """Sends through a socket a Message object."""

        # Object message -> Bytes (via pickle)
        message = msg.to_bytes()

        # Create a header with the length
        header = len(message).to_bytes(2, byteorder='big')

        # Send through the socket
        socket.send(header + message)

    @classmethod
    def recv_msg(cls, socket: socket) -> Message:
        """Receives through a connection a Message object."""
        
        # Receive message size
        size = int.from_bytes(socket.recv(2),'big')

        if (size == 0): return None # Client disconnected

        received = socket.recv(size)

        try:
            # decoding PICKLE to Message
            data = pickle.loads(received) 
        except Exception:
            raise P2PProtocolBadFormat(received)     
        
        command = data.get("command") 

        if command == "JOIN_REQUEST":
            return JoinRequestMessage()
        elif command == "JOIN_REPLY":
            return JoinReplyMessage(data["args"]["nodesList"])
        elif command == "HELLO":
            return HelloMessage(data["args"]["nodesList"])
        elif command == "SOLVE_REQUEST":
            return SolveRequestMessage(data["task"])
        elif command == "SOLVE_REPLY":
            return SolveReplyMessage(data["task"])
        else:
            raise P2PProtocolBadFormat(received)


    
class P2PProtocolBadFormat(Exception):
    """Exception when source message is not P2PProtocol."""

    def __init__(self, original_msg: bytes=None) :
        """Store original message that triggered exception."""
        self._original = original_msg

    @property
    def original_msg(self) -> str:
        """Retrieve original message as a string."""
        return self._original.decode("utf-8")
