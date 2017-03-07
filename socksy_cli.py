import sys

from socksy import ProxyServer

MAX_CONNECTION = 256
LISTENING_PORT = 1080

def main():
    port = LISTENING_PORT
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    server = ProxyServer(port, MAX_CONNECTION)
    server.start()
    while True:
        packet = server.recv()
        print(packet)

if __name__ == "__main__":
    main()
