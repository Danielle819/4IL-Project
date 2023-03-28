import time
import commprot
import socket
import select
import game
import threading
from threading import *
import random
import string
# from colorama import Fore, Style

# GLOBALS
users = {}  # username: {password: _, score: _}
friends = {}
logged_users = {}  # sock.getpeername(): username
write_lock = Semaphore()
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
    print("----recv_message_and_parse - got:", message)
    cmd, msg = commprot.parse_message(message)
    # print(Fore.CYAN + "----recv_message_and_parse - commprot parsed:", cmd, "|", msg + Style.RESET_ALL)
    print("----recv_message_and_parse - commprot parsed:", cmd, "|", msg)
    return cmd, msg


# OTHER HELPER METHODS

def send_waiting_messages(messages, wlist):

    for i in range(len(messages)):
        current_socket, data = messages[0]
        # print("----send_waiting_messages - before if:", data)
        if current_socket in wlist:
            current_socket.send(data.encode())
            # print("----send_waiting_messages - sent:", data)
            messages.remove(messages[0])


def send_success(conn, msg='', player=False):
    """
    sends success message with given message
    """
    build_and_send_message(conn, "SUCCESS", msg, player)


def send_error(conn, error_msg, player=False):
    """
    Send error message with given message

    """
    build_and_send_message(conn, "ERROR", error_msg, player)


def send_longer_message(conn, cmd, data, player=False):
    bit_len = commprot.MAX_DATA_LENGTH
    data_len = len(data)
    rem = data_len % bit_len
    wholes = data_len - rem
    messages = [data[i: i + bit_len] for i in range(0, wholes, bit_len)]
    messages.append(data[-rem:])

    for i in range(len(messages) - 1):
        # print("sent", i, "out of", len(messages) - 1)
        build_and_send_message(conn, commprot.SERVER_CMD[cmd + "_part_msg"], messages[i], player)
    # print("sending final msg")
    build_and_send_message(conn, commprot.SERVER_CMD[cmd + "_fin_msg"], messages[-1], player)
    # print("done")


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
    update_database("users", username)
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


def update_database(tb, user, new_user=False, un_cng=False):
    updatedb_th = threading.Thread(target=update_database_target, args=[tb, user, new_user, un_cng])
    updatedb_th.start()
    updatedb_th.join()


def update_database_target(tb, user, new_user=False, un_cng=False):
    global users
    global friends
    global write_lock

    write_lock.acquire()
    if tb == "users":
        commprot.update_database(tb, users, user, new_user, un_cng)
    elif tb == "friends":
        commprot.update_database(tb, friends, user, new_user, un_cng)
    write_lock.release()


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

    if cmd == commprot.CLIENT_CMD["logout_msg"]:
        handle_logout(conn)
    elif cmd == commprot.CLIENT_CMD["change_username_msg"]:
        handle_change_username(conn, data)
    elif cmd == commprot.CLIENT_CMD["change_password_msg"]:
        handle_change_password(conn, data)
    elif cmd == commprot.CLIENT_CMD["create_id_room_msg"]:
        handle_create_id_room(conn)
    elif cmd == commprot.CLIENT_CMD["create_open_room_msg"]:
        handle_create_open_room(conn)
    elif cmd == commprot.CLIENT_CMD["join_id_room_msg"]:
        th = threading.Thread(target=handle_join_id_room, args=(conn, data))  # data=ID
        th.start()
    elif cmd == commprot.CLIENT_CMD["join_open_room_msg"]:
        th = threading.Thread(target=handle_join_open_room, args=[conn])
        th.start()
    elif cmd == commprot.CLIENT_CMD["my_score_msg"]:
        handle_my_score(conn)
    elif cmd == commprot.CLIENT_CMD["topten_msg"]:
        handle_top_ten(conn)
    elif cmd == commprot.CLIENT_CMD["my_friends_msg"]:
        handle_my_friends(conn)
    elif cmd == commprot.CLIENT_CMD["my_p_requests_msg"]:
        handle_my_pending_requests(conn)
    elif cmd == commprot.CLIENT_CMD["my_s_requests_msg"]:
        handle_my_sent_requests(conn)
    elif cmd == commprot.CLIENT_CMD["remove_friend_msg"]:
        handle_remove_friend(conn, data)
    elif cmd == commprot.CLIENT_CMD["send_friend_request_msg"]:
        handle_send_friend_request(conn, data)
    elif cmd == commprot.CLIENT_CMD["remove_friend_request_msg"]:
        handle_remove_friend_request(conn, data)
    elif cmd == commprot.CLIENT_CMD["accept_friend_request_msg"]:
        handle_accept_friend_request(conn, data)
    elif cmd == commprot.CLIENT_CMD["reject_friend_request_msg"]:
        handle_reject_friend_request(conn, data)
    elif cmd == commprot.CLIENT_CMD["invite_to_play_msg"]:
        handle_invite_to_play(conn, data)
    elif cmd == commprot.CLIENT_CMD["accept_invitation_msg"]:
        handle_accept_invitation(conn, data)
    elif cmd == commprot.CLIENT_CMD["reject_invitation_msg"]:
        handle_reject_invitation(conn, data)
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
    send_success(conn)


