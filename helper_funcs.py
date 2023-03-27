import commprot
import server
import string
import random
import sqlite3


def send_error(conn, error_msg, player=False):
    """
    Send error message with given message
    Receives: socket, message error string from called function
    Returns: None
    """
    server.build_and_send_message(conn, "ERROR", error_msg, player)


def create_id():
    chars = string.ascii_uppercase
    return ''.join(random.choice(chars) for _ in range(6))


def send_players_board(players, board):
    str_board = commprot.board_to_string(board.board)
    return send_both_players(players[0], players[1], commprot.SERVER_CMD["updated_board_msg"], str_board, str_board)


def send_both_players(player1, player2, cmd, msg1, msg2):
    if not server.build_and_send_message(player1, cmd, msg1, True):
        server.build_and_send_message(player2, commprot.SERVER_CMD["error_msg"], "other_player_disconnected", True)
        return False
    if not server.build_and_send_message(player2, cmd, msg2, True):
        server.build_and_send_message(player1, commprot.SERVER_CMD["error_msg"], "other_player_disconnected", True)
        return False
    return True


def update_database(new_user=False):
    global users
    update_database("users", users, new_user)


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
    update_database()
    return score


def players_turn(board, player1, player2, turn):
    if not send_both_players(player1, player2, commprot.SERVER_CMD["status_msg"],
                             "your_turn", "not_your_turn"):
        return "A player disconnected"

    cmd, place = server.recv_message_and_parse(player1)
    if cmd == commprot.CLIENT_CMD["exit_room_msg"]:
        send_both_players(player1, player2, commprot.SERVER_CMD["game_over_msg"], "you_exited", "other_player_exited")
        return "A player exited the room"

    elif cmd == commprot.CLIENT_CMD["choose_cell_msg"]:
        place = (int(place[0]), int(place[2]))
        board.choose_cell(turn, place)
        return "GAME ON"

    return place


def read_database(tb):
    try:
        db_conn = sqlite3.connect(r"sqlite\usersdb.db")
    except:
        print("didnt work")
        return None
    cur = db_conn.cursor()

    db_dict = {}

    if tb == "users":
        sql = ''' SELECT * FROM Users '''
        cur.execute(sql)
        data = cur.fetchall()
        for t in data:
            db_dict[t[0]] = {'password': t[1], 'score': t[2]}

    cur.close()
    db_conn.close()
    return db_dict


def update_database(tb, db_dict, new_user=False):
    try:
        db_conn = sqlite3.connect(r"sqlite\usersdb.db")
    except:
        print("didnt work")
        return
    cur = db_conn.cursor()

    if tb == "users":
        for username, user in zip(db_dict.keys(), db_dict.values()):
            if new_user:
                sql = f'''SELECT * FROM Users WHERE username = '{username}' '''
                cur.execute(sql)
                result = cur.fetchone()
                if result is None:
                    sql = f'''INSERT INTO Users VALUES ('{username}', '{user["password"]}', {user["score"]})'''
                    cur.execute(sql)
            else:
                sql = f''' UPDATE Users SET password = '{user["password"]}', score = {user["score"]} WHERE username = '{username}' '''
                cur.execute(sql)
        db_conn.commit()

    cur.close()
    db_conn.close()