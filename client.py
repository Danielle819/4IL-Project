# GUI IMPORTS
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
# COSTUME MODULES IMPORTS
import commprot
import game
# OPERATIONS NECESSITY IMPORTS
import socket
import threading
from threading import *
# HELPER MODULES
import numpy as np
import random
import sys
import time


# SOCKETS SETUP
IP = '192.168.1.113'
PORT = 1984
client_socket = socket.socket()
client_socket.connect((IP, PORT))

# GLOBAL VARIABLES
listen = False
listen_socket = None
server_socket = None
logging_out = False
invitations = []
cell_map = {}
client_username, client_password, client_score = "", "", 0
# SEMAPHORE LOCKS
edit_invitations_list = Semaphore()


# HELPER SOCKET METHODS

def build_and_send_message(code, msg, sock=client_socket):
    """
    Builds a new message using commprot, wanted code and message.
    Prints debug info, then sends it to the given socket.
    Parameters: conn (socket object), code (str), msg (str)
    Returns: Nothing
    """
    message = commprot.build_message(code, msg)
    try:
        sock.send(message.encode())
        print("----build_and_send_message - sent:", message)
        # print("----build_and_send_message - sent:", message)
    except:
        if logging_out:
            # print("build_and_send_message func PASS")
            pass
        else:
            print("build_and_send_message func END")
            logout()


def recv_message_and_parse(settimeout=0, sock=client_socket):
    """
    Receives a new message from given socket.
    Prints debug info, then parses the message using commprot.
    Parameters: conn (socket object)
    Returns: cmd (str) and data (str) of the received message.
    If error occurred, will return None, None
    """

    try:
        if settimeout != 0:
            sock.settimeout(settimeout)
        data = sock.recv(126).decode()
    except TimeoutError:
        return None, None
    except:
        if not logging_out:
            print("recv_message_and_parse func END")
            if sock is client_socket:
                print("from client socket")
            else:
                print("from server socket")
            logout()
    else:
        print("----recv_message_and_parse - got:", data)
        cmd, msg = commprot.parse_message(data)
        # if sock is client_socket:
        #     cmd, msg = commprot.parse_message(data)
        # else:
        #     cmd, msg = commprot.parse_message(data, False)
        print("----recv_message_and_parse - commprot parsed:", cmd, "|", msg)
        return cmd, msg
    return None, None


def build_send_recv_parse(cmd, data, settimeout=0, sock=client_socket):
    build_and_send_message(cmd, data)
    return recv_message_and_parse(settimeout, sock)


# OTHER HELPER METHODS

def recv_and_print_board(settimeout=0):
    cmd, data = recv_message_and_parse(settimeout)
    if cmd != commprot.SERVER_CMD["updated_board_msg"]:
        try:
            print(commprot.DATA_MESSAGES[data])
        except KeyError:
            print("recv_and_print_board error:", cmd, data)
        return None
    # if cmd != commprot.SERVER_CMD["updated_board_msg"]:
    #     print("something went wrong")
    #     return None
    board = commprot.string_to_board(data)
    print("\n")
    print(board, "\n")
    return board


def set_cell_map():
    x = 190
    for col in range(7):
        y = 80
        for row in range(6):
            cell_map[str(col) + str(row)] = {"X": x, "Y": y}
            y += 80
        x += 90


# GUI

# INDEX 0
class WelcomeScreen(QDialog):
    def __init__(self):
        super(WelcomeScreen, self).__init__()
        loadUi("UIfiles\\welcomescreen.ui", self)
        # DEFINING BUTTONS
        self.loginbutton.clicked.connect(self.loginscreen)
        self.signupbutton.clicked.connect(self.signupscreen)

    # USER COMMANDS FUNCTIONS
    def loginscreen(self):
        login_screen.set_fields()
        widget.setCurrentIndex(1)

    def signupscreen(self):
        signup_screen.set_fields()
        widget.setCurrentIndex(2)


# INDEX 1
class LoginScreen(QDialog):
    def __init__(self):
        super(LoginScreen, self).__init__()
        loadUi("UIfiles\\loginscreen.ui", self)
        # COMPLETING APPEARANCE
        self.hidden = False
        self.show_hide_password()
        # DEFINING BUTTONS
        self.loginbutton.clicked.connect(self.login)
        self.gobackbutton.clicked.connect(self.goback)
        self.showhidepasswordbutton.clicked.connect(self.show_hide_password)

    # APPEARANCE FUNCTIONS
    def set_fields(self):
        self.usernamefield.setText("")
        self.passwordfield.setText("")

    def show_hide_password(self):
        if self.hidden:
            self.showhidepasswordbutton.setIcon(QtGui.QIcon('pictures\\passwordcloseeye.png'))
            self.passwordfield.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.hidden = False
        else:
            self.passwordfield.setEchoMode(QtWidgets.QLineEdit.Password)
            self.showhidepasswordbutton.setIcon(QtGui.QIcon('pictures\\passwordopeneye.png'))
            self.hidden = True

    # USER COMMANDS FUNCTIONS
    def login(self):
        global client_socket, IP, PORT
        username = self.usernamefield.text()
        password = self.passwordfield.text()

        if len(username) == 0 or len(password) == 0:
            self.errorlabel.setText("Please fill all fields")
            return

        # client_socket = socket.socket()
        # client_socket.connect((IP, PORT))
        # print("peer id:", client_socket.getpeername())
        # time.sleep(2)

        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["login_msg"], username + "#" + password)
        if response == commprot.SERVER_CMD["error_msg"]:
            self.errorlabel.setText(commprot.DATA_MESSAGES[_])
            return
        elif response == commprot.SERVER_CMD["success_msg"]:
            print("You logged in successfully!")
            global client_username, client_password, logging_out
            client_username, client_password = username, password
            logging_out = False
        else:
            print("login func:", response, _)
            return

        global listen_socket
        global server_socket
        global listen
        # setting up listening socket
        hostname = socket.gethostname()
        ipadd = socket.gethostbyname(hostname)
        port = random.randint(49152, 65535)
        listen_socket = socket.socket()
        listen_socket.bind((ipadd, int(port)))
        listen_socket.listen(1)

        response, _ = "", ""
        # server_socket = None
        build_and_send_message(commprot.CLIENT_CMD["my_address_msg"], ipadd + "#" + str(port))
        server_socket, add = listen_socket.accept()
        response, _ = recv_message_and_parse()
        if response == commprot.SERVER_CMD["error_msg"]:
            print(commprot.DATA_MESSAGES[_])
            return
        elif response == commprot.SERVER_CMD["success_msg"]:
            print("server connected successfully")
            # listen_th = threading.Thread(target=self.receive_invitation)
            # listen_th.start()
            self.set_next_windows()
            self.receive_updates()

    def goback(self):
        widget.setCurrentIndex(0)

    # HELPERS
    def set_next_windows(self):
        global main_menu, edit_user_screen, topten_screen, friends_menu, play_menu, invitations_menu
        main_menu = MainMenu()
        widget.insertWidget(3, main_menu)
        widget.setCurrentIndex(3)
        edit_user_screen = EditUserScreen()
        widget.insertWidget(4, edit_user_screen)
        topten_screen = TopTenScreen()
        widget.insertWidget(5, topten_screen)
        friends_menu = FriendsMenu()
        widget.insertWidget(6, friends_menu)
        play_menu = PlayMenu()
        widget.insertWidget(7, play_menu)
        invitations_menu = InvitationsMenu()
        widget.insertWidget(8, invitations_menu)

    def receive_updates(self):
        global listen
        self.receiver_thread = QThread()
        self.receiver = UpdatesReceiver()
        self.receiver.moveToThread(self.receiver_thread)
        self.receiver_thread.started.connect(self.receiver.run)  # when the thread starts - run receiver
        # connecting signals to appropriate handling functions
        self.receiver.topten_updated.connect(self.update_topten)
        self.receiver.friends_updated.connect(self.update_friends)
        self.receiver.invitation_received.connect(self.invitation_received)
        self.receiver.invitation_removed.connect(self.invitation_removed)
        # handling finished
        self.receiver.finished.connect(self.receiver_thread.quit)
        self.receiver.finished.connect(self.receiver.deleteLater)
        self.receiver_thread.finished.connect(self.receiver_thread.deleteLater)
        # starting thread
        listen = True
        self.receiver_thread.start()

    # UPDATES HANDLING FUNCTIONS
    def update_topten(self):
        topten_screen.show_refresh_button()

    def update_friends(self):
        friends_menu.show_refresh_button()

    def invitation_received(self, inv):
        invitations_menu.set_invitations_table()
        if widget.currentIndex() == 8:
            return
        msg = QMessageBox()
        msg.setWindowTitle("")
        msg.setText(f"{inv} has invited you to play!")
        msg.setStyleSheet("QMessageBox{background-color: rgb(230, 224, 207); font: 12pt 'Century Gothic';} "
                          "QPushButton{border-radius:5px; width: 60; color: rgb(255, 255, 255); "
                          "font: 12pt 'Century Gothic'; background-color: rgb(222, 191, 181);}"
                          "QLabel{color: rgb(100, 83, 82);}")
        msg.setStandardButtons(QMessageBox.Open | QMessageBox.Ignore)
        msg.setDefaultButton(QMessageBox.Ignore)

        ret = msg.exec_()
        if ret == QMessageBox.Open:
            widget.setCurrentIndex(8)

    def invitation_removed(self):
        invitations_menu.set_invitations_table()


