import sqlite3

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
    "my_address_msg": "MY_ADDRESS",  # ipadress#port
    "signup_part_msg": "SIGNUP_PART",  # username#password
    "signup_fin_msg": "SIGNUP_FIN",  # username#password
    "login_part_msg": "LOGIN_PART",  # username#password
    "login_fin_msg": "LOGIN_FIN",  # username#password
    "logout_msg": "LOGOUT",  # ''
    "change_username_msg": "CHANGE_USERNAME",  # username
    "change_password_msg": "CHANGE_PASSWORD",  # password
    "create_id_room_msg": "CREATE_ID_ROOM",  # ''
    "create_open_room_msg": "CREATE_OPEN_ROOM",  # ''
    "join_id_room_msg": "JOIN_ID_ROOM",  # ID
    "join_open_room_msg": "JOIN_OPEN_ROOM",  # ''
    "exit_room_msg": "EXIT_ROOM",  # '' or ID or open or invitation
    "choose_cell_msg": "CHOOSE_CELL",  # row#column
    "my_score_msg": "MY_SCORE",  # ''
    "topten_msg": "TOPTEN",  # ''
    "logged_users_msg": "LOGGED_USERS",  # ''
    "my_friends_msg": "MY_FRIENDS",  # ''
    "my_p_requests_msg": "MY_P_REQUESTS",  # ''
    "my_s_requests_msg": "MY_S_REQUESTS",  # ''
    "remove_friend_msg": "REMOVE_FRIEND",  # username
    "send_friend_request_msg": "SEND_FRIEND_REQUEST",  # username
    "remove_friend_request_msg": "RMV_FRIEND_REQUEST",  # username
    "accept_friend_request_msg": "ACPT_FRIEND_REQUEST",  # username
    "reject_friend_request_msg": "RJCT_FRIEND_REQUEST",  # username
    "invite_to_play_msg": "INVITE_TO_PLAY",  # username
    "invitation_received_msg": "INVITATION_RECEIVED",  # ''
    "accept_invitation_msg": "ACCEPT_INVITATION",  # username
    "reject_invitation_msg": "REJECT_INVITATION",  # username
    "remove_invitation_msg": "REMOVE_INVITATION",  # inviting username
}

SERVER_CMD = {
    "success_msg": "SUCCESS",  # '' or ID
    "other_player_msg": "OTHER_PLAYER",  # other player's username
    "status_msg": "STATUS",  # your_turn/not_your_turn
    "other_cell_msg": "OTHER_CELL",  # other player's choice
    "game_over_msg": "GAME_OVER",  # ''
    "game_result_msg": "GAME_RESULT",  # 'you_won\you_lost\game_over'
    "game_score_msg": "GAME_SCORE",  # score
    "your_score_msg": "YOUR_SCORE",  # score
    "topten_part_msg": "TOPTEN_PART",  # user1:score1#user2:score2#...
    "topten_fin_msg": "TOPTEN_FIN",  # user9:score9#user10:score10#...
    "logged_users_part_msg": "LOGGED_USERS_PART",  # user1#user2:#...
    "logged_users_fin_msg": "LOGGED_USERS_FIN",  # user9#user10#...
    "your_friends_part_msg": "YOUR_FRIENDS_PART",  # user1#user2...
    "your_friends_fin_msg": "YOUR_FRIENDS_FIN",  # user1#user2...
    "your_p_requests_part_msg": "YOUR_P_REQUESTS_PART",  # user1#user2...
    "your_p_requests_fin_msg": "YOUR_P_REQUESTS_FIN",  # user1#user2...
    "your_s_requests_part_msg": "YOUR_S_REQUESTS_PART",  # user1#user2...
    "your_s_requests_fin_msg": "YOUR_S_REQUESTS_FIN",  # user1#user2...
    "playing_invitation_msg": "PLAYING_INVITATION",  # inviting username
    "remove_invitation_msg": "REMOVE_INVITATION",  # inviting username
    "invitation_accepted_msg": "INVITATION_ACCEPTED",  # ''
    "invitation_rejected_msg": "INVITATION_REJECTED",  # ''
    "invitation_removed_msg": "INVITATION_REMOVED",  # ''
    "topten_updated_msg": "TOPTEN_UPDATED",  # ''
    "friends_updated_msg": "FRIENDS_UPDATED",  # ''
    "error_msg": "ERROR"  # the error
}

