import commprot
import socket
import game
from colorama import Fore, Style

# CONSTANTS
IP = '127.0.0.1'
PORT = 1984


# HELPER SOCKET METHODS

def build_and_send_message(conn, code, msg):
    """
    Builds a new message using commprot, wanted code and message.
    Prints debug info, then sends it to the given socket.
    Parameters: conn (socket object), code (str), msg (str)
    Returns: Nothing
    """
    message = commprot.build_message(code, msg)
    # print("----build_and_send_message - sent:", message)
    conn.send(message.encode())


def recv_message_and_parse(conn):
    """
    Receives a new message from given socket.
    Prints debug info, then parses the message using commprot.
    Parameters: conn (socket object)
    Returns: cmd (str) and data (str) of the received message.
    If error occurred, will return None, None
    """

    try:
        data = conn.recv(10019).decode()
    except ConnectionResetError:
        return None, None
    # print("----recv_message_and_parse - got:", data)
    cmd, msg = commprot.parse_message(data)
    # print("----recv_message_and_parse - commprot parsed:", cmd, "|", msg)
    return cmd, msg


def build_send_recv_parse(conn, cmd, data):
    build_and_send_message(conn, cmd, data)
    return recv_message_and_parse(conn)


# OTHER HELPER METHODS

def recv_and_print_board(client_socket):
    cmd, message = recv_message_and_parse(client_socket)
    if cmd == commprot.SERVER_CMD["error_msg"]:
        print(message)
        return None
    # if cmd != commprot.SERVER_CMD["updated_board_msg"]:
    #     print("something went wrong")
    #     return None
    board = commprot.string_to_board(message)
    print("\n")
    print(board, "\n")
    return board


# COMMAND HANDLING METHODS

def create_id_room(client_socket):
    """
    sends the server a message that client wants to create an id room,
    gets a response (was the room created) and the id (if it was) and starts the game
    Parameters: client_socket (socket)
    Return: None if the room was not created
    """
    response, ID = build_send_recv_parse(client_socket, commprot.CLIENT_CMD["create_id_room_msg"], "")
    # print(response)
    if response == commprot.SERVER_CMD["create_id_room_ok_msg"]:
        print(ID)
        play(client_socket)
    else:
        print("something went wrong")
        return


def join_id_room(client_socket):
    """
    sends the server a message that the client wants to join an id room
    and the room's id, and starts the game if response was ok. if not, prints error
    Parameters: client_socket (socket)
    Return: None if the room was not created
    """
    ID = input("enter room ID: ")
    response, _ = build_send_recv_parse(client_socket, commprot.CLIENT_CMD["join_id_room_msg"], ID)
    if response == commprot.SERVER_CMD["join_id_room_ok_msg"]:
        play(client_socket, False)
    else:
        print(_)


def create_open_room(client_socket):
    """
    sends the server a message that client wants to create an open room,
    gets a response (was the room created) and starts the game
    Parameters: client_socket (socket)
    Return: None if the room was not created
    """
    response, _ = build_send_recv_parse(client_socket, commprot.CLIENT_CMD["create_open_room_msg"], "")
    if response == commprot.SERVER_CMD["create_open_room_ok_msg"]:
        play(client_socket)
    else:
        print("something went wrong")
        return


def join_open_room(client_socket):
    """
    sends the server a message that the client wants to join an open room
    and starts the game if response was ok. if not, prints error
    Parameters: client_socket (socket)
    Return: None if the room was not created
    """
    response, _ = build_send_recv_parse(client_socket, commprot.CLIENT_CMD["join_open_room_msg"], "")
    if response == commprot.SERVER_CMD["no_open_rooms_msg"]:
        print("no rooms were available. try again later")
        return
    elif response == commprot.SERVER_CMD["join_open_room_ok_msg"]:
        play(client_socket, False)
    else:
        print(_)


def play(client_socket, creator=True):
    if creator:
        print("waiting for another player to join...")

    board = recv_and_print_board(client_socket)
    if board is None: return
    cmd, status = recv_message_and_parse(client_socket)
    if cmd == commprot.SERVER_CMD["error_msg"] and status == "OTHER_PLAYER_DISCONNECTED":
        print("other player had disconnected, game over")
        return

    while cmd != commprot.SERVER_CMD["game_over_msg"] and cmd != commprot.SERVER_CMD["error_msg"]:
        if status == "YOUR_TURN":
            place = game.get_place(board)
            build_and_send_message(client_socket, commprot.CLIENT_CMD["choose_cell_msg"], str(place[0])+"#"+str(place[1]))
            board = recv_and_print_board(client_socket)
            if board is None: return
        elif status == "NOT_YOUR_TURN":
            print("waiting for other player to play...")
            board = recv_and_print_board(client_socket)
            if board is None: return
        cmd, status = recv_message_and_parse(client_socket)

    if cmd == commprot.SERVER_CMD["error_msg"]:
        print(status)
        return

    cmd, result = recv_message_and_parse(client_socket)
    if result == "YOU_WON":
        print("you won! well done!")
    elif result == "YOU_LOST":
        print("you lost. good luck next time!")
    elif result == "GAME_OVER":
        print("the game is over. good luck next time!")
    else:
        print("result:", result)


def main():
    client_socket = socket.socket()
    client_socket.connect((IP, PORT))

    # login(client_socket)

    # first - login or signup

    print("\nWHAT DO YOU WANT TO DO?")
    print("commands: CID - create room with ID")
    print("          JID - join room with ID")
    print("          COD - create open room")
    print("          JOD - join open room")
    print("          Q - quit")
    # print("          S - get your score")
    # print("          H - get the scores table")
    # print("          U - get all the logged users")
    # print("          L - logout")
    cmd = input("your command: ")

    while cmd != 'L' and cmd != "l":
        if cmd == "CID" or cmd == "cid":
            create_id_room(client_socket)
        elif cmd == "JID" or cmd == "jid":
            join_id_room(client_socket)
        elif cmd == "COD" or cmd == "cod":
            create_open_room(client_socket)
        elif cmd == "JOD" or cmd == "jod":
            join_open_room(client_socket)
        # elif cmd == "Q" or cmd == "q":
        #     play_question(client_socket)
        # elif cmd == "H" or cmd == "h":
        #     get_highscore(client_socket)
        # elif cmd == "U" or cmd == "u":
        #     get_logged_users(client_socket)
        # else:
        #     print("invalid answer. try again.")
        elif cmd == "Q" or "q":
            break

        print("commands: CID - create room with ID")
        print("          JID - join room with ID")
        print("          JID - join room with ID")
        print("          COD - create open room")
        print("          JOD - join open room")
        print("          Q - quit")
        # print("          S - get your score")
        # print("          H - get the scores table")
        # print("          U - get all the logged users")
        # print("          L - logout")
        cmd = input("WHAT DO YOU WANT TO DO? ")

    # logout(client_socket)
    client_socket.close()


if __name__ == '__main__':
    main()


