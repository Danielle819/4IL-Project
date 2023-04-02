import socket

IP = '127.0.0.1'
PORT = 1995
server_socket = socket.socket()
server_socket.bind((IP, PORT))
server_socket.listen(5)

# client_socket = socket.socket()
# client_socket.connect((IP, PORT))

while True:
    pass