DATA_MESSAGES = {
    "address_not_received": "The address of your listening socket was not received",
    "user_logged_in": "User is already logged in",
    "user_not_connected": "User was not connected",
    "unrecognized_command": "Unrecognized command",
    "username_not_registered": "Username is not registered",
    "incorrect_password": "Password is incorrect",
    "username_taken": "Username is already taken",
    "username_restrictions": "Username should be 6-20 characters, letters and digits only",
    "password_restrictions": "Password should be 8-20 characters, letters and digits only",
    "its_current_username": "That is your current username",
    "its_current_password": "That is your current password",
    "other_player_disconnected": "The other player has disconnected",
    "id_not_found": "ID was not found",
    "exited_room": "You have exited the room successfully",
    "you_won": "You won! Well done!",
    "you_lost": "You lost. Good luck next time!",
    "game_over": "Game over",
    "other_player_exited": "The other player exited the game room",
    "you_exited": "You exited the game room",
    "no_open_rooms": "There are no open rooms available. Try again later",
    "your_username": "This username is yours",
    "friend_not_found": "This user was found not in your friends list",
    "user_not_found": "This user was not found",
    "user_in_sent_requests": "You already sent a friend request to this user",
    "user_in_pend_requests": "This user has sent you a friend request already. Accept it!",
    "user_in_your_friends": "This user is already in your friends list",
    "user_not_sent": "The friend request you tried to remove does not exist",
    "user_not_pending": "This user was not found in your pending requests list",
    "user_not_currently_connected": "This user is currently not connected. Try again later",
    "user_is_playing": "This user is currently playing. Try again later",
    "invitation_exist": "The invitation already exists. Check if the other player had sent you one already",
    "invitation_not_sent": "The invitation was not able to get to the other user",
    "invited_disconnected": "This user has already disconnected",
    "invitation_not_found": "The invitation was not found",
    '': '',
    None: None
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
        print("-----parse_message - there is no data or there is no | in data")
        return None, None

    expected_fields = 3

    splt_msg = split_msg(data, expected_fields)
    padded_cmd = splt_msg[0]

    if padded_cmd is None:
        print("-----parse_message - command is None")
        return None, None

    # removing unnecessary spaces from the command
    cmd = ""
    for char in padded_cmd:
        if char.isalpha() or char == '_':
            cmd += char

    if cmd not in CLIENT_CMD.values() and cmd not in SERVER_CMD.values():
        return None, None

    padded_msg = splt_msg[2]
    msg = ""
    for char in padded_msg:
        if char != ' ':
            msg += char

    padded_length = splt_msg[1]
    try:
        length = int(padded_length)
    except ValueError:
        return None, None

    if length != len(msg):
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


def read_database(tb):
    try:
        db_conn = sqlite3.connect(r"sqlite\usersdb.db")
    except:
        print("db connecting didnt work")
        return None
    cur = db_conn.cursor()

    db_dict = {}

    if tb == "users":
        sql = ''' SELECT * FROM Users '''
        cur.execute(sql)
        data = cur.fetchall()
        for t in data:
            db_dict[t[0]] = {'password': t[1], 'score': t[2]}

    if tb == "friends":
        sql = ''' SELECT * FROM Friends '''
        cur.execute(sql)
        data = cur.fetchall()
        for user in data:
            friends = user[1]
            if friends is None:
                friends = ''
            pending_requests = user[2]
            if pending_requests is None:
                pending_requests = ''
            sent_requests = user[3]
            if sent_requests is None:
                sent_requests = ''
            db_dict[user[0]] = {"friends": friends, "pending_requests": pending_requests, "sent_requests": sent_requests}

    cur.close()
    db_conn.close()
    return db_dict


def update_database(tb, db_dict, user, new_user=False):
    try:
        db_conn = sqlite3.connect(r"sqlite\usersdb.db")
    except:
        print("db connecting didnt work")
        return
    cur = db_conn.cursor()

    if tb == "users":
        if new_user:
            sql = f'''INSERT INTO Users VALUES ('{user}', '{db_dict[user]["password"]}', {db_dict[user]["score"]})'''
            cur.execute(sql)
        else:
            sql = f''' UPDATE Users SET password = '{db_dict[user]["password"]}', score = {db_dict[user]["score"]} 
                        WHERE username = '{user}' '''
            cur.execute(sql)

    elif tb == "friends":
        if new_user:
            sql = f''' INSERT INTO Friends VALUES ('{user}', '{db_dict[user]["friends"]}', 
                        '{db_dict[user]["pending_requests"]}', '{db_dict[user]["sent_requests"]}') '''
            cur.execute(sql)
        else:
            sql = f''' UPDATE Friends SET friends = '{db_dict[user]["friends"]}', 
                        pending_requests = '{db_dict[user]["pending_requests"]}',
                        sent_requests = '{db_dict[user]["sent_requests"]}'
                        WHERE username = '{user}' '''
            cur.execute(sql)

    db_conn.commit()
    cur.close()
    db_conn.close()

