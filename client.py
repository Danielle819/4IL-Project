import random
import sys

import commprot
import socket
import game
import threading
from threading import *
# from colorama import Fore, Style

# SOCKETS SETUP
IP = '192.168.1.113'
PORT = 1984
client_socket = socket.socket()
client_socket.connect((IP, PORT))
listen = False
run_client = True
listen_socket = None
server_socket = None
print_input_lock = Semaphore()
invitations = []
invitations_lock = Semaphore()


# HELPER SOCKET METHODS

def build_and_send_message(code, msg, in_logout=False, sock=client_socket):
    """
    Builds a new message using commprot, wanted code and message.
    Prints debug info, then sends it to the given socket.
    Parameters: conn (socket object), code (str), msg (str)
    Returns: Nothing
    """
    message = commprot.build_message(code, msg)
    try:
        print("----build_and_send_message - sent:", message)
        sock.send(message.encode())
        # print("----build_and_send_message - sent:", message)
    except:
        if in_logout:
            # print("build_and_send_message func PASS")
            pass
        else:
            # print("build_and_send_message func END")
            end()


def recv_message_and_parse(settimeout=0, sock=client_socket):
    """
    Receives a new message from given socket.
    Prints debug info, then parses the message using commprot.
    Parameters: conn (socket object)
    Returns: cmd (str) and data (str) of the received message.
    If error occurred, will return None, None
    """

    try:
        if settimeout != 0:
            sock.settimeout(settimeout)
        data = sock.recv(126).decode()
    except TimeoutError:
        return None, None
    except:
        # print("recv_message_and_parse func END")
        end()
    else:
        print("----recv_message_and_parse - got:", data)
        cmd, msg = commprot.parse_message(data)
        # if sock is client_socket:
        #     cmd, msg = commprot.parse_message(data)
        # else:
        #     cmd, msg = commprot.parse_message(data, False)
        # print("----recv_message_and_parse - commprot parsed:", cmd, "|", msg)
        return cmd, msg
    return None, None


def build_send_recv_parse(cmd, data, settimeout=0, sock=client_socket):
    build_and_send_message(cmd, data)
    return recv_message_and_parse(settimeout, sock)


# OTHER HELPER METHODS

def recv_and_print_board(settimeout=0):
    cmd, data = recv_message_and_parse(settimeout)
    if cmd != commprot.SERVER_CMD["updated_board_msg"]:
        try:
            print(commprot.DATA_MESSAGES[data])
        except KeyError:
            print("recv_and_print_board error:", cmd, data)
        return None
    # if cmd != commprot.SERVER_CMD["updated_board_msg"]:
    #     print("something went wrong")
    #     return None
    board = commprot.string_to_board(data)
    print("\n")
    print(board, "\n")
    return board


def receive_invitation():
    print("entered receive_invitation func")
    global listen
    global listen_socket
    global server_socket
    global invitations
    global invitations_lock

    while listen:
        # print_input_lock.acquire()
        # print("receive_invitation func waiting for an invitation...")
        # print_input_lock.release()
        try:
            cmd, data = recv_message_and_parse(sock=server_socket)
            # print_input_lock.acquire()
            # print("receive_invitation func an invitation was received!")
            # print("cmd:", cmd, "data:", data)
            # print_input_lock.release()
            if cmd == commprot.SERVER_CMD["playing_invitation_msg"]:
                build_and_send_message(commprot.CLIENT_CMD["invitation_received_msg"], "", sock=server_socket)
                invitations_lock.acquire()
                invitations.append(data)
                invitations_lock.release()
                print("\n", data, "has invited you to a game!")
            elif cmd == commprot.SERVER_CMD["remove_invitation_msg"]:
                invitations_lock.acquire()
                try:
                    invitations.remove(data)
                except ValueError:
                    print("receive_invitation func - removed invitation was not in invitations")
                else:
                    print("\n", data, "has removed their playing invitation to you")
                invitations_lock.release()
            else:
                build_and_send_message("", "", sock=server_socket)

        except OSError and Exception as e:
            print("receive_invitation func error:", e)
            break

    print("receive_invitation DONE")
    listen = False


