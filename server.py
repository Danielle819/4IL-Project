import time
import commprot
import socket
import select
import game
import string
import random
import threading
from colorama import Fore, Style

# GLOBALS
users = {}  # username: {password: _, score: _}
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


# HELPER SOCKET METHODS

def build_and_send_message(conn, cmd, msg, player=False):
    """
    Builds a new message using commprot, wanted code and message.
    Prints debug info, then sends it to the given socket.
    Parameters: conn (socket object), cmd (str), msg (str)
    Returns: Nothing
    """
    message = commprot.build_message(cmd, str(msg))
    # print("----build_and_send_message - sent:", message)
    # print(Fore.GREEN + "build_and_send_message - sent:", message + Style.RESET_ALL)
    if not player:
        messages_to_send.append((conn, message))
    if player:
        try:
            conn.send(message.encode())
        except ConnectionResetError and ConnectionAbortedError:
            return False
    return True


def recv_message_and_parse(conn):
    """
    Receives a new message from given socket.
    Prints debug info, then parses the message using commprot.
    Parameters: conn (socket object)
    Returns: cmd (str) and data (str) of the received message.
    If error occurred, will return None, None
    """
    try:
        message = conn.recv(126).decode()
    except ConnectionResetError:
        return "", ""
    if message == "":
        return "", ""
    # print(Fore.GREEN + "recv_message_and_parse - got:", message + Style.RESET_ALL)
    # print(Fore.CYAN + "----recv_message_and_parse - message:", message + Style.RESET_ALL)
    cmd, msg = commprot.parse_message(message)
    # print(Fore.CYAN + "----recv_message_and_parse - commprot parsed:", cmd, "|", msg + Style.RESET_ALL)
    return cmd, msg


# OTHER HELPER METHODS

def send_waiting_messages(messages, wlist):
    for message in messages:
        current_socket, data = message
        if current_socket in wlist:
            current_socket.send(data.encode())
            messages.remove(message)


def send_error(conn, error_msg, player=False):
    """
    Send error message with given message
    Receives: socket, message error string from called function
    Returns: None
    """
    build_and_send_message(conn, "ERROR", error_msg, player)


def create_id():
    chars = string.ascii_uppercase
    return ''.join(random.choice(chars) for _ in range(6))


def send_players_board(players, board):
    str_board = commprot.board_to_string(board.board)
    return send_both_players(players[0], players[1], commprot.SERVER_CMD["updated_board_msg"], str_board, str_board)


def send_both_players(player1, player2, cmd, msg1, msg2):
    if not build_and_send_message(player1, cmd, msg1, True):
        build_and_send_message(player2, commprot.SERVER_CMD["error_msg"], "other_player_disconnected", True)
        return False
    if not build_and_send_message(player2, cmd, msg2, True):
        build_and_send_message(player1, commprot.SERVER_CMD["error_msg"], "other_player_disconnected", True)
        return False
    return True


def update_players_score(username, turns):
    """
    updates winner player's score in the users dictionary and in db
    parameters: username - string (not socket), score - int
    """

    global users

    winner_turns = (turns + 1) / 2
    if 4 <= winner_turns <= 10:
        score = 25
    elif 11 <= winner_turns <= 20:
        score = 15
    else:
        score = 10

    users[username]["score"] += score
    commprot.update_users_database(users)
    return score


def players_turn(board, player1, player2, turn):
    if not send_both_players(player1, player2, commprot.SERVER_CMD["status_msg"],
                             "your_turn", "not_your_turn"):
        return "A player disconnected"

    cmd, place = recv_message_and_parse(player1)
    if cmd == commprot.CLIENT_CMD["exit_room_msg"]:
        send_both_players(player1, player2, commprot.SERVER_CMD["game_over_msg"], "you_exited", "other_player_exited")
        return "A player exited the room"

    elif cmd == commprot.CLIENT_CMD["choose_cell_msg"]:
        place = (int(place[0]), int(place[2]))
        board.choose_cell(turn, place)
        return "GAME ON"

    return place


# COMMANDS HANDLING METHODS

def handle_client_message(conn, cmd, data):
    """
    Gets message code and data and calls the right function to handle command
    Receives: socket, message code and data
    """
    global logged_users

    if conn.getpeername() not in logged_users:
        if cmd == "LOGIN":
            username = data.split("#")[0]
            if username not in logged_users.values():
                handle_login(conn, data)
            else:
                send_error(conn, "user_logged_in")
            return
        elif cmd == "SIGNUP":
            handle_signup(conn, data)
            return
        else:
            send_error(conn, "user_not_connected")
            return

    if cmd == "LOGOUT":
        handle_logout_message(conn)
    elif cmd == "CREATE_ID_ROOM":
        handle_create_id_room(conn)
    elif cmd == "CREATE_OPEN_ROOM":
        handle_create_open_room(conn)
    elif cmd == "JOIN_ID_ROOM":
        th = threading.Thread(target=handle_join_id_room, args=(conn, data))  # data=ID
        th.start()
    elif cmd == "JOIN_OPEN_ROOM":
        th = threading.Thread(target=handle_join_open_room, args=[conn])
        th.start()
    elif cmd == "EXIT_ROOM":
        pass
    elif cmd == "MY_SCORE":
        pass
    elif cmd == "TOPTEN":
        pass
    else:
        send_error(conn, "unrecognized_command")


def handle_login(conn, data):
    global users
    global logged_users

    username, password = data.split("#")

    if username not in users:
        send_error(conn, "username_not_registered")
        return
    elif password != users[username]["password"]:
        send_error(conn, "incorrect_password")
        return

    logged_users[conn.getpeername()] = username
    build_and_send_message(conn, commprot.SERVER_CMD["login_ok_msg"], "")


