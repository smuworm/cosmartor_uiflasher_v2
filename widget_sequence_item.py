from PyQt5 import QtWidgets,QtCore
from PyQt5.QtWidgets import QApplication,QMainWindow,QAction,QMessageBox,QTableWidgetItem,QCheckBox,QAbstractItemView,QLabel,QSizePolicy,QToolBar,QWidget,QHBoxLayout,QVBoxLayout,QGraphicsDropShadowEffect,QFrame,QPushButton,QMenu,QProgressBar,QToolButton,QGraphicsBlurEffect,QDialog
from PyQt5.QtWidgets import QListView,QHeaderView
import os
from common.comm_ctrl import *

from ui.Ui_widget_sequence_item import Ui_widget_sequence_item

class widget_squence_item(QDialog, Ui_widget_sequence_item):
    def __init__(self):
        super(widget_squence_item,self).__init__()
        self.setupUi(self)
        self.setWindowOpacity(1)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
        self.setGraphicsEffect(CustomShadowEffect())
        self.setStyleSheet(dialog_qss_gray)