def handle_logout(conn):
    """
    Closes the given socket remove user from logged_users dictionary
    Receives: socket
    Returns: None
    """
    global logged_users
    global messages_to_send

    if conn in not_playing_client_sockets:
        not_playing_client_sockets.remove(conn)
    elif conn in playing_client_sockets:
        playing_client_sockets.remove(conn)

    for message in messages_to_send:
        if conn in message:
            messages_to_send.remove(message)

    p_id = conn.getpeername()
    try:
        logged_users.pop(p_id)
    except KeyError:
        pass
    print(f"Connection with client {p_id} closed.")


def handle_signup(conn, data):
    global users

    username, password = data.split("#")

    if username in users.keys():
        send_error(conn, "username_taken")
        return
    if len(username) <= 6 or len(username) >= 20 or not username.isalnum():
        send_error(conn, "username_restrictions")
        return
    if len(password) <= 8 or len(username) >= 20 or not username.isalnum():
        send_error(conn, "password_restrictions")
        return

    users[username] = {"password": password, "score": 0}
    update_database("users", username, new_user=True)
    send_success(conn)


def handle_change_username(conn, data):
    global users
    global logged_users

    try:
        pre_username = logged_users[conn.getpeername()]
    except KeyError:
        print("handle_change_username func - client was not logged")
        handle_logout(conn)
        return
    new_username = data

    if new_username == pre_username:
        send_error(conn, "its_current_username")
        return
    if new_username in users.keys():
        send_error(conn, "username_taken")
        return
    if len(new_username) <= 6 or len(new_username) >= 20 or not new_username.isalnum():
        send_error(conn, "username_restrictions")
        return

    # print("pre:", pre_username, "new:", new_username)
    users[new_username] = users[pre_username]
    users.pop(pre_username)
    logged_users[conn.getpeername()] = new_username
    update_database("users", user=(pre_username, new_username), un_cng=True)
    send_success(conn)


def handle_change_password(conn, data):
    global users
    global logged_users

    try:
        username = logged_users[conn.getpeername()]
    except KeyError:
        print("handle_change_password func - client was not logged")
        handle_logout(conn)
        return

    new_password = data
    pre_password = users[username]["password"]

    if new_password == pre_password:
        send_error(conn, "its_current_password")
    if len(new_password) <= 8 or len(new_password) >= 20 or not new_password.isalnum():
        send_error(conn, "password_restrictions")
        return

    users[username]["password"] = new_password
    update_database("users", username)
    send_success(conn)


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
    send_success(conn, msg=ID)


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

    send_success(conn, player=True)

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
    send_success(conn)


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

    send_success(conn, player=True)
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


def handle_my_score(conn):
    global users
    global logged_users

    try:
        username = logged_users[conn.getpeername()]
    except KeyError:
        print("handle_my_score func - client was not logged")
        handle_logout(conn)
        return

    score = users[username]["score"]
    build_and_send_message(conn, commprot.SERVER_CMD["your_score_msg"], score)


def handle_top_ten(conn):
    """
    creates the current list of the top ten players and sends to client.
    if the list is longer than 100 characters (max data field length),
    it also breaks the list to 100 char long bits to send to the client
    """
    global users

    # CREATING TOP TEN LIST
    scores = []  # a list of the users and their scores - format: (username, score)
    for username, user in zip(users.keys(), users.values()):
        scores.append((username, user["score"]))
    scores.sort(key=lambda x: x[1], reverse=True)  # sorting the list from big to small by the score

    if len(scores) < 10:
        range_num = len(scores)
    else:
        range_num = 10
    topten = ""  # the topten list string - format: username1:score1#username2:score2...
    for i in range(range_num):
        topten += scores[i][0] + ":" + str(scores[i][1]) + "#"
    topten = topten[:-1]

    # if the topten list string is within the protocol's limits, sends the client
    # the list as it is, with COMMAND indicating there are no more bits to come
    if len(topten) <= commprot.MAX_DATA_LENGTH:
        build_and_send_message(conn, commprot.SERVER_CMD["topten_fin_msg"], topten)
    else:
        send_longer_message(conn, "topten", topten)

    # if the topten list string is longer than the protocol's limit,
    # BREAKING IT INTO 100 CHAR LONG BITS
    # bit_len = commprot.MAX_DATA_LENGTH
    # tt_len = len(topten)
    # rem = tt_len % bit_len
    # wholes = tt_len - rem
    # messages = [topten[i: i + bit_len] for i in range(0, wholes, bit_len)]
    # messages.append(topten[-rem:])
    #
    # for i in range(len(messages) - 1):
    #     build_and_send_message(conn, commprot.SERVER_CMD["topten_part_msg"], messages[i])
    # build_and_send_message(conn, commprot.SERVER_CMD["topten_fin_msg"], messages[-1])


