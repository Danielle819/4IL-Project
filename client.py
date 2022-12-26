import commprot
import socket
import game

IP = '127.0.0.1'
PORT = 1984
client_socket = socket.socket()
client_socket.connect((IP, PORT))


def print_board():
    board = client_socket.recv(83).decode()
    board = commprot.string_to_board(board)
    print(board)
    return board


def play():
    print("waiting for another player to join...")
    status = client_socket.recv(26).decode()
    print(status, "\n")

    board = print_board()
    status = client_socket.recv(13).decode()
    while status != "-----end-----":
        if status == "--your turn--":
            place = game.get_place(board)
            client_socket.send(str(place).encode())
            board = print_board()
        elif status == "not your turn":
            print("\nwaiting for other player to play...")
            board = print_board()

        status = client_socket.recv(13).decode()
        # print(status)

    # print("game ended")
    status = client_socket.recv(1024).decode()
    print(status)


play()
client_socket.close()


