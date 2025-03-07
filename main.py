import sys
import PyQt5.QtCore
from PyQt5 import QtWidgets,QtCore,QtGui
from mainwindow import MainWindow
from PyQt5.QtWidgets import QApplication,QMainWindow
from PyQt5.QtCore import Qt,QTranslator

if __name__ == '__main__':

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    app.setStyle(QtWidgets.QStyleFactory.create("Fusion"))
    
    # 设置图标
    
    app.setWindowIcon(QtGui.QIcon(':ico/app.ico'))
    
    font = QtGui.QFont("Consolas", 8)
    app.setFont(font)

    win = MainWindow()

    win.show()

    sys.exit(app.exec_())