def handle_my_friends(conn):
    """
    sends client the list of their friends. if the list is longer than 100 characters
    (max data field length), it also breaks the list to 100 char long bits to send to the client
    """
    global friends
    global logged_users

    try:  # trying to get client's username (in case an error occurred, and they disconnected)
        username = logged_users[conn.getpeername()]
    except KeyError:
        print("handle_my_friends func - client was not logged")
        handle_logout(conn)
        return

    # getting user's friends list from the friends database
    if username not in friends.keys():
        friends_lst = ""
    else:
        friends_lst = friends[username]["friends"]

    # if the friends list is within the protocol's limits, sends the client
    # the list as it is, with COMMAND indicating there are no more bits to come
    if len(friends_lst) <= commprot.MAX_DATA_LENGTH:
        build_and_send_message(conn, commprot.SERVER_CMD["your_friends_fin_msg"], friends_lst)
    else:
        send_longer_message(conn, "your_friends", friends_lst)

    # if the friends list  is longer than the protocol's limit,
    # BREAKING IT INTO 100 CHAR LONG BITS
    # bit_len = commprot.MAX_DATA_LENGTH
    # fl_len = len(friends_lst)
    # rem = fl_len % bit_len
    # wholes = fl_len - rem
    # messages = [friends_lst[i: i + bit_len] for i in range(0, wholes, bit_len)]
    # messages.append(friends_lst[-rem:])
    #
    # for i in range(len(messages) - 1):
    #     build_and_send_message(conn, commprot.SERVER_CMD["your_friends_part_msg"], messages[i])
    # build_and_send_message(conn, commprot.SERVER_CMD["your_friends_fin_msg"], messages[-1])


def handle_my_pending_requests(conn):
    global friends
    global logged_users

    try:  # trying to get client's username (in case an error occurred, and they disconnected)
        username = logged_users[conn.getpeername()]
    except KeyError:
        print("handle_my_pending_requests func - client was not logged")
        handle_logout(conn)
        return

    if username not in friends.keys():
        reqs = ""
    else:
        reqs = friends[username]["pending_requests"]

    if len(reqs) <= commprot.MAX_DATA_LENGTH:
        build_and_send_message(conn, commprot.SERVER_CMD["your_p_requests_fin_msg"], reqs)
    else:
        send_longer_message(conn, "your_p_requests", reqs)


def handle_my_sent_requests(conn):
    global friends
    global logged_users

    try:  # trying to get client's username (in case an error occurred, and they disconnected)
        username = logged_users[conn.getpeername()]
    except KeyError:
        print("handle_my_sent_requests func - client was not logged")
        handle_logout(conn)
        return

    if username not in friends.keys():
        reqs = ""
    else:
        reqs = friends[username]["sent_requests"]

    if len(reqs) <= commprot.MAX_DATA_LENGTH:
        build_and_send_message(conn, commprot.SERVER_CMD["your_s_requests_fin_msg"], reqs)
    else:
        send_longer_message(conn, "your_s_requests", reqs)


def handle_remove_friend(conn, data):
    global friends

    try:  # trying to get client's username (in case an error occurred, and they disconnected)
        username = logged_users[conn.getpeername()]
    except KeyError:
        print("handle_remove_friend func - client was not logged")
        handle_logout(conn)
        return

    if data == username:
        send_error(conn, "your_username")
        return

    if username not in friends.keys():
        send_error(conn, "friend_not_found")
        return

    friends_str = friends[username]["friends"]
    friends_lst = friends_str.split("#")

    try:
        friends_lst.remove(data)
    except ValueError:
        send_error(conn, "friend_not_found")
        return

    friends_str = ""
    for friend in friends_lst:
        friends_str += friend + "#"
    friends_str = friends_str[:-1]
    friends[username]["friends"] = friends_str
    update_database("friends", username)
    send_success(conn)

    # REMOVING USER FROM THE OTHER FRIEND"S FRIEND LIST
    if data not in friends.keys():
        print("other friend was not found on friends db")
        return

    other_friend_str = friends[data]["friends"]
    other_friend_lst = other_friend_str.split("#")

    try:
        other_friend_lst.remove(username)
    except ValueError:
        print("user was not in other friend's list")

    other_friend_str = ""
    for friend in other_friend_lst:
        other_friend_str += friend + "#"
    other_friend_str = other_friend_str[:-1]
    friends[data]["friends"] = other_friend_str
    update_database("friends", data)


