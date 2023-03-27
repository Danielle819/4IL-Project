import commprot
import socket
import game
# from colorama import Fore, Style

# SOCKET SETUP
IP = '127.0.0.1'
PORT = 1985
client_socket = socket.socket()
client_socket.connect((IP, PORT))


# HELPER SOCKET METHODS

def build_and_send_message(code, msg):
    """
    Builds a new message using commprot, wanted code and message.
    Prints debug info, then sends it to the given socket.
    Parameters: conn (socket object), code (str), msg (str)
    Returns: Nothing
    """
    message = commprot.build_message(code, msg)
    # print("----build_and_send_message - sent:", message)
    client_socket.send(message.encode())


def recv_message_and_parse():
    """
    Receives a new message from given socket.
    Prints debug info, then parses the message using commprot.
    Parameters: conn (socket object)
    Returns: cmd (str) and data (str) of the received message.
    If error occurred, will return None, None
    """

    try:
        data = client_socket.recv(126).decode()
    except ConnectionResetError:
        return None, None
    # print("----recv_message_and_parse - got:", data)
    cmd, msg = commprot.parse_message(data)
    # print("----recv_message_and_parse - commprot parsed:", cmd, "|", msg)
    return cmd, msg


def build_send_recv_parse(cmd, data):
    build_and_send_message(cmd, data)
    return recv_message_and_parse()


# OTHER HELPER METHODS

def recv_and_print_board():
    cmd, message = recv_message_and_parse()
    if cmd != commprot.SERVER_CMD["updated_board_msg"]:
        print(commprot.DATA_MESSAGES[message])
        return None
    # if cmd != commprot.SERVER_CMD["updated_board_msg"]:
    #     print("something went wrong")
    #     return None
    board = commprot.string_to_board(message)
    print("\n")
    print(board, "\n")
    return board


# COMMAND HANDLING METHODS

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
    build_and_send_message(commprot.CLIENT_CMD["logout_msg"], "")
    print("CLIENT LOGOUT")


def change_username():
    response, _ = "", ""
    username = input("enter username: ")
    while response != commprot.SERVER_CMD["success_msg"] and username != "Q" and username != "q":
        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["change_username_msg"], username)

        if response == commprot.SERVER_CMD["error_msg"]:
            print(commprot.DATA_MESSAGES[_])

        username = input("enter username: ")
    if username != "Q" and username != "q":
        print("You have changed your username successfully!")


def change_password():
    response, _ = "", ""
    password = input("enter password: ")
    while response != commprot.SERVER_CMD["success_msg"] and password != "Q" and password != "q":

        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["change_password_msg"], password)

        if response == commprot.SERVER_CMD["error_msg"]:
            print(commprot.DATA_MESSAGES[_])

        password = input("enter password: ")
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

    print("\nWHAT DO YOU WANT TO DO?")
    print("commands: P - play")
    print("          E - edit your profile")
    print("          S - get your score")
    print("          TT - get the top ten players")
    print("          L - logout")
    print("          Q - quit")
    cmd = input("your command: ")

    ql_options = ['L', 'l', 'Q', 'q']
    while cmd not in ql_options:

        if cmd == "P" or cmd == "p":
            print("\nSTART PLAYING BY:")
            print("commands: CID - create room with ID")
            print("          JID - join room with ID")
            print("          COD - create open room")
            print("          JOD - join open room")
            print("          B - go back")
            cmd = input("your command: ")

            play_options = ['CID', 'cid', 'JID', 'jid', 'COD', 'cod', 'JOD', 'jod', 'B', 'b']
            while cmd not in play_options:
                cmd = input("try again, your command: ")

            if cmd == "CID" or cmd == "cid":
                create_id_room()
            elif cmd == "JID" or cmd == "jid":
                join_id_room()
            elif cmd == "COD" or cmd == "cod":
                create_open_room()
            elif cmd == "JOD" or cmd == "jod":
                join_open_room()
            elif cmd == "B" or cmd == "b":
                pass

        elif cmd == "E" or cmd == "e":
            print("commands: UN - change your username")
            print("          P - change your password")
            print("          B - go back")
            cmd = input("your command: ")

            edit_options = ['UN', 'un', 'P', 'p', 'B', 'b']
            while cmd not in edit_options:
                cmd = input("try again, your command: ")

            if cmd == "UN" or cmd == "un":
                change_username()
            elif cmd == "P" or cmd == "p":
                change_password()
            elif cmd == "B" or cmd == "b":
                pass

        elif cmd == "S" or cmd == "s":
            my_score()
        elif cmd == "TT" or cmd == "tt":
            topten()
        else:
            print("invalid answer. try again.")

        print("\nWHAT DO YOU WANT TO DO?")
        print("commands: P - play")
        print("          E - edit your profile")
        print("          S - get your score")
        print("          TT - get the top ten players")
        print("          L - logout")
        print("          Q - quit")
        cmd = input("WHAT DO YOU WANT TO DO? ")

    logout()
    client_socket.close()


if __name__ == '__main__':
    main()


