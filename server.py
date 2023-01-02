import commprot
import socket
import select
import game
import string
import random
import threading

# GLOBALS
users = {}  # username: {password: _, score: _, playing: _}
logged_users = {}  # sock.getpeername(): username
messages_to_send = []  # (socket, message)
"""
when a player starts playing they're moving from the not playing to 
the playing list, and when the game is over they go back
"""
not_playing_client_sockets = []  # client_socket
playing_client_sockets = []  # client_socket
"""
when the other player does join room by id, the handling method
will take the waiting socket from the dict and open a thread 
that will run the game (and send both sockets to it)
"""
waiting_id_rooms = {}  # id : (waiting) client_socket
"""
when the other player does join open room, the handling method
will take the first waiting socket from the list and open a thread 
that will run the game (and send both sockets to it)
"""
waiting_open_rooms = []  # (waiting) client_socket


def send_to_players(players, message):
    players[0].send(message.encode())
    players[1].send(message.encode())


def send_waiting_messages(messages, wlist):
    for message in messages:
        current_socket, data = message
        if current_socket in wlist:
            current_socket.send(data)
            messages.remove(message)


def send_error(conn, error_msg):
    """
    Send error message with given message
    Receives: socket, message error string from called function
    Returns: None
    """

    build_and_send_message(conn, "ERROR", error_msg)


# HELPER SOCKET METHODS

def build_and_send_message(conn, cmd, msg):
    """
    Builds a new message using commprot, wanted code and message.
    Prints debug info, then sends it to the given socket.
    Parameters: conn (socket object), cmd (str), msg (str)
    Returns: Nothing
    """

    message = commprot.build_message(cmd, str(msg))
    messages_to_send.append((conn, message))


def recv_message_and_parse(conn):
    """
    Receives a new message from given socket.
    Prints debug info, then parses the message using commprot.
    Parameters: conn (socket object)
    Returns: cmd (str) and data (str) of the received message.
    If error occurred, will return None, None
    """

    try:
        message = conn.recv(10019).decode()
    except ConnectionResetError:
        return "", ""
    if message == "":
        return "", ""
    cmd, msg = commprot.parse_message(message)
    return cmd, msg


# OTHER HELPER METHODS

def create_id():
    chars = string.ascii_uppercase
    return ''.join(random.choice(chars) for _ in range(6))


# COMMANDS HANDLING METHODS

def handle_create_id_room(conn):
    """
    gets a client who wants to start a game, sends them an ID
    and puts them in the waiting list
    parameters: conn (client socket)
    """
    ID = create_id()
    while ID in waiting_id_rooms:
        ID = create_id()

    waiting_id_rooms[ID] = conn
    build_and_send_message(conn, commprot.SERVER_CMD["create_open_room_ok_msg"], ID)


def handle_join_id_room(conn, ID):
    """
    gets a client who wants to join a room by an ID. if ID exists,
    moves both clients to the playing list and starts a thread that runs the game
    parameters: conn (client socket), ID (string)
    """
    if ID not in waiting_id_rooms:
        build_and_send_message(conn, commprot.SERVER_CMD, "ID not found")
        return

    playing_client_sockets.append(conn)
    playing_client_sockets.append(waiting_id_rooms[ID])
    not_playing_client_sockets.remove(conn)
    not_playing_client_sockets.remove(waiting_id_rooms[ID])

    game_thread = threading.Thread(target=play, args=[waiting_id_rooms[ID], conn])
    game_thread.start()
    game_thread.join()

    playing_client_sockets.remove(conn)
    playing_client_sockets.remove(waiting_id_rooms[ID])
    not_playing_client_sockets.append(conn)
    not_playing_client_sockets.append(waiting_id_rooms[ID])



def handle_client_message(conn, cmd, data):
    """
    Gets message code and data and calls the right function to handle command
    Receives: socket, message code and data
    """
    global logged_users

    if conn.getpeername() not in logged_users:
        if cmd == "LOGIN":
            pass
            # username = data.split("#")[0]
            # if username not in logged_users.values():
            #     handle_login_message(conn, data)
            # else:
            #     send_error(conn, "User is already logged in")
            # return
        elif cmd == "SIGNUP":
            pass
        else:
            send_error(conn, "User was not connected")
            return

    username = logged_users[conn.getpeername()]

    if cmd == "LOGOUT":
        pass
    elif cmd == "CREATE_ID_ROOM":
        handle_create_id_room(conn)
    elif cmd == "CREATE_OPEN_ROOM":
        pass
    elif cmd == "JOIN_ID_ROOM":
        handle_join_id_room(conn, data)  # data=ID
    elif cmd == "JOIN_OPEN_ROOM":
        pass
    elif cmd == "EXIT_ROOM":
        pass
    elif cmd == "MY_SCORE":
        pass
    elif cmd == "TOPTEN":
        pass
    else:
        send_error(conn, "Unrecognised command")


def play(players):
    # print("waiting for first player...")
    # client_socket1, client_address1 = server_socket.accept()
    # print("the first player has joined!")
    # print("waiting for second player...")
    # client_socket2, client_address2 = server_socket.accept()
    # print("the second player has joined!")
    # players = [client_socket1, client_socket2]
    # print(client_socket1.getpeername())
    #
    # # to allow the game to begin
    # client_socket1.send("another player has joined!".encode())
    # client_socket2.send("another player has joined!".encode())

    board = game.Board()
    turn1 = True
    turn2 = False
    turn = 0

    str_board = commprot.board_to_string(board.board)
    send_to_players(players, str_board)

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
        send_to_players(players, str_board)

        turn1 = not turn1
        turn2 = not turn2
        turn += 1

    send_to_players(players, "-----end-----")

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
        send_to_players(players, "game over")


IP = '192.168.11.157'
PORT = 1984
server_socket = socket.socket()
server_socket.bind((IP, PORT))
server_socket.listen(5)


def main():
    global users
    global messages_to_send
    global not_playing_client_sockets

    print("Welcome to the trivia server")

    # users = load_user_database()
    # questions = load_questions()

    # server_socket = setup_socket()

    while True:
        rlist, wlist, xlist = select.select([server_socket] + not_playing_client_sockets, [not_playing_client_sockets]
                                            + [playing_client_sockets], [])
        for current_socket in rlist:
            if current_socket is server_socket:
                (new_socket, address) = server_socket.accept()
                print("new socket connected to server: ", new_socket.getpeername())
                not_playing_client_sockets.append(new_socket)
            else:
                cmd, msg = recv_message_and_parse(current_socket)
                if cmd != "":
                    handle_client_message(current_socket, cmd, msg)
                else:
                    p_id = current_socket.getpeername()
                    not_playing_client_sockets.remove(current_socket)
                    # handle_logout_message(current_socket)
                    print(f"Connection with client {p_id} closed.")
        send_waiting_messages(messages_to_send, wlist)


if __name__ == '__main__':
    main()