def handle_send_friend_request(conn, data):
    global friends
    global users
    global logged_users
    
    if data not in users.keys():
        send_error(conn, "user_not_found")
        return

    try:
        username = logged_users[conn.getpeername()]
    except KeyError:
        print("handle_send_friend_request func - client was not logged")
        handle_logout(conn)
        return

    # check if the username is the user's first
    if data == username:
        send_error(conn, "your_username")
        return

    if username not in friends.keys():
        friends[username] = {"friends": '', "pending_requests": '', "sent_requests": data}
        update_database("friends", username, new_user=True)
        send_success(conn)
    else:
        sent_reqs = friends[username]["sent_requests"]
        friends_str = friends[username]["friends"]
        pend_reqs = friends[username]["pending_requests"]
        # checks if other user is already in user's friends list
        friends_lst = friends_str.split("#")
        if data in friends_lst:
            send_error(conn, "user_in_your_friends")
            return
        # checks if other user is in user's pending requestes list
        pend_reqs_lst = pend_reqs.split("#")
        if data in pend_reqs_lst:
            send_error(conn, "user_in_pend_requests")
            return

        if sent_reqs == "":
            sent_reqs = data
        else:
            # checks if other user is already in user's sent requests list
            sent_reqs_lst = sent_reqs.split("#")
            if data in sent_reqs_lst:
                send_error(conn, "user_in_sent_requests")
                return
            sent_reqs += "#" + data
        friends[username]["sent_requests"] = sent_reqs
        update_database("friends", username)
        send_success(conn)

    if data in friends.keys():
        pend_reqs = friends[data]["pending_requests"]
        if pend_reqs == "":
            pend_reqs = username
        else:
            pend_reqs += "#" + username
        friends[data]["pending_requests"] = pend_reqs
        update_database("friends", data)
    else:
        friends[data] = {"friends": '', "pending_requests": username, "sent_requests": ''}
        update_database("friends", data, new_user=True)


def handle_remove_friend_request(conn, data):
    global friends
    global logged_users

    try:
        username = logged_users[conn.getpeername()]
    except KeyError:
        print("handle_remove_friend_request func - client was not logged")
        handle_logout(conn)
        return

    if username == data:
        send_error(conn, "your_username")
        return
    if username not in friends.keys():
        send_error(conn, "user_not_sent")
        return

    # removing request from username's sent requests
    sent_reqs_str = friends[username]["sent_requests"]
    sent_reqs_lst = sent_reqs_str.split("#")
    try:
        sent_reqs_lst.remove(data)
    except ValueError:
        send_error(conn, "user_not_sent")
        return
    sent_reqs_str = ""
    for req in sent_reqs_lst:
        sent_reqs_str += req + "#"
    sent_reqs_str = sent_reqs_str[:-1]
    friends[username]["sent_requests"] = sent_reqs_str
    update_database("friends", username)
    send_success(conn)

    if data not in friends.keys():
        print("handle_remove_friend_request func ERROR: other user was not in friends db")
        return

    # removing request from "data"'s pending requests
    pend_reqs_str = friends[data]["pending_requests"]
    pend_reqs_lst = pend_reqs_str.split("#")
    try:
        pend_reqs_lst.remove(username)
    except ValueError:
        print("handle_remove_friend_request func ERROR: username was not in other user's pending_requests")
    else:
        pend_reqs_str = ""
        for req in pend_reqs_lst:
            pend_reqs_str += req + "#"
        pend_reqs_str = pend_reqs_str[:-1]
        friends[data]["pending_requests"] = pend_reqs_str
        update_database("friends", data)

    