# INDEX 2
class SignupScreen(QDialog):
    def __init__(self):
        super(SignupScreen, self).__init__()
        loadUi("UIfiles\\signupscreen.ui", self)
        # DEFINING BUTTONS
        self.signupbutton.clicked.connect(self.signup)
        self.gobackbutton.clicked.connect(self.goback)

    # APPEARANCE FUNCTIONS
    def set_fields(self):
        self.usernamefield.setText("")
        self.passwordfield.setText("")
        self.confirmpasswordfield.setText("")

    # USER COMMANDS FUNCTIONS
    def signup(self):
        username = self.usernamefield.text()
        password = self.passwordfield.text()
        confpassword = self.confirmpasswordfield.text()

        if len(username) == 0 or len(password) == 0:
            self.messagelabel.setText("Please fill all fields")
            self.messagelabel.setStyleSheet("font: 10pt 'MS Shell Dlg 2'; color: rgb(255, 0, 0);")
            return
        if password != confpassword:
            self.messagelabel.setText("Password and Confirm password fields must be identical")
            self.messagelabel.setStyleSheet("font: 10pt 'MS Shell Dlg 2'; color: rgb(255, 0, 0);")
            return

        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["signup_msg"], username + "#" + password)
        if response == commprot.SERVER_CMD["error_msg"]:
            self.messagelabel.setText(commprot.DATA_MESSAGES[_])
            self.messagelabel.setStyleSheet("font: 10pt 'MS Shell Dlg 2'; color: rgb(255, 0, 0);")
        elif response == commprot.SERVER_CMD["success_msg"]:
            self.messagelabel.setText("You have signed up successfully. Now log in")
            self.messagelabel.setStyleSheet("font: 10pt 'MS Shell Dlg 2'; color: rgb(117, 104, 104);")
            print("You signed up successfully!")
        else:
            print("signup func:", response, _)

    def goback(self):
        widget.setCurrentIndex(0)


# INDEX 3
class MainMenu(QDialog):
    def __init__(self):
        super(MainMenu, self).__init__()
        loadUi("UIfiles\\mainmenu.ui", self)
        # COMPLETING APPEARANCE
        self.usernamelabel.setText(client_username)
        self.set_score()
        # DEFINING BUTTONS
        self.logoutbutton.clicked.connect(self.logout)
        self.edituserbutton.clicked.connect(self.edituser)
        self.playbutton.clicked.connect(self.playmenu)
        self.toptenbutton.clicked.connect(self.topten)
        self.friendsbutton.clicked.connect(self.friendsmenu)

    # APPEARANCE FUNCTIONS
    def set_score(self):
        global client_score
        client_score = my_score()
        if client_score is None:
            self.scorelabel.setText("SCORE: None")
        else:
            self.scorelabel.setText("SCORE: " + str(client_score))

    # USER COMMANDS FUNCTIONS
    def edituser(self):
        widget.setCurrentIndex(4)

    def playmenu(self):
        widget.setCurrentIndex(7)

    def topten(self):
        # global topten_screen
        # widget.setCurrentIndex(5)
        # widget.removeWidget(widget.currentWidget())
        # topten_screen = TopTenScreen()
        # widget.insertWidget(5, topten_screen)
        widget.setCurrentIndex(5)

    def friendsmenu(self):
        # global friends_menu
        # widget.setCurrentIndex(6)
        # widget.removeWidget(widget.currentWidget())
        # friends_menu = FriendsMenu()
        # widget.insertWidget(6, friends_menu)
        widget.setCurrentIndex(6)

    def logout(self):
        logout()


# INDEX 4
class EditUserScreen(QDialog):
    def __init__(self):
        super(EditUserScreen, self).__init__()
        loadUi("UIfiles\\edituserscreen.ui", self)
        # COMPLETING APPEARANCE
        self.usernamelabel.setText("username: " + client_username)
        self.passwordlabel.setText("password: " + client_password)
        self.editusernamebutton.hide()
        self.hide_editors()
        self.username_hidden = True
        self.password_hidden = True
        # DEFINING BUTTONS
        # self.editusernamebutton.clicked.connect(self.show_hide_edit_username)
        self.editpasswordbutton.clicked.connect(self.show_hide_edit_password)
        # self.usernamesavebutton.clicked.connect(lambda: self.change_info("username"))
        self.passwordsavebutton.clicked.connect(lambda: self.change_info("password"))
        self.gobackbutton.clicked.connect(self.goback)

    # APPEARANCE FUNCTIONS
    def hide_editors(self):
        self.usernameminilabel.hide()
        self.passwordminilabel.hide()
        self.upfield.hide()
        self.confirmusernamelabel.hide()
        self.confirmpasswordlabel.hide()
        self.confirmupfield.hide()
        self.usernamesavebutton.hide()
        self.passwordsavebutton.hide()
        self.messagelabel.setText("")
        self.username_hidden = True
        self.password_hidden = True

    def show_edit_username(self):
        self.usernameminilabel.show()
        self.upfield.show()
        self.upfield.clear()
        self.confirmusernamelabel.show()
        self.confirmupfield.show()
        self.confirmupfield.clear()
        self.usernamesavebutton.show()

    def show_edit_password(self):
        self.passwordminilabel.show()
        self.upfield.show()
        self.upfield.clear()
        self.confirmpasswordlabel.show()
        self.confirmupfield.show()
        self.confirmupfield.clear()
        self.passwordsavebutton.show()

    def show_hide_edit_username(self):
        if self.username_hidden:
            if not self.password_hidden:
                self.hide_editors()
            self.show_edit_username()
            self.username_hidden = False
        else:
            self.hide_editors()
            self.username_hidden = True

    def show_hide_edit_password(self):
        if self.password_hidden:
            if not self.username_hidden:
                self.hide_editors()
            self.show_edit_password()
            self.password_hidden = False
        else:
            self.hide_editors()
            self.password_hidden = True

    # USER COMMANDS FUNCTIONS
    def change_info(self, type):
        up = self.upfield.text()
        confirmup = self.confirmupfield.text()

        if len(up) == 0 or len(confirmup) == 0:
            self.messagelabel.setText("Please fill all fields")
            return
        elif up != confirmup:
            if type == "username":
                self.messagelabel.setText("Username and Confirm username fields must be identical")
            else:
                self.messagelabel.setText("Password and Confirm password fields must be identical")
            return

        response, _ = build_send_recv_parse(commprot.CLIENT_CMD[f"change_{type}_msg"], up)
        if response == commprot.SERVER_CMD["error_msg"]:
            self.messagelabel.setText(commprot.DATA_MESSAGES[_])
        elif response == commprot.SERVER_CMD["success_msg"]:
            self.messagelabel.setText(f"You have changed your {type} successfully")
            print(f"You have changed your {type} successfully!")
            if type == "username":
                global client_username
                client_username = up
                self.usernamelabel.setText("username: " + client_username)
            else:
                global client_password
                client_password = up
                self.passwordlabel.setText("password: " + client_password)
        else:
            print("change_username func:", response, _)

    def goback(self):
        widget.setCurrentIndex(3)


