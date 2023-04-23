# COSTUME MODULES IMPORTS
import commprot
import game
# OPERATIONS NECESSITY IMPORTS
import socket
import select
import threading
from threading import *
# HELPER MODULES
import random
import string
import time
# from colorama import Fore, Style

# GLOBALS
users = {}  # username: {password: _, score: _}
friends = {}  # username: {friends: _, pending_requests: _, sent_requests: _}
topten = []  # (username, score)
logged_users = {}  # client_socket.getpeername(): username
user_sockets = {}  # username: socket
# messages_to_send = []  # (socket, message)
not_playing_clients = []  # client_socket
playing_clients = []  # client_socket
waiting_id_rooms = {}  # id : (waiting) client_socket
waiting_open_rooms = []  # (waiting) client_socket
waiting_invitations = []  # (inviting_username, inviting_socket, invited_username, invited_socket)
# SEMAPHORE LOCKS
write_lock = Semaphore()  # lock for updating database
edit_logged_users = Semaphore()  # lock for editing the logged_users dict
edit_playing_lists = Semaphore()  # lock for editing the not_playing_clients and playing_clients lists
edit_waiting_invitations = Semaphore()


# HELPER SOCKET METHODS

def build_and_send_message(conn, cmd, msg, direct=False):
    message = commprot.build_message(cmd, str(msg))
    # print(Fore.GREEN + "build_and_send_message - sent:", message + Style.RESET_ALL)
    try:
        conn.send(message.encode())
        print("----build_and_send_message - SENT:", message)
    except:
        print("----build_and_send_message - NOT SENT:", message)
        handle_logout(conn)
        return False
    return True


def recv_message_and_parse(conn, settimeout=0):
    try:
        if settimeout != 0:
            conn.settimeout(settimeout)
        message = conn.recv(126).decode()
    except TimeoutError:
        return None, None
    except:
        return "", ""

    if message == "":
        print("----recv_message_and_parse - GOT: EMPTY MESSAGE")
        return "", ""
    # print(Fore.CYAN + "----recv_message_and_parse - message:", message + Style.RESET_ALL)
    print("----recv_message_and_parse - GOT:", message)
    cmd, msg = commprot.parse_message(message)
    # print(Fore.CYAN + "----recv_message_and_parse - commprot parsed:", cmd, "|", msg + Style.RESET_ALL)
    print("----recv_message_and_parse - commprot parsed:", cmd, ",", msg)
    return cmd, msg


# OTHER HELPER METHODS

def send_success(conn, msg='', direct=False):
    """
    sends success message with given message
    """
    build_and_send_message(conn, "SUCCESS", msg, direct)


def send_error(conn, error_msg='', direct=False):
    """
    Send error message with given message

    """
    build_and_send_message(conn, "ERROR", error_msg, direct)


def send_longer_message(conn, cmd, data, direct=False):
    bit_len = commprot.MAX_DATA_LENGTH
    data_len = len(data)
    rem = data_len % bit_len
    wholes = data_len - rem
    messages = [data[i: i + bit_len] for i in range(0, wholes, bit_len)]
    messages.append(data[-rem:])

    for i in range(len(messages) - 1):
        # print("sent", i, "out of", len(messages) - 1)
        build_and_send_message(conn, commprot.SERVER_CMD[cmd + "_part_msg"], messages[i], direct)
    # print("sending final msg")
    build_and_send_message(conn, commprot.SERVER_CMD[cmd + "_fin_msg"], messages[-1], direct)
    # print("done")


def set_topten():
    global users, topten
    # CREATING TOP TEN LIST
    topten = []  # a list of the users and their scores - format: (username, score)
    for username, user in zip(users.keys(), users.values()):
        topten.append((username, user["score"]))
    topten.sort(key=lambda x: x[1], reverse=True)  # sorting the list from big to small by the score

    if len(topten) > 10:
        topten = topten[:10]


