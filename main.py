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


if __name__ == '__main__':
    db = sqlite3.connect("sqlite\\db\\users.db")
    cursor = db.cursor()

    cmd = "INSERT INTO Users (username, password, score) VALUES ('user1', 'user1', 0)"
    cursor.execute(cmd)
    cursor.commit()

    cmd = "SELECT * FROM Users"
    cursor.execute(cmd)
    rows = cursor.fetchall()
    for row in rows:
        print(row)


    db.close()