# INDEX 5
class TopTenScreen(QDialog):
    def __init__(self):
        super(TopTenScreen, self).__init__()
        loadUi("UIfiles\\toptenscreen.ui", self)
        # COMPLETING APPEARANCE
        self.usernamelabel.setText(client_username)
        self.refreshbutton.hide()
        self.set_score()
        self.set_topten_table()
        # DEFINING BUTTONS
        self.refreshbutton.clicked.connect(self.refresh_page)
        self.gobackbutton.clicked.connect(self.goback)

    # APPEARANCE FUNCTIONS
    def set_score(self):
        global client_score
        if client_score is None:
            self.scorelabel.setText("SCORE: None")
        else:
            self.scorelabel.setText("SCORE: " + str(client_score))

    def show_refresh_button(self):
        self.refreshbutton.show()

    def set_topten_table(self):
        scores = top_ten()
        self.toptentable.setRowCount(len(scores))
        self.toptentable.setColumnCount(2)
        self.toptentable.setColumnWidth(0, 199)
        self.toptentable.setColumnWidth(1, 199)
        row = 0
        for score in scores:
            username_item = QtWidgets.QTableWidgetItem(score[0])
            username_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.toptentable.setItem(row, 0, username_item)
            score_item = QtWidgets.QTableWidgetItem(score[1])
            score_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.toptentable.setItem(row, 1, score_item)
            row += 1

    # USER COMMANDS FUNCTIONS
    def refresh_page(self):
        self.set_topten_table()
        self.refreshbutton.hide()

    def goback(self):
        widget.setCurrentIndex(3)


# INDEX 6
class FriendsMenu(QDialog):
    def __init__(self):
        super(FriendsMenu, self).__init__()
        loadUi("UIfiles\\friendsmenu.ui", self)
        self.friends_lst = []
        self.pending_lst = []
        self.sent_lst = []
        self.searchbar_hidden = False
        self.searched = False
        # COMPLETING APPEARANCE
        self.refreshbutton.hide()
        self.editfriendstable.hide()
        self.savefriendseditbutton.hide()
        self.editsenttable.hide()
        self.savesenteditbutton.hide()
        self.usernamefield.hide()
        self.sendbutton.hide()
        self.closebutton.hide()
        self.messagelabel.hide()
        self.usernamelabel.setText(client_username)
        self.set_score()
        self.show_hide_searchbar()
        self.set_friends_table()
        self.set_pending_table()
        self.set_sent_table()
        # DEFINING BUTTONS
        self.refreshbutton.clicked.connect(self.refresh_page)
        self.editfriendsbutton.clicked.connect(self.show_edit_friends_table)
        self.savefriendseditbutton.clicked.connect(self.save_edit_friends)
        self.searchfriendsbutton.clicked.connect(self.show_hide_searchbar)
        self.startsearchbutton.clicked.connect(self.search_friends)
        self.editsentbutton.clicked.connect(self.show_edit_sent_table)
        self.savesenteditbutton.clicked.connect(self.save_edit_sent)
        self.sendarequestbutton.clicked.connect(self.show_send_friend_request)
        self.sendbutton.clicked.connect(self.send_friend_request)
        self.closebutton.clicked.connect(self.close_send_friend_request)
        self.gobackbutton.clicked.connect(self.goback)

    # APPEARANCE FUNCTIONS
    def set_score(self):
        global client_score
        if client_score is None:
            self.scorelabel.setText("SCORE: None")
        else:
            self.scorelabel.setText("SCORE: " + str(client_score))

    def show_refresh_button(self):
        self.refreshbutton.show()

    def set_friends_table(self, f_lst=None):
        if f_lst is None:
            self.friends_lst = my_friends()
            friends_lst = self.friends_lst
        else:
            friends_lst = f_lst
        # friends table
        self.friendstable.setRowCount(len(friends_lst))
        self.friendstable.setColumnCount(2)
        self.friendstable.setColumnWidth(0, 196)
        self.friendstable.setColumnWidth(1, 20)

        # edit friends table
        self.editfriendstable.setRowCount(len(friends_lst))
        self.editfriendstable.setColumnCount(2)
        self.editfriendstable.setColumnWidth(0, 196)
        self.editfriendstable.setColumnWidth(1, 20)

        self.edit_friends_buttons, self.invite_friend_buttons = [], []
        row = 0
        for friend in friends_lst:
            # friends table
            friend_item = QtWidgets.QTableWidgetItem(friend)
            self.friendstable.setItem(row, 0, friend_item)
            self.invite_friend_buttons.append(QtWidgets.QPushButton(self))
            self.invite_friend_buttons[row].setObjectName(f"invite{row}button")
            self.invite_friend_buttons[row].setGeometry(0, 0, 20, 20)
            self.invite_friend_buttons[row].setIcon(QIcon('pictures\\send2.png'))
            self.invite_friend_buttons[row].setToolTip('Invite friend to play')
            self.invite_friend_buttons[row].setStyleSheet("QToolTip {color: black; font: 8pt 'Century Gothic'}")
            self.invite_friend_buttons[row].clicked.connect(self.invite_friend_to_play)
            self.friendstable.setCellWidget(row, 1, self.invite_friend_buttons[row])
            # edit friends table
            friend_item = QtWidgets.QTableWidgetItem(friend)
            self.editfriendstable.setItem(row, 0, friend_item)
            self.edit_friends_buttons.append(QtWidgets.QPushButton(self))
            self.edit_friends_buttons[row].setObjectName(f"removefriend{row}button")
            self.edit_friends_buttons[row].setGeometry(0, 0, 20, 20)
            self.edit_friends_buttons[row].setIcon(QIcon('pictures\\X.png'))
            self.edit_friends_buttons[row].clicked.connect(self.remove_friend_popup)
            self.editfriendstable.setCellWidget(row, 1, self.edit_friends_buttons[row])

            row += 1

    def show_edit_friends_table(self):
        self.friendstable.hide()
        self.editfriendsbutton.hide()
        self.editfriendstable.show()
        self.savefriendseditbutton.show()

    def show_hide_searchbar(self):
        if self.searchbar_hidden:
            self.searchbar.show()
            self.startsearchbutton.show()
            self.searchbar_hidden = False
        else:
            self.searchbar.hide()
            self.searchbar.setText("")
            self.startsearchbutton.hide()
            self.friendnotfoundlabel.hide()
            self.searchbar_hidden = True
            if self.searched:
                self.set_friends_table()
            self.searched = False

    def set_pending_table(self):
        self.pending_lst = my_pending_requests()
        self.pendingrequeststable.setRowCount(len(self.pending_lst))
        self.pendingrequeststable.setColumnCount(3)
        self.pendingrequeststable.setColumnWidth(0, 157)
        self.pendingrequeststable.setColumnWidth(1, 18)
        self.pendingrequeststable.setColumnWidth(2, 18)

        row = 0
        self.pending_buttons1, self.pending_buttons2 = [], []
        for req in self.pending_lst:
            req_item = QtWidgets.QTableWidgetItem(req)
            self.pendingrequeststable.setItem(row, 0, req_item)

            self.pending_buttons1.append(QtWidgets.QPushButton(self))
            self.pending_buttons1[row].setObjectName(f"accept{row}button")
            self.pending_buttons1[row].setGeometry(0, 0, 18, 18)
            self.pending_buttons1[row].setIcon(QIcon('pictures\\checkmark2.png'))
            self.pending_buttons1[row].clicked.connect(self.accept_friend_request)
            self.pendingrequeststable.setCellWidget(row, 1, self.pending_buttons1[row])

            self.pending_buttons2.append(QtWidgets.QPushButton(self))
            self.pending_buttons2[row].setObjectName(f"reject{row}button")
            self.pending_buttons2[row].setGeometry(0, 0, 18, 18)
            self.pending_buttons2[row].setIcon(QIcon('pictures\\X.png'))
            self.pending_buttons2[row].clicked.connect(self.reject_friend_request)
            self.pendingrequeststable.setCellWidget(row, 2, self.pending_buttons2[row])

            row += 1

    def set_sent_table(self):
        self.sent_lst = my_sent_requests()
        # sets table
        self.sentrequeststable.setRowCount(len(self.sent_lst))
        self.sentrequeststable.setColumnCount(1)
        self.sentrequeststable.setColumnWidth(0, 240)
        # edit sents table
        self.editsenttable.setRowCount(len(self.sent_lst))
        self.editsenttable.setColumnCount(2)
        self.editsenttable.setColumnWidth(0, 196)
        self.editsenttable.setColumnWidth(1, 20)

        self.edit_sent_buttons = []
        row = 0
        for req in self.sent_lst:
            # sets table
            req_item = QtWidgets.QTableWidgetItem(req)
            self.sentrequeststable.setItem(row, 0, req_item)
            # edit sents table
            req_item = QtWidgets.QTableWidgetItem(req)
            self.editsenttable.setItem(row, 0, req_item)
            self.edit_sent_buttons.append(QtWidgets.QPushButton(self))
            self.edit_sent_buttons[row].setObjectName(f"removesent{row}button")  # start index 10
            self.edit_sent_buttons[row].setGeometry(0, 0, 20, 20)
            self.edit_sent_buttons[row].setIcon(QIcon('pictures\\X.png'))
            self.edit_sent_buttons[row].clicked.connect(self.remove_friend_request)
            self.editsenttable.setCellWidget(row, 1, self.edit_sent_buttons[row])

            row += 1

    def show_edit_sent_table(self):
        self.sentrequeststable.hide()
        self.editsentbutton.hide()
        self.editsenttable.show()
        self.savesenteditbutton.show()

    def save_edit_friends(self):
        self.friendstable.show()
        self.editfriendsbutton.show()
        self.editfriendstable.hide()
        self.savefriendseditbutton.hide()

    def save_edit_sent(self):
        self.sentrequeststable.show()
        self.editsentbutton.show()
        self.editsenttable.hide()
        self.savesenteditbutton.hide()

    def show_send_friend_request(self):
        self.sendarequestbutton.move(170, 510)
        self.usernamefield.show()
        self.sendbutton.show()
        self.closebutton.show()
        self.messagelabel.show()
        self.messagelabel.setText("")

    def close_send_friend_request(self):
        self.sendarequestbutton.move(400, 510)
        self.usernamefield.hide()
        self.usernamefield.setText("")
        self.sendbutton.hide()
        self.closebutton.hide()
        self.messagelabel.hide()
        self.messagelabel.setText("")

    # USER COMMANDS FUNCTIONS
    def refresh_page(self):
        self.set_friends_table()
        self.set_pending_table()
        self.set_sent_table()
        self.refreshbutton.hide()

    def invite_friend_to_play(self):
        button_name = self.sender().objectName()
        row = int(button_name[6:-6])
        friend = self.friends_lst[row]
        widget.setCurrentIndex(8)
        invitations_menu.show_invite_to_play(friend)

    def remove_friend_popup(self):
        msg = QMessageBox()
        msg.setWindowTitle("")
        msg.setText("Are you sure?")
        msg.setIcon(QMessageBox.Question)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.setStyleSheet("QMessageBox{background-color: rgb(230, 224, 207); font: 12pt 'Century Gothic';} "
                          "QPushButton{border-radius:5px; width: 40; color: rgb(255, 255, 255); "
                          "font: 12pt 'Century Gothic'; background-color: rgb(222, 191, 181);}"
                          "QLabel{color: rgb(100, 83, 82);}")
        ret = msg.exec_()
        if ret == QMessageBox.Yes:
            self.remove_friend(self.sender().objectName())

    def remove_friend(self, button_name):
        if len(self.friends_lst) == 0:
            return
        row = int(button_name[12:-6])
        friend = self.friends_lst[row]
        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["remove_friend_msg"], friend)
        if response == commprot.SERVER_CMD["success_msg"]:
            self.set_friends_table()
            self.show_edit_friends_table()
            print("Friend was removed successfully")
        else:
            print(commprot.DATA_MESSAGES[_])

    def search_friends(self):
        txt = self.searchbar.text()
        f_lst = []
        for friend in self.friends_lst:
            if txt in friend:
                f_lst.append(friend)
        if len(f_lst) == 0:
            self.friendnotfoundlabel.show()
        else:
            self.searched = True
            self.set_friends_table(f_lst)

    def accept_friend_request(self):
        if len(self.pending_lst) == 0:
            return
        button_name = self.sender().objectName()
        row = int(button_name[6:-6])
        req = self.pending_lst[row]
        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["accept_friend_request_msg"], req)
        if response == commprot.SERVER_CMD["success_msg"]:
            self.set_pending_table()
            self.set_friends_table()
            print("Friend request was accepted successfully")
        else:
            print(commprot.DATA_MESSAGES[_])

    def reject_friend_request(self):
        if len(self.pending_lst) == 0:
            return
        button_name = self.sender().objectName()
        row = int(button_name[6:-6])
        req = self.pending_lst[row]
        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["reject_friend_request_msg"], req)
        if response == commprot.SERVER_CMD["success_msg"]:
            self.set_pending_table()
            print("Friend request was rejected successfully")
        else:
            print(commprot.DATA_MESSAGES[_])

    def remove_friend_request(self):
        if len(self.sent_lst) == 0:
            return
        button_name = self.sender().objectName()
        row = int(button_name[10:-6])
        req = self.sent_lst[row]
        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["remove_friend_request_msg"], req)
        if response == commprot.SERVER_CMD["success_msg"]:
            self.set_sent_table()
            self.show_edit_sent_table()
            print("Friend request was removed successfully")
        else:
            print(commprot.DATA_MESSAGES[_])

    def send_friend_request(self):
        username = self.usernamefield.text()
        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["send_friend_request_msg"], username)
        if response == commprot.SERVER_CMD["success_msg"]:
            self.set_sent_table()
            self.show_edit_sent_table()
            self.messagelabel.setText("")
            print("Friend request was sent successfully")
        else:
            self.messagelabel.setText(commprot.DATA_MESSAGES[_])
            self.messagelabel.adjustSize()

    def goback(self):
        widget.setCurrentIndex(3)