def create_id():
    chars = string.ascii_uppercase
    return ''.join(random.choice(chars) for _ in range(6))


def send_players_board(players, board):
    str_board = commprot.board_to_string(board.board)
    return send_both_players(players[0], players[1], commprot.SERVER_CMD["updated_board_msg"], str_board, str_board)


def send_both_players(player1, player2, cmd, msg1, msg2):
    if not build_and_send_message(player1, cmd, msg1, True):
        print("send_both_players func sent error")
        build_and_send_message(player2, commprot.SERVER_CMD["error_msg"], "other_player_disconnected", True)
        return False
    if not build_and_send_message(player2, cmd, msg2, True):
        print("send_both_players func sent error")
        build_and_send_message(player1, commprot.SERVER_CMD["error_msg"], "other_player_disconnected", True)
        return False
    return True


def send_to_players(player1, player2, cmd1, cmd2, msg1, msg2):
    if not build_and_send_message(player1, cmd1, msg1, True):
        print("send_to_players func sent error")
        build_and_send_message(player2, commprot.SERVER_CMD["error_msg"], "other_player_disconnected", True)
        return False
    if not build_and_send_message(player2, cmd2, msg2, True):
        print("send_to_players func sent error")
        build_and_send_message(player1, commprot.SERVER_CMD["error_msg"], "other_player_disconnected", True)
        return False
    return True


def players_turn(board, player1, player2, turn):
    if not send_both_players(player1, player2, commprot.SERVER_CMD["status_msg"],
                             "your_turn", "not_your_turn"):
        return "A player disconnected", ""

    # print("players_turn func - waiting for player's choice...")
    cmd, choice = recv_message_and_parse(player1)
    if cmd == commprot.CLIENT_CMD["exit_room_msg"]:
        send_success(player1)
        send_error(player2, "other_player_exited", direct=True)
        return "A player exited the room", ""
    elif cmd == commprot.CLIENT_CMD["choose_cell_msg"]:
        place = (int(choice[0]), int(choice[2]))
        board.choose_cell(turn, place)
        return "GAME ON", choice
    else:
        print("a player disconnected")
        send_error(player2, "other_player_disconnected", direct=True)
        return "A player disconnected", ""


def update_players_score(username, turns):
    """
    updates winner player's score in the users dictionary and in db
    parameters: username - string (not socket), turns - int
    """
    global users, topten, user_sockets

    winner_turns = (turns + 1) / 2
    if 4 <= winner_turns <= 6:
        score = 25
    elif 7 <= winner_turns <= 15:
        score = 10
    else:
        score = 5

    users[username]["score"] += score
    update_database("users", username)
    if users[username]["score"] > topten[len(topten) - 1][1]:
        set_topten()
        for user_socket in user_sockets.values():
            build_and_send_message(user_socket, commprot.SERVER_CMD["topten_updated_msg"], "")
    return score


def update_database(tb, user, new_user=False, un_cng=False):
    """
    function creates the thread that actually edits the database
    """
    updatedb_th = threading.Thread(target=update_database_target, args=[tb, user, new_user, un_cng])
    updatedb_th.start()
    updatedb_th.join()


def update_database_target(tb, user, new_user=False, un_cng=False):
    global users, friends, write_lock

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

    # print("handle_client_message func - ", cmd)
    if cmd == commprot.CLIENT_CMD["logout_msg"]:
        handle_logout(conn)
    # elif cmd == commprot.CLIENT_CMD["change_username_msg"]:
    #     handle_change_username(conn, data)
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
    elif cmd == commprot.CLIENT_CMD["invite_to_play_msg"]:
        handle_invite_to_play(conn, data)
    elif cmd == commprot.CLIENT_CMD["accept_invitation_msg"]:
        th = threading.Thread(target=handle_accept_invitation, args=[conn, data])
        th.start()
    elif cmd == commprot.CLIENT_CMD["reject_invitation_msg"]:
        handle_reject_invitation(conn, data)
    elif cmd == commprot.CLIENT_CMD["remove_invitation_msg"]:
        handle_remove_invitation(conn)
    elif cmd == commprot.CLIENT_CMD["exit_room_msg"] and data != "":
        handle_exit_room(conn, data)
    elif cmd == commprot.CLIENT_CMD["my_score_msg"]:
        handle_my_score(conn)
    elif cmd == commprot.CLIENT_CMD["topten_msg"]:
        handle_top_ten(conn)
    elif cmd == commprot.CLIENT_CMD["logged_users_msg"]:
        handle_logged_users(conn)
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

    else:
        send_error(conn, "unrecognized_command")


