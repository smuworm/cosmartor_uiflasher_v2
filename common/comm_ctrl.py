from PyQt5 import QtWidgets,QtCore
from PyQt5.QtWidgets import QApplication,QMainWindow,QAction,QMessageBox,QTableWidgetItem,QCheckBox,QAbstractItemView,QLabel,QSizePolicy,QToolBar,QWidget,QHBoxLayout,QVBoxLayout,QFrame,QPushButton,QDialog
from PyQt5.QtWidgets import QListView,QHeaderView,QLCDNumber,QGraphicsDropShadowEffect
import os
import sys
from PyQt5.QtCore import QUrl,QMargins,QThread,QDateTime,QMutex,Qt,QFileInfo,QVariant,QEvent,pyqtSignal,pyqtSlot,QObject,QTimer

from PyQt5.QtGui import QImage, QPixmap,QIcon,QFont,QColor,QKeySequence,QConicalGradient,QLinearGradient,QPalette,QCursor, QStandardItemModel,QStandardItem,QBrush
from PyQt5.QtCore import QTranslator,QLocale
import re
import intelhex as ih
import struct
import datetime

import psutil
import signal
import time

import subprocess

from PyQt5.QtCore import QProcess

translate = QtCore.QCoreApplication.translate
trans = QTranslator()

cantype_dict = {
    0:'CAN',
    1:'CANFD'
    }

devicetype_dict = {
    0:'PCAN',
    1:'USBCAN-4E-U',
    2:'USBCAN-II',
    3:'USBCAN-2E-U'
    }

baudrate_dict = {
    0:"125K",
    1:'250K',
    2:'500K',
    3:"800K",
    4:'1000K',
    5:'1440K'
    }

RUN_STATUS_RUNOK = 0
RUN_STATUS_RUNNING = 1
RUN_STATUS_RUNERROR = 2
RUN_STATUS_RUNEND = 3

RESULT_STATUS_INFO = 0
RESULT_STATUS_UPDATE_PROCESS_BAR = 1
RESULT_STATUS_OK = 2
RESULT_STATUS_ERROR = 3

progressbarStyle = "QProgressBar { border: 1px solid grey; border-radius: 5px; background-color: #FFFFFF; text-align: center;} QProgressBar::chunk {background:QLinearGradient(x1:0,y1:0,x2:2,y2:0,stop:0 #666699,stop:1  #00ff00); }"

listview_qss = '''
        QListView {
            outline:none;
            show-decoration-selected: 1;
        }
        
        QListView::item:alternate {
            background: #EEEEEE;
        }
        
        QListView::item {
            padding: 10px;
        }

        QListView::item:selected:!active {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #f0f0f0, stop: 1 #f0f0f0);
        }
        
        QListView::item:selected:active {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #1b9aee, stop: 1 #1b9aee);
        }
        
        QListView::item:hover {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #FAFBFE, stop: 1 #DCDEF1);
        }

        '''

flashlistview_qss_gray = '''
        QListView {
            outline:none;
            background-image:url(:png/gnd.png);
        }
        QListView::item {
            padding: 2px;
            height: 40px;
            margin: 4px;
            border-radius: 6px;
        }

       '''

dialog_qss_gray = '''
        QDialog{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #f0f0f0, stop: 1 #e5e5e5);
            height: 40px;
            margin: 0px;
            padding: 0px 0px 0px 6px;
            border-radius: 6px;
            border: 1px solid white; 
        }
        QLabel{ color:black;}
       '''

dialog_qss_green = '''
        QDialog{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #408030, stop: 1 #306030);
            height: 40px;
            margin: 0px;
            padding: 0px 0px 0px 6px;
            border-radius: 6px;
            border: 1px solid white; 
        }
        QLabel{ color:white;}
       '''

dialog_qss_yellow = '''
        QDialog{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #f0f000, stop: 1 #e0e000);
            height: 40px;
            margin: 0px;
            padding: 0px 0px 0px 6px;
            border-radius: 6px;
            border: 1px solid white; 
        }
        QLabel{ color:black;}
       '''

dialog_qss_red = '''
        QDialog{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #c00000, stop: 1 #b00000);
            height: 40px;
            margin: 0px;
            padding: 0px 0px 0px 6px;
            border-radius: 6px;
            border: 1px solid white; 
        }
        QLabel{ color:white;}
       '''


