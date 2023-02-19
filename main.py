import numpy as np
import sqlite3
# import server


def print_hi():
    BOARD = np.zeros((6, 7), dtype=int)
    BOARD[1, 6] = 1
    BOARD[2, 5] = 1
    BOARD[3, 4] = 1
    BOARD[4, 3] = 1

    # print(BOARD, "\n\n\n\n")

    string = board_to_string(BOARD)
    # string_to_board(string)
    #
    print(len(string))

    # lst = [1,2,3,4,5]
    # lst = []
    # print(lst)
    # try:
    #     lst.remove(lst[0])
    # except IndexError:
    #     pass
    # print(lst)


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


def read_database(db):
    if db == "users":
        try:
            db_conn = sqlite3.connect(r"sqlite\usersdb.db")
        except:
            print("didnt work")
            return None

        sql = ''' SELECT * FROM Users '''
        cur = conn.cursor()
        cur.execute(sql)

        data = cur.fetchall()
        users = {}
        for t in data:
            users[t[0]] = {'password': t[1], 'score': t[2]}

        return users



if __name__ == '__main__':
    conn = None
    try:
        conn = sqlite3.connect(r"sqlite\usersdb.db")
    except:
        print("didnt work")

    sql = ''' SELECT * FROM Users '''
    cur = conn.cursor()
    # Users = ('Cool App with SQLite & Python', '2015-01-01', '2015-01-30')
    cur.execute(sql)
    data = cur.fetchall()
    print(data)

    users = {}
    for t in data:
        users[t[0]] = {'password': t[1], 'score': t[2]}
    print(users)

    conn.commit()
    cur.close()
    conn.close()
    # users_id = cur.lastrowid