def handle_login(conn, data):
    global users, logged_users

    username, password = data.split("#")

    if username not in users:
        send_error(conn, "username_not_registered")
        return
    elif password != users[username]["password"]:
        send_error(conn, "incorrect_password")
        return

    logged_users[conn.getpeername()] = username
    send_success(conn, direct=True)

    # connecting to client's listening socket
    cmd, data = recv_message_and_parse(conn)
    if cmd != commprot.CLIENT_CMD["my_address_msg"]:
        send_error(conn, "address_not_received")
        handle_logout(conn)
        return

    ipadd, port = data.split("#")
    port = int(port)
    try:
        user_socket = socket.socket()
        user_socket.connect((ipadd, port))
        user_sockets[username] = user_socket
    except:
        print("data:", data)
        send_error(conn)
    else:
        send_success(conn)


def handle_logout(conn):
    """
    Closes the given socket and: removes client from playing/not playing lists,
    removes client from waiting rooms and ivitations lists if in one,
    removes client from logged_users dictionary,
    closes connection to client's listening socket and closes client's socket
    """
    global playing_clients, not_playing_clients, waiting_id_rooms, waiting_open_rooms
    global logged_users, waiting_invitations, user_sockets
    # global messages_to_send

    # removing client from the playing lists
    edit_playing_lists.acquire()
    if conn in not_playing_clients:
        not_playing_clients.remove(conn)
    elif conn in playing_clients:
        playing_clients.remove(conn)
    edit_playing_lists.release()
    # removing client from waiting_id_rooms if in it
    if conn in waiting_id_rooms.values():
        waiting_id_rooms_temp = {key: value for key, value in waiting_id_rooms.items() if value is not conn}
        waiting_id_rooms = waiting_id_rooms_temp
    # removing client from waiting_open_rooms if in it
    elif conn in waiting_open_rooms:
        waiting_open_rooms.remove(conn)

    # removing an invitation with client
    edit_waiting_invitations.acquire()
    wait_inv_to_remove = []
    for wait_inv in waiting_invitations:
        if conn is wait_inv[1]:
            username, other_username = wait_inv[0], wait_inv[2]
            wait_inv_to_remove.append(wait_inv)
            try:
                other_user_socket = user_sockets[other_username]
            except KeyError:
                print("handle_logout func - in waiting invitations, other player not in user_sockets")
            else:
                build_and_send_message(other_user_socket, commprot.SERVER_CMD["remove_invitation_msg"], username, direct=True)
        elif conn is wait_inv[3]:
            other_conn = wait_inv[1]
            wait_inv_to_remove.append(wait_inv)
            send_error(other_conn, "invited_disconnected")
    for wait_inv in wait_inv_to_remove:
        waiting_invitations.remove(wait_inv)
    edit_waiting_invitations.release()

    # removing all messages for client
    # for message in messages_to_send:
    #     if conn in message:
    #         messages_to_send.remove(message)

    p_id = conn.getpeername()
    try:
        username = logged_users[p_id]
    except KeyError:
        print("handle_logout func - username was not in logged_users")
        return

    # removing client from logged_users
    edit_logged_users.acquire()
    logged_users.pop(p_id)
    print(username, "has logged out")
    edit_logged_users.release()

    # closing client's user_socket
    try:
        user_sockets[username].close()
        user_sockets.pop(username)
    except KeyError:
        print("handle_logout func - username was not in user_sockets")
        return

    conn.close()
    print(f"Connection with client {p_id} closed.")