# INDEX 7
class PlayMenu(QDialog):
    def __init__(self):
        super(PlayMenu, self).__init__()
        loadUi("UIfiles\\playmenu.ui", self)
        # COMPLETING APPEARANCE
        self.show_create_room()
        self.show_join_room()
        self.usernamelabel.setText(client_username)
        self.set_score()
        # DEFINING BUTTONS
        self.createroombutton.clicked.connect(self.create_a_room)
        self.createopenbutton.clicked.connect(self.create_open_room)
        self.createbyidbutton.clicked.connect(self.create_id_room)
        self.closecreatebutton.clicked.connect(self.show_create_room)
        self.joinroombutton.clicked.connect(self.join_a_room)
        self.joinbyidbutton.clicked.connect(self.show_join_id_room)
        self.sendidbutton.clicked.connect(self.join_id_room)
        self.joinopenbutton.clicked.connect(self.join_open_room)
        self.closejoinbutton.clicked.connect(self.show_join_room)
        self.invitationbutton.clicked.connect(self.invitations)
        self.gobackbutton.clicked.connect(self.goback)

    # APPEARANCE FUNCTIONS
    def set_score(self):
        global client_score
        if client_score is None:
            self.scorelabel.setText("SCORE: None")
        else:
            self.scorelabel.setText("SCORE: " + str(client_score))

    def show_create_room(self):
        self.createopenbutton.hide()
        self.createbyidbutton.hide()
        self.closecreatebutton.hide()
        self.createroombutton.show()

    def create_a_room(self):
        self.createopenbutton.show()
        self.createbyidbutton.show()
        self.closecreatebutton.show()
        self.createroombutton.hide()

    def show_join_room(self):
        self.joinopenbutton.hide()
        self.joinbyidbutton.hide()
        self.closejoinbutton.hide()
        self.idfield.hide()
        self.sendidbutton.hide()
        self.errorlabel.setText("")
        self.joinroombutton.show()

    def join_a_room(self):
        self.joinopenbutton.show()
        self.joinbyidbutton.show()
        self.closejoinbutton.show()
        self.joinroombutton.hide()

    def show_join_id_room(self):
        self.idfield.show()
        self.sendidbutton.show()

    # USER COMMANDS FUNCTIONS
    def create_id_room(self):
        """
        sends the server a message that client wants to create an id room,
        gets a response (was the room created) and the id (if it was) and starts the game
        Return: None if the room was not created
        """
        global client_socket
        response, ID = build_send_recv_parse(commprot.CLIENT_CMD["create_id_room_msg"], "")
        # print(response)
        if response == commprot.SERVER_CMD["success_msg"]:
            print(ID)
            if widget.count() >= 10:
                widget.setCurrentIndex(9)
                widget.removeWidget(widget.currentWidget())
            gameroom = GameRoom(ID=ID, creator=True)
            widget.insertWidget(9, gameroom)
            widget.setCurrentIndex(9)
        else:
            print(commprot.DATA_MESSAGES[ID])
            return

    def create_open_room(self):
        """
            sends the server a message that client wants to create an open room,
            gets a response (was the room created) and starts the game
            """
        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["create_open_room_msg"], "")
        if response == commprot.SERVER_CMD["success_msg"]:
            if widget.count() >= 10:
                widget.setCurrentIndex(9)
                widget.removeWidget(widget.currentWidget())
            gameroom = GameRoom(creator=True)
            widget.insertWidget(9, gameroom)
            widget.setCurrentIndex(9)
        else:
            print(commprot.DATA_MESSAGES[_])
            return

    def join_id_room(self):
        ID = self.idfield.text()
        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["join_id_room_msg"], ID)
        if response == commprot.SERVER_CMD["success_msg"]:
            self.errorlabel.setText("")
            self.idfield.setText("")
            if widget.count() >= 10:
                widget.setCurrentIndex(9)
                widget.removeWidget(widget.currentWidget())
            gameroom = GameRoom(creator=False)
            widget.insertWidget(9, gameroom)
            widget.setCurrentIndex(9)
        else:
            print(commprot.DATA_MESSAGES[_])
            self.errorlabel.setText(commprot.DATA_MESSAGES[_])

    def join_open_room(self):
        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["join_open_room_msg"], "")
        if response == commprot.SERVER_CMD["success_msg"]:
            self.errorlabel.setText("")
            if widget.count() >= 10:
                widget.setCurrentIndex(9)
                widget.removeWidget(widget.currentWidget())
            gameroom = GameRoom(creator=False)
            widget.insertWidget(9, gameroom)
            widget.setCurrentIndex(9)
        else:
            print(commprot.DATA_MESSAGES[_])
            self.errorlabel.setText(commprot.DATA_MESSAGES[_])

    def invitations(self):
        widget.setCurrentIndex(8)

    def goback(self):
        widget.setCurrentIndex(3)


