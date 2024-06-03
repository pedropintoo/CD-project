from socket import socket
import pickle
from src.p2p_loadbalancer import TaskID

class Message:
    """Message Type."""

    def __init__(self, command: str, replyAddress: str = None):
        self.data = {"command":command}
        if replyAddress is not None:
            self.data["replyAddress"] = replyAddress

    def to_bytes(self) -> bytes:
        return pickle.dumps(self.data)


class FloodingHelloMessage(Message):
    """Message to communicate baseValue and incrementedValue."""

    def __init__(self, replyAddress: str, nodesList: list, baseValue: int, incrementedValue: int):
        super().__init__("FLOODING_HELLO", replyAddress)
        self.data["baseValue"] = baseValue
        self.data["incrementedValue"] = incrementedValue
        self.data["args"] = {"nodesList": nodesList}

class FloodingConfirmationMessage(Message):
    """Message to confirm the flooding result."""

    def __init__(self, replyAddress: str, baseValue: int):
        super().__init__("FLOODING_CONFIRMATION", replyAddress)
        self.data["baseValue"] = baseValue

class JoinRequestMessage(Message):
    """Message to join the P2P network."""
    
    def __init__(self, replyAddress: str):
        super().__init__("JOIN_REQUEST", replyAddress)

class JoinReplyMessage(Message):
    """Message to replay to a joining node."""
    
    def __init__(self, nodesList: list):
        super().__init__("JOIN_REPLY")
        self.data["args"] = {"nodesList": nodesList}

class SolveRequestMessage(Message):
    """Message to request to solve a task."""
    
    def __init__(self, replyAddress:str, task_id: TaskID, sudoku: str):
        super().__init__("SOLVE_REQUEST", replyAddress)
        self.data["args"] = {"task_id": task_id, "sudoku": sudoku}

class SolveReplyMessage(Message):
    """Message to reply a solve request."""
    
    def __init__(self, replyAddress: str, task_id: TaskID, solution: str = None):
        super().__init__("SOLVE_REPLY", replyAddress)
        self.data["args"] = {"task_id": task_id, "solution": solution}


    
class P2PProtocol:
    """P2P Protocol."""
    
    @classmethod
    def flooding_hello(cls, replyAddress: str, nodesList: list, baseValue: int = 0, incrementedValue: int = 0) -> FloodingHelloMessage:
        """Creates a SolveRequestMessage object."""
        return FloodingHelloMessage(replyAddress, nodesList, baseValue, incrementedValue)

    @classmethod
    def flooding_confirmation(cls, replyAddress: str, baseValue: int) -> FloodingConfirmationMessage:
        """Creates a FloodingConfirmationMessage object."""
        return FloodingConfirmationMessage(replyAddress, baseValue)

    @classmethod
    def join_request(cls, replyAddress: str) -> JoinRequestMessage:
        """Creates a JoinRequestMessage object."""
        return JoinRequestMessage(replyAddress)

    @classmethod
    def join_reply(cls, nodesList: list) -> JoinReplyMessage:
        """Creates a JoinReplyMessage object."""
        return JoinReplyMessage(nodesList)

    @classmethod
    def solve_request(cls, replyAddress: str, task_id: TaskID, sudoku: str) -> SolveRequestMessage:
        """Creates a SolveRequestMessage object."""
        return SolveRequestMessage(replyAddress, task_id, sudoku)
    
    @classmethod
    def solve_reply(cls, replyAddress: str, task_id: TaskID, solution: str = None) -> SolveReplyMessage:
        """Creates a SolveRequestMessage object."""
        return SolveReplyMessage(replyAddress, task_id, solution)
    
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

        if command == "FLOODING_HELLO":
            return FloodingHelloMessage(data["replyAddress"], data["args"]["nodesList"], data["baseValue"], data["incrementedValue"])
        elif command == "FLOODING_CONFIRMATION":
            return FloodingConfirmationMessage(data["replyAddress"],data["baseValue"])    
        elif command == "JOIN_REQUEST":
            return JoinRequestMessage(data["replyAddress"])
        elif command == "JOIN_REPLY":
            return JoinReplyMessage(data["args"]["nodesList"])
        elif command == "SOLVE_REQUEST":
            return SolveRequestMessage(data["replyAddress"], data["args"]["task_id"], data["args"]["sudoku"])
        elif command == "SOLVE_REPLY":
            return SolveReplyMessage(data["replyAddress"], data["args"]["task_id"], data["args"]["solution"])
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
