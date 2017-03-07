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

class TCPPacket:

    def __init__(self, src_info, dst_info, data):
        self.src_info = src_info
        self.dst_info = dst_info
        self.data = data

    def __repr__(self):
        repr_data = self.data.hex() if len(self.data.hex()) < 16 else self.data.hex()[0:16] + "..."
        repr_string = "<TCPPacket {0}:{1} > {2}:{3} 0x{4}>"
        return repr_string.format(self.src_info[0], self.src_info[1],
                                  self.dst_info[0], self.dst_info[1], repr_data)

class Connection(threading.Thread):

    def __init__(self, server, socket_client):
        super().__init__()
        self.server = server
        self.socket_client = socket_client
        self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.queue = queue
        self.version = 0
        self.command = 0
        self.src_info = socket_client.getpeername()
        self.dst_info = None
        self.user_id = ""

    def on_receive(self, data, origin):
        if origin == self.socket_client:
            self.send_to_server(data)
            packet = TCPPacket(self.src_info, self.dst_info, data)
            self.server.queue.put(packet)
        elif origin == self.socket_server:
            self.send_to_client(data)
            packet = TCPPacket(self.dst_info, self.src_info, data)
            self.server.queue.put(packet)

    def send_to_server(self, data):
        self.socket_server.sendall(data)

    def send_to_client(self, data):
        self.socket_client.sendall(data)

    def connect_to_server(self, info):
        try:
            self.socket_server.connect(info)
        except ConnectionError:
            return 0x5B
        return 0x5A

    def run(self):
        data = self.socket_client.recv(BUFFER_SIZE)
        if len(data) < 9:
            self.socket_client.close()
            return
        self.server.add_connection(self)
        version, command, port, raw_address = struct.unpack("!BBH4s", data[0:8])
        self.version = version
        self.command = command
        self.dst_info = (socket.inet_ntoa(raw_address), port)
        self.user_id = str(data[8:-1])
        return_code = self.connect_to_server(self.dst_info)
        response = struct.pack("!BBHI", 0x00, return_code, 0xDEAD, 0xBEEFFFFF)
        self.send_to_client(response)

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
        self.server.remove_connection(self)

class ProxyServer(threading.Thread):

    def __init__(self, listening_port, max_connection):
        super().__init__()
        self.listening_port = listening_port
        self.max_connection = max_connection
        self.connections = []
        self.connections_lock = threading.Lock()
        self.queue = queue.Queue()

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', self.listening_port))
        sock.listen(self.max_connection)
        while True:
            socket_client, _ = sock.accept()
            connection = Connection(self, socket_client)
            connection.start()

    def recv(self):
        return self.queue.get()

    def add_connection(self, connection):
        with self.connections_lock:
            self.connections.append(connection)

    def remove_connection(self, connection):
        with self.connections_lock:
            self.connections.remove(connection)

    def get_connection(self, info):
        with self.connections_lock:
            for connection in self.connections:
                if connection.dst_info == info or connection.src_info == info:
                    return connection
