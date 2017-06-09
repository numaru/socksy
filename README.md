# Socksy

A tiny SOCKS proxy server. It support SOCKS4 and provide received messages throught callbacks.

# Callbacks

The followings callbacks are availables:

 - `on_client_message(thread_id, socket_from, socket_to, data)` When a message arrive from client
 - `on_server_message(thread_id, socket_from, socket_to, data)` When a message arrive from server
 - `on_open(thread_id, socket_client, socket_server)` When a connection is opened
 - `on_close(thread_id)` When a connection is closed

# Socksy CLI

A small example which print the received packets to the standard output.

```
python socksy_cli.py [port_number]
```

The default port number is 1080.
