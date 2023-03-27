import numpy as np

# Protocol Constants
CMD_FIELD_LENGTH = 20  # Exact length of cmd field (in bytes)
LENGTH_FIELD_LENGTH = 4  # Exact length of length field (in bytes)
MAX_DATA_LENGTH = 100  # Max size of data field according to protocol
BUFFER = "|"  # Delimiter character in protocol
CMD_FIELD = CMD_FIELD_LENGTH * ' '
LENGTH_FIELD = LENGTH_FIELD_LENGTH * ' '
DATA_FIELD = MAX_DATA_LENGTH * ' '

# Protocol Messages 
# In this dictionary we will have all the client and server command names
CLIENT_CMD = {
    "signup_msg": "SIGNUP",  # username#password
    "login_msg": "LOGIN",  # username#password
    "logout_msg": "LOGOUT",  # ''
    "create_id_room_msg": "CREATE_ID_ROOM",  # ''
    "create_open_room_msg": "CREATE_OPEN_ROOM",  # ''
    "join_id_room_msg": "JOIN_ID_ROOM",  # ID
    "join_open_room_msg": "JOIN_OPEN_ROOM",  # ''
    "exit_room_msg": "EXIT_ROOM",  #
    "choose_cell_msg": "CHOOSE_CELL",  # row#column
    "my_score_msg": "MY_SCORE",  # ''
    "topten_msg": "TOPTEN"  # ''
}

SERVER_CMD = {
    "signup_ok_msg": "SIGNUP_OK",  # ''
    "login_ok_msg": "LOGIN_OK",  # ''
    "create_id_room_ok_msg": "CREATE_ID_ROOM_OK",  # ID
    "create_open_room_ok_msg": "CREATE_OPEN_ROOM_OK",  # ''
    "join_id_room_ok_msg": "JOIN_ID_ROOM_OK",  # ''
    "join_open_room_ok_msg": "JOIN_OPEN_ROOM_OK",  # ''
    "no_open_rooms_msg": "NO_OPEN_ROOMS",  # ''
    "exit_room_ok_msg": "EXIT_ROOM_OK",  # ''
    "choose_cell_ok_msg": "CHOOSE_CELL_OK",  # ''
    "status_msg": "STATUS",  # your_turn/not_your_turn
    "updated_board_msg": "UPDATED_BOARD",  # the updated game board
    "game_over_msg": "GAME_OVER",  # ''
    "game_score_msg": "GAME_SCORE",  # score
    "game_result_msg": "GAME_RESULT",  # 'you_won\you_lost\game_over'
    "your_score_msg": "YOUR_SCORE",  # score
    "topten_ans_msg": "TOPTEN_ANS",  # user1: score1\nuser2: score2\n...
    "error_msg": "ERROR"  # the error
}

DATA_MESSAGES = {
    "user_logged_in": "User is already logged in",
    "user_not_connected": "User was not connected",
    "unrecognized_command": "Unrecognized command",
    "username_not_registered": "Username is not registered",
    "incorrect_password": "Password is incorrect",
    "username_taken": "Username is already taken",
    "username_restrictions": "username should be 6-20 characters, letters and digits only",
    "password_restrictions": "password should be 8-20 characters, letters and digits only",
    "other_player_disconnected": "Other player disconnected",
    "id_not_found": "ID was not found",
    "you_won": "You won! Well done!",
    "you_lost": "You lost. Good luck next time!",
    "game_over": "Game over",
    "other_player_exited": "The other player exited the game room",
    "you_exited": "You exited the game room",
    "no_open_rooms": "There are no open rooms available. Try again later",
    '': ''
}


def build_message(cmd, data):
    """
    Gets command name and data field and creates a valid protocol message
    Returns: str, or None if error occurred
    """
    if len(cmd) > CMD_FIELD_LENGTH:
        return None

    data_length = len(data)

    if data_length > 9999:
        return None

    command = (cmd + CMD_FIELD)[:CMD_FIELD_LENGTH]
    length = (LENGTH_FIELD + str(data_length))[-LENGTH_FIELD_LENGTH:]
    padded_data = (data + DATA_FIELD)[:MAX_DATA_LENGTH]

    full_msg = join_msg([command, length, padded_data])

    return full_msg


def parse_message(data):
    """
    Parses protocol message and returns command name and data field
    Returns: cmd (str), data (str). If some error occurred, returns None, None
    """

    if data == "" or "|" not in data:
        # print("-----parse_message - there is no data or there is no | in data")
        return None, None

    expected_fields = 3

    splt_msg = split_msg(data, expected_fields)
    padded_cmd = splt_msg[0]

    if padded_cmd is None:
        # print("-----parse_message - command is None")
        return None, None

    # removing unnecessary spaces from the command
    cmd = ""
    for char in padded_cmd:
        if char.isalpha() or char == '_':
            cmd += char

    if cmd not in CLIENT_CMD.values() and cmd not in SERVER_CMD.values():
        # print("-----parse_message - command is not in CLIENT_CMD or in SERVER_CMD")
        return None, None

    padded_msg = splt_msg[2]
    msg = ""
    for char in padded_msg:
        if char.isalnum() or char == '_' or char == "#" or char == ",":
            msg += char

    padded_length = splt_msg[1]
    try:
        length = int(padded_length)
    except ValueError:
        # print("-----parse_message - length is not int")
        return None, None

    if length != len(msg):
        # print("-----parse_message - length is not message's length")
        # print("length:", length)
        # print("message:", msg, "message len:", len(msg))
        return None, None

    return cmd, msg


def split_msg(msg, expected_fields):
    """
    Helper method. gets a string and number of expected fields in it. Splits the string
    using protocol's delimiter (|) and validates that there are correct number of fields.
    Returns: list of fields if all ok. If some error occurred, returns list of None
    """

    splitted_msg = msg.split('|')
    if len(splitted_msg) == expected_fields:
        return splitted_msg
    else:
        # creating a list of None in the length of the expected fields
        none_list = []
        for i in range(expected_fields):
            none_list.append(None)
        return none_list


def join_msg(msg_fields):
    """
    Helper method. Gets a list, joins all of its fields to one string divided by the delimiter.
    Returns: string that looks like cell1|cell2|cell3
    """

    msg = ""
    for field in msg_fields:
        msg += str(field) + "|"

    return msg[:-1]


def board_to_string(board):
    string = ""
    for row in board:
        for cell in row:
            string += str(cell) + ","
        string = string[:-1] + "#"
    return string[:-1]


def string_to_board(string):
    board = np.ndarray((6, 7), dtype=int)
    rows = string.split("#")
    lst_board = []
    for row in rows:
        lst_board.append(row.split(","))

    for row in range(6):
        for col in range(7):
            board[row, col] = lst_board[row][col]

    return board


def load_users_database():
    users = {}
    with open("users.txt", "r") as f:
        data = f.read().split("\n")[:-1]
        for line in data:
            username, password, score = line.split("|")
            users[username] = {"password": password, "score": int(score)}
    return users


def update_users_database(users):
    # updates from: handle_signup, update_players_score
    s_users = ""
    for username, user in zip(users.keys(), users.values()):
        s_users += username + "|" + user["password"] + "|" + str(user["score"]) + "\n"

    with open("users.txt", "w") as f:
        f.write(s_users)