def print_general_menu():
    print_input_lock.acquire()
    print("\nWHAT DO YOU WANT TO DO?")
    print("commands: P - play")
    print("          E - edit your profile")
    print("          S - get your score")
    print("          TT - get the top ten players")
    print("          F - look at your friends")
    print("          L - logout")
    print("          Q - quit")
    cmd = input("your command: ")
    print_input_lock.release()
    return cmd


def print_play_menu():
    print_input_lock.acquire()
    print("\nSTART PLAYING BY:")
    print("commands: CID - create room with ID")
    print("          JID - join room with ID")
    print("          COR - create open room")
    print("          JOR - join open room")
    print("          I - see invitation menu")
    print("          B - go back")
    cmd = input("your command: ")
    play_options = ['CID', 'cid', 'JID', 'jid', 'COR', 'cor', 'JOR', 'jor', 'I', 'i', 'B', 'b']
    while cmd not in play_options:
        cmd = input("try again, your command: ")
    print_input_lock.release()
    return cmd


def print_invitation_menu():
    print_input_lock.acquire()
    print("commands: I - invite a friend to play")
    print("          SI - see your invitations")
    print("          A - accept an invitation")
    print("          R - reject an invitation")
    # print("          JOR - join open room")
    print("          B - go back")
    cmd = input("your command: ")
    invitation_options = ['I', 'i', 'SI', 'si', 'A', 'a', 'R', 'r']
    while cmd not in invitation_options:
        cmd = input("try again, your command: ")
    print_input_lock.release()
    return cmd


def print_edit_profile_menu():
    print_input_lock.acquire()
    print("commands: UN - change your username")
    print("          P - change your password")
    print("          B - go back")
    cmd = input("your command: ")
    edit_options = ['UN', 'un', 'P', 'p', 'B', 'b']
    while cmd not in edit_options:
        cmd = input("try again, your command: ")
    print_input_lock.release()
    return cmd


def print_friends_menu():
    print_input_lock.acquire()
    print("commands: FL - get your friends list")
    print("          PRL - get your pending friend requests")
    print("          SRL - get your sent friend requests")
    print("          RMVF - remove a friend")
    print("          SR - send a friend request")
    print("          RMVR - remove a friend request")
    print("          AR - accept a friend request")
    print("          RJR - reject a friend request")
    print("          B - go back")
    cmd = input("your command: ")
    friend_options = ['FL', 'fl', 'PRL', 'prl', 'SRL', 'srl', 'RMVF', 'rmvf', 'SR', 'sr', 'RMVR', 'rmvr',
                      'AR', 'ar', 'RJR', 'rjr', 'B', 'b']
    while cmd not in friend_options:
        cmd = input("try again, your command: ")
    print_input_lock.release()
    return cmd


# COMMAND HANDLING METHODS