def handle_signup(conn, data):
    global users, friends

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
    update_database("users", username, new_user=True)
    friends[username] = {"friends": '', "pending_requests": '', "sent_requests": ''}
    update_database("friends", username, new_user=True)
    send_success(conn)


# def handle_change_username(conn, data):
#     global users, logged_users, user_sockets
#
#     try:
#         old_username = logged_users[conn.getpeername()]
#     except KeyError:
#         print("handle_change_username func - client was not logged")
#         handle_logout(conn)
#         return
#     new_username = data
#
#     if new_username == old_username:
#         send_error(conn, "its_current_username")
#         return
#     if new_username in users.keys():
#         send_error(conn, "username_taken")
#         return
#     if len(new_username) < 6 or len(new_username) > 20 or not new_username.isalnum():
#         send_error(conn, "username_restrictions")
#         return
#
#     users[new_username] = users[old_username]
#     users.pop(old_username)
#     update_database("users", user=(old_username, new_username), un_cng=True)
#     logged_users[conn.getpeername()] = new_username
#     try:
#         user_socket = user_sockets[old_username]
#     except KeyError:
#         print("handle_change_username func - old username was not in user_sockets")
#     else:
#         user_sockets.pop(old_username)
#         user_sockets[new_username] = user_socket
#     send_success(conn)


def handle_change_password(conn, data):
    global users, logged_users

    try:
        username = logged_users[conn.getpeername()]
    except KeyError:
        print("handle_change_password func - client was not logged")
        handle_logout(conn)
        return

    new_password = data
    old_password = users[username]["password"]

    if new_password == old_password:
        send_error(conn, "its_current_password")
        return
    if len(new_password) < 8 or len(new_password) > 20 or not new_password.isalnum():
        send_error(conn, "password_restrictions")
        return

    users[username]["password"] = new_password
    update_database("users", username)
    send_success(conn)


def handle_create_id_room(conn):
    """
    gets a client who wants to start a game, sends them an ID
    and puts them in the waiting list
    """
    global waiting_id_rooms
    ID = create_id()
    while ID in waiting_id_rooms:
        ID = create_id()
    waiting_id_rooms[ID] = conn
    send_success(conn, msg=ID)


def handle_join_id_room(conn, ID):
    """
    gets a client who wants to join a room by an ID. if ID exists,
    moves both clients to the playing list and runs the game
    after game ends, moving clients back to the not playing list
    parameters: conn (client socket), ID (string)
    """
    global waiting_id_rooms, not_playing_clients, playing_clients, logged_users

    if ID not in waiting_id_rooms:
        build_and_send_message(conn, commprot.SERVER_CMD["error_msg"], "id_not_found")
        return
    send_success(conn, direct=True)

    other_player = waiting_id_rooms[ID]
    waiting_id_rooms.pop(ID)

    # moving clients to the playing list and adding them to the playing rooms list
    edit_playing_lists.acquire()
    try:
        not_playing_clients.remove(conn)
    except ValueError:
        send_error(other_player, "other_player_disconnected")
        edit_playing_lists.release()
        return
    try:
        not_playing_clients.remove(other_player)
    except ValueError:
        send_error(conn, "other_player_disconnected")
        edit_playing_lists.release()
        return
    playing_clients.append(conn)
    playing_clients.append(other_player)
    edit_playing_lists.release()

    players = [other_player, conn]
    play(players)

    # moving clients back to the not playing list and removing them from the playing rooms list
    edit_playing_lists.acquire()
    try:
        playing_clients.remove(conn)
        not_playing_clients.append(conn)
    except ValueError:
        print("handle_join_id_room func - error: conn was not in playing clients")
    try:
        playing_clients.remove(other_player)
        not_playing_clients.append(other_player)
    except ValueError:
        print("handle_join_id_room func - error: other player was not in playing clients")
    edit_playing_lists.release()


