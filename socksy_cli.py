import sys

from socksy import ProxyServer

MAX_CONNECTION = 256
LISTENING_PORT = 1080

def message_handler(thread_id, socket_from, socket_to, data):
    socket_to.sendall(data)
    print("[{0}] new message {1} -> {2}".format(
        thread_id,
        socket_from.getpeername(),
        socket_to.getpeername()
    ))

def open_handler(thread_id, socket_client, socket_server):
    print("[{0}] connection open {1} -> {2}".format(
        thread_id,
        socket_client.getpeername(),
        socket_server.getpeername()
    ))

def close_handler(thread_id):
    print("[{0}] connection close".format(thread_id))

def main():
    port = LISTENING_PORT
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    server = ProxyServer(port, MAX_CONNECTION)
    server.on_client_message = message_handler
    server.on_server_message = message_handler
    server.on_open = open_handler
    server.on_close = close_handler
    server.start()
    server.join()

if __name__ == "__main__":
    main()