def handle_user_command():
    # GENERAL MENU
    global run_client
    cmd = print_general_menu()
    ql_options = ['L', 'l', 'Q', 'q']
    while cmd not in ql_options and run_client:
        # PLAY MENU
        if cmd == "P" or cmd == "p":
            cmd = print_play_menu()
            if cmd == "CID" or cmd == "cid":
                create_id_room()
            elif cmd == "JID" or cmd == "jid":
                join_id_room()
            elif cmd == "COR" or cmd == "cor":
                create_open_room()
            elif cmd == "JOR" or cmd == "jor":
                join_open_room()
            # INVITATION MENU
            elif cmd == "I" or cmd == "i":
                cmd = print_invitation_menu()
                if cmd == "I" or cmd == "i":
                    invite_to_play()
                elif cmd == "SI" or cmd == "si":
                    print("Your invitations:")
                    invitations_lock.acquire()
                    for invitation in invitations:
                        print(invitation, "has invited you to play")
                    invitations_lock.release()
                elif cmd == "A" or cmd == 'a':
                    accept_invitation()
                elif cmd == "R" or cmd == "r":
                    reject_invitation()

            elif cmd == "B" or cmd == "b":
                pass

        # EDIT PROFILE MENU
        elif cmd == "E" or cmd == "e":
            cmd = print_edit_profile_menu()
            if cmd == "UN" or cmd == "un":
                change_username()
            elif cmd == "P" or cmd == "p":
                change_password()
            elif cmd == "B" or cmd == "b":
                pass

        # FRIENDS MENU
        elif cmd == "F" or cmd == "f":
            cmd = print_friends_menu()
            if cmd == "FL" or cmd == "fl":
                my_friends()
            elif cmd == "PRL" or cmd == "prl":
                my_pending_requests()
            elif cmd == "SRL" or cmd == "srl":
                my_sent_requests()
            elif cmd == "RMVF" or cmd == "rmvf":
                remove_friend()
            elif cmd == "SR" or cmd == "sr":
                send_friend_request()
            elif cmd == "RMVR" or cmd == "rmvr":
                remove_friend_request()
            elif cmd == "AR" or cmd == "ar":
                accept_friend_request()
            elif cmd == "RJR" or cmd == "rjr":
                reject_friend_request()
            elif cmd == "B" or cmd == "b":
                pass

        elif cmd == "S" or cmd == "s":
            my_score()
        elif cmd == "TT" or cmd == "tt":
            topten()
        else:
            print("invalid answer. try again.")

        cmd = print_general_menu()


def login():
    response, _ = "", ""
    while response != commprot.SERVER_CMD["success_msg"]:
        username = input("enter username: ")
        password = input("enter password: ")

        cmd = commprot.CLIENT_CMD["login_msg"]
        msg = username + "#" + password
        response, _ = build_send_recv_parse(cmd, msg)

        if response == commprot.SERVER_CMD["error_msg"]:
            print(commprot.DATA_MESSAGES[_])
    print("You logged in successfully!")

    global listen_socket
    global server_socket
    global listen
    # setting up listening socket
    hostname = socket.gethostname()
    ipadd = socket.gethostbyname(hostname)
    port = random.randint(49152, 65535)
    listen_socket = socket.socket()
    listen_socket.bind((ipadd, int(port)))
    listen_socket.listen(1)

    response, _ = "", ""
    # server_socket = None
    build_and_send_message(commprot.CLIENT_CMD["my_address_msg"], ipadd + "#" + str(port))
    server_socket, add = listen_socket.accept()
    response, _ = recv_message_and_parse()
    if response == commprot.SERVER_CMD["error_msg"]:
        print(commprot.DATA_MESSAGES[_])
        return
    elif response == commprot.SERVER_CMD["success_msg"]:
        print("server connected successfully")
        listen = True
        listen_th = threading.Thread(target=receive_invitation)
        listen_th.start()

    # while response != commprot.SERVER_CMD["success_msg"]:
    #     build_and_send_message(commprot.CLIENT_CMD["my_address_msg"], ipadd + "#" + str(port))
    #     server_socket, add = listen_socket.accept()
    #     response, _ = recv_message_and_parse()
    #
    #     if response == commprot.SERVER_CMD["error_msg"]:
    #         print(commprot.DATA_MESSAGES[_])


def signup():
    response, _ = "", ""
    while response != commprot.SERVER_CMD["success_msg"]:
        username = input("enter username: ")
        password = input("enter password: ")

        cmd = commprot.CLIENT_CMD["signup_msg"]
        msg = username + "#" + password
        response, _ = build_send_recv_parse(cmd, msg)

        if response == commprot.SERVER_CMD["error_msg"]:
            print(commprot.DATA_MESSAGES[_])
    print("You signed up successfully!")