def handle_create_open_room(conn):
    """
    gets a client who wants to start a game and puts them in the waiting list
    """
    global waiting_open_rooms
    waiting_open_rooms.append(conn)
    send_success(conn)


def handle_join_open_room(conn):
    """
    gets a client who wants to join an open room. if there are open rooms,
    moves both clients to the playing list and runs the game. After game ends,
    moves them back to the not playing list.
    if there are no open rooms, sends back the message.
    """
    global waiting_open_rooms
    if len(waiting_open_rooms) == 0:
        send_error(conn, "no_open_rooms")
        return
    send_success(conn, direct=True)

    other_player = waiting_open_rooms[0]
    waiting_open_rooms.remove(other_player)

    # moving clients to the playing list and adding them to the playing rooms list
    edit_playing_lists.acquire()
    try:
        not_playing_clients.remove(conn)
    except ValueError:
        send_error(other_player, "other_player_disconnected")
        edit_playing_lists.release()
        return
    try:
        not_playing_clients.remove(other_player)
    except ValueError:
        send_error(conn, "other_player_disconnected")
        edit_playing_lists.release()
        return
    playing_clients.append(conn)
    playing_clients.append(other_player)
    edit_playing_lists.release()

    players = [other_player, conn]
    play(players)

    # moving clients back to the not playing list and removing them from the playing rooms list
    edit_playing_lists.acquire()
    try:
        playing_clients.remove(conn)
        not_playing_clients.append(conn)
    except ValueError:
        print("handle_join_open_room func - error: conn was not in playing clients")
    try:
        playing_clients.remove(other_player)
        not_playing_clients.append(other_player)
    except ValueError:
        print("handle_join_open_room func - error: other player was not in playing clients")
    edit_playing_lists.release()


def handle_invite_to_play(conn, data):
    global users, logged_users, playing_clients, user_sockets, waiting_invitations

    if data not in users.keys():  # if wanted user does not exist
        send_error(conn, "user_not_found")
        return
    if data not in logged_users.values():  # if wanted user is not connected to server
        send_error(conn, "user_not_currently_connected")
        return

    try:
        username = logged_users[conn.getpeername()]
    except KeyError:
        print("handle_invite_to_play func - client was not logged")
        handle_logout(conn)
        return
    if username == data:  # if the user tried to invite themselves
        send_error(conn, "your_username")
        return

    # getting wanted user's peername by username
    edit_logged_users.acquire()
    p_id = ""
    for p, u in zip(logged_users.keys(), logged_users.values()):
        if u == data:
            p_id = p
    edit_logged_users.release()
    # if it's not found:
    if p_id == "":
        send_error(conn, "user_not_currently_connected")
        return

    # find other user's connection in the not_playing list
    edit_playing_lists.acquire()
    other_conn = None
    for sock in not_playing_clients:
        if sock.getpeername() == p_id:
            other_conn = sock
    edit_playing_lists.release()
    if other_conn is None:  # if not found in this list, user is currently playing
        send_error(conn, "user_is_playing")
        return

    # check if other user is in a waiting room already
    if other_conn in waiting_id_rooms.values() or other_conn in waiting_open_rooms:
        send_error(conn, "user_is_playing")
        return

    edit_waiting_invitations.acquire()
    for wait_inv in waiting_invitations:
        if username in wait_inv and data in wait_inv:
            send_error(conn, "invitation_exist")
            edit_waiting_invitations.release()
            return
    edit_waiting_invitations.release()

    try:  # getting the socket to connected to other user's listening socket
        user_socket = user_sockets[data]
    except KeyError:
        print("handle_invite_to_play func - invited client not in user_sockets")
        send_error(conn, "invitation_not_sent")
        return

    build_and_send_message(user_socket, commprot.SERVER_CMD["playing_invitation_msg"], username, direct=True)
    response, _ = recv_message_and_parse(user_socket, settimeout=20)
    # if invitation was not received properly:
    if response != commprot.CLIENT_CMD["invitation_received_msg"]:
        print("handle_invite_to_play func ERROR - invitation didnt reach client. cmd:", response, "msg:", _)
        send_error(conn, "invitation_not_sent")
        return
    edit_waiting_invitations.acquire()
    waiting_invitations.append((username, conn, data, other_conn))
    edit_waiting_invitations.release()
    # if all above went well, send inviting user that invitation was sent
    send_success(conn)


