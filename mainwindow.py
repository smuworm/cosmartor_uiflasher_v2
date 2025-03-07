from PyQt5 import QtWidgets,QtCore
from PyQt5.QtWidgets import QApplication,QMainWindow,QAction,QMessageBox,QTableWidgetItem,QCheckBox,QAbstractItemView,QLabel,QSizePolicy,QToolBar,QWidget,QHBoxLayout,QVBoxLayout,QGraphicsDropShadowEffect,QFrame,QPushButton,QMenu,QProgressBar,QToolButton,QGraphicsBlurEffect
from PyQt5.QtWidgets import QListView,QHeaderView,QLCDNumber,QSplitter,QFileDialog,QListWidgetItem
import os
from PyQt5.QtCore import QUrl,QMargins,QThread,QDateTime,QMutex,Qt,QFileInfo,QVariant,QEvent,pyqtSignal,pyqtSlot,QPropertyAnimation
from PyQt5.QtGui import QImage, QPixmap,QIcon,QFont,QColor,QKeySequence,QConicalGradient,QLinearGradient,QPalette,QCursor, QStandardItemModel,QStandardItem,QTextCursor
from PyQt5.QtCore import QTranslator,QLocale,QByteArray,QTimer
import json
import time
import sys
import struct
from pyfiglet import Figlet
import shlex

from datetime import datetime, timedelta

from res.res_rc import *
from common.comm_ctrl import *
from resourceid import *
from config import Config, global_config
from ui.Ui_mainwindow import Ui_MainWindow
from widget_sequence_item import widget_squence_item

from editflashconfig import EditFlashConfig, global_executeflashconfig
from uniflasher import uniflasher

from rwreg import *

RELEASE_VER  = '0.0.2'
RELEASE_DATE = '2025/1/10'

