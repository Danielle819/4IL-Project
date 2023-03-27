import numpy as np
import sqlite3
# import server


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


if __name__ == '__main__':
    # conn = None
    # try:
    #     conn = sqlite3.connect(r"sqlite\usersdb.db")
    # except:
    #     print("didnt work")
    # else:
    #     cur = conn.cursor()
    #     # sql = "INSERT INTO Users VALUES ('user5', 'user5', 10)"
    #     sql = "UPDATE Users SET score = 20, password = 'user7' WHERE username = 'user5' "
    #     cur.execute(sql)
    #
    #     # u_score = read_database("users")["user1"]["score"]
    #     # cur = conn.cursor()
    #     # sql = f''' UPDATE Users SET score = {u_score + 5} WHERE username = 'user1' '''
    #     # cur.execute(sql)
    #     sql = ''' SELECT * FROM Users '''
    #     cur.execute(sql)
    #     data = cur.fetchall()
    #     print(data)
    #
    #     # users = {}
    #     # for t in data:
    #     #     users[t[0]] = {'password': t[1], 'score': t[2]}
    #     # print(users)
    #
    #     conn.commit()
    #     cur.close()
    #     conn.close()
    #     users_id = cur.lastrowid

    conn = sqlite3.connect(r"sqlite\usersdb.db")
    cur = conn.cursor()
    sql = '''SELECT * FROM Users WHERE username = 'user4' '''
    cur.execute(sql)
    print(cur.fetchone())
    cur.close()
    conn.close()



    print("before")
    print(read_database("users"))

    dicty = {"user1": {"password": "user1", "score": 0}, "user2": {"password": "user2", "score": 0},
             "user3": {"password": "user3", "score": 5}, "user4": {"password": "user4", "score": 0},
             "user5": {"password": "user5", "score": 0}}

    update_database("users", dicty)
    print("after")
    print(read_database("users"))



