import socket;

# Returns the IP address of the current machine
def get_ip_address() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        host = s.getsockname()[0]
    except Exception:
        host = "localhost"
    finally:
        s.close()
    return host