def logout():
    global listen_socket
    global server_socket
    global listen
    build_and_send_message(commprot.CLIENT_CMD["logout_msg"], "", in_logout=True)
    listen = False
    try:
        listen_socket.close()
        server_socket.close()
    except:
        pass
    print("CLIENT LOGOUT")


def change_username():
    response, _ = "", ""
    username = ""
    while response != commprot.SERVER_CMD["success_msg"] and username != "Q" and username != "q":
        username = input("enter username: ")
        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["change_username_msg"], username)

        if response == commprot.SERVER_CMD["error_msg"]:
            print(commprot.DATA_MESSAGES[_])
    if username != "Q" and username != "q":
        print("You have changed your username successfully!")


def change_password():
    response, _ = "", ""
    password = ""
    while response != commprot.SERVER_CMD["success_msg"] and password != "Q" and password != "q":
        password = input("enter password: ")
        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["change_password_msg"], password)

        if response == commprot.SERVER_CMD["error_msg"]:
            print(commprot.DATA_MESSAGES[_])

    if password != "Q" and password != "q":
        print("You have changed your password successfully!")


def create_id_room():
    """
    sends the server a message that client wants to create an id room,
    gets a response (was the room created) and the id (if it was) and starts the game
    Return: None if the room was not created
    """
    global client_socket
    response, ID = build_send_recv_parse(commprot.CLIENT_CMD["create_id_room_msg"], "")
    # print(response)
    if response == commprot.SERVER_CMD["success_msg"]:
        print(ID)
        play()
    else:
        print(commprot.DATA_MESSAGES[ID])
        return


def join_id_room():
    """
    sends the server a message that the client wants to join an id room
    and the room's id, and starts the game if response was ok. if not, prints error
    """
    ID = input("enter room ID: ")
    response, _ = build_send_recv_parse(commprot.CLIENT_CMD["join_id_room_msg"], ID)
    if response == commprot.SERVER_CMD["success_msg"]:
        play(False)
    else:
        print(commprot.DATA_MESSAGES[_])


def create_open_room():
    """
    sends the server a message that client wants to create an open room,
    gets a response (was the room created) and starts the game
    """
    response, _ = build_send_recv_parse(commprot.CLIENT_CMD["create_open_room_msg"], "")
    if response == commprot.SERVER_CMD["success_msg"]:
        play()
    else:
        print(commprot.DATA_MESSAGES[_])
        return


def join_open_room():
    """
    sends the server a message that the client wants to join an open room
    and starts the game if response was ok. if not, prints error
    """
    response, _ = build_send_recv_parse(commprot.CLIENT_CMD["join_open_room_msg"], "")
    if response == commprot.SERVER_CMD["success_msg"]:
        play(False)
    else:
        print(commprot.DATA_MESSAGES[_])


def my_score():
    """
    sends the server a message that the client wants to know their score
    """
    cmd, score = build_send_recv_parse(commprot.CLIENT_CMD["my_score_msg"], "")
    if cmd == commprot.SERVER_CMD["your_score_msg"]:
        print("Your current score:", score)
    else:
        print("error:", cmd, score)


def topten():
    cmd, data = build_send_recv_parse(commprot.CLIENT_CMD["topten_msg"], "")

    if cmd == commprot.SERVER_CMD["error_msg"]:
        print("error:", cmd, data)
        return

    topten = data
    while cmd != commprot.SERVER_CMD["topten_fin_msg"]:
        cmd, data = recv_message_and_parse()
        if cmd == commprot.SERVER_CMD["error_msg"]:
            print("error:", cmd, data)
            return
        topten += data

    scores = topten.split("#")
    for user in scores:
        username, score = user.split(":")
        print(username, "-", score)


def logged_users():
    cmd, data = build_send_recv_parse(commprot.CLIENT_CMD["logged_users_msg"], "")
    if cmd == commprot.SERVER_CMD["error_msg"]:
        print("error:", cmd, data)
        return
    logged = data
    while cmd != commprot.SERVER_CMD["logged_users_fin_msg"]:
        cmd, data = recv_message_and_parse()
        if cmd == commprot.SERVER_CMD["error_msg"]:
            print("error:", cmd, data)
            return
        logged += data
    logged = logged.replace("#", "\n")
    print("Logged users:")
    print(logged)


