import numpy as np


class Board:
    def __init__(self):
        self.board = np.zeros((6,7), dtype=int)
        self.winner = 0

    def choose_cell(self, p, place):
        self.board[place] = p

    def get_board(self):
        return str(self.board)

    def set_winner(self, player):
        self.winner = player


# def start_game():
#     board = np.zeros((6,7), dtype=int)
#     print(board)
#
#     turn1 = True
#     turn2 = False
#     turn = 0
#     while turn < 42 and not check_board(board):
#         if turn1:
#             print("turn:", 1)
#             turn = 1
#         elif turn2:
#             print("turn:", 2)
#             turn = 2
#         place = get_place(board)
#         board[place] = turn
#         print(board)
#         turn1 = not turn1
#         turn2 = not turn2
#
#         turn += 1
#
#     if turn1:
#         print("winner:", 2)
#     else:
#         print("winner:", 1)


def get_place(board, col):
    # col = get_col()
    if col == "E":
        return "E"

    while not check_col(board, col):
        print("inaccessible place, try again.")
        col = get_col()

    row = board.shape[0] - 1
    while board[row, col] != 0:
        row -= 1

    return row, col


def get_col():
    col = None
    while col is None:
        col = input("choose col (or e to exit): ")
        if col == "e" or col == "E":
            return "E"
        else:
            try:
                col = int(col)
            except ValueError:
                print("invalid input. try again")
                col = None
    return col


def check_col(board, col):
    if col >= board.shape[1] or col < 0:
        return False

    return board[0, col] == 0


def check_board(BOARD):
    # check rows
    counter = 1
    turn = 0
    for row in range(BOARD.board.shape[0])[::-1]:
        if counter == 4:
            BOARD.set_winner(turn)
            return True
        counter = 1
        turn = 0
        for col in range(BOARD.board.shape[1] - 1):
            if counter == 4:
                BOARD.set_winner(turn)
                return True
            if BOARD.board[row, col] == BOARD.board[row, col + 1] != 0:
                counter += 1
                turn = BOARD.board[row, col]
            else:
                counter = 1
                turn = 0

    # check columns
    counter = 1
    turn = 0
    for col in range(BOARD.board.shape[1]):
        if counter == 4:
            BOARD.set_winner(turn)
            return True
        counter = 1
        turn = 0
        for row in range(1, BOARD.board.shape[0])[::-1]:
            if counter == 4:
                BOARD.set_winner(turn)
                return True
            if BOARD.board[row, col] == BOARD.board[row - 1, col] != 0:
                counter += 1
                turn = BOARD.board[row, col]
            else:
                counter = 1
                turn = 0

    # check diagonal line
    counter1 = 1
    counter2 = 1
    turn1, turn2 = 0, 0
    for start in range(3)[::-1]:
        if counter1 == 4:
            BOARD.set_winner(turn1)
            return True
        elif counter2 == 4:
            BOARD.set_winner(turn2)
            return True
        counter1 = 1
        counter2 = 1
        turn1, turn2 = 0, 0

        for row, col in zip(range(start, 6), range(6)):
            if counter1 == 4:
                BOARD.set_winner(turn1)
                return True
            elif counter2 == 4:
                BOARD.set_winner(turn2)
                return True

            try:
                if BOARD.board[row, col] == BOARD.board[row + 1, col + 1] != 0:
                    counter1 += 1
                    turn1 = BOARD.board[row, col]
                else:
                    counter1 = 1
                    turn1 = 0
            except IndexError:
                pass

            try:
                if BOARD.board[col, row + 1] == BOARD.board[col + 1, row + 2] != 0:
                    counter2 += 1
                    turn2 = BOARD.board[col, row + 1]
                else:
                    counter2 = 1
                    turn2 = 0
            except IndexError:
                pass

    # check diagonal line 2
    counter1 = 1
    counter2 = 1
    turn1, turn2 = 0, 0
    for start in range(3)[::-1]:
        if counter1 == 4:
            BOARD.set_winner(turn1)
            return True
        elif counter2 == 4:
            BOARD.set_winner(turn2)
            return True
        counter1 = 1
        counter2 = 1
        turn1, turn2 = 0, 0

        for row, col in zip(range(start, 6), range(1, 7)[::-1]):
            if counter1 == 4:
                BOARD.set_winner(turn1)
                return True
            elif counter2 == 4:
                BOARD.set_winner(turn2)
                return True

            try:
                if BOARD.board[row, col] == BOARD.board[row + 1, col - 1] != 0:
                    counter1 += 1
                    turn1 = BOARD.board[row, col]
                else:
                    counter1 = 1
                    turn1 = 0
            except IndexError:
                pass

            try:
                if BOARD.board[6 - col, 5 - row] == BOARD.board[6 - col + 1, 5 - row - 1] != 0:
                    counter2 += 1
                    turn2 = BOARD.board[6 - col, 5 - row]
                else:
                    counter2 = 1
                    turn2 = 0
            except IndexError:
                pass

    return False
