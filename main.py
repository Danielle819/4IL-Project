import numpy as np


def print_hi():
    BOARD = np.zeros((6, 7), dtype=int)
    BOARD[1, 6] = 1
    BOARD[2, 5] = 1
    BOARD[3, 4] = 1
    BOARD[4, 3] = 1

    print(BOARD, "\n\n\n\n")

    string = board_to_string(BOARD)
    string_to_board(string)

    print(len(string))
    #
    # counter1 = 1
    # counter2 = 1
    # for start in range(3)[::-1]:
    #     if counter1 == 4 or counter2 == 4:
    #         return True
    #     counter1 = 1
    #     counter2 = 1
    #     for row, col in zip(range(start, 6), range(1, 7)[::-1]):
    #         if counter1 == 4 or counter2 == 4:
    #             return True
    #         try:
    #             if BOARD[row, col] == BOARD[row + 1, col - 1] != 0:
    #                 counter1 += 1
    #             else:
    #                 counter1 = 1
    #         except IndexError:
    #             pass
    #         try:
    #             if BOARD[6 - col, 5 - row] == BOARD[6 - col + 1, 5 - row - 1] != 0:
    #                 counter2 += 1
    #             else:
    #                 counter2 = 1
    #         except IndexError:
    #             pass
    #
    # return False


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
    print(print_hi())
