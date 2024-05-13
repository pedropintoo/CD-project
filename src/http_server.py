import http.server
import time

class HTTPProtocol(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()

        message = "Hello, World! Here is a POST response"

        time.sleep(2)
        # Start the computation
        # Send the message to the other side of the node

        self.wfile.write(bytes(message, "utf8"))

class HTTPServer:
    def __init__(self):
        self.server = http.server.HTTPServer(('localhost', 8000), HTTPProtocol)
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()




    webServer.server_close()
    print("Server stopped.")