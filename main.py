import numpy as np

import server


def print_hi():
    BOARD = np.zeros((6, 7), dtype=int)
    BOARD[1, 6] = 1
    BOARD[2, 5] = 1
    BOARD[3, 4] = 1
    BOARD[4, 3] = 1

    print(BOARD, "\n\n\n\n")

    string = board_to_string(BOARD)
    string_to_board(string)

    print(int("    1"))



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
    print(server.create_id())
