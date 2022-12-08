import numpy as np


def start_game(shape):
    board = np.zeros(shape, dtype=int)
    print(board)

    turn1 = True
    turn2 = False
    turn = 0
    while turn < 42 and not check_board(board):
        if turn1:
            print("turn:", 1)
            turn = 1
        elif turn2:
            print("turn:", 2)
            turn = 2
        place = get_place(board)
        board[place] = turn
        print(board)
        turn1 = not turn1
        turn2 = not turn2

        turn += 1

    if turn1:
        print("winner:", 2)
    else:
        print("winner:", 1)


def get_place(board):
    row = get_row()
    col = get_col()

    while not check_place(board, (row, col)):
        print("inaccessible place, try again.")
        row = get_row()
        col = get_col()

    return row, col


def get_row():
    row = None
    while row is None:
        try:
            row = int(input("choose a row to insert: "))
        except ValueError:
            print("invalid input. try again")
    return row


def get_col():
    col = None
    while col is None:
        try:
            col = int(input("choose a column: "))
        except ValueError:
            print("invalid input. try again")
    return col


def check_board(BOARD):
    # check rows
    for row in range(BOARD.shape[0])[::-1]:
        counter = 1
        for col in range(1, BOARD.shape[1]):
            if counter == 4:
                return True
            if BOARD[row, col - 1] == BOARD[row, col] != 0:
                counter += 1
            else:
                counter = 1

    # check columns
    counter = 1
    for col in range(BOARD.shape[1]):
        if counter == 4:
            return True
        counter = 1
        for row in range(1, BOARD.shape[0])[::-1]:
            if counter == 4:
                return True
            if BOARD[row, col] == BOARD[row - 1, col] != 0:
                counter += 1
            else:
                counter = 1

    # check diagonal line
    counter1 = 1
    counter2 = 1
    for start in range(3)[::-1]:
        if counter1 == 4 or counter2 == 4:
            return True
        counter1 = 1
        counter2 = 1
        for row, col in zip(range(start, 6), range(6)):
            if counter1 == 4 or counter2 == 4:
                return True
            try:
                if BOARD[row, col] == BOARD[row + 1, col + 1] != 0:
                    counter1 += 1
                else:
                    counter1 = 1
            except IndexError:
                pass
            try:
                if BOARD[col, row + 1] == BOARD[col + 1, row + 2] != 0:
                    counter2 += 1
                else:
                    counter2 = 1
            except IndexError:
                pass

    # check diagonal line 2
    counter1 = 1
    counter2 = 1
    for start in range(3)[::-1]:
        if counter1 == 4 or counter2 == 4:
            return True
        counter1 = 1
        counter2 = 1
        for row, col in zip(range(start, 6), range(1, 7)[::-1]):
            if counter1 == 4 or counter2 == 4:
                return True
            try:
                if BOARD[row, col] == BOARD[row + 1, col - 1] != 0:
                    counter1 += 1
                else:
                    counter1 = 1
            except IndexError:
                pass
            try:
                if BOARD[6 - col, 5 - row] == BOARD[6 - col + 1, 5 - row - 1] != 0:
                    counter2 += 1
                else:
                    counter2 = 1
            except IndexError:
                pass

    return False


def check_place(BOARD, place):
    if place[0] >= BOARD.shape[0] or place[1] >= BOARD.shape[1]:
        return False

    if place[0] == BOARD.shape[0] - 1:
        return BOARD[place] == 0

    if BOARD[place[0] + 1, place[1]] == 0:
        return False

    return BOARD[place] == 0


start_game((6, 7))

# board = np.zeros((5,5))
# board[4,0] = 2
# board[4,1] = 1
# board[4,2] = 2
# board[4,3] = 2
# board[4,4] = 1
# print(check_board(board))