class MainWindow(QMainWindow, Ui_MainWindow):
    signal_reload_sequence_file = pyqtSignal()
    def __init__(self):
        super(MainWindow,self).__init__()
        self.setupUi(self)

        global_config.loadConfig()
        self.loadconfigok = False

        self.setupButton()
        self.setup_ToolBar()
        self.spliter_win()

        self.ChangeLang('cn')
         
        self.signal_reload_sequence_file.connect(self.on_reload_sequence_file)
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_watch_file_modify_status)
        
        if global_config.flash_ver <= 1:
            self.radioButton_v2.setChecked(True)
            self.radioButton_v3.setChecked(False)
        else:
            self.radioButton_v2.setChecked(False)
            self.radioButton_v3.setChecked(True)

        self.init_flash_sequence()

        self.radioButton_v2.toggled.connect(self.onRadioButtonToggled)
        self.radioButton_v3.toggled.connect(self.onRadioButtonToggled)

        self.udsflasher = uniflasher()
        self.mutex = QMutex()
        self.thread = QThread()
        self.udsflasher.moveToThread(self.thread)
        self.thread.start()
        self.udsflasher.signal_update_sequence.connect(self.on_update_squence_status_byindex)
        self.udsflasher.signal_Respond.connect(self.on_receivedResponse)
        self.udsflasher.signal_NegRespond.connect(self.on_receivedNegResponse)
        self.udsflasher.signal_write_to_log.connect(self.on_write_to_log)

        self.btn_edit_clk_current_time = datetime.datetime.now() - timedelta(seconds=5)
        self.sequence_file_esist = False

        self.setWindowTitle("UniFlasher V" + RELEASE_VER)

        self.changeResp =  True

        self.comboBox_candev.currentIndexChanged.connect(self.on_indexChange_dev)                # 关联信号与槽   
        self.comboBox_canrate.currentIndexChanged.connect(self.on_indexChange_baud)               # 关联信号与槽
        self.lineEdit_severid.textChanged.connect(self.on_textChange_server)                # 关联信号与槽   
        self.lineEdit_clientid.textChanged.connect(self.on_textChange_client)    
    
    def on_indexChange_dev(self, i):
        global_executeflashconfig.moresettings["devtype"] = self.comboBox_candev.currentIndex()
        global_executeflashconfig.writeflashConfig(global_config.flashsequencefile)

    def on_indexChange_baud(self, i):
        global_executeflashconfig.moresettings["baud"] = self.comboBox_canrate.currentIndex()
        global_executeflashconfig.writeflashConfig(global_config.flashsequencefile)
    
    def on_textChange_server(self):
        global_executeflashconfig.moresettings["respid"] = self.lineEdit_severid.text()
        global_executeflashconfig.writeflashConfig(global_config.flashsequencefile)

    def on_textChange_client(self):
        global_executeflashconfig.moresettings["requid"] = self.lineEdit_clientid.text()
        global_executeflashconfig.writeflashConfig(global_config.flashsequencefile)

    def startTimer(self):
        try:
           self.initial_modify_time = os.path.getmtime(global_config.flashsequencefile)
           self.sequence_file_esist = True
        except:
           self.initial_modify_time = datetime.datetime.now()
           self.sequence_file_esist = False
        self.timer.start(1000)  # 每1000毫秒（1秒）触发一次showTime函数
    
    def stopTimer(self):
        self.timer.stop()  # 停止定时器

    def closeEvent(self,event):
        result = showtipbox(self, 'warn', self.tr("warnning"), self.tr("Are you sure to quit?"), 2)
        if result == QMessageBox.Yes:
            event.accept()  # 接受关闭事件
            #self.stopTimer()
            self.on_menubar_StopFlashThread()
            self.thread.quit()
        else:
            event.ignore()  # 忽略关闭事件

    def retransToolbar(self):
        self.toolbtn_quit.setText(self.tr("Quit"))
        self.toolbtn_quit.setToolTip(self.tr("Quit"))
    
    def ChangeLang(self, lang = 'en'):
        _app = QApplication.instance()
        if lang == 'en':
           _app.removeTranslator(trans)
           self.setLocale(QLocale(QLocale.English))

        elif lang == 'cn':
           trans.load("mul_zh_CN.qm")
           _app.installTranslator(trans)
           self.setLocale(QLocale(QLocale.Chinese))

        self.retranslateUi(self)
        self.retransToolbar()

    def onRadioButtonToggled(self, state):
        if self.radioButton_v2.isChecked():
            global_config.flash_ver = 1
        if self.radioButton_v3.isChecked():
            global_config.flash_ver = 2

        self.init_flash_sequence()

    #监控文件是否修改
    def on_watch_file_modify_status(self):
        # 监控指定目录
        if self.udsflasher.isRunning():
            return

        filename = global_config.flashsequencefile
        try:
           current_modify_time = os.path.getmtime(filename)
           self.sequence_file_esist = True
        except:
           current_modify_time = self.initial_modify_time
           if self.sequence_file_esist:
               self.sequence_file_esist = False
               self.signal_reload_sequence_file.emit()
               return
           self.sequence_file_esist = False

        if current_modify_time != self.initial_modify_time and self.sequence_file_esist:
           self.initial_modify_time = current_modify_time
           self.signal_reload_sequence_file.emit()

    #开机读取配置文件中的序列文件名，并分析显示至列表
    def init_flash_sequence(self):
        if global_config.flash_ver <= 2:
            filename = get_current_exe_path() + '\\' + 'sequence_v2.config'
            if global_config.flash_ver > 1:
               filename = get_current_exe_path() + '\\' + 'sequence_v3.config'
            global_config.flashsequencefile = filename
            global_config.writeConfig()
            try:
                self.filename_label.setText(filename)
                global_executeflashconfig.loadflashConfig(filename)
            except:
                global_executeflashconfig.sequence = []
            #self.startTimer()
            self.ShowFlashSequence()
        else:
            self.show_logo_txt()
            #self.textBrowser_flashlog.append(getFormatText("error", "-----Please select a sequence file firstly----"))

    #初始化按钮
    def setupButton(self):
        self.progressBar_flash.setStyleSheet(progressbarStyle)

        MAP_CLICKED_MESSAGE(self.pushButton_main_clear_flashlog, BTN_MAINWINDOW_CLEAR_FLASH_LOG, self.on_btnclick)
        MAP_CLICKED_MESSAGE(self.pushButton_main_export_flashlog, BTN_MAINWINDOW_EXPORT_FLASH_LOG, self.on_btnclick)

        MAP_CLICKED_MESSAGE(self.pushButton_select_flash_drv_hex_file, BTN_MAINWINDOW_SELECT_FLASH_DRV_HEX_FILE, self.on_btnclick)
        MAP_CLICKED_MESSAGE(self.pushButton_select_hex_file, BTN_MAINWINDOW_SELECT_HEX_FILE, self.on_btnclick)
        MAP_CLICKED_MESSAGE(self.pushButton_select_key_dll_file, BTN_MAINWINDOW_SELECT_KEY_DLL_FILE, self.on_btnclick)

        #self.listWidget_main_execute_flash_sequence.setGraphicsEffect(CustomShadowEffect())
        self.listWidget_main_execute_flash_sequence.setStyleSheet(flashlistview_qss_gray)
 
    #拆分窗口
    def spliter_win(self):
        self.splitter = QSplitter(Qt.Horizontal)  # 水平拆分
        self.splitter.addWidget(self.listWidget_main_execute_flash_sequence)
        self.splitter.addWidget(self.frame_main_flashlog)
        self.splitter.setSizes([250,300])
        self.horizontalLayout_flash_executor.addWidget(self.splitter)
        self.filename_label = QLabel("")
        
        #self.filename_label.setGraphicsEffect(CustomShadowEffect(x=1,y=1))
        #self.statusbar.addWidget(QLabel(''))
        #self.statusbar.addWidget(self.filename_label)

    #初始化工具栏     
    def setup_ToolBar(self):
        self.toolBar.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self.toolbtn_sequence_load=QAction(QIcon(':png/open.png'), self.tr("Load"),self)
        MAP_TRIGGERED_MESSAGE(self.toolbtn_sequence_load, IDN_MENU_LOAD_FLASH_SEQU, self.on_menucommand)
        #self.toolBar.addAction(self.toolbtn_sequence_load) 
        #self.toolBar.widgetForAction(self.toolbtn_sequence_load).setFixedWidth(60)

        self.toolbtn_sequence_edit=QAction(QIcon(':png/edit.png'), self.tr("Edit"),self)
        MAP_TRIGGERED_MESSAGE(self.toolbtn_sequence_edit, IDN_MENU_EDIT_FLASH_SEQU, self.on_menucommand)
        #self.toolBar.addAction(self.toolbtn_sequence_edit) 
        #self.toolBar.widgetForAction(self.toolbtn_sequence_edit).setFixedWidth(60)        

        #self.toolBar.addSeparator()

        self.toolbtn_start=QAction(QIcon(':png/start.png'), self.tr("Run"),self)
        MAP_TRIGGERED_MESSAGE(self.toolbtn_start, IDM_MENU_START, self.on_menucommand)
        self.toolBar.addAction(self.toolbtn_start)
        #self.toolBar.widgetForAction(self.toolbtn_start).setFixedWidth(60)
        
        self.toolBar.addSeparator()

        self.toolbtn_stop=QAction(QIcon(':png/stop.png'), self.tr("Stop"),self)
        MAP_TRIGGERED_MESSAGE(self.toolbtn_stop, IDM_MENU_STOP, self.on_menucommand)
        self.toolBar.addAction(self.toolbtn_stop)
        #self.toolBar.widgetForAction(self.toolbtn_stop).setFixedWidth(60)
        self.toolbtn_stop.setEnabled(False)
        
        spacer = QWidget()
        # 设置占位控件的策略，使其可以增长和收缩
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # # 在工具栏中添加占位控件
        self.toolBar.addWidget(spacer)

        self.toolbtn_quit=QAction(QIcon(':png/logo.png'), self.tr(""),self)
        #MAP_TRIGGERED_MESSAGE(self.toolbtn_quit, IDM_MENU_QUIT, self.on_menucommand)
        #self.toolBar.addAction(self.toolbtn_quit)
        #self.toolBar.widgetForAction(self.toolbtn_quit).setFixedWidth(60)
        #self.toolbtn_quit.setDisabled(True)
       
        self.label_logo = QLabel()
        self.label_logo.setFixedSize(48,48)
        self.label_logo.setScaledContents(True)
        self.label_logo.setPixmap(QPixmap(':png/logo.png'))
        self.toolBar.addWidget(self.label_logo)
        self.label_logo.setToolTip('UniFlasher\n' + 'V' + RELEASE_VER)
    
    def show_logo_txt(self):
        uniflaser_font = Figlet(font="speed")
        self.textBrowser_flashlog.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.textBrowser_flashlog.append('<font color=black>\n' + "</font>")
        self.textBrowser_flashlog.append('<font color=black>\n' + "</font>")
        self.textBrowser_flashlog.append('<font color=black>\n' + "</font>")
        self.textBrowser_flashlog.append('<font color=black>\n' + "</font>")
        self.textBrowser_flashlog.append('<font color=black>' + "</font>")

        self.textBrowser_flashlog.append(uniflaser_font.renderText("UniFlasher"))
        self.textBrowser_flashlog.append(uniflaser_font.renderText('V' + RELEASE_VER))

        self.textBrowser_flashlog.append(self.filename_label.text())

        self.textBrowser_flashlog.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

    #显示读取的升级序列基本信息
    def dispSettingStr(self):
        try:
            self.textBrowser_flashlog.append('<font color=black>---------------------------------' + "</font>")
            self.textBrowser_flashlog.append("<font color=black>ID List: " + "</font>")
            self.textBrowser_flashlog.append('<font color=black>---------------------------------' + "</font>")
            self.textBrowser_flashlog.append('<font color=black>Physical&nbsp;&nbsp;&nbsp;&nbsp;address:&nbsp;&nbsp;' + global_executeflashconfig.moresettings['requid'] + "</font>")
            self.textBrowser_flashlog.append('<font color=black>Functioncal&nbsp;address:&nbsp;&nbsp;' + global_executeflashconfig.moresettings['funcpid'] + "</font>")
            self.textBrowser_flashlog.append('<font color=black>Response&nbsp;&nbsp;&nbsp;&nbsp;address:&nbsp;&nbsp;' + global_executeflashconfig.moresettings['respid'] + "</font>")
            self.textBrowser_flashlog.append("<font color=black>---------------------------------" + "</font>")
            self.textBrowser_flashlog.append("<font color=black>" + cantype_dict[global_executeflashconfig.moresettings['cantype']] + ':&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;' + devicetype_dict[global_executeflashconfig.moresettings['devtype']] + "</font>")
            self.textBrowser_flashlog.append('<font color=black>Channel:&nbsp;&nbsp;&nbsp;&nbsp;' + str(global_executeflashconfig.moresettings['ch']) + "</font>")
            self.textBrowser_flashlog.append('<font color=black>Baud rate:&nbsp;&nbsp;' + baudrate_dict[global_executeflashconfig.moresettings['baud']] + "</font>")

            self.textBrowser_flashlog.append('<font color=black>---------------------------------' + "</font>")
        except:
            self.textBrowser_flashlog.append(getFormatText("error", "-----PARSE Setting file error----"))
            return False
        return True

    #显示烧写序列文件
    def ShowFlashSequence(self):

        self.textBrowser_flashlog.clear()
        count = len(global_executeflashconfig.sequence)
        self.show_logo_txt()
        self.textBrowser_flashlog.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        if count <= 0:
           self.loadconfigok = False
           self.textBrowser_flashlog.append("<font color=\"#FF0000\">" + "<b>Load ERROR, BAD Sequence file ...</b>" + "</font>")
        else:
           self.loadconfigok = True
           self.textBrowser_flashlog.append("<font color = black><b>Load OK ...</b></font>")
           self.dispSettingStr()
        
        self.changeResp =  False

        self.lineEdit_severid.setText(global_executeflashconfig.moresettings['respid'])
        self.lineEdit_clientid.setText(global_executeflashconfig.moresettings['requid'])
        self.comboBox_candev.setCurrentIndex(global_executeflashconfig.moresettings['devtype'])
        self.comboBox_canrate.setCurrentIndex(global_executeflashconfig.moresettings['baud'])
        iDownLoadCount = -1
        iFlashDrvHexIdx = -1
        iFlashHexIdx = -1
        for i in range(count):
            if global_executeflashconfig.sequence[i]["sid"] == 0x27:
                self.lineEdit_key_dll_file.setText(global_executeflashconfig.sequence[i]["libfilename_s"])
                palette = self.lineEdit_key_dll_file.palette()
                if os.path.exists(global_executeflashconfig.sequence[i]["libfilename_s"]):
                    palette.setColor(QPalette.Text, QColor(0, 0, 0)) # 设置文本颜色为黑色
                else:
                    palette.setColor(QPalette.Text, QColor(255, 0, 0)) # 设置文本颜色为红色
                self.lineEdit_key_dll_file.setPalette(palette)
     
            if global_executeflashconfig.sequence[i]["sid"] == 0x34:
                if iDownLoadCount < 0:
                   iDownLoadCount = 0
                if iDownLoadCount == 0:
                   iFlashHexIdx = i
                   iFlashDrvHexIdx = i
                elif iDownLoadCount > 0:
                    iFlashHexIdx = i
                iDownLoadCount += 1

        if iDownLoadCount == 0:
            iFlashDrvHexIdx = -1
            iFlashHexIdx = -1
            self.lineEdit_hex_file.setText('')
            self.lineEdit_flash_drv_hex_file.setText('')
            self.lineEdit_hex_file.setEnabled(False)
            self.pushButton_select_hex_file.setEnabled(False)
            self.lineEdit_flash_drv_hex_file.setEnabled(False)
            self.pushButton_select_flash_drv_hex_file.setEnabled(False)

        elif iDownLoadCount == 1:
            self.lineEdit_hex_file.setText(global_executeflashconfig.sequence[iFlashHexIdx]["hexfilename_s"])
            palette = self.lineEdit_hex_file.palette()
            if os.path.exists(global_executeflashconfig.sequence[iFlashHexIdx]["hexfilename_s"]):
                palette.setColor(QPalette.Text, QColor(0, 0, 0)) # 设置文本颜色为黑色
            else:
                palette.setColor(QPalette.Text, QColor(255, 0, 0)) # 设置文本颜色为红色
            self.lineEdit_hex_file.setPalette(palette)
            self.lineEdit_flash_drv_hex_file.setText('')

            self.lineEdit_hex_file.setEnabled(True)
            self.pushButton_select_hex_file.setEnabled(True)
            self.lineEdit_flash_drv_hex_file.setEnabled(False)
            self.pushButton_select_flash_drv_hex_file.setEnabled(False)

        elif iDownLoadCount > 1:
            self.lineEdit_hex_file.setText(global_executeflashconfig.sequence[iFlashHexIdx]["hexfilename_s"])
            palette = self.lineEdit_hex_file.palette()
            if os.path.exists(global_executeflashconfig.sequence[iFlashHexIdx]["hexfilename_s"]):
                palette.setColor(QPalette.Text, QColor(0, 0, 0)) # 设置文本颜色为黑色
            else:
                palette.setColor(QPalette.Text, QColor(255, 0, 0)) # 设置文本颜色为红色
            self.lineEdit_hex_file.setPalette(palette)
            self.lineEdit_flash_drv_hex_file.setText(global_executeflashconfig.sequence[iFlashDrvHexIdx]["hexfilename_s"])
            palette = self.lineEdit_flash_drv_hex_file.palette()
            if os.path.exists(global_executeflashconfig.sequence[iFlashDrvHexIdx]["hexfilename_s"]):
                palette.setColor(QPalette.Text, QColor(0, 0, 0)) # 设置文本颜色为黑色
            else:
                palette.setColor(QPalette.Text, QColor(255, 0, 0)) # 设置文本颜色为红色
            self.lineEdit_flash_drv_hex_file.setPalette(palette)

            self.lineEdit_hex_file.setEnabled(True)
            self.pushButton_select_hex_file.setEnabled(True)
            self.lineEdit_flash_drv_hex_file.setEnabled(True)
            self.pushButton_select_flash_drv_hex_file.setEnabled(True)

        self.changeResp =  True

        self.listWidget_main_execute_flash_sequence.clear()
        for i in range(count):
           item = QListWidgetItem("")
           disp_widget = widget_squence_item()
           datastr = global_executeflashconfig.getDataString(i, True)
           disp_widget.label_sequece_descript.setText( str(i + 1) + '. ' + global_executeflashconfig.sequence[i]["descript_s"])
           disp_widget.label_sequence_data.setText(datastr)

           self.listWidget_main_execute_flash_sequence.addItem(item)
           self.listWidget_main_execute_flash_sequence.setItemWidget(item, disp_widget)
        #列表回滚至第一行
        self.listWidget_main_execute_flash_sequence.setCurrentRow(0)

    #显示获取生成种子dll库文件界面
    def GetFlashLibFile(self,path='D:/'):
        filename, _ = QFileDialog.getOpenFileName(self, 'Select security library file', path, 'DLL Files (*.dll)')
        if filename:
            return filename
        return None

    #显示获取hex文件路径界面
    def GetFlashHexFile(self, path='D:/'):
        filename, _ = QFileDialog.getOpenFileName(self, 'Select Hex file', path, 'Hex Files (*.hex)')
        if filename:
            return filename
        return None

    #菜单及工具栏按钮事件响应函数
    def on_menucommand(self):
        id = self.sender().property('id')
        if id == IDM_MENU_CHINESE:
            self.ChangeLang('cn')

        elif id == IDM_MENU_ENGLISH:
            self.ChangeLang('en')

        elif id == IDM_MENU_QUIT:
            self.close()

        elif id == IDN_MENU_LOAD_FLASH_SEQU:
            self.on_menubar_OpenflashSequenceFile()

        elif id == IDN_MENU_EDIT_FLASH_SEQU:
            self.on_menubar_EditflashSequenceFile()

        elif id == IDM_MENU_START:
            self.on_menubar_StartFlashThread()
        
        elif id == IDM_MENU_STOP:
            self.on_menubar_StopFlashThread()

    #按钮事件响应函数
    def on_btnclick(self):
        id = self.sender().property('id')

        if id == BTN_MAINWINDOW_CLEAR_FLASH_LOG:
            self.textBrowser_flashlog.clear()
            self.show_logo_txt()

        elif id == BTN_MAINWINDOW_EXPORT_FLASH_LOG:
            self.on_btn_Export_log_toFile()
    
        elif id == BTN_MAINWINDOW_SELECT_FLASH_DRV_HEX_FILE:
            self.on_select_flash_drv_hex()

        elif id == BTN_MAINWINDOW_SELECT_HEX_FILE:
            self.on_select_flash_hex()

        elif id == BTN_MAINWINDOW_SELECT_KEY_DLL_FILE:
            self.on_select_key_dllkey_dll()

    #获取hex文件长度及地址    
    def get_hex_info_str(self, hex_file):
        segments = len(hex_file.segments())
        tipstr = '\n'
        for i in range(segments):
            start_addr = hex_file.segments()[i][0]
            end_addr = hex_file.segments()[i][1]
            hex_file_size = end_addr - start_addr
            tipstr += "Start Address: " + hex(start_addr) + " File Length: " + str(hex_file_size)  + ' (' + hex(hex_file_size) + ')\n'
        return tipstr

    #计算hex文件的CRC
    def cal_check(self, idx, hex_file_binary):
        # 计算crc
        try:
            crc_type = global_executeflashconfig.sequence[idx]["crc_type"]
            crc_polynormial = global_executeflashconfig.sequence[idx]["crc_polynormial"]
            crc_initial = global_executeflashconfig.sequence[idx]["crc_initial"]
            crc_output_xor_value = global_executeflashconfig.sequence[idx]["crc_output_xor_value"] 
            input_inversion_b = global_executeflashconfig.sequence[idx]["input_inversion_b"]
            output_inversion_b = global_executeflashconfig.sequence[idx]["output_inversion_b"]
            crc = common_cal_crc(hex_file_binary, 
                            crc_type, 
                            crc_polynormial, 
                            crc_initial, 
                            crc_output_xor_value, 
                            input_inversion_b, 
                            output_inversion_b)
            crc_str = '0x00'
            if crc_type == 0:
                  crc_str = '0x' + format(crc, '08x')
            elif crc_type == 1:
                  crc_str = '0x' + format(crc, '04x')
            else:
                  crc_str = '0x' + format(crc, '02x')
            global_executeflashconfig.sequence[idx]['crc_a'] = crc_str

            return crc
        except:
           return -1
    
    def modify_EraseRoutine(self, idx, address_size, len_size):
        count = len(global_executeflashconfig.sequence)
        if idx > 0:
           erase_idx = idx - 1
           if global_executeflashconfig.sequence[erase_idx]["sid"] == 0x31:
              databytes = global_executeflashconfig.sequence[erase_idx]["data_s"]

        addr_len_size = (address_size * 0x10) + len_size
        addr_len_size_str = format(addr_len_size, '02x')
        hex_file = None
        filename = global_executeflashconfig.sequence[idx]["hexfilename_s"]
        if len(filename) > 0:
            hex_file, hex_file_start_address, hex_file_end_address, hex_file_size = hex_file_parse_func(filename)
        if hex_file is None:
            hex_file_start_address = 0
            hex_file_size = 0

        if address_size == 4:
            hex_str_addr_str = format(hex_file_start_address, '08x')
        else:
            hex_str_addr_str = format(hex_file_start_address, '04x')
        if len_size == 4:
            hex_file_size_str = format(hex_file_size, '08x')
        else:
            hex_file_size_str = format(hex_file_size, '04x')
        
        #添加erase flash
        if len(databytes) > 8:
            databytes = databytes[:9]
            if address_size == 4:
                databytes += hex_str_addr_str[:2] + " " + hex_str_addr_str[2:4] + " " + hex_str_addr_str[4:6] + " " + hex_str_addr_str[6:] + " "
            else:
                databytes += hex_str_addr_str[:2] + " " + hex_str_addr_str[2:4] + " "

            if len_size == 4:
                databytes +=  hex_file_size_str[:2] + " " + hex_file_size_str[2:4] + " " + hex_file_size_str[4:6] + " " + hex_file_size_str[6:]
            else:
                databytes +=  hex_file_size_str[:2] + " " + hex_file_size_str[2:4]
            
            global_executeflashconfig.sequence[erase_idx]["data_s"] = databytes

    def modify_crc_check_seq(self, idx, crctype, crc):
        count = len(global_executeflashconfig.sequence)
        crc_check_idx = idx + 3
        if count > crc_check_idx:
           if global_executeflashconfig.sequence[crc_check_idx]["sid"] == 0x31:
              databytes = global_executeflashconfig.sequence[crc_check_idx]["data_s"]

              crc_str = '0x00'
              if crctype == 0:
                  crc_str = '0x' + format(crc, '08x')
              elif crctype == 1:
                  crc_str = '0x' + format(crc, '04x')
              else:
                  crc_str = '0x' + format(crc, '02x')
              crc_str = crc_str[2:]
              str_len = len(crc_str)
              if str_len == 4:
                  crc_final_str = crc_str[:2] + " " + crc_str[2:]
              elif str_len == 8:
                  crc_final_str = crc_str[:2] + " " + crc_str[2:4] + " " + crc_str[4:6] + " " + crc_str[6:]
              else:
                  crc_final_str = crc_str
                            
              if len(databytes) > 8:
                 global_executeflashconfig.sequence[crc_check_idx]["data_s"] = databytes[:6] + crc_final_str

    def on_select_flash_drv_hex(self):
        defaultfile = self.lineEdit_flash_drv_hex_file.text()
        filename =self.GetFlashHexFile(defaultfile)
        if filename is not None:
            self.lineEdit_flash_drv_hex_file.setText(filename)
            count = len(global_executeflashconfig.sequence)
            drvidx = -1
            for i in range(count):
                if global_executeflashconfig.sequence[i]["sid"] == 0x34:
                    global_executeflashconfig.sequence[i]["hexfilename_s"] = filename
                    drvidx = i
                    break
            if drvidx >= 0:
                hex_file, hex_file_start_address, hex_file_end_address, hex_file_size = hex_file_parse_func(filename)
                if hex_file is None:
                    self.lineEdit_flash_drv_hex_file.setToolTip("Failed to parse hex file")
                    showtipbox(title = 'Hex file error', info='Hex file format is Bad!')
                    return
                else:
                    self.lineEdit_flash_drv_hex_file.setToolTip(self.get_hex_info_str(hex_file))
                    start_addr = hex_file.segments()[0][0]
                    end_addr = hex_file.segments()[0][1]
                    hex_file_binary = hex_file.tobinarray(start = start_addr, size = end_addr - start_addr)

                crc = self.cal_check(drvidx, hex_file_binary)
                self.modify_crc_check_seq(drvidx, global_executeflashconfig.sequence[drvidx]["crc_type"], crc)
                if global_executeflashconfig.sequence[drvidx + 1]["sid"] == 0x36:
                    global_executeflashconfig.sequence[drvidx + 1]["hexfilename_s"] = filename
            global_executeflashconfig.writeflashConfig(global_config.flashsequencefile)

            self.ShowFlashSequence()

    def on_select_flash_hex(self):
        defaultfile = self.lineEdit_hex_file.text()
        filename =self.GetFlashHexFile(defaultfile)
        if filename is not None:
            self.lineEdit_hex_file.setText(filename)
            hex_file, hex_file_start_address, hex_file_end_address, hex_file_size = hex_file_parse_func(filename)
            if hex_file is None:
                self.lineEdit_hex_file.setToolTip("Failed to parse hex file")
                showtipbox(title = 'Hex file error', info='Hex file format is Bad!')
                return
            else:
                self.lineEdit_hex_file.setToolTip(self.get_hex_info_str(hex_file))
                start_addr = hex_file.segments()[0][0]
                end_addr = hex_file.segments()[0][1]
                hex_file_binary = hex_file.tobinarray(start = start_addr, size = end_addr - start_addr)
            count = len(global_executeflashconfig.sequence)
            downloadcount = -1
            downIdx1 = -1
            downIdx2 = -1
            for i in range(count):
                if global_executeflashconfig.sequence[i]["sid"] == 0x34:
                   if downloadcount < 0:
                       downloadcount = 0
                   if downloadcount == 0:
                       downIdx1 = i
                   elif downloadcount == 1:
                       downIdx2 = i
                   downloadcount += 1
            if downloadcount > 0:
                if downloadcount == 1:
                    global_executeflashconfig.sequence[downIdx1]["hexfilename_s"] = filename
                    self.modify_EraseRoutine(downIdx1, 4, 4)
                    crc = self.cal_check(downIdx1, hex_file_binary)
                    self.modify_crc_check_seq(downIdx1, global_executeflashconfig.sequence[downIdx1]["crc_type"], crc)
                    if global_executeflashconfig.sequence[downIdx1 + 1]["sid"] == 0x36:
                       global_executeflashconfig.sequence[downIdx1 + 1]["hexfilename_s"] = filename
                elif downloadcount == 2:
                    global_executeflashconfig.sequence[downIdx2]["hexfilename_s"] = filename
                    self.modify_EraseRoutine(downIdx2, 4, 4)
                    crc = self.cal_check(downIdx2, hex_file_binary)
                    self.modify_crc_check_seq(downIdx2, global_executeflashconfig.sequence[downIdx2]["crc_type"], crc)
                    if global_executeflashconfig.sequence[downIdx2 + 1]["sid"] == 0x36:
                       global_executeflashconfig.sequence[downIdx2 + 1]["hexfilename_s"] = filename
                global_executeflashconfig.writeflashConfig(global_config.flashsequencefile)
                self.ShowFlashSequence()

    def on_select_key_dllkey_dll(self):
        defaultfile = self.lineEdit_key_dll_file.text()
        count = len(global_executeflashconfig.sequence)
        filename =self.GetFlashLibFile(defaultfile)
        if filename is not None:
            self.lineEdit_key_dll_file.setText(filename)
            for i in range(count):
                if global_executeflashconfig.sequence[i]["sid"] == 0x27:
                    global_executeflashconfig.sequence[i]["libfilename_s"] = filename

            global_executeflashconfig.writeflashConfig(global_config.flashsequencefile)

            self.ShowFlashSequence()

    #log导出至文件
    def on_btn_Export_log_toFile(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'Save to html file', '', 'HTML (*.html)')
        if len(filename) > 1:
            with open(filename, "w", encoding="utf-8") as file:
                file.write(self.textBrowser_flashlog.toHtml())
    
    #自动写入日志文件
    def on_write_to_log(self):
        dir_path = 'log'
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        path, seqfilename_with_ext = os.path.split(global_config.flashsequencefile)
        seqfilename, extension = os.path.splitext(seqfilename_with_ext)

        current_time = datetime.datetime.now()
        filename = current_time.strftime("%y_%m_%d_%H_%M_%S")
        filename = 'log/log_' + filename + '_'+ seqfilename + '.txt'
        with open(filename, "w", encoding="utf-8") as file:
            file.write(self.textBrowser_flashlog.toPlainText())

    #序列列表根据执行结果，修改状态是红色或绿色、黄色
    def on_update_squence_status_byindex(self, idx, status):
       count = self.listWidget_main_execute_flash_sequence.count()
 
       item = self.listWidget_main_execute_flash_sequence.item(idx)
       if status == RUN_STATUS_RUNOK:
           if idx < count and idx >= 0:
              self.listWidget_main_execute_flash_sequence.itemWidget(item).setStyleSheet(dialog_qss_green)
       elif status == RUN_STATUS_RUNNING:
           if idx < count and idx >= 0:
              self.listWidget_main_execute_flash_sequence.itemWidget(item).setStyleSheet(dialog_qss_yellow)
              #设置列表滚动至此，执行过程中不断滚动
              self.listWidget_main_execute_flash_sequence.setCurrentRow(idx)  
       elif status == RUN_STATUS_RUNERROR:
           if idx < count and idx >= 0:
              self.listWidget_main_execute_flash_sequence.itemWidget(item).setStyleSheet(dialog_qss_red)
       elif status == RUN_STATUS_RUNEND:
           self.on_menubar_StopFlashThread()

    #打开测试序列文件
    def on_menubar_EditflashSequenceFile(self):

        if not reg_does_value_exist(g_sub_key, g_value_name):
           showtipbox(self, 'warn', self.tr("warnning"), self.tr("FlashSeqEditor is not installed!"))
           return
       
        editor_path = reg_read_value(g_sub_key, g_value_name)
        if not os.path.exists(editor_path):
           showtipbox(self, 'warn', self.tr("warnning"), self.tr("FlashSeqEditor path error!"))
           return

        time_difference = datetime.datetime.now() - self.btn_edit_clk_current_time
        total_seconds = time_difference.total_seconds()
        if total_seconds < 2:
            return
        self.btn_edit_clk_current_time = datetime.datetime.now()
        if len(global_config.flashsequencefile) > 1:
            end_process_by_name('FlashSeqEditor.exe')
            try:
                run_command_without_console([editor_path, global_config.flashsequencefile])
            except:
                pass

    #重新加载升级序列
    def on_reload_sequence_file(self):
        result = showtipbox(self, 'warn', self.tr("warnning"), self.tr("Sequence file has been modified!\n\nDo you want to reload it?"), 2)
        if result == QMessageBox.Yes:
            global_executeflashconfig.loadflashConfig(global_config.flashsequencefile)
            self.ShowFlashSequence()

    #打开测试序列文件
    def on_menubar_OpenflashSequenceFile(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Open Flash Sequence File', '', 'Sequence Config Files (*.config)')
        if filename:
            self.stopTimer()
            
            time.sleep(0.25)
            self.filename_label.setText(filename)
            global_config.flashsequencefile = filename
            global_config.writeConfig()
            global_executeflashconfig.loadflashConfig(filename)
            self.ShowFlashSequence()
            
            #self.startTimer()
        else:
            if len(filename) < 1:
                showtipbox(self, 'warn', self.tr("warnning"), self.tr("Select config file firstly!"))

    #开始升级线程
    def on_menubar_StartFlashThread(self):
        cursor = QTextCursor(self.textBrowser_flashlog.document())
        self.textBrowser_flashlog.setTextCursor(cursor)
        self.textBrowser_flashlog.clear()
        self.show_logo_txt()

        self.progressBar_flash.setValue(0)
        count = self.listWidget_main_execute_flash_sequence.count()
        if self.loadconfigok:
            if not self.dispSettingStr():
                self.textBrowser_flashlog.append(getFormatText('error',"-----flash thread not start, flash failed----"))
                self.udsflasher.signal_write_to_log.emit()
                return
            
        for i in range(count):
            item = self.listWidget_main_execute_flash_sequence.item(i)
            self.listWidget_main_execute_flash_sequence.itemWidget(item).setStyleSheet(dialog_qss_gray)
        if count > 0:
            self.udsflasher.start_flashloop()
            self.EnableSettingCtrl(False)
        else:
            self.textBrowser_flashlog.append(getFormatText('error', 'Sequence is None!'))
            self.udsflasher.signal_write_to_log.emit()

    #结束升级线程
    def on_menubar_StopFlashThread(self):
        self.udsflasher.stop_flashloop()
        
        while self.udsflasher.isRunning():
            time.sleep(0.010)
        self.EnableSettingCtrl(True)
    
    def EnableSettingCtrl(self, bEnable = True):
        self.toolbtn_start.setEnabled(bEnable)
        self.toolbtn_stop.setEnabled(not bEnable)
        self.toolbtn_sequence_load.setEnabled(bEnable)
        self.toolbtn_sequence_edit.setEnabled(bEnable)
        self.radioButton_v2.setEnabled(bEnable)
        self.radioButton_v3.setEnabled(bEnable)    
        if self.radioButton_v3.isChecked():
            self.lineEdit_flash_drv_hex_file.setEnabled(bEnable)
            self.pushButton_select_flash_drv_hex_file.setEnabled(bEnable)

        self.comboBox_candev.setEnabled(bEnable)
        self.comboBox_canrate.setEnabled(bEnable) 
        self.lineEdit_severid.setEnabled(bEnable)
        self.lineEdit_clientid.setEnabled(bEnable)  
        self.lineEdit_hex_file.setEnabled(bEnable)
        self.pushButton_select_hex_file.setEnabled(bEnable)  
        self.lineEdit_key_dll_file.setEnabled(bEnable)
        self.pushButton_select_key_dll_file.setEnabled(bEnable) 

    #处理反馈的状态消息
    #处理执行正常的反馈信息
    def on_receivedResponse(self, response, status):
        if status == RESULT_STATUS_INFO:
           self.textBrowser_flashlog.append(getFormatText('info', response))
        elif status == RESULT_STATUS_OK:
           self.textBrowser_flashlog.append(getFormatText('ok', response))
        elif status == RESULT_STATUS_ERROR:
           self.textBrowser_flashlog.append(getFormatText('error', response))
        elif status == RESULT_STATUS_UPDATE_PROCESS_BAR: #更新进度条
           self.progressBar_flash.setValue(int(response))
    
    #处理执行序列出现错误的反馈信息
    def on_receivedNegResponse(self, response):
        self.on_menubar_StopFlashThread()
        self.textBrowser_flashlog.append(getFormatText('error', response))
        runIdx = self.udsflasher.get_has_run_index()
        if runIdx >= 0 and runIdx < self.listWidget_main_execute_flash_sequence.count():
           self.on_update_squence_status_byindex(runIdx, RUN_STATUS_RUNERROR)

#end class mainwindow
