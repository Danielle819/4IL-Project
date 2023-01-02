import commprot
import socket
import game

# CONSTANTS
IP = '192.168.11.157'
PORT = 1984



# HELPER SOCKET METHODS

def build_and_send_message(conn, code, msg):
    """
    Builds a new message using chatlib, wanted code and message.
    Prints debug info, then sends it to the given socket.
    Parameters: conn (socket object), code (str), msg (str)
    Returns: Nothing
    """

    message = commprot.build_message(code, msg)
    conn.send(message.encode())


def recv_message_and_parse(conn):
    """
    Receives a new message from given socket.
    Prints debug info, then parses the message using chatlib.
    Parameters: conn (socket object)
    Returns: cmd (str) and data (str) of the received message.
    If error occurred, will return None, None
    """

    try:
        data = conn.recv(10019).decode()
    except ConnectionResetError:
        return None, None
    cmd, msg = commprot.parse_message(data)
    return cmd, msg


def build_send_recv_parse(conn, cmd, data):
    build_and_send_message(conn, cmd, data)
    return recv_message_and_parse(conn)


# OTHER HELPER METHODS

def print_board(client_socket):
    board = client_socket.recv(83).decode()
    board = commprot.string_to_board(board)
    print("\n")
    print(board, "\n")
    return board


# COMMAND HANDLING METHODS

def create_id_room(client_socket):
    response = build_send_recv_parse(client_socket, commprot.CLIENT_CMD["create_id_room_msg"], "")
    if response == commprot.SERVER_CMD["create_id_room_ok_msg"]:
        play(client_socket)
    else:
        print("something went wrong")
        return


def play(client_socket, creator=True):
    if creator:
        print("waiting for another player to join...")
    status = client_socket.recv(26).decode()
    print(status)

    board = print_board(client_socket)
    status = client_socket.recv(13).decode()
    while status != "-----end-----":
        if status == "--your turn--":
            place = game.get_place(board)
            client_socket.send(str(place).encode())
            board = print_board(client_socket)
        elif status == "not your turn":
            print("waiting for other player to play...")
            board = print_board(client_socket)
        status = client_socket.recv(13).decode()

    status = client_socket.recv(9).decode()
    print(status)




def main():
    client_socket = socket.socket()
    client_socket.connect((IP, PORT))

    # login(client_socket)

    # first - login or signup

    print("\nWHAT DO YOU WANT TO DO?")
    print("commands: CID - create room with")
    # print("          S - get your score")
    # print("          H - get the scores table")
    # print("          U - get all the logged users")
    # print("          L - logout")
    cmd = input("your command: ")

    while cmd != 'L' and cmd != "l":
        if cmd == "CID" or cmd == "cid":
            create_id_room(client_socket)
        # elif cmd == "Q" or cmd == "q":
        #     play_question(client_socket)
        # elif cmd == "H" or cmd == "h":
        #     get_highscore(client_socket)
        # elif cmd == "U" or cmd == "u":
        #     get_logged_users(client_socket)
        # else:
        #     print("invalid answer. try again.")

        print("\ncommands: Q - get a question")
        print("          S - get your score")
        print("          H - get the scores table")
        print("          U - get all the logged users")
        print("          L - logout")
        cmd = input("WHAT DO YOU WANT TO DO? ")
    # logout(client_socket)
    client_socket.close()


if __name__ == '__main__':
    main()