def my_friends():
    cmd, data = build_send_recv_parse(commprot.CLIENT_CMD["my_friends_msg"], "")

    if cmd == commprot.SERVER_CMD["error_msg"]:
        print("error:", cmd, data)
        return

    friends_str = data
    while cmd != commprot.SERVER_CMD["your_friends_fin_msg"]:
        cmd, data = recv_message_and_parse()
        if cmd == commprot.SERVER_CMD["error_msg"] or cmd is None:
            print("error:", cmd, data)
            return
        friends_str += data

    friends_lst = friends_str.replace("#", "\n")
    print("YOUR FRIENDS LIST:\n" + friends_lst)


def my_pending_requests():
    cmd, data = build_send_recv_parse(commprot.CLIENT_CMD["my_p_requests_msg"], "")

    if cmd == commprot.SERVER_CMD["error_msg"]:
        print("error:", cmd, data)
        return

    reqs_str = data
    while cmd != commprot.SERVER_CMD["your_p_requests_fin_msg"]:
        cmd, data = recv_message_and_parse()
        if cmd == commprot.SERVER_CMD["error_msg"]:
            print("error:", cmd, data)
            return
        reqs_str += data

    reqs_list = reqs_str.replace("#", "\n")
    print("YOUR PENDING FRIEND REQUESTS LIST:\n" + reqs_list)


def my_sent_requests():
    cmd, data = build_send_recv_parse(commprot.CLIENT_CMD["my_s_requests_msg"], "")

    if cmd == commprot.SERVER_CMD["error_msg"]:
        print("error:", cmd, data)
        return

    reqs_str = data
    while cmd != commprot.SERVER_CMD["your_s_requests_fin_msg"]:
        cmd, data = recv_message_and_parse()
        if cmd == commprot.SERVER_CMD["error_msg"]:
            print("error:", cmd, data)
            return
        reqs_str += data

    reqs_list = reqs_str.replace("#", "\n")
    print("YOUR SENT FRIEND REQUESTS LIST:\n" + reqs_list)


def remove_friend():
    friend = input("Enter friend's username: ")
    response, _ = build_send_recv_parse(commprot.CLIENT_CMD["remove_friend_msg"], friend)
    if response == commprot.SERVER_CMD["success_msg"]:
        print("Friend was removed successfully")
    else:
        print(commprot.DATA_MESSAGES[_])


def send_friend_request():
    friend = input("Enter friend's username: ")
    response, _ = build_send_recv_parse(commprot.CLIENT_CMD["send_friend_request_msg"], friend)
    if response == commprot.SERVER_CMD["success_msg"]:
        print("Friend request was sent successfully")
    else:
        print(commprot.DATA_MESSAGES[_])


def remove_friend_request():
    friend = input("Enter friend's username: ")
    response, _ = build_send_recv_parse(commprot.CLIENT_CMD["remove_friend_request_msg"], friend)
    if response == commprot.SERVER_CMD["success_msg"]:
        print("Friend request was removed successfully")
    else:
        print(commprot.DATA_MESSAGES[_])


def accept_friend_request():
    friend = input("Enter friend's username: ")
    response, _ = build_send_recv_parse(commprot.CLIENT_CMD["accept_friend_request_msg"], friend)
    if response == commprot.SERVER_CMD["success_msg"]:
        print("Friend request was accepted successfully")
    else:
        print(commprot.DATA_MESSAGES[_])


def reject_friend_request():
    friend = input("Enter friend's username: ")
    response, _ = build_send_recv_parse(commprot.CLIENT_CMD["reject_friend_request_msg"], friend)
    if response == commprot.SERVER_CMD["success_msg"]:
        print("Friend request was rejected successfully")
    else:
        print(commprot.DATA_MESSAGES[_])