# INDEX 8
class InvitationsMenu(QDialog):
    def __init__(self):
        super(InvitationsMenu, self).__init__()
        loadUi("UIfiles/invitationsmenu.ui", self)
        # COMPLETING APPEARANCE
        self.usernamelabel.setText(client_username)
        self.set_score()
        self.hide_invite_to_play()
        self.set_invitations_table()
        # PARAMETERS
        self.buttons1, self.buttons2 = [], []
        self.invitation_removed = False
        # DEFINING BUTTONS
        self.invitetoplaybutton.clicked.connect(lambda: self.show_invite_to_play(friend=""))
        self.sendbutton.clicked.connect(self.invite_to_play)
        self.closebutton.clicked.connect(self.hide_invite_to_play)
        self.gobackbutton.clicked.connect(self.goback)

    # APPEARANCE FUNCTIONS
    def set_score(self):
        global client_score
        if client_score is None:
            self.scorelabel.setText("SCORE: None")
        else:
            self.scorelabel.setText("SCORE: " + str(client_score))

    def set_invitations_table(self):
        global invitations, edit_invitations_list
        edit_invitations_list.acquire()
        self.invitationstable.setRowCount(len(invitations))
        self.invitationstable.setColumnCount(3)
        self.invitationstable.setColumnWidth(0, 157)
        self.invitationstable.setColumnWidth(1, 18)
        self.invitationstable.setColumnWidth(2, 18)

        row = 0
        self.buttons1, self.buttons2 = [], []
        for inv in invitations:
            inv_item = QtWidgets.QTableWidgetItem(inv)
            self.invitationstable.setItem(row, 0, inv_item)

            self.buttons1.append(QtWidgets.QPushButton(self))
            self.buttons1[row].setObjectName(f"accept{row}button")
            self.buttons1[row].setGeometry(0, 0, 18, 18)
            self.buttons1[row].setIcon(QIcon('pictures\\checkmark2.png'))
            self.buttons1[row].clicked.connect(self.accept_invitation)
            self.invitationstable.setCellWidget(row, 1, self.buttons1[row])

            self.buttons2.append(QtWidgets.QPushButton(self))
            self.buttons2[row].setObjectName(f"reject{row}button")
            self.buttons2[row].setGeometry(0, 0, 18, 18)
            self.buttons2[row].setIcon(QIcon('pictures\\X.png'))
            self.buttons2[row].clicked.connect(self.reject_invitation)
            self.invitationstable.setCellWidget(row, 2, self.buttons2[row])

            row += 1
        edit_invitations_list.release()

    def hide_invite_to_play(self):
        self.statuslabel.hide()
        self.detailslabel.hide()
        self.usernamefield.hide()
        self.sendbutton.hide()
        self.closebutton.hide()
        self.errorlabel.hide()
        self.usernamefield.setText("")
        self.errorlabel.setText("")
        self.statuslabel.setText("")
        self.detailslabel.setText("")

    def show_invite_to_play(self, friend=""):
        self.usernamefield.show()
        self.sendbutton.show()
        self.closebutton.show()
        self.statuslabel.show()
        self.detailslabel.show()
        self.errorlabel.show()
        self.usernamefield.setText("")
        if friend != "":
            self.usernamefield.setText(friend)
            self.statuslabel.setText("Press send to invite friend to play")

    def disable_buttons(self):
        for i in range(len(self.buttons1)):
            self.buttons1[i].setEnabled(False)
            self.buttons2[i].setEnabled(False)

    def enable_buttons(self):
        for i in range(len(self.buttons1)):
            self.buttons1[i].setEnabled(True)
            self.buttons2[i].setEnabled(True)

    # SIGNALS HANDLING FUNCTIONS
    def invitation_accepted(self):
        if widget.count() >= 10:
            widget.setCurrentIndex(9)
            widget.removeWidget(widget.currentWidget())
        gameroom = GameRoom(creator=True)
        widget.insertWidget(9, gameroom)
        widget.setCurrentIndex(9)

    def invitation_rejected(self):
        self.statuslabel.setText("Your invitation was rejected.")
        self.detailslabel.setText("")

    def error_occurred(self, error):
        self.statuslabel.setText("")
        self.detailslabel.setText("")
        self.errorlabel.setText(error)

    def invitation_not_answered(self):
        self.statuslabel.setText("The invitation was not answered.")
        self.detailslabel.setText("Try again later")
        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["remove_invitation_msg"], "")
        print("removing message -", response, _)

    # USER COMMANDS FUNCTIONS
    def invite_to_play(self):
        self.errorlabel.setText("")
        self.statuslabel.setText("")
        self.detailslabel.setText("")

        friend = self.usernamefield.text()
        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["invite_to_play_msg"], friend)
        if response != commprot.SERVER_CMD["success_msg"]:
            print("invite_to_play func - error:", commprot.DATA_MESSAGES[_])
            self.errorlabel.setText(commprot.DATA_MESSAGES[_])
            return

        print("Invitation was sent successfully")
        self.statuslabel.setText("Waiting for answer...")
        self.detailslabel.setText("Invitation will be automatically deleted after 30 seconds")
        self.waiting_thread = QThread()
        self.waiting_worker = AnswerWaitingWorker()
        self.waiting_worker.moveToThread(self.waiting_thread)
        self.waiting_thread.started.connect(self.waiting_worker.run)  # when the thread starts - run worker
        # connecting signals to appropriate handling functions
        self.waiting_worker.accepted.connect(self.invitation_accepted)
        self.waiting_worker.rejected.connect(self.invitation_rejected)
        self.waiting_worker.error.connect(self.error_occurred)
        self.waiting_worker.not_answered.connect(self.invitation_not_answered)
        # handling finished
        self.waiting_worker.finished.connect(self.waiting_thread.quit)
        self.waiting_worker.finished.connect(self.waiting_worker.deleteLater)
        self.waiting_thread.finished.connect(self.waiting_thread.deleteLater)
        # starting thread
        self.waiting_thread.start()

        # additional resets
        self.sendbutton.setEnabled(False)
        self.closebutton.setEnabled(False)
        self.gobackbutton.setEnabled(False)
        self.disable_buttons()
        # self.closebutton.clicked.connect(lambda: self.remove_invitation(closebutton=True))
        # self.gobackbutton.clicked.connect(lambda: self.remove_invitation(gobackbutton=True))
        # after worker finishes resets
        self.waiting_thread.finished.connect(lambda: self.sendbutton.setEnabled(True))
        self.waiting_thread.finished.connect(lambda: self.closebutton.setEnabled(True))
        self.waiting_thread.finished.connect(lambda: self.gobackbutton.setEnabled(True))
        self.waiting_thread.finished.connect(lambda: self.enable_buttons())
        # self.waiting_thread.finished.connect(lambda: self.closebutton.clicked.connect(self.hide_invite_to_play))
        # self.waiting_thread.finished.connect(lambda: self.gobackbutton.clicked.connect(self.goback))

    def accept_invitation(self):
        button_name = self.sender().objectName()
        row = int(button_name[6:-6])
        inv = invitations[row]
        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["accept_invitation_msg"], inv)
        if response == commprot.SERVER_CMD["success_msg"]:
            print("starting game")
            edit_invitations_list.acquire()
            try:
                invitations.remove(inv)
            except ValueError:
                print("Invitation was not found in your invitations")
                edit_invitations_list.release()
            else:
                edit_invitations_list.release()
                self.set_invitations_table()
            if widget.count() >= 10:
                widget.setCurrentIndex(9)
                widget.removeWidget(widget.currentWidget())
            gameroom = GameRoom(creator=False)
            widget.insertWidget(9, gameroom)
            widget.setCurrentIndex(9)
        else:
            print("accept_invitation func - error:", commprot.DATA_MESSAGES[_])
            if _ == "invitation_not_found" or _ == "other_player_disconnected":
                edit_invitations_list.acquire()
                try:
                    invitations.remove(inv)
                except ValueError:
                    print("Invitation was not found in your invitations")
                    edit_invitations_list.release()
                else:
                    edit_invitations_list.release()
                    self.set_invitations_table()

    def reject_invitation(self):
        button_name = self.sender().objectName()
        row = int(button_name[6:-6])
        inv = invitations[row]
        response, _ = build_send_recv_parse(commprot.CLIENT_CMD["reject_invitation_msg"], inv)
        if response != commprot.SERVER_CMD["success_msg"]:
            print(commprot.DATA_MESSAGES[_])

        edit_invitations_list.acquire()
        try:
            invitations.remove(inv)
        except ValueError:
            print("Invitation was not found in your invitations")
            edit_invitations_list.release()
            return
        else:
            edit_invitations_list.release()
            print("Invitation was rejected successfully")
            self.set_invitations_table()

    def goback(self):
        widget.setCurrentIndex(7)