def handle_accept_invitation(conn, data):
    global waiting_invitations, logged_users, playing_clients, not_playing_clients

    other_conn = None
    invitation = None
    edit_waiting_invitations.acquire()
    for wait_inv in waiting_invitations:
        if wait_inv[0] == data and wait_inv[3] is conn:
            invitation = wait_inv
            other_conn = wait_inv[1]
    if invitation is None:
        send_error(conn, "invitation_not_found")
        edit_waiting_invitations.release()
        return
    waiting_invitations.remove(invitation)
    edit_waiting_invitations.release()

    if data not in logged_users.values():
        send_error(conn, "other_player_disconnected")
        return

    send_success(conn, direct=True)
    build_and_send_message(other_conn, commprot.SERVER_CMD["invitation_accepted_msg"], "", direct=True)

    edit_playing_lists.acquire()
    try:
        not_playing_clients.remove(conn)
    except ValueError:
        send_error(other_conn, "other_player_disconnected")
        playing_clients.append(other_conn)
        return
    try:
        not_playing_clients.remove(other_conn)
    except ValueError:
        send_error(conn, "other_player_disconnected")
        playing_clients.append(other_conn)
        return
    playing_clients.append(conn)
    playing_clients.append(other_conn)
    edit_playing_lists.release()

    players = [other_conn, conn]
    play(players)

    edit_playing_lists.acquire()
    try:
        playing_clients.remove(conn)
        not_playing_clients.append(conn)
    except ValueError:
        print("handle_accept_invitation func - error: conn was not in playing clients")
    try:
        playing_clients.remove(other_conn)
        not_playing_clients.append(other_conn)
    except ValueError:
        print("handle_accept_invitation func - error: other player was not in playing clients")
    edit_playing_lists.release()


def handle_reject_invitation(conn, data):
    global waiting_invitations

    remove_inv = None
    edit_waiting_invitations.release()
    for wait_inv in waiting_invitations:
        if wait_inv[0] == data and wait_inv[3] is conn:
            remove_inv = wait_inv
    if remove_inv is None:
        send_error(conn, "invitation_not_found")
        return
    waiting_invitations.remove(remove_inv)
    edit_waiting_invitations.release()

    other_conn = remove_inv[1]
    build_and_send_message(other_conn, commprot.SERVER_CMD["invitation_rejected_msg"], "")
    send_success(conn)


def handle_remove_invitation(conn):
    global waiting_invitations, user_sockets

    remove_inv = None

    edit_waiting_invitations.acquire()
    for wait_inv in waiting_invitations:
        if wait_inv[1] is conn:
            remove_inv = wait_inv
    if remove_inv is not None:
        waiting_invitations.remove(remove_inv)
        build_and_send_message(conn, commprot.SERVER_CMD["invitation_removed_msg"], "")
        username = remove_inv[0]
        try:
            other_user_socket = user_sockets[remove_inv[2]]
        except KeyError:
            print("handle_remove_invitation func - other user was not in user_sockets")
        else:
            build_and_send_message(other_user_socket, commprot.SERVER_CMD["remove_invitation_msg"], username)
    else:
        send_error(conn, "invitation_not_found")
    edit_waiting_invitations.release()