btn_qss = '''
   QPushButton {
                color: white;
                background-color: #1b9aee;
                border-radius: 8px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #0171c2;
            }
            QPushButton:pressed {
                background-color: #004f8a;
            }
            QPushButton:disabled{
                background-color:#CCCCCC;
                color:#FFFFFF;    
            }
            QPushButton:focus {
                border: 1px solid blue; 
                outline: none;
            }
   '''
menu_qss = '''
   QMenuBar {
      background-color: rgb(250,250,250);
      font-family: 'SimSun';
      font: 9pt;
   }
   QMenuBar::item {
      spacing: 3px;           
      padding: 5px 6px;
      background-color: transparent;
      border-radius: 6px;
      margin-left: 5px;
      font-family: 'SimSun';
      font: 9pt;
      
   }
   QMenuBar::item:selected {    
      background-color: rgb(220,220,220);
   }
   QMenuBar::item:pressed {
      background: rgb(220,220,220);
   }

   QMenu {
      background-color: #ffffff;   
      border: 1px solid lightgrey;
      margin: 2px;
      border-radius: 6px;
      margin-left: 3px;
      font-family: 'SimSun';
      font: 9pt;
   }
   QMenu::item {
      background-color: transparent;
      padding: 5px 10px 5px 10px; 
      border-radius: 6px;
      margin: 6px;
      font-family: 'SimSun';
      font: 9pt;
   }
   QMenu::item:selected { 
      background-color: #005fbb;
      color: rgb(255,255,255);
      border-radius: 6px;
      margin: 6px;
   }
'''

def MAP_TRIGGERED_MESSAGE(ctrl, ctrl_id, slot_func, short_cut = None):
    ctrl.triggered.connect(slot_func)
    ctrl.setProperty('id', ctrl_id)
    if short_cut is not None:
        ctrl.setShortcut(short_cut)

def MAP_CLICKED_MESSAGE(ctrl, ctrl_id, slot_func,style = btn_qss, bhas_effect = True):
    ctrl.clicked.connect(slot_func)
    ctrl.setProperty('id', ctrl_id)
    ctrl.setStyleSheet(style)
    if(bhas_effect):
        ctrl.setGraphicsEffect(CustomShadowEffect())
  
class AutoCloseDialog(QDialog):
    def __init__(self, timeout = 2, tipstr = "", parent=None):
        super(AutoCloseDialog, self).__init__(parent)
        self.h_layout = QVBoxLayout()
        self.tip = QLabel(tipstr)
        self.h_layout.addWidget(self.tip )
        self.setLayout(self.h_layout)
        self.setWindowTitle('Tip infomation')
        self.setFixedSize(200, 60)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.close)
        self.timer.start(timeout)
 
    def closeEvent(self, event):
        self.timer.stop()
        QDialog.closeEvent(self, event)

def find_window_by_title(title):
    windows = QApplication.allWidgets()
    print(windows)
    for window in windows:
        if isinstance(window, QMainWindow):
            if window.windowTitle() == title:
                return window
    return None
 
def get_current_exe_disk():
    path_exe = os.getcwd()
    disk_label = path_exe.split('\\')[0]
    return disk_label

def get_current_exe_path():
    return os.getcwd()
 
