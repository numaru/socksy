import socket
import struct
import threading
import queue
import select

# Exit on CTRL+C
# Because the accept method seems to block SIGINT on windows
import os
if os.name == "nt":
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

BUFFER_SIZE = 4096

class Connection(threading.Thread):

    def __init__(self, server, socket_client):
        super().__init__()
        self.server = server
        self.socket_client = socket_client
        self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.version = 0
        self.command = 0
        self.user_id = ""

    def on_receive(self, data, origin):
        if origin == self.socket_client:
            self.server.on_client_message(
                self.ident,
                self.socket_client,
                self.socket_server,
                data
            )
        elif origin == self.socket_server:
            self.server.on_server_message(
                self.ident,
                self.socket_server,
                self.socket_client,
                data
            )

    def connect_to_server(self, address, port):
        try:
            self.socket_server.connect((address, port))
        except ConnectionError:
            return 0x5B
        return 0x5A

    def run(self):
        # Receive the SOCKS connection bytes
        data = self.socket_client.recv(BUFFER_SIZE)
        if len(data) < 9:
            self.socket_client.close()
            return
        # Parse the connection info
        self.version, self.command, port, raw_address = struct.unpack("!BBH4s", data[0:8])
        self.user_id = str(data[8:-1])
        # Try to connect to the given address
        return_code = self.connect_to_server(socket.inet_ntoa(raw_address), port)
        # Give to the client the connection status
        response = struct.pack("!BBHI", 0x00, return_code, 0xDEAD, 0xBEEFFFFF)
        self.socket_client.sendall(response)

        # If the connection is refused, abort
        if return_code == 0x5B:
            return

        self.server.on_open(self.ident, self.socket_client, self.socket_server)

        # Listen to the incomings packets
        sockets = [self.socket_client, self.socket_server]
        active = True
        try:
            while active:
                rlist, _, xlist = select.select(sockets, [], sockets)
                if xlist or not rlist:
                    break
                for readable in rlist:
                    data = readable.recv(BUFFER_SIZE)
                    if data:
                        self.on_receive(data, readable)
                    else:
                        active = False
                        break
        finally:
            for sock in sockets:
                sock.close()
        self.server.on_close(self.ident)

class ProxyServer(threading.Thread):

    def __init__(self, listening_port, max_connection):
        super().__init__()
        self.listening_port = listening_port
        self.max_connection = max_connection
        self.on_client_message = lambda *args: None
        self.on_server_message = lambda *args: None
        self.on_open = lambda *args: None
        self.on_close = lambda *args: None

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', self.listening_port))
        sock.listen(self.max_connection)
        while True:
            socket_client, _ = sock.accept()
            connection = Connection(self, socket_client)
            connection.start()