# INDEX 9
class GameRoom(QDialog):
    def __init__(self, ID="", invitation=False, creator=True):
        super(GameRoom, self).__init__()
        loadUi("UIfiles\\gameroom.ui", self)
        # COMPLETING APPEARANCE
        self.yourusernamelabel.setText(client_username)
        self.ID = ID
        self.invitation = invitation
        if self.ID != "":
            self.idlabel.setText("ID: " + self.ID)
        # PARAMETERS
        global cell_map
        set_cell_map()
        # parameters for gui
        self.columns = []
        self.bin_board = None
        # self.added_circles = []
        self.ui_board = []
        self.column = -1
        self.enabled_columns = [0, 1, 2, 3, 4, 5, 6]
        self.last_row, self.last_col = None, None
        # parameters for exiting the room
        self.exited = False
        self.game_started = False
        self.your_turn_ind = False
        # parameters for popups
        self.over = False
        self.update_score = False

        if creator:
            self.your_color = "243,211,193"  # light
            self.alternate_your_color = "223, 195, 178"
            self.other_color = "154, 133, 143"  # dark
            self.alternate_other_color = "144, 124, 134"
        else:
            self.other_color = "243,211,193"
            self.alternate_other_color = "223, 195, 178"
            self.your_color = "154, 133, 143"
            self.alternate_your_color = "144, 124, 134"

        # self.animated_circle.setStyleSheet("border-radius:35px;"
        #                                    "background-color: rgb("+self.alternate_your_color+");"
        #                                    "border: 10px solid  rgb("+self.your_color+");")
        # self.animated_circle.hide()
        # self.animation = QPropertyAnimation(self.animated_circle, b"geometry")
        # self.animation.setDuration(600)

        play_th = threading.Thread(target=self.play)
        play_th.daemon = True
        play_th.start()

        # DEFINING BUTTONS
        self.exitbutton.clicked.connect(self.exit_room)

    # SETTING VARIABLES
    def create_bin_board(self):
        self.bin_board = np.array([[0,0,0,0,0,0,0],
                                   [0,0,0,0,0,0,0],
                                   [0,0,0,0,0,0,0],
                                   [0,0,0,0,0,0,0],
                                   [0,0,0,0,0,0,0],
                                   [0,0,0,0,0,0,0]], dtype=int)

    def create_ui_board(self):
        self.ui_board.append([])
        self.ui_board[0].append(self.cell00)
        self.ui_board[0].append(self.cell10)
        self.ui_board[0].append(self.cell20)
        self.ui_board[0].append(self.cell30)
        self.ui_board[0].append(self.cell40)
        self.ui_board[0].append(self.cell50)
        self.ui_board[0].append(self.cell60)
        self.ui_board.append([])
        self.ui_board[1].append(self.cell01)
        self.ui_board[1].append(self.cell11)
        self.ui_board[1].append(self.cell21)
        self.ui_board[1].append(self.cell31)
        self.ui_board[1].append(self.cell41)
        self.ui_board[1].append(self.cell51)
        self.ui_board[1].append(self.cell61)
        self.ui_board.append([])
        self.ui_board[2].append(self.cell02)
        self.ui_board[2].append(self.cell12)
        self.ui_board[2].append(self.cell22)
        self.ui_board[2].append(self.cell32)
        self.ui_board[2].append(self.cell42)
        self.ui_board[2].append(self.cell52)
        self.ui_board[2].append(self.cell62)
        self.ui_board.append([])
        self.ui_board[3].append(self.cell03)
        self.ui_board[3].append(self.cell13)
        self.ui_board[3].append(self.cell23)
        self.ui_board[3].append(self.cell33)
        self.ui_board[3].append(self.cell43)
        self.ui_board[3].append(self.cell53)
        self.ui_board[3].append(self.cell63)
        self.ui_board.append([])
        self.ui_board[4].append(self.cell04)
        self.ui_board[4].append(self.cell14)
        self.ui_board[4].append(self.cell24)
        self.ui_board[4].append(self.cell34)
        self.ui_board[4].append(self.cell44)
        self.ui_board[4].append(self.cell54)
        self.ui_board[4].append(self.cell64)
        self.ui_board.append([])
        self.ui_board[5].append(self.cell05)
        self.ui_board[5].append(self.cell15)
        self.ui_board[5].append(self.cell25)
        self.ui_board[5].append(self.cell35)
        self.ui_board[5].append(self.cell45)
        self.ui_board[5].append(self.cell55)
        self.ui_board[5].append(self.cell65)

    def connect_buttons(self):
        self.columns.append(self.column0)
        self.columns.append(self.column1)
        self.columns.append(self.column2)
        self.columns.append(self.column3)
        self.columns.append(self.column4)
        self.columns.append(self.column5)
        self.columns.append(self.column6)
        for column in self.columns:
            column.clicked.connect(self.choose_column)

    # APPEARANCE FUNCTIONS
    def your_turn(self):
        self.your_turn_ind = True
        self.yourusernamelabel.setStyleSheet("font: 16pt 'Century Gothic'; color: rgba("+self.your_color+",255);")
        self.otherusernamelabel.setStyleSheet("font: 14pt 'Century Gothic'; color: rgba("+self.other_color+", 155);")
        self.enable_buttons()
        self.instructionslabel.setText("Play")

    def other_turn(self):
        self.your_turn_ind = False
        self.yourusernamelabel.setStyleSheet("font: 14pt 'Century Gothic'; color: rgba("+self.your_color+", 155);")
        self.otherusernamelabel.setStyleSheet("font: 16pt 'Century Gothic'; color: rgba("+self.other_color+", 255);")
        self.disable_buttons()
        self.instructionslabel.setText("Waiting for the other player to play...")

    # PLAYER'S CHOICE HANDLERS
    def disable_buttons(self):
        for i in self.enabled_columns:
            self.columns[i].setEnabled(False)

    def enable_buttons(self):
        for i in self.enabled_columns:
            self.columns[i].setEnabled(True)

    def choose_column(self):
        print("got player's choice")
        self.column = int(self.sender().objectName()[6])
        print(self.column)
        place = game.get_place(self.bin_board, self.column)
        print(self.bin_board)
        print("place:", place)
        self.drop_circle(place)

    def drop_circle(self, place, your_turn=True):
        row, col = place[0], place[1]
        ax, ay = cell_map[str(col) + str(row)]["X"], cell_map[str(col) + str(row)]["Y"]
        if your_turn:
            # self.added_circles[row][col] = QtWidgets.QLabel(self)
            # self.added_circles[row][col].setGeometry(ax, 0, 70, 70)
            # self.added_circles[row][col].setStyleSheet("border-radius:35px;"
            #                                            "background-color: rgb("+self.alternate_your_color+");"
            #                                            "border: 10px solid  rgb("+self.your_color+");")
            # self.added_circles[row][col].raise_()
            # self.added_circles[row][col].show()

            # self.animated_circle.setGeometry(ax, 0, 70, 70)
            # self.animated_circle.show()
            # self.animated_circle.raise_()
            # self.animation = QPropertyAnimation(self.animated_circle, b"geometry")
            # self.animation.setDuration(600)
            # self.animation.setEasingCurve(QEasingCurve.OutBounce)
            # self.animation.setStartValue(QRect(ax, 0, 70, 70))
            # self.animation.setEndValue(QRect(ax, ay, 70, 70))
            # self.animation.start()
            # self.last_row, self.last_col = row, col

            self.ui_board[row][col].setStyleSheet("border-radius:35px; "
                                                                      "background-color: rgb(" + self.alternate_your_color + ");"
                                                                    "border: 10px solid  rgb(" + self.your_color + ");")
        else:
            self.ui_board[row][col].setStyleSheet("border-radius:35px; "
                                                  "background-color: rgb("+self.alternate_other_color+");"
                                                  "border: 10px solid  rgb("+self.other_color+");")
            # if self.last_row is not None:
            #     self.ui_board[self.last_row][self.last_col].setStyleSheet("border-radius:35px; "
            #                                                               "background-color: rgb("+self.alternate_your_color+");"
            #                                                               "border: 10px solid  rgb("+self.your_color+");")
            #     self.animated_circle.hide()

        if row == 0:
            self.columns[col].setEnabled(False)
            self.enabled_columns.remove(col)

    # END OF GAME HANDLERS
    def error_occurred(self, error):
        try:
            error_message = commprot.DATA_MESSAGES[error]
        except ValueError:
            error_message = "An error has occurred"
        self.errorlabel.setText(error_message)
        self.instructionslabel.setText("Press exit to exit the room")
        self.disable_buttons()
        self.over = True

    def game_over(self, result, score=0):
        self.disable_buttons()
        if result == "you_won":
            self.gameoverlabel.setText("YOU WON!")
            self.gamescorelabel.setText(f"You got {score} points!")
            self.update_score = True
        elif result == "you_lost":
            self.gameoverlabel.setText("YOU LOST")
            self.gamescorelabel.setText("Good luck next time!")
        elif result == "game_over":
            self.gameoverlabel.setText("GAME OVER")
            self.gamescorelabel.setText("Good luck next time!")
        self.instructionslabel.setText("Press exit to exit the room")
        self.over = True

    # USER COMMANDS FUNCTIONS
    def play(self):
        self.instructionslabel.setText("Waiting for another player to join the game room...")

        self.create_bin_board()

        # receiving other player's username from server
        cmd, other_player = recv_message_and_parse()
        if cmd != commprot.SERVER_CMD["other_player_msg"] or self.exited:
            if not self.exited:
                print("play func - getting other players username failed", cmd, other_player)
                self.error_occurred(other_player)
            print("play func - thread done")
            return
        print("You are playing with", other_player)
        self.otherusernamelabel.setText(other_player)

        cmd, status = recv_message_and_parse()
        if cmd == commprot.SERVER_CMD["error_msg"] or cmd is None:
            print("play func - error:", commprot.DATA_MESSAGES[status])
            self.error_occurred(status)
            print("play func - thread done")
            return

        self.game_started = True
        self.instructionslabel.setText("")
        self.idlabel.hide()
        # self.create_added_circles()
        self.create_ui_board()
        self.connect_buttons()
        while cmd != commprot.SERVER_CMD["game_over_msg"] and cmd != commprot.SERVER_CMD["error_msg"] and cmd is not None:
            if status == "your_turn":
                self.your_turn()
                print("waiting for player's choice...")
                if self.column == "E":
                    print("play func - player exited, thread done")
                    return
                while self.column == -1:
                    pass
                if self.column == "E":
                    print("play func - player exited, thread done")
                    return
                place = game.get_place(self.bin_board, self.column)
                response, _ = build_send_recv_parse(commprot.CLIENT_CMD["choose_cell_msg"],
                                                    str(place[0]) + "#" + str(place[1]))
                if response != commprot.SERVER_CMD["success_msg"]:
                    print("play func - choose cell error:", response, _)
                    self.error_occurred(_)
                    print("play func - thread stops")
                    return

                self.bin_board[place[0], place[1]] = 1
                self.column = -1

            elif status == "not_your_turn":
                self.other_turn()
                print("waiting for other player to play...")
                cmd, place = recv_message_and_parse()
                if self.column == "E":
                    print("play func - player exited, thread done")
                    return
                if cmd != commprot.SERVER_CMD["other_cell_msg"]:
                    print("play func - receiving other cell error:", cmd, place)
                    self.error_occurred(place)
                    print("play func - thread done")
                    return
                print("OTHER PLAYER CHOSE:", place)
                place = (int(place[0]), int(place[2]))
                self.drop_circle(place, False)
                self.bin_board[place[0], place[1]] = 2
            cmd, status = recv_message_and_parse()

        if cmd == commprot.SERVER_CMD["error_msg"] or cmd is None:
            print("play func - error", commprot.DATA_MESSAGES[status])
            self.error_occurred(status)
            print("play func - thread done")
            return

        cmd, result = recv_message_and_parse()
        if result == "you_won":
            print(commprot.DATA_MESSAGES[result])
            cmd, score = recv_message_and_parse()
            if cmd == commprot.SERVER_CMD["game_score_msg"]:
                self.game_over(result, score)
        else:
            self.game_over(result)
            print(commprot.DATA_MESSAGES[result])
        print("play func - thread done")

    def exit_room(self):
        print("enter exit_room")
        if self.over:  # when exiting after the game is over, don't send exit_room_msg to server
            self.goback()
            return
        if self.game_started:  # when exiting after the game started, exit_room_msg needs to have empty data field
            self.column = "E"
            if self.your_turn_ind:  # when exiting while it's your turn, server only sends success_msg
                response, _ = build_send_recv_parse(commprot.CLIENT_CMD["exit_room_msg"], "")
                if response != commprot.SERVER_CMD["success_msg"]:
                    print("exit_room func - exit while it's your turn failed:", response, _)
                print("exit_room func - exiting while its your turn")
            else:  # when exiting while not your turn, server will send other_cell_msg and status_msg before success_msg
                self.instructionslabel.setText("Waiting until the other player gets the message...")
                self.waiting_thread = QThread()
                self.exit_worker = ExitWorker()
                self.exit_worker.moveToThread(self.waiting_thread)
                self.waiting_thread.started.connect(self.exit_worker.run)  # when the thread starts - run worker
                # handling finished
                self.exit_worker.finished.connect(self.waiting_thread.quit)
                self.exit_worker.finished.connect(self.exit_worker.deleteLater)
                self.waiting_thread.finished.connect(self.waiting_thread.deleteLater)
                self.waiting_thread.start()
                # additional resets
                self.exitbutton.setEnabled(False)

        else:  # when exiting before the game started, exit_room_msg needs to have the room type in data field
            self.exited = True
            if self.ID != "":
                build_and_send_message(commprot.CLIENT_CMD["exit_room_msg"], self.ID)
            elif self.invitation:
                build_and_send_message(commprot.CLIENT_CMD["exit_room_msg"], "invitation")
            else:
                build_and_send_message(commprot.CLIENT_CMD["exit_room_msg"], "open")
        self.goback()

    def goback(self):
        print("enter goback")
        # widget.setCurrentIndex(7)

        # global main_menu, edit_user_screen, topten_screen, friends_menu, play_menu, invitations_menu

        if self.update_score:
            global main_menu, edit_user_screen, topten_screen, friends_menu, play_menu, invitations_menu
            main_menu.set_score()
            topten_screen.set_score()
            friends_menu.set_score()
            play_menu.set_score()
            invitations_menu.set_score()

        widget.setCurrentIndex(7)
        # widget.removeWidget(widget.currentWidget())
        # play_menu = PlayMenu()
        # widget.insertWidget(7, play_menu)
        # widget.setCurrentIndex(7)


