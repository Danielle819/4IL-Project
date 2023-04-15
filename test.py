from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow
import sys


class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()
        self.initUI()

    def initUI(self):
        self.label = QtWidgets.QLabel(self)
        self.label.setText("Welcome to 4IL!")
        self.label.move(150, 150)

        self.button1 = QtWidgets.QPushButton(self)
        self.button1.setText("Click Me")
        self.button1.clicked.connect(touched)

    def touched(self):
        self


def touched():
    print("clicked")


def window():
    app = QApplication(sys.argv)
    win = QMainWindow()
    win.setGeometry(200, 200, 300, 300)
    win.setWindowTitle("4IL Window")

    label = QtWidgets.QLabel(win)
    label.setText("Welcome to 4IL!")
    label.move(150, 150)

    button1 = QtWidgets.QPushButton(win)
    button1.setText("Click Me")
    button1.clicked.connect(touched)

    win.show()
    sys.exit(app.exec_())


window()