def handle_accept_friend_request(conn, data):
    global friends
    global logged_users

    try:
        username = logged_users[conn.getpeername()]
    except KeyError:
        print("handle_accept_friend_request func - client was not logged")
        handle_logout(conn)
        return
    if username == data:
        send_error(conn, "your_username")
        return
    if username not in friends.keys():
        send_error(conn, "user_not_pending")
        return

    pend_reqs_str = friends[username]["pending_requests"]
    pend_reqs_lst = pend_reqs_str.split("#")

    try:
        pend_reqs_lst.remove(data)
    except ValueError:
        send_error(conn, "user_not_pending")
        return

    # removing "data" from user's pending list
    pend_reqs_str = ""
    for req in pend_reqs_lst:
        pend_reqs_str += req + "#"
    pend_reqs_str = pend_reqs_str[:-1]
    friends[username]["pending_requests"] = pend_reqs_str
    update_database("friends", username)

    # adding data to user's friends list
    friends_str = friends[username]["friends"]
    if friends_str == "":
        friends_str = data
    else:
        friends_str += "#" + data
    friends[username]["friends"] = friends_str
    update_database("friends", username)
    send_success(conn)

    # HANDLING OTHER USER'S (DATA'S) FRIENDS LISTS
    if data not in friends.keys():
        friends[data] = {"friends": username, "pending_requests": '', "sent_requests": ''}
        update_database("friends", data, new_user=True)
        print("handle_accept_friend_request func ERROR: other user was not in friends db")
        return

    # removing username from "data"'s sent list
    sent_reqs_str = friends[data]["sent_requests"]
    sent_reqs_lst = sent_reqs_str.split("#")
    try:
        sent_reqs_lst.remove(username)
    except ValueError:
        print("handle_accept_friend_request func ERROR: other user didnt have username in sent_requests")
    else:
        sent_reqs_str = ""
        for req in sent_reqs_lst:
            sent_reqs_str += req + "#"
        sent_reqs_str = sent_reqs_str[:-1]
        friends[data]["sent_requests"] = sent_reqs_str
        update_database("friends", data)
    # adding username to "data"'s friends list
    friends_str = friends[data]["friends"]
    if friends_str == "":
        friends_str = username
    else:
        friends_str += "#" + username
    friends[data]["friends"] = friends_str
    update_database("friends", data)


def handle_reject_friend_request(conn, data):
    global friends
    global logged_users

    try:
        username = logged_users[conn.getpeername()]
    except KeyError:
        print("handle_accept_friend_request func - client was not logged")
        handle_logout(conn)
        return
    if username == data:
        send_error(conn, "your_username")
        return
    if username not in friends.keys():
        send_error(conn, "user_not_pending")
        return

    pend_reqs_str = friends[username]["pending_requests"]
    pend_reqs_lst = pend_reqs_str.split("#")

    try:
        pend_reqs_lst.remove(data)
    except ValueError:
        send_error(conn, "user_not_pending")
        return

    # removing "data" from user's pending list
    pend_reqs_str = ""
    for req in pend_reqs_lst:
        pend_reqs_str += req + "#"
    pend_reqs_str = pend_reqs_str[:-1]
    friends[username]["pending_requests"] = pend_reqs_str
    update_database("friends", username)
    send_success(conn)

    # HANDLING OTHER USER"S (DATA'S) FRIENDS LISTS
    if data not in friends.keys():
        print("handle_accept_friend_request func ERROR: other user was not in friends db")
        return

    # removing username from "data"'s sent list
    sent_reqs_str = friends[data]["sent_requests"]
    sent_reqs_lst = sent_reqs_str.split("#")
    try:
        sent_reqs_lst.remove(username)
    except ValueError:
        print("handle_accept_friend_request func ERROR: other user didnt have username in sent_requests")
    else:
        sent_reqs_str = ""
        for req in sent_reqs_lst:
            sent_reqs_str += req + "#"
        sent_reqs_str = sent_reqs_str[:-1]
        friends[data]["sent_requests"] = sent_reqs_str
        update_database("friends", data)


def handle_invite_to_play(conn, data):
    pass


def handle_accept_invitation(conn, data):
    pass


def handle_reject_invitation(conn, data):
    pass


# GAME OPERATOR

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


# SERVER SETUP

def main():
    global users
    global friends
    global messages_to_send
    global playing_client_sockets
    global not_playing_client_sockets

    # print(Fore.MAGENTA + "Welcome to the 4IL server!!" + Style.RESET_ALL)
    print("Welcome to the 4IL server!!")

    users = commprot.read_database("users")
    friends = commprot.read_database("friends")

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
                    handle_logout(current_socket)

        send_waiting_messages(messages_to_send, wlist)


if __name__ == '__main__':
    IP = '127.0.0.1'
    PORT = 1985
    server_socket = socket.socket()
    server_socket.bind((IP, PORT))
    server_socket.listen(5)

    main()