# QTHREADS WORKERS

class UpdatesReceiver(QObject):
    topten_updated = pyqtSignal(name="topten_updated")
    friends_updated = pyqtSignal(name="friends_updated")
    invitation_received = pyqtSignal(str, name="invitation_received")
    invitation_removed = pyqtSignal(name="invitation_removed")
    finished = pyqtSignal(name="finished")

    def run(self):
        print("entered UpdatesReceiver's run func")
        global listen, listen_socket, server_socket, invitations, edit_invitations_list

        while listen:
            try:
                cmd, data = recv_message_and_parse(sock=server_socket)
                if cmd == commprot.SERVER_CMD["playing_invitation_msg"]:
                    build_and_send_message(commprot.CLIENT_CMD["invitation_received_msg"], "", sock=server_socket)
                    edit_invitations_list.acquire()
                    invitations.append(data)
                    edit_invitations_list.release()
                    self.invitation_received.emit(data)
                elif cmd == commprot.SERVER_CMD["remove_invitation_msg"]:
                    edit_invitations_list.acquire()
                    try:
                        invitations.remove(data)
                    except ValueError:
                        print("receive_invitation func - removed invitation was not in invitations")
                    else:
                        print("\n", data, "has removed their playing invitation to you")
                        self.invitation_removed.emit()
                    edit_invitations_list.release()
                elif cmd == commprot.SERVER_CMD["topten_updated_msg"]:
                    self.topten_updated.emit()
                elif cmd == commprot.SERVER_CMD["friends_updated_msg"]:
                    self.friends_updated.emit()
                else:
                    build_and_send_message("", "", sock=server_socket)

            except OSError and Exception as e:
                print("receive_invitation func error:", e)
                break

        print("receive_invitation DONE")
        self.finished.emit()
        listen = False