def run_command_without_console(command = '', block = False):
    #os.system(command)
    if not block:
        subprocess.Popen(command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def is_process_running(process_name):
    for proc in psutil.process_iter(['name', 'pid']):
        # 检查进程名是否匹配
        if proc.info['name'] == process_name:
            return True
    return False
 
def end_process_by_name(process_name):
    #遍历所有运行中的进程
    bkill = True
    i = 0
    while True:
        bkill = True
        i += 1
        for proc in psutil.process_iter(['name', 'pid']):
            # 检查进程名是否匹配
            if proc.info['name'] == process_name:
                # 使用进程ID来结束进程
                pid = proc.info['pid']
                run_command_without_console(f'taskkill /F /PID {pid}', True)
                #time.sleep(0.1)
                bkill = False

        if bkill or i > 2:
            break

def common_cal_crc(data, crctype, poly, init, final_xor, rev_in, rev_out)-> int:
    crcwidth = 32
    if crctype == 1:
        crcwidth = 16
    elif crctype == 2:
        crcwidth = 8

    polynomial = poly
    width = crcwidth
    initial_value = init
    result_xor_value = final_xor
    input_reversed = rev_in
    output_reversed = rev_out

    crc = initial_value
    for byte in data:
        if input_reversed:
            byte = int('{:08b}'.format(byte)[::-1], 2)
        for _ in range(8):
            bit = (byte >> 7) & 1
            byte <<= 1
            crc <<= 1
            if (crc >> width) & 1 ^ bit:
                crc ^= polynomial
        crc &= (1 << width) - 1

    if output_reversed:
        crc = int('{:0{width}b}'.format(crc, width=width)[::-1], 2)

    crc = crc ^ result_xor_value

    return crc & 0xFFFFFFFF
	
def hex_file_parse_func(path):
    # 解析hex文件并打印相关信息
    try:
        hex_file = ih.IntelHex(path)
        return hex_file, hex_file.minaddr(), hex_file.maxaddr(), (hex_file.maxaddr() - hex_file.minaddr() + 1)
    except Exception as e:
        return None, None, None, None



def bytes_to_hex(byte_array):
    '''
    将字节数组转换为16进制字符串
    '''
    return ' '.join('{:02x}'.format(b) for b in byte_array)

def hex_to_bytes( hex_string):
    '''
    将16进制字符串转换为字节数组
    '''
    return bytes.fromhex(hex_string)

def bytes_to_short(byte_h, byte_l):
    # 将两个字节合并为一个16位的二进制数
    bytes_combined = byte_h << 8 | byte_l  # 将byte1左移8位，然后通过或运算(|)与byte2合并
    return bytes_combined

def hexStringToListArray(data_s):
    data = []
    if len(data_s) > 0:
       strList = data_s.split(' ')
       count = len(strList)
       if count > 0:
          for i in range(count):
              data.append(int(strList[i], 16))
    return data

def getFormatText(catalog, msg):
    current_time = datetime.datetime.now()
    time_string = current_time.strftime("%m-%d %H:%M:%S")
    if catalog == 'error':
        return "<font color=\"#FF0000\">"+  '[ERRORS&nbsp;] ' + time_string + '  '+ '<b>'+  msg + '</b>' + "</font>"
    elif catalog == 'ok':
        return "<font color=\"#00A000\">" + '[SUCCEED] ' + time_string + '  '+ msg + "</font>"
    else:
        return "<font color=\"#000000\">" + '[INFO&nbsp;&nbsp;&nbsp;] ' + time_string + '  '+ msg + "</font>"

def showtipbox(parent = None, wintype = 'warnning', title = "", info="", btncount = 1):
    msg_box = QMessageBox(parent)
    msg_box.setStyleSheet("QMessageBox {font-family: 'Consolas';font-weight: lighter;font: 10pt;}")
    msg_icon_lab = msg_box.findChild(QLabel, "qt_msgboxex_icon_label")
    if msg_icon_lab is not None:
        msg_icon_lab.setStyleSheet("QLabel {max-width: 60px;"
                                    "qproperty-alignment: 'AlignCenter';"
                                    "max-height: 60px;}")
    msg_lab = msg_box.findChild(QLabel, "qt_msgbox_label")
    if msg_lab is not None:
        msg_lab.setStyleSheet("QLabel {min-width: 270px;"
                                "min-height: 60px;}")
    msg_box.setWindowTitle(title)
    msg_box.setText(info)
    
    if wintype == 'info':
        msg_box.setIcon(QMessageBox.Information)
    elif wintype == 'ask':
        msg_box.setIcon(QMessageBox.Question)
    else:
        msg_box.setIcon(QMessageBox.Warning)

    ok_button = msg_box.addButton(translate("MainWindow","Ok"), QMessageBox.ActionRole)
    if btncount >= 2:
        cancel_button = msg_box.addButton(translate("MainWindow", "Cancel"), QMessageBox.ActionRole)
    
    msg_box.exec_()

    result = QMessageBox.No
    if msg_box.clickedButton() == ok_button:
        result = QMessageBox.Yes

    return result

class CustomShadowEffect(QGraphicsDropShadowEffect):
    def __init__(self, blurcolor = Qt.black, x = 0, y = 0, radius = 10):
        super(QGraphicsDropShadowEffect, self).__init__()
        self.setColor(blurcolor)
        self.setOffset(x, y)
        self.setBlurRadius(radius)
        return None

class MyCheckBox(QWidget):

    def __init__(self,checkState):
        super(MyCheckBox, self).__init__()
        self.setStyleSheet("background-color:#232629")
        widgetHLayout = QHBoxLayout()
        widgetHLayout.setContentsMargins(0, 0, 0, 0)
        widgetHLayout.setAlignment(Qt.AlignHCenter)
        self.setLayout(widgetHLayout)
        self.AddCheckBox(checkState)
 
    def AddCheckBox(self,checkState):
        self.checkBox = QCheckBox()
        self.checkBox.setChecked(checkState)
        self.layout().addWidget(self.checkBox)
