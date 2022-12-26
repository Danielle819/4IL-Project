import commprot
import socket
import time
import game

IP = '127.0.0.1'
PORT = 1984
server_socket = socket.socket()
server_socket.bind((IP, PORT))
server_socket.listen(1)


def play():
    print("waiting for first player...")
    client_socket1, client_address1 = server_socket.accept()
    print("the first player has joined!")
    print("waiting for second player...")
    client_socket2, client_address2 = server_socket.accept()
    print("the second player has joined!")
    players = [client_socket1, client_socket2]
    # to allow the game to begin
    client_socket1.send("another player has joined!".encode())
    client_socket2.send("another player has joined!".encode())

    board = game.Board()
    turn1 = True
    turn2 = False
    turn = 0

    str_board = commprot.board_to_string(board.board)
    players[0].send(str_board.encode())
    players[1].send(str_board.encode())
    # time.sleep(5)

    while turn < 42 and not game.check_board(board):
        if turn1:
            players[0].send("--your turn--".encode())
            players[1].send("not your turn".encode())
            place = eval(players[0].recv(1024))
            board.choose_cell(1, place)
        elif turn2:
            players[0].send("not your turn".encode())
            players[1].send("--your turn--".encode())
            place = eval(players[1].recv(1024))
            board.choose_cell(2, place)

        str_board = commprot.board_to_string(board.board)
        players[0].send(str_board.encode())
        players[1].send(str_board.encode())

        turn1 = not turn1
        turn2 = not turn2
        turn += 1

    players[0].send("-----end-----".encode())
    players[1].send("-----end-----".encode())

    winner = board.winner
    if winner == 1:
        print("player 1 won!")
        players[0].send("-you won-".encode())
        players[1].send("-you lost".encode())
    elif winner == 2:
        print("player 2 won!")
        players[1].send("-you won-".encode())
        players[0].send("-you lost".encode())
    elif winner == 0:
        print("game over")
        players[0].send("game over".encode())
        players[1].send("game over".encode())






play()