def handle_exit_room(conn, data):
    """
    gets in data the type of room the client wants to exit - id room, open room
    or an invitation room, so server can remove them from the appropriate list
    """
    global waiting_id_rooms, waiting_open_rooms, waiting_invitations
    # removing client from waiting open rooms list
    if data == "open":
        try:
            waiting_open_rooms.remove(conn)
            print("client was removed from open rooms")
            send_success(conn, "exited_room")
        except ValueError:
            print("handle_exit_room func - error: client wasn't found in waiting_open_rooms")
    # removing client from waiting invitations list
    elif data == "invitation":
        inv_remove = None
        for wait_inv in waiting_invitations:
            if wait_inv[1] is conn:
                inv_remove = conn
        if inv_remove is None:
            print("handle_exit_room func - error: client wasn't found in waiting_invitations")
            return
        waiting_invitations.remove(inv_remove)
        print("client was removed from waiting invitations")
        send_success(conn, "exited_room")
    # removing client from waiting id rooms list
    else:
        try:
            waiting_id_rooms.pop(data)
            print("client was removed from id rooms")
            send_success(conn, "exited_room")
        except KeyError:
            print("handle_exit_room func - error: client wasn't found in waiting_id_rooms")


def handle_my_score(conn):
    global users, logged_users

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
    sends client list of current top ten players.
    if the list is longer than 100 characters (max data field length),
    it also breaks the list to 100 char long bits to send to the client
    """
    global topten

    topten_str = ""  # the topten list string - format: username1:score1#username2:score2...
    for i in range(len(topten)):
        topten_str += topten[i][0] + ":" + str(topten[i][1]) + "#"
    topten_str = topten_str[:-1]

    # if the topten list string is within the protocol's limits, sends the client
    # the list as it is, with COMMAND indicating there are no more bits to come
    if len(topten_str) <= commprot.MAX_DATA_LENGTH:
        build_and_send_message(conn, commprot.SERVER_CMD["topten_fin_msg"], topten_str)
    else:
        send_longer_message(conn, "topten", topten_str)


def handle_logged_users(conn):
    global logged_users
    logged = ""
    for user in logged_users.values():
        logged += user + "#"
    logged = logged[:-1]

    if len(logged) <= commprot.MAX_DATA_LENGTH:
        build_and_send_message(conn, commprot.SERVER_CMD["logged_users_fin_msg"], logged)
    else:
        send_longer_message(conn, "logged_users", logged)


def handle_my_friends(conn):
    """
    sends client the list of their friends. if the list is longer than 100 characters
    (max data field length), it also breaks the list to 100 char long bits to send to the client
    """
    global friends, logged_users

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

    if len(friends_lst) <= commprot.MAX_DATA_LENGTH:
        build_and_send_message(conn, commprot.SERVER_CMD["your_friends_fin_msg"], friends_lst)
    else:
        send_longer_message(conn, "your_friends", friends_lst)


def handle_my_pending_requests(conn):
    global friends, logged_users

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
    global friends, logged_users

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
    if data in user_sockets:
        build_and_send_message(user_sockets[data], commprot.SERVER_CMD["friends_updated_msg"], "")


def handle_send_friend_request(conn, data):
    global friends, users, logged_users
    
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
    if data in user_sockets:
        build_and_send_message(user_sockets[data], commprot.SERVER_CMD["friends_updated_msg"], "")


def handle_remove_friend_request(conn, data):
    global friends, logged_users

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
        return

    pend_reqs_str = ""
    for req in pend_reqs_lst:
        pend_reqs_str += req + "#"
    pend_reqs_str = pend_reqs_str[:-1]
    friends[data]["pending_requests"] = pend_reqs_str
    update_database("friends", data)
    if data in user_sockets:
        build_and_send_message(user_sockets[data], commprot.SERVER_CMD["friends_updated_msg"], "")


def handle_accept_friend_request(conn, data):
    global friends, logged_users

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
        if data in user_sockets:
            build_and_send_message(user_sockets[data], commprot.SERVER_CMD["friends_updated_msg"], "")
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
    if data in user_sockets:
        build_and_send_message(user_sockets[data], commprot.SERVER_CMD["friends_updated_msg"], "")


def handle_reject_friend_request(conn, data):
    global friends, logged_users

    try:
        username = logged_users[conn.getpeername()]
    except KeyError:
        print("handle_reject_friend_request func - client was not logged")
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

    # HANDLING OTHER USER'S (DATA'S) FRIENDS LISTS
    if data not in friends.keys():
        print("handle_reject_friend_request func ERROR: other user was not in friends db")
        return

    # removing username from "data"'s sent list
    sent_reqs_str = friends[data]["sent_requests"]
    sent_reqs_lst = sent_reqs_str.split("#")
    try:
        sent_reqs_lst.remove(username)
    except ValueError:
        print("handle_reject_friend_request func ERROR: other user didnt have username in sent_requests")
        return

    sent_reqs_str = ""
    for req in sent_reqs_lst:
        sent_reqs_str += req + "#"
    sent_reqs_str = sent_reqs_str[:-1]
    friends[data]["sent_requests"] = sent_reqs_str
    update_database("friends", data)
    if data in user_sockets:
        build_and_send_message(user_sockets[data], commprot.SERVER_CMD["friends_updated_msg"], "")


# GAME OPERATOR

def play(players):
    board = game.Board()
    turn1 = True
    turn2 = False
    turns = 0

    usernames = [logged_users[players[0].getpeername()], logged_users[players[1].getpeername()]]

    if not send_both_players(players[0], players[1], commprot.SERVER_CMD["other_player_msg"], usernames[1], usernames[0]):
        return False

    print(board.board)
    while turns < 42 and not game.check_board(board):
        if turn1:
            status, place = players_turn(board, players[0], players[1], 1)
        else:
            status, place = players_turn(board, players[1], players[0], 2)

        if status != "GAME ON":
            return False

        if turn1:
            if not send_to_players(players[0], players[1], commprot.SERVER_CMD["success_msg"],
                                   commprot.SERVER_CMD["other_cell_msg"], "", place): return False
        else:
            if not send_to_players(players[1], players[0], commprot.SERVER_CMD["success_msg"],
                                   commprot.SERVER_CMD["other_cell_msg"], "", place): return False

        print(board.board)
        turn1 = not turn1
        turn2 = not turn2
        turns += 1

    if not send_both_players(players[0], players[1], commprot.SERVER_CMD["game_over_msg"], "", ""):
        return False
    # time.sleep(0.5)

    if turns == 42:
        game.check_board(board)
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
    return True


# SERVER SETUP

def main():
    global users, friends, playing_clients, not_playing_clients

    print("Welcome to the 4IL server!!")

    users = commprot.read_database("users")
    friends = commprot.read_database("friends")
    set_topten()

    while True:
        rlist, wlist, xlist = select.select([server_socket] + not_playing_clients,
                                            not_playing_clients + playing_clients, [])

        for current_socket in rlist:
            if current_socket is server_socket:
                (new_socket, address) = server_socket.accept()
                print("new socket connected to server: ", new_socket.getpeername())
                not_playing_clients.append(new_socket)

            else:
                cmd, msg = recv_message_and_parse(current_socket)
                if cmd != "":
                    handle_client_message(current_socket, cmd, msg)
                else:
                    print("cmd was empty - logging client out")
                    handle_logout(current_socket)


if __name__ == '__main__':
    IP = '192.168.1.113'
    # IP = '127.0.0.1'
    PORT = 1984
    server_socket = socket.socket()
    server_socket.bind((IP, PORT))
    server_socket.listen(10)

    main()