class AnswerWaitingWorker(QObject):
    finished = pyqtSignal(name="finished")
    accepted = pyqtSignal(name="accepted")
    rejected = pyqtSignal(name="rejected")
    not_answered = pyqtSignal(name="not_answered")
    error = pyqtSignal(str, name="error")

    def run(self):
        print("waiting for response...")
        response, _ = recv_message_and_parse(settimeout=30)
        if response == commprot.SERVER_CMD["invitation_accepted_msg"]:
            self.accepted.emit()
        elif response == commprot.SERVER_CMD["invitation_rejected_msg"]:
            self.rejected.emit()
        elif response == commprot.SERVER_CMD["error_msg"]:
            self.error.emit(commprot.DATA_MESSAGES[_])
        else:
            self.not_answered.emit()
        self.finished.emit()


class ExitWorker(QObject):
    finished = pyqtSignal(name="finished")

    def run(self):
        build_and_send_message(commprot.CLIENT_CMD["exit_room_msg"], "")
        response, _ = recv_message_and_parse()
        while response != commprot.SERVER_CMD["success_msg"] and response != commprot.SERVER_CMD["error_msg"]:
            response, _ = recv_message_and_parse()
        if response == commprot.SERVER_CMD["error_msg"]:
            if _ != "other_player_exited" and _ != "unrecognized_command":
                print("exit_room func - exit while it's not your turn failed:", response, _)
                return
        self.finished.emit()


# DATA RETRIEVING METHODS

def my_score():
    """
    sends the server a message that the client wants to know their score
    """
    cmd, score = build_send_recv_parse(commprot.CLIENT_CMD["my_score_msg"], "")
    if cmd == commprot.SERVER_CMD["your_score_msg"]:
        print("Your current score:", score)
        return score
    else:
        print("error:", cmd, score)
        return None


def top_ten():
    cmd, data = build_send_recv_parse(commprot.CLIENT_CMD["topten_msg"], "")

    if cmd == commprot.SERVER_CMD["error_msg"]:
        print("error:", cmd, data)
        return

    topten = data
    while cmd != commprot.SERVER_CMD["topten_fin_msg"]:
        cmd, data = recv_message_and_parse()
        if cmd == commprot.SERVER_CMD["error_msg"]:
            print("error:", cmd, data)
            return
        topten += data

    users = topten.split("#")
    scores = []
    for user in users:
        username, score = user.split(":")
        scores.append(user.split(":"))
        print(username, "-", score)

    return scores


def logged_users():
    cmd, data = build_send_recv_parse(commprot.CLIENT_CMD["logged_users_msg"], "")
    if cmd == commprot.SERVER_CMD["error_msg"]:
        print("error:", cmd, data)
        return
    logged = data
    while cmd != commprot.SERVER_CMD["logged_users_fin_msg"]:
        cmd, data = recv_message_and_parse()
        if cmd == commprot.SERVER_CMD["error_msg"]:
            print("error:", cmd, data)
            return
        logged += data
    logged = logged.replace("#", "\n")
    print("Logged users:")
    print(logged)


def my_friends():
    cmd, data = build_send_recv_parse(commprot.CLIENT_CMD["my_friends_msg"], "")

    if cmd == commprot.SERVER_CMD["error_msg"]:
        print("error:", cmd, data)
        return

    friends_str = data
    while cmd != commprot.SERVER_CMD["your_friends_fin_msg"]:
        cmd, data = recv_message_and_parse()
        if cmd == commprot.SERVER_CMD["error_msg"] or cmd is None:
            print("error:", cmd, data)
            return
        friends_str += data

    if len(friends_str) == 0:
        friends_lst = []
    else:
        friends_lst = friends_str.split("#")
    print("YOUR FRIENDS LIST:\n", friends_lst)
    return friends_lst


def my_pending_requests():
    cmd, data = build_send_recv_parse(commprot.CLIENT_CMD["my_p_requests_msg"], "")

    if cmd == commprot.SERVER_CMD["error_msg"]:
        print("error:", cmd, data)
        return

    reqs_str = data
    while cmd != commprot.SERVER_CMD["your_p_requests_fin_msg"]:
        cmd, data = recv_message_and_parse()
        if cmd == commprot.SERVER_CMD["error_msg"]:
            print("error:", cmd, data)
            return
        reqs_str += data

    if len(reqs_str) == 0:
        reqs_list = []
    else:
        reqs_list = reqs_str.split("#")
    print("YOUR PENDING FRIEND REQUESTS LIST:\n", reqs_list)
    return reqs_list


def my_sent_requests():
    cmd, data = build_send_recv_parse(commprot.CLIENT_CMD["my_s_requests_msg"], "")

    if cmd == commprot.SERVER_CMD["error_msg"]:
        print("error:", cmd, data)
        return

    reqs_str = data
    while cmd != commprot.SERVER_CMD["your_s_requests_fin_msg"]:
        cmd, data = recv_message_and_parse()
        if cmd == commprot.SERVER_CMD["error_msg"]:
            print("error:", cmd, data)
            return
        reqs_str += data

    if len(reqs_str) == 0:
        reqs_lst = []
    else:
        reqs_lst = reqs_str.split("#")
    print("YOUR SENT FRIEND REQUESTS LIST:\n", reqs_lst)
    return reqs_lst


# CLOSING METHODS

def logout():
    global listen_socket, server_socket, listen, logging_out

    logging_out = True
    listen = False
    build_and_send_message(commprot.CLIENT_CMD["logout_msg"], "")

    try:
        listen_socket.close()
    except:
        print("logout func: listen_socket closing failed")
    try:
        server_socket.close()
    except:
        print("logout func: server_socket closing failed")
    try:
        client_socket.close()
    except:
        print("logout func: client_socket closing failed")

    print("CLIENT LOGOUT")
    print("ENDING")
    sys.exit()


# ---------------------------- MAIN ----------------------------
# CREATING GUI APP
app = QApplication(sys.argv)
# CREATING SCREENS
welcome_screen = WelcomeScreen()
login_screen = LoginScreen()
signup_screen = SignupScreen()
main_menu = None
edit_user_screen = None
topten_screen = None
friends_menu = None
play_menu = None
invitations_menu = None
# SETTING SHOWING WIDGET
widget = QStackedWidget()
widget.insertWidget(0, welcome_screen)
widget.insertWidget(1, login_screen)
widget.insertWidget(2, signup_screen)
widget.setFixedHeight(600)
widget.setFixedWidth(1000)
widget.show()

try:
    app.exec_()
    logout()
except:
    print("end")
