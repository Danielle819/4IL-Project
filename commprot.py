import numpy as np

# Protocol Constants
CMD_FIELD_LENGTH = 20  # Exact length of cmd field (in bytes)
LENGTH_FIELD_LENGTH = 4  # Exact length of length field (in bytes)
# MAX_DATA_LENGTH = 10 ** LENGTH_FIELD_LENGTH - 1  # Max size of data field according to protocol
BUFFER = "|"  # Delimiter character in protocol

# Protocol Messages 
# In this dictionary we will have all the client and server command names
PROTOCOL_CLIENT = {
    "signup_msg": "SIGNUP",  # username#password
    "login_msg": "LOGIN",  # username#password
    "logout_msg": "LOGOUT",  # ''
    "create_id_room_msg": "CREATE_ID_ROOM",  # username
    "create_open_room_msg": "CREATE_OPEN_ROOM",  # username
    "join_id_room_msg": "JOIN_ID_ROOM",  # username#ID
    "join_open_room_msg": "JOIN_OPEN_ROOM",  # username
    "exit_room_msg": "EXIT_ROOM",  # username#ID
    "choose_cell_msg": "CHOOSE_CELL",  # username#ID#row#column
    "my_score_msg": "MY_SCORE",  # username
    "topten_msg": "TOPTEN"  # ''
}

PROTOCOL_SERVER = {
    "signup_ok_msg": "SIGNUP_OK",  # ''
    "signup_error_msg": "SIGNUP_ERROR",  # 'username should be 6-20 characters, letters and digits only' or
                                         # 'password should be 8-20 characters, letters and digits only'
    "login_ok_msg": "LOGIN_OK",  # ''
    "login_error_msg": "LOGIN_ERROR",  # 'username is not registered' or 'incorrect password'
    "create_id_room_ok_msg": "CREATE_ID_ROOM_OK",  # ID
    "create_open_room_ok_msg": "CREATE_OPEN_ROOM_OK",  # ''
    "join_id_room_ok_msg": "JOIN_ID_ROOM_OK",  # ''
    "join_open_room_ok_msg": "JOIN_OPEN_ROOM_OK",  # ''
    "exit_room_ok_msg": "EXIT_ROOM_OK",  # ''
    "choose_cell_ok_msg": "CHOOSE_CELL_OK",  # ''
    "not_your_turn_msg": "NOT_YOUR_TURN",  # ''
    "updated_board_msg": "UPDATED_BOARD",  # the updated game board
    "game_result_msg": "GAME_RESULT",  # 'winner is (username) + well done!/good luck next time!' or 'game over'
    "your_score_msg": "YOUR_SCORE",  # score
    "topten_ans_msg": "TOPTEN_ANS",  # user1: score1\nuser2: score2\n...
}

# Other constants

CMD_FIELD = CMD_FIELD_LENGTH * ' '
LENGTH_FIELD = LENGTH_FIELD_LENGTH * ' '


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

    full_msg = join_msg([command, length, data])

    return full_msg


def parse_message(data):
    """
    Parses protocol message and returns command name and data field
    Returns: cmd (str), data (str). If some error occurred, returns None, None
    """

    if data == "" or "|" not in data:
        return None, None

    expected_fields = 3

    splt_msg = split_msg(data, expected_fields)
    command = splt_msg[0]

    if command is None:
        return None, None

    # removing unnecessary spaces from the command
    cmd = ""
    for char in command:
        if char.isalpha() or char == '_':
            cmd += char

    if cmd not in PROTOCOL_CLIENT.values() and cmd not in PROTOCOL_SERVER.values():
        return None, None

    length = splt_msg[1]
    try:
        length = int(length)
    except ValueError:
        return None, None

    msg = splt_msg[2]
    if length != len(msg):
        return None, None

    return cmd, msg


def split_msg(msg, expected_fields):
    """
    Helper method. gets a string and number of expected fields in it. Splits the string
    using protocol's delimiter (|) and validates that there are correct number of fields.
    Returns: list of fields if all ok. If some error occurred, returns None
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
        string = string[:-1] + "|"
    return string[:-1]


def string_to_board(string):
    board = np.ndarray((6, 7), dtype=int)
    rows = string.split("|")
    lst_board = []
    for row in rows:
        lst_board.append(row.split(","))

    for row in range(6):
        for col in range(7):
            board[row, col] = lst_board[row][col]

    return board