def handle_logout_message(conn):
    """
    Closes the given socket remove user from logged_users dictionary
    Receives: socket
    Returns: None
    """
    global logged_users

    if conn in not_playing_client_sockets:
        not_playing_client_sockets.remove(conn)
    elif conn in playing_client_sockets:
        playing_client_sockets.remove(conn)

    p_id = conn.getpeername()
    logged_users.pop(p_id)
    print(f"Connection with client {p_id} closed.")


def handle_signup(conn, data):
    global users

    username, password = data.split("#")

    if username in users.keys():
        send_error(conn, "username_taken")
        return
    if len(username) < 6 or len(username) > 20 or not username.isalnum():
        send_error(conn, "username_restrictions")
        return
    if len(password) < 8 or len(username) > 20 or not username.isalnum():
        send_error(conn, "password_restrictions")
        return

    users[username] = {"password": password, "score": 0}
    commprot.update_users_database(users)
    build_and_send_message(conn, commprot.SERVER_CMD["signup_ok_msg"], "")


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
    build_and_send_message(conn, commprot.SERVER_CMD["create_id_room_ok_msg"], ID)


def handle_join_id_room(conn, ID):
    """
    gets a client who wants to join a room by an ID. if ID exists,
    moves both clients to the playing list and starts a thread that runs the game
    parameters: conn (client socket), ID (string)
    """
    global users

    if ID not in waiting_id_rooms:
        build_and_send_message(conn, commprot.SERVER_CMD["error_msg"], "id_not_found")
        return

    build_and_send_message(conn, commprot.SERVER_CMD["join_id_room_ok_msg"], "", player=True)

    playing_client_sockets.append(conn)
    playing_client_sockets.append(waiting_id_rooms[ID])
    not_playing_client_sockets.remove(conn)
    not_playing_client_sockets.remove(waiting_id_rooms[ID])

    players = [waiting_id_rooms[ID], conn]
    play(players)

    playing_client_sockets.remove(players[0])
    playing_client_sockets.remove(players[1])
    not_playing_client_sockets.append(players[0])
    not_playing_client_sockets.append(players[1])
    waiting_id_rooms.pop(ID)


def handle_create_open_room(conn):
    """
    gets a client who wants to start a game and puts them in the waiting list
    parameters: conn (client socket)
    """
    global waiting_open_rooms
    waiting_open_rooms.append(conn)
    build_and_send_message(conn, commprot.SERVER_CMD["create_open_room_ok_msg"], "")


def handle_join_open_room(conn):
    """
    gets a client who wants to join an open room. if there are open rooms,
    moves both clients to the playing list and starts a thread that runs the game.
    if there aren't, sends back the message
    parameters: conn (client socket)
    """
    global waiting_open_rooms
    if len(waiting_open_rooms) == 0:
        send_error(conn, "no_open_rooms")
        return

    build_and_send_message(conn, commprot.SERVER_CMD["join_open_room_ok_msg"], "", player=True)
    other_player = waiting_open_rooms[0]
    waiting_open_rooms.remove(other_player)

    playing_client_sockets.append(conn)
    playing_client_sockets.append(other_player)
    not_playing_client_sockets.remove(conn)
    not_playing_client_sockets.remove(other_player)

    players = [other_player, conn]
    play(players)

    playing_client_sockets.remove(conn)
    playing_client_sockets.remove(other_player)
    not_playing_client_sockets.append(conn)
    not_playing_client_sockets.append(other_player)


def play(players):
    board = game.Board()
    turn1 = True
    turn2 = False
    turns = 0

    usernames = [logged_users[players[0].getpeername()], logged_users[players[1].getpeername()]]

    if not send_players_board(players, board):
        return

    while turns < 42 and not game.check_board(board):
        if turn1:
            status = players_turn(board, players[0], players[1], 1)
        else:
            status = players_turn(board, players[1], players[0], 2)

        if status != "GAME ON":
            return

        if not send_players_board(players, board):
            return
        turn1 = not turn1
        turn2 = not turn2
        turns += 1

    if not send_both_players(players[0], players[1], commprot.SERVER_CMD["game_over_msg"], "", ""):
        return
    # time.sleep(0.5)

    winner = board.winner
    if winner == 1:
        send_both_players(players[0], players[1], commprot.SERVER_CMD["game_result_msg"], "you_won", "you_lost")
        score = update_players_score(usernames[0], turns)
        build_and_send_message(players[0], commprot.SERVER_CMD["game_score_msg"], str(score), True)
    elif winner == 2:
        send_both_players(players[1], players[0], commprot.SERVER_CMD["game_result_msg"], "you_won", "you_lost")
        score = update_players_score(usernames[1], turns)
        build_and_send_message(players[1], commprot.SERVER_CMD["game_score_msg"], str(score), True)

    else:
        send_both_players(players[0], players[1], commprot.SERVER_CMD["game_result_msg"], "game_over", "game_over")


IP = '192.168.11.147'
PORT = 1984
server_socket = socket.socket()
server_socket.bind((IP, PORT))
server_socket.listen(5)


def main():
    global users
    global messages_to_send
    global playing_client_sockets
    global not_playing_client_sockets

    # print(Fore.MAGENTA + "Welcome to the 4IL server!!" + Style.RESET_ALL)
    print("Welcome to the 4IL server!!")

    users = commprot.load_users_database()

    # server_socket = setup_socket()

    while True:
        rlist, wlist, xlist = select.select([server_socket] + not_playing_client_sockets,
                                            not_playing_client_sockets + playing_client_sockets, [])
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
                    handle_logout_message(current_socket)

        send_waiting_messages(messages_to_send, wlist)


if __name__ == '__main__':
    main()