def invite_to_play():
    friend = input("Enter friend's username: ")
    response, _ = build_send_recv_parse(commprot.CLIENT_CMD["invite_to_play_msg"], friend)
    if response != commprot.SERVER_CMD["success_msg"]:
        print(commprot.DATA_MESSAGES[_])
        return

    print("Invitation was sent successfully")
    print("waiting for response...")
    response, _ = recv_message_and_parse(settimeout=30)
    if response == commprot.SERVER_CMD["invitation_accepted_msg"]:
        print("Your invitation was accepted!")
        play()
    elif response == commprot.SERVER_CMD["invitation_rejected_msg"]:
        print("Your invitation was rejected")
    elif response == commprot.SERVER_CMD["error_msg"]:
        print(commprot.DATA_MESSAGES[_])
    else:
        print("Invitation was not answered")


def accept_invitation():
    friend = input("Enter friend's username: ")
    response, _ = build_send_recv_parse(commprot.CLIENT_CMD["accept_invitation_msg"], friend)
    if response == commprot.SERVER_CMD["success_msg"]:
        print("starting game")
        try:
            invitations.remove(friend)
        except ValueError:
            print("Invitation was not found in your invitations")
        play()
    else:
        print(commprot.DATA_MESSAGES[_])
        if _ == "invitation_not_found" or _ == "other_player_disconnected":
            try:
                invitations.remove(friend)
            except ValueError:
                print("Invitation was not found in your invitations")


def reject_invitation():
    friend = input("Enter friend's username: ")
    response, _ = build_send_recv_parse(commprot.CLIENT_CMD["reject_invitation_msg"], friend)
    if response != commprot.SERVER_CMD["success_msg"]:
        print(commprot.DATA_MESSAGES[_])
        return

    try:
        invitations.remove(friend)
    except ValueError:
        print("Invitation was not found in your invitations")
    else:
        print("Invitation was rejected successfully")


# GAME OPERATOR

def play(creator=True):
    if creator:
        print("waiting for another player to join...")

    board = recv_and_print_board()
    if board is None: return
    cmd, status = recv_message_and_parse()
    if cmd == commprot.SERVER_CMD["error_msg"]:
        print(commprot.DATA_MESSAGES[status])
        return

    while cmd != commprot.SERVER_CMD["game_over_msg"] and cmd != commprot.SERVER_CMD["error_msg"]:
        if status == "your_turn":
            place = game.get_place(board)
            if place == "E":
                build_and_send_message(commprot.CLIENT_CMD["exit_room_msg"], "")
            else:
                build_and_send_message(commprot.CLIENT_CMD["choose_cell_msg"], str(place[0])+"#"+str(place[1]))
            board = recv_and_print_board()
            if board is None: return
        elif status == "not_your_turn":
            print("waiting for other player to play...")
            board = recv_and_print_board()
            if board is None: return
        cmd, status = recv_message_and_parse()

    if cmd == commprot.SERVER_CMD["error_msg"]:
        print(commprot.DATA_MESSAGES[status])
        return

    cmd, result = recv_message_and_parse()
    if result == "you_won":
        print(commprot.DATA_MESSAGES[result])
        cmd, score = recv_message_and_parse()
        if cmd == commprot.SERVER_CMD["game_score_msg"]:
            print(f"You got {score} points!")
    else:
        print(commprot.DATA_MESSAGES[result])


def main():
    cmd = input("Login or Signup? (L/S): ")
    while cmd != "L" and cmd != "S":
        cmd = input("try again, Login or Signup? (L/S): ")
    if cmd == "L":
        login()
    elif cmd == "S":
        signup()
        print("Now, log in")
        login()

    # logged_users()
    handle_user_command()


def end():
    global run_client
    global listen
    print("ENDING")
    logout()
    run_client = False
    listen = False
    try:
        listen_socket.close()
        client_socket.close()
    except:
        pass
    sys.exit()


if __name__ == '__main__':
    main()
    end()



