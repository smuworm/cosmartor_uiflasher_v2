'''
Author: litianwen
Date: 2024-10-20 08:57:39
LastEditTime: 2024-06-24 09:08:12
LastEditors: litianwen
Description: 
Copyright (c) 2024 by Cosmartor, All Rights Reserved. 
'''
from PyQt5.QtCore import QMutex, QMutexLocker,pyqtSignal,pyqtSlot,QVariant,QObject,QDateTime

import time
import intelhex as ih
import can
from can.interfaces.pcan import PcanBus
import isotp
import udsoncan
import udsoncan.exceptions
import udsoncan.services
from udsoncan.connections import PythonIsoTpConnection

import udsoncan.client
from udsoncan.client import Client
import udsoncan.configs

from editflashconfig import EditFlashConfig, global_executeflashconfig
from zlgcan.zlgcan_interface import ZlgCanBus
from common.comm_ctrl import *
from KeyGenerator import *

# "potocol":self.potocol,
# "bReplremotestmin":self.bReplremotestmin,
# "replremotestminvalue":self.replremotestminvalue,
# "downloadtrytimes":self.downloadtrytimes,
# "bWaitsuppressresp":self.bWaitsuppressresp,
# "bJudgeanynegresp":self.bJudgeanynegresp,
# "bShowrawframe":self.bShowrawframe

def remove_duplicates(nums):
    seen = set()
    return [x for x in nums if not (x in seen or seen.add(x))]

class uniflasher(QObject):
    signal_start = pyqtSignal()
    signal_update_sequence = pyqtSignal(int, int)
    signal_Respond = pyqtSignal(str, int)
    signal_NegRespond = pyqtSignal(str)
    signal_write_to_log = pyqtSignal()
    def __init__(self): 
        super().__init__()
        self.bRun = False
        self.runCountIndex = 0
        self.mutex = QMutex()
        self.task = None
        self.iRunIndex = -1
        self.currentErrors = ''
        self.bEnd = True
        self.seed_key_s = ''
        self.max_download_length = 0
        self.download_times = 0
        self.download_crc = 0
        self.bhas_inited_signal = False
        self.disk_label = get_current_exe_disk()
        self.UDS_REQUEST_TIMEOUT = 5
        self.data_mode = 'big'
        
        self.start_time = datetime.datetime.now()
         
    def get_has_run_index(self):
        return self.iRunIndex
    
    def getDevType(self, devtype:int):
        if devtype == 0:
           canstr= 'pcan'
        elif devtype == 1:
           canstr = 'USBCAN-4E-U'
        elif devtype == 2:
           canstr = 'USBCAN-II'
        elif devtype == 3:
            canstr = 'USBCAN-2E-U'
        elif devtype == 4:
            canstr = 'USBCANFD-100U'
        elif devtype == 5:
            canstr = 'USBCANFD-MINI'
        elif devtype == 6:
            canstr = 'USBCAN-E-U'
        else:
            canstr= 'USBCANFD-200U'
        return canstr
    
    def getBaudRate(self, baud:int):
        if baud == 0:
           can_bitrate= 125000
        if baud == 1:
           can_bitrate= 250000
        if baud == 2:
           can_bitrate= 500000
        if baud == 3:
           can_bitrate=  800000
        if baud > 3:
           can_bitrate= 1000000
        return can_bitrate

    def getChannelString(sef, Chidx):
       if Chidx == 0:
          return 'PCAN_USBBUS1'
       elif Chidx == 1:
          return 'PCAN_USBBUS2'

    def key_file_parse_func(self, path)->CKeyGenerator:
        '''
        解析密钥文件
        返回CDLL对象
        '''
        # 解析密钥文件并打印相关信息
        try:
            keygen = CKeyGenerator(path)

            if keygen is not None:
                self.signal_Respond.emit("Key file parsed successfully!", RESULT_STATUS_INFO)

            return keygen
        
        except Exception as e:
            self.signal_NegRespond.emit("Failed to parse key file: " + str(e))
            return None  

    def default_function(self, idx, uds_client):
        self.signal_NegRespond.emit('Without executable fuction: '+ self.sequence[idx]["descript_s"]+ ':' + hex(self.sequence[idx]["sid"]))
    
    #映射uds各服务对应的接口函数
    def map_sequence_execute_func(self):
        self.actions = {
                       0x10: self.session_ctrl_func_0x10,
                       0x11: self.ecu_reset_func_0x11,
                       0x14: self.clear_dtc_func_0x14,
                       0x19: self.read_dtc_func_0x19,
                       0x22: self.read_data_by_id_func_0x22,
                       0x2e: self.write_data_by_id_func_0x2e,
                       0x27: self.security_func_0x27,
                       0x28: self.communication_ctrl_func_0x28,
                       0x31: self.routine_ctrl_func_0x31,
                       0x34: self.download_func_0x34,
                       0x36: self.transfer_data_func_0x36,
                       0x37: self.transfer_exit_func_0x37,
                       0x85: self.ctrl_dtc_setting_func_0x85,
                       0xfe: self.delay_func_0xfe
                       }

    #设置can消息过滤器
    def init_can_id_filter(self):
        canmask = 0x7ff
        extended = False
        if self.bExtid:
            canmask = 0x1FFFFFFF
            extended = True            
        filters = [
                  {"can_id": self.respid, "can_mask": canmask, "extended": extended},
                  {"can_id": self.requid, "can_mask": canmask, "extended": extended},
                  {"can_id": self.funcpid, "can_mask": canmask, "extended": extended},
                 ]
        return filters

    #配置isotp参数
    def init_isotp_params(self):
        # 创建isotp参数
        if self.setting['bBytefill']:
            isotp_params = {
                'stmin': self.setting['stmin'],
                'blocksize': self.setting['bs'],
                # 'wftmax': 0,
                # 'tx_data_length': 8,
                # 'tx_data_min_length': None,
                'tx_padding': self.setting['bytefillValue'],
                'rx_flowcontrol_timeout': self.setting['flowctrltimeout'],
                'rx_consecutive_frame_timeout': 3000,
                'max_frame_size': 4095,
                'can_fd': False,
            }
        else:
            isotp_params = {
                'stmin': self.setting['stmin'],
                'blocksize': self.setting['bs'],
                # 'wftmax': 0,
                # 'tx_data_length': 8,
                # 'tx_data_min_length': None,
                #'tx_padding': self.setting['bytefillValue'],
                'rx_flowcontrol_timeout': self.setting['flowctrltimeout'],
                'rx_consecutive_frame_timeout': 3000,
                'max_frame_size': 4095,
                'can_fd': False,
            }            
        return isotp_params
    
    #初始化uds客户端，超时，数据id的设置
    def init_uds_client_config(self):
        uds_client_config = udsoncan.client.default_client_config.copy()
        # 关闭使用服务器返回的定时参数，如果不适用此方法，搬运app程序等费时间的routine将触发p2_timeout
        uds_client_config["use_server_timing"] = False
        self.UDS_REQUEST_TIMEOUT = self.setting['p2timeout']/1000.0
        # 更改p2 timeout
        uds_client_config['p2_timeout'] = self.setting['p2timeout']
        uds_client_config['p2_star_timeout'] = self.setting['p2xtimeout']
        uds_client_config['request_timeout'] = self.UDS_REQUEST_TIMEOUT
        if self.data_mode == 'little':
            uds_client_config['data_identifiers'] = {
                'default' : '<H'
            }
        else:
            uds_client_config['data_identifiers'] = {
                'default' : '>H'
            }
        return uds_client_config
    
    #生成物理地址
    def make_isotp_phy_address(self):
        if self.bExtid:
            return isotp.Address(isotp.AddressingMode.Extended_29bits, txid=self.requid, rxid=self.respid)
        else:
            return isotp.Address(isotp.AddressingMode.Normal_11bits, txid=self.requid, rxid=self.respid)

    #生成功能地址
    def make_isotp_func_address(self):
        if self.bExtid:
            return isotp.Address(isotp.AddressingMode.Extended_29bits, txid=self.funcpid, rxid=self.respid)
        else:
            return isotp.Address(isotp.AddressingMode.Normal_11bits, txid=self.funcpid, rxid=self.respid)
    
    #初始化can参数，波特率，端口等
    def init_can_params(self):

        self.setting = global_executeflashconfig.moresettings
        self.sequence = global_executeflashconfig.sequence
        self.canstr = self.getDevType(self.setting['devtype'])
        self.can_bitrate = self.getBaudRate(self.setting['baud'])
        self.pcanchStr = self.getChannelString(self.setting['ch'])
        self.can_bitrate_str = str(int(self.can_bitrate/1000)) + 'K'
        if self.can_bitrate >= 1000000:
           self.can_bitrate_str = "1M"
        self.zlgcanchStr = str(self.setting['ch'])

        self.requid = int(self.setting['requid'], 16)
        self.respid = int(self.setting['respid'], 16)
        self.funcpid = int(self.setting['funcpid'], 16)

        self.cantype = self.setting["cantype"]
        self.bExtid = self.setting["bExtid"]
        self.bSuppressresp = self.setting["bSuppressresp"]
        self.idtype = self.setting["idtype"]
        self.handsake_start = self.setting["handsake_start"]
        self.handsake_interval = self.setting["handsake_interval"]
        try:
            self.data_mode = self.setting["data_mode_s"]
        except:
            self.data_mode = 'big'

    #获取序列是否正在执行状态
    def isRunning(self):
       return not self.bEnd
    
    #停止执行序列
    def stop_flashloop(self):
       self.bRun = False
    
    #开始执行烧写序列
    def start_flashloop(self):
       if self.bhas_inited_signal == False:
          self.signal_start.connect(self.excute_sequence)
          self.bhas_inited_signal = True

       self.bRun = True
       self.signal_start.emit()

    #解析hex文件
    def hex_file_parse_func(self, path):
        # 解析hex文件并打印相关信息
        try:
            hex_file = ih.IntelHex(path)

            # 成功解析并打印hex文件起始地址、结束地址、总大小
            self.signal_Respond.emit("Hex file parsed successfully!", RESULT_STATUS_INFO)
            self.signal_Respond.emit("Hex file start address: " + str(hex(hex_file.minaddr())), RESULT_STATUS_INFO)
            self.signal_Respond.emit("Hex file end address: " + str(hex(hex_file.maxaddr())), RESULT_STATUS_INFO)
            self.signal_Respond.emit("Hex file total size: " + str((hex_file.maxaddr() - hex_file.minaddr() + 1) / 1024) + "KB", RESULT_STATUS_INFO)

            return hex_file, hex_file.minaddr(), hex_file.maxaddr(), (hex_file.maxaddr() - hex_file.minaddr() + 1)
        except Exception as e:
            self.currentErrors  = str(e)
            return None, None, None, None

    #执行升级序列，主线程函数
    def excute_sequence(self):
        uds_client = None
        can_bus = None
        self.iRunIndex = -1
        self.seed_key_s = ''
        self.start_time = datetime.datetime.now()

        count = len(global_executeflashconfig.sequence)
        if count < 1:
            self.signal_NegRespond.emit("Sequence is none!")
            self.signal_write_to_log.emit()
            return
        try:
           self.init_can_params()
           self.map_sequence_execute_func()
        except:
            self.signal_NegRespond.emit("init_can_params error!")
            self.signal_write_to_log.emit()
            return

        self.bEnd = False
        bRunsequenceOK = True        
        # 创建UDS客户端  
        try:
            if self.canstr == 'pcan':
               can_bus = can.interface.Bus(interface=self.canstr, channel=self.pcanchStr, bitrate=self.can_bitrate, can_filters=self.init_can_id_filter())
            else:
               can_bus = ZlgCanBus(interface = self.canstr, dev_index = 0, channel = self.zlgcanchStr, bitrate=self.can_bitrate_str, can_filters=self.init_can_id_filter())
            with can_bus:
                # 创建isotp栈
                isotp_phy_stack = isotp.CanStack(bus=can_bus, address=self.make_isotp_phy_address(), params=self.init_isotp_params()) #PROTCOL STACK
                isotp_func_stack = isotp.CanStack(bus=can_bus, address=self.make_isotp_func_address(), params=self.init_isotp_params()) #PROTCOL STACK
                
                self.simple_periodic_send(can_bus)
                
                for i in range(count):
                     if self.bRun == False:
                        bRunsequenceOK = False
                        break
                     self.iRunIndex = i
                     if self.sequence[i]['addresstype'] == 0:
                        conn = PythonIsoTpConnection(isotp_phy_stack)
                     else:
                        conn = PythonIsoTpConnection(isotp_func_stack)
                     with conn:
                         with Client(conn, config=self.init_uds_client_config(), request_timeout = self.UDS_REQUEST_TIMEOUT) as uds_client: 
                             if not self.execute_sequence_sub(i, uds_client):
                                 bRunsequenceOK = False
                                 break
                self.iRunIndex = count
        except Exception as e:
            self.signal_NegRespond.emit(str(e))
            bRunsequenceOK = False
        
        self.stop_periodic_send()
        
        self.signal_Respond.emit("  ", RESULT_STATUS_INFO)
        self.signal_Respond.emit("--------------<b>RESULT</b>-------------", RESULT_STATUS_INFO)
        self.signal_Respond.emit("  ", RESULT_STATUS_INFO)
        # 计算时间差
        time_difference = datetime.datetime.now() - self.start_time
        total_seconds = time_difference.total_seconds()
        if bRunsequenceOK:
            self.signal_update_sequence.emit(self.iRunIndex, RUN_STATUS_RUNEND)
            self.signal_Respond.emit(str(100), RESULT_STATUS_UPDATE_PROCESS_BAR)
            self.signal_Respond.emit('<b>Running completed ( run time: ' + str(total_seconds) +' s ),   SUCCESSFULLY !</b>', RESULT_STATUS_OK)
        else:
            self.signal_NegRespond.emit('Running sequence has errors ( run time: ' + str(total_seconds) +' s ),   FAILED !')
            self.signal_Respond.emit(str(0), RESULT_STATUS_UPDATE_PROCESS_BAR)
        self.signal_Respond.emit("  ", RESULT_STATUS_INFO)
        self.bEnd = True

        self.signal_write_to_log.emit()
    
    #执行某个序号的序列，由主线程函数循环调用
    def execute_sequence_sub(self, i, uds_client):
        self.signal_Respond.emit('execute: ' + hex(self.sequence[i]["sid"]) + '-' + self.sequence[i]["descript_s"], RESULT_STATUS_INFO)
        self.signal_update_sequence.emit(i, RUN_STATUS_RUNNING)
        action = self.actions.get(self.sequence[i]['sid'], self.default_function)
        try:
            if action(i, uds_client):
                self.signal_update_sequence.emit(i, RUN_STATUS_RUNOK)
                self.signal_Respond.emit('execute: ' + hex(self.sequence[i]["sid"]) + '-' + self.sequence[i]["descript_s"] + "  succeed", RESULT_STATUS_OK)
                return True
            else:
                self.signal_update_sequence.emit(i, RUN_STATUS_RUNERROR)
                self.signal_Respond.emit('execute: ' + hex(self.sequence[i]["sid"]) + '-' + self.sequence[i]["descript_s"] + "  failed", RESULT_STATUS_ERROR)
                return False
        except Exception as e:
            self.signal_NegRespond.emit(str(e))

    #循环发送0x3e握手消息
    def simple_periodic_send(self, bus):
        self.task = None
        id = self.requid
        if self.idtype > 0:
           id = self.funcpid
        data = [0x3e,0x00]
        if self.bSuppressresp:
           data = [0x3e,0x80]
        if self.handsake_start:
           msg = can.Message(arbitration_id=id, data=data, is_extended_id = self.bExtid )
           self.task = bus.send_periodic(msg, self.handsake_interval/1000.0 - 0.01)
           
           if not isinstance(self.task, can.ModifiableCyclicTaskABC):  # 断言task类型
                self.signal_Respond.emit("send_periodic() function is not supported.", RESULT_STATUS_INFO)
                self.task.stop()
                self.task = None

    #停止发送0x3e握手消息
    def stop_periodic_send(self):
        if self.task is not None:
            self.task.stop()
            self.task = None      
            print("stopped cyclic send")

    def get_read_byid_type_dict(self, id, read_type, read_len)->dict:

        if self.data_mode == 'little':
            if read_type == 0:
                return {'default' : '<H', id : 'B'}
            elif read_type == 1:
                return {'default' : '<H', id : '<H'}
            elif read_type == 2:
                return {'default' : '<H', id : '<i'}
            elif read_type == 3:
                return {'default' : '<H', id : '<q'}
            elif read_type == 4:
                return {'default' : '<H', id : '<f'}
            elif read_type == 5:
                return {'default' : '<H', id : '<d'}    
            elif read_type == 6:
                return {'default' : '<H', id : udsoncan.AsciiCodec(read_len)}
            
            return {'default' : '<H', id : '<H'}
        else:
            if read_type == 0:
                return {'default' : '>H', id : 'B'}
            elif read_type == 1:
                return {'default' : '>H', id : '>H'}
            elif read_type == 2:
                return {'default' : '>H', id : '>i'}
            elif read_type == 3:
                return {'default' : '>H', id : '>q'}
            elif read_type == 4:
                return {'default' : '>H', id : '>f'}
            elif read_type == 5:
                return {'default' : '>H', id : '>d'}    
            elif read_type == 6:
                return {'default' : '>H', id : udsoncan.AsciiCodec(read_len)}
            
            return {'default' : '>H', id : '>H'}
    
    #defaultSession = 1
    #programmingSession = 2
    #extendedDiagnosticSession = 3
    #safetySystemDiagnosticSession = 4

    #0x10:"Diagnostic Session Control"
    def session_ctrl_func_0x10(self, idx, uds_client):
        bret = True
        if uds_client is None:
            return False
        sequ = self.sequence[idx]
        sub = sequ['sub']
        data_s = sequ['data_s']
        suppress = sequ['suppress']
        try:
            if suppress:
                with uds_client.suppress_positive_response(wait_nrc=False):
                    uds_client.change_session(sub)   # Will not wait for a response and always return None
                    #self.signal_Respond.emit("Enter the flashing session successfully!", RESULT_STATUS_INFO)
            else:
                response = uds_client.change_session(sub)
                if response.valid == True and response.positive == True:
                   pass
                   #self.signal_Respond.emit("Enter the flashing session successfully!", RESULT_STATUS_INFO)
                else:
                   self.signal_NegRespond.emit("Enter the flashing session failed!", RESULT_STATUS_INFO)
                   bret = False
        except Exception as e:
            bret = False
            self.signal_NegRespond.emit(str(e))
        return bret

    #0x11:"ECU Reset"
    def ecu_reset_func_0x11(self, idx, uds_client):
        bret = True
        if uds_client is None:
            return False
        sequ = self.sequence[idx]
        sub = sequ['sub']
        suppress = sequ['suppress']
        try:
            if suppress:
                with uds_client.suppress_positive_response(wait_nrc=False):
                    uds_client.ecu_reset(sub)   # Will not wait for a response and always return None
                    #self.signal_Respond.emit("ECU Reset successfully!", RESULT_STATUS_INFO)
            else:
                response = uds_client.ecu_reset(sub)
                if response.valid == True and response.positive == True:
                   pass
                   #self.signal_Respond.emit("ECU Reset successfully!", RESULT_STATUS_INFO)
                else:
                   self.signal_NegRespond.emit("ECU Reset failed!")
                   bret = False
        except Exception as e:
            bret = False
            self.signal_NegRespond.emit(str(e))
        return bret

    #0x14 Clear DTC 
    def clear_dtc_func_0x14(self, idx, uds_client):
        
        response = uds_client.clear_dtc()  # 使用清除所有DTC的子功能

        if response.valid and response.positive == True:
           pass
           #self.signal_Respond.emit("DTC cleared successfully.")
        else:
            self.signal_NegRespond.emit("DTC cleared failed.")
            return False
        return True

    #0x19 Read DTC
    def read_dtc_func_0x19(self, idx, uds_client):
        bret = True
        if uds_client is None:
            return False
        sequ = self.sequence[idx]
        sub = sequ['sub']
        data = hexStringToListArray(sequ['data_s'])
        data_len = len(data)
        if data_len < 1:
            data = None
        suppress = sequ['suppress']
        
        response = None
        if sub == 0x01:
            if data is not None:
               response = uds_client.get_number_of_dtc_by_status_mask(data[0])
        elif sub == 0x02:
            if data is not None:
               response = uds_client.get_dtc_by_status_mask(data[0])
        elif sub == 0x03:
            response = uds_client.get_dtc_snapshot_identification()
        elif sub == 0x04:
            #id of dtc
            if data_len > 1:
               response = uds_client.get_dtc_snapshot_by_dtc_number(bytes_to_short(data[0], data[1]))
        elif sub == 0x05:
            record_number = 0xFF
            if data_len > 1: 
                record_number = data[0]
            response = uds_client.get_dtc_snapshot_by_record_number(record_number)
        elif sub == 0x06:
            if data_len > 1: 
               response = uds_client.get_dtc_extended_data_by_dtc_number(bytes_to_short(data[0], data[1]))
        elif sub == 0x07:
            if data_len > 1: 
               response = uds_client.get_number_of_dtc_by_status_severity_mask(data[0], data[1])
        elif sub == 0x08:
            if data_len > 1: 
               response = uds_client.get_dtc_by_status_severity_mask(data[0], data[1])
        elif sub == 0x09:
            if data_len > 1: 
               response = uds_client.get_dtc_severity(bytes_to_short(data[0], data[1]))
        elif sub == 0x0a:
            response = uds_client.get_supported_dtc()
            
        if response is not None: 
            if response.valid and response.positive == True:
                response = udsoncan.services.ReadDTCInformation.interpret_response(response, sub)
                self.signal_Respond.emit("ReadDTCInformation dtc_count:"  + str(response.service_data.dtc_count), RESULT_STATUS_INFO)
                self.signal_Respond.emit("ReadDTCInformation dtcs:"  + str(response.service_data.dtcs), RESULT_STATUS_INFO)
            else:
                bret = False
                self.signal_NegRespond.emit("ReadDTCInformation Failed")
        else:
            bret = False
            self.signal_NegRespond.emit("ReadDTCInformation Failed")
        
        return bret

    #0x22 Read Data By Identifier
    def read_data_by_id_func_0x22(self, idx, uds_client):
        bret = True
        if uds_client is None:
            return False
        sequ = self.sequence[idx]
        data = hexStringToListArray(sequ['data_s'])
        if len(data) < 1:
            return False
        id = bytes_to_short(data[0], data[1])
        read_type = sequ['read_byid_type']
        read_len = sequ['read_byid_len']
        try:
            response = uds_client.read_data_by_identifier([id])
            if response.valid and response.positive == True:
                response = udsoncan.services.ReadDataByIdentifier.interpret_response(response, [id], self.get_read_byid_type_dict(id, read_type, read_len))
                bOk = False
                for key, value in response.service_data.values.items():
                    if key == id:
                        # 不是字符串取第一个值
                        if read_type < 6: 
                            self.signal_Respond.emit("Read Data [" + hex(id) + '] value is: ' + hex(value[0]), RESULT_STATUS_INFO)
                        # 是字符串，返回整个数组
                        else:
                            self.signal_Respond.emit("Read Data [" + hex(id) + '] value is: ' + value, RESULT_STATUS_INFO)
                        bOk = True
                if not bOk:
                    bret = False
            else:
                self.signal_NegRespond.emit("ReadDataByIdentifier error[" +  hex(id) + "]...")
                return False
        except Exception as e:
            bret = False
            self.signal_NegRespond.emit(str(e))
       
        return bret
    
    #0x2e Write Data By Identifier
    def write_data_by_id_func_0x2e(self, idx, uds_client):
        bret = True
        if uds_client is None:
            return False
        sequ = self.sequence[idx]
        data = hexStringToListArray(sequ['data_s'])
        if len(data) < 1:
            return False
        id = bytes_to_short(data[0], data[1])
        data_list = data[2:]
        if len(data_list) <= 0:
            data_list = None
        try:
            response = uds_client.write_data_by_identifier(id, data_list)
            if response.valid and response.positive == True:
                response = udsoncan.services.WriteDataByIdentifier.interpret_response(response)
                self.signal_Respond.emit("WirteDataByIdentifier OK[" + hex(id) + '] ' + bytes_to_hex(data_list) + ' ...' , RESULT_STATUS_INFO)
            else:
                self.signal_NegRespond.emit("WirteDataByIdentifier error[" +  hex(id) + '] ' + bytes_to_hex(data_list) + ' ...')
                return False
        except Exception as e:
            bret = False
            self.signal_NegRespond.emit(str(e))
       
        return bret

    #0x27:"Security Access"
    def security_func_0x27(self, idx, uds_client):
        bret = True
        if uds_client is None:
            return False
        sequ = self.sequence[idx]
        securitylevel = sequ['level']
        ignore_unlock_b = sequ['ignore_unlock_b']
        libfilename_s = sequ['libfilename_s']
        if len(libfilename_s) < 1:
            self.signal_NegRespond.emit('DLL file is not set...')
            return False
        
        if not os.path.exists(libfilename_s):
           libfilename_s = self.disk_label[0] + libfilename_s[1:]
        
        if not os.path.exists(libfilename_s):
            self.signal_NegRespond.emit('DLL file is not found...')
            return False

        try:
            # # 1.2.2 请求种子
            response = uds_client.request_seed(level=securitylevel)

            if response.valid == True and response.positive == True:
                # 解析响应
                response = udsoncan.services.SecurityAccess.interpret_response(response, udsoncan.services.SecurityAccess.Mode.RequestSeed)
                # 以十六进制格式打印种子
                self.signal_Respond.emit("Request seed successfully! Seed: " + bytes_to_hex(response.service_data.seed) + ", Seed Level: " + str(response.service_data.security_level_echo), RESULT_STATUS_INFO)
            else:
                # 请求种子失败，退出编程
                self.signal_NegRespond.emit("Request seed failed! Exit flashing...")
                return False
        
            # 1.2.3 计算key并发送
            seed = list(response.service_data.seed)
            keygen = self.key_file_parse_func(libfilename_s)
            result, actual_key_size, key = keygen.generate_key(seed, securitylevel, "GenerateKey", 4)

            # key计算成功，打印实际key和key实际大小
            if result == CKeyGenResultEx.KGRE_Ok:
                arr_len = len(key)
                self.seed_key_s = ''
                for i in range(arr_len - 1):
                    self.seed_key_s += (hex(key[i])[2:]+' ')
                if arr_len > 0:
                    self.seed_key_s += hex(key[arr_len - 1])[2:]

                self.signal_Respond.emit("Calculate key successfully! Actual key size: " + str(actual_key_size) + ", Key: " + self.seed_key_s, RESULT_STATUS_INFO)

            # 发送key
            response = uds_client.send_key(level=securitylevel, key=bytes(key))

            if response.valid == True and response.positive == True:
                # 解析响应
                response = udsoncan.services.SecurityAccess.interpret_response(response, udsoncan.services.SecurityAccess.Mode.SendKey)

                # 安全访问成功，打印安全访问级别
                self.signal_Respond.emit("Security access successfully! Key Level: " + str(response.service_data.security_level_echo), RESULT_STATUS_INFO)
            else:
                # 安全访问失败，退出编程
                self.signal_NegRespond.emit("Security access failed! Exit flashing...")
                bret = False
        except Exception as e:
            bret = False
            self.signal_NegRespond.emit(str(e))

        return bret

    #0x28:"Communication Control"
    def communication_ctrl_func_0x28(self, idx, uds_client):
        bret = True
        if uds_client is None:
            return False
        sequ = self.sequence[idx]
        sub = sequ['sub']
        data = hexStringToListArray(sequ['data_s'])
        if len(data) < 1:
            data = [0x01]
        suppress = sequ['suppress']
        try:
            if suppress:
                with uds_client.suppress_positive_response(wait_nrc=False):
                    uds_client.communication_control(sub, data[0])   # Will not wait for a response and always return None
                    #self.signal_Respond.emit("Communication Control successfully!", RESULT_STATUS_INFO)
            else:
                response = uds_client.communication_control(sub, data[0])
                if response.valid == True and response.positive == True:
                   pass
                   #self.signal_Respond.emit("Communication Control successfully!", RESULT_STATUS_INFO)
                else:
                   self.signal_NegRespond.emit("Communication Control failed!")
                   bret = False
        except Exception as e:
            bret = False
            self.signal_NegRespond.emit(str(e))
        return bret
    
    #0x31:"Routine Control"
    def routine_ctrl_func_0x31(self, idx, uds_client):
        bret = True
        sequ = self.sequence[idx]
        sub = sequ['sub']
        data = hexStringToListArray(sequ['data_s'])
        datalen = len(data)
        if datalen < 2:
            self.signal_NegRespond.emit("Start routine error, data len &lt; 2 !")
            return False
        id = bytes_to_short(data[0], data[1])
        suppress = sequ['suppress']
         
        byte_data = None
        if(datalen > 2):
          byte_data = bytes(data[2:])
        
        if uds_client is None:
            return False

        response = None 
        try:
            if suppress:
                with uds_client.suppress_positive_response(wait_nrc=False):
                    if sub == 0x01:
                        uds_client.start_routine(id, byte_data)
                    elif sub == 0x02:
                        uds_client.stop_routine(id, byte_data)
                    elif sub == 0x03:
                        uds_client.get_routine_result(id, byte_data)
            else:
                if sub == 0x01:
                    response = uds_client.start_routine(id, byte_data)
                elif sub == 0x02:
                    response = uds_client.stop_routine(id, byte_data)
                elif sub == 0x03:
                    response = uds_client.get_routine_result(id, byte_data)
                
            if response is not None:
                if response.valid == True and response.positive == True:
                    # 解析响应
                    response = udsoncan.services.RoutineControl.interpret_response(response)
                    self.signal_Respond.emit("Routine Control sucsessful! data[] = " + bytes_to_hex(response.service_data.routine_status_record), RESULT_STATUS_INFO)
                else:
                    bret = False
                    self.signal_NegRespond.emit(str(response))
            else:
                if suppress:
                    pass
                    #self.signal_Respond.emit("Routine Control sucsessful!", RESULT_STATUS_INFO)
                else:
                    self.signal_NegRespond.emit("Routine Control failed, not reply!")
                    bret = False
        except Exception as e:
            bret = False
            self.signal_NegRespond.emit(str(e))
        return bret
    
    #0x34:"Download"
    def download_func_0x34(self, idx, uds_client):
        bret = True

        if uds_client is None:
            return False
        
        filename = self.sequence[idx]["hexfilename_s"]
        if len(filename) < 1:
            self.signal_NegRespond.emit('hex file is not set...')
            return False
        if not os.path.exists(filename):
           filename = self.disk_label[0] + filename[1:]
        if not os.path.exists(filename):
            self.signal_NegRespond.emit('hex file is not found...')
            return False

        #解析hex文件
        hex_file, hex_file_start_address, hex_file_end_address, hex_file_size = self.hex_file_parse_func(filename)
        if hex_file is None:
           self.signal_NegRespond.emit("Failed to parse hex file: " + self.currentErrors)
           return False

        data_format_id = self.sequence[idx]["dataformatid_34"]
        addr_size =  self.sequence[idx]["address_size"]
        len_size = self.sequence[idx]["len_size"]
        
        #请求下载
        try:
            self.max_download_length = self.request_download(idx, uds_client, hex_file_start_address, hex_file_size, addr_size, len_size, data_format_id)
            if self.max_download_length <= 0:
                return False
        except Exception as e:
            bret = False
            self.signal_NegRespond.emit(str(e))
            return False
        
        # 计算下载次数
        if self.max_download_length > 0:
           self.download_times = int(hex_file_size / self.max_download_length) + 1

        return bret

    #0x36:"transfer data"
    def transfer_data_func_0x36(self, idx, uds_client):
        if uds_client is None: 
            return False
        if self.max_download_length <= 0:
            return False
        bret = True
        filename = self.sequence[idx]["hexfilename_s"]
        if len(filename) < 1:
            self.signal_NegRespond.emit('hex file is not set...')
            return False
        if not os.path.exists(filename):
           filename = self.disk_label[0] + filename[1:]
        if not os.path.exists(filename):
            self.signal_NegRespond.emit('hex file is not found...')
            return False
        try:
            #解析hex文件
            hex_file, hex_file_start_address, hex_file_end_address, hex_file_size = self.hex_file_parse_func(filename)
            if hex_file is None:
                self.signal_NegRespond.emit("Failed to parse hex file: " + self.currentErrors)
                return False
            
            hex_file_binary = hex_file.tobinarray()
            #开始传输文件
            if not self.transfer_data(idx, uds_client, self.max_download_length, hex_file_size, hex_file_binary):
                return False
        except Exception as e:
            bret = False
            self.signal_NegRespond.emit(str(e))

        return bret

    #0x37:"Request Transfer Exit"
    def transfer_exit_func_0x37(self, idx, uds_client):
        bret = True
        if uds_client is None: 
            return False
        sequ = self.sequence[idx]
        data = hexStringToListArray(sequ['data_s'])
        if len(data) < 1:
            data = None
        suppress = sequ['suppress']
        try:
            if suppress:
                with uds_client.suppress_positive_response(wait_nrc=False):
                    uds_client.request_transfer_exit(data)   # Will not wait for a response and always return None
                    #self.signal_Respond.emit("Request Transfer Exit successfully!", RESULT_STATUS_INFO)
            else:
                response = uds_client.request_transfer_exit(data)
                if response.valid == True and response.positive == True:
                   pass
                   #self.signal_Respond.emit("Request Transfer Exit successfully!", RESULT_STATUS_INFO)
                else:
                   self.signal_NegRespond.emit("Request Transfer Exit failed!")
                   bret = False
        except Exception as e:
            bret = False
            self.signal_NegRespond.emit(str(e))
        return bret

    #0x85:"Control DTC Setting"
    def ctrl_dtc_setting_func_0x85(self, idx, uds_client):
        bret = True
        sequ = self.sequence[idx]
        sub = sequ['sub']
        data = hexStringToListArray(sequ['data_s'])
        suppress = sequ['suppress']
        if len(data) <= 0:
            data = None
        if uds_client is None:
            return False
        try:
            #屏蔽回复
            if suppress:
                with uds_client.suppress_positive_response(wait_nrc=False):
                    uds_client.control_dtc_setting(sub, data)   # Will not wait for a response and always return None
                    #self.signal_Respond.emit("Control DTC Setting successfully!", RESULT_STATUS_INFO)
            else:
                response = uds_client.control_dtc_setting(sub, data)
                if response.valid == True and response.positive == True:
                   pass
                   #self.signal_Respond.emit("Control DTC Setting successfully!", RESULT_STATUS_INFO)
                else:
                   self.signal_NegRespond.emit("Control DTC Setting failed!")
                   bret = False
        except Exception as e:
            bret = False
            self.signal_NegRespond.emit(str(e))
        return bret

    #0xfe:"Delay(ms)"
    def delay_func_0xfe(self, idx, uds_client):
        delay = self.sequence[idx]["delay"]/1000.0
        if delay > 0:
           time.sleep(delay)
        return True
    
    #下列是下载0x34主函数，调用的子功能函数
    #download实现函数体太大，拆开子函数调用，缩短0x34的函数体

    #擦除flash函数
    def erase_flash(self, idx, uds_client, start_address, datalen, address_size_len = 4, data_size_len = 4):
        #31 01 FF 00 44 地址+长度
        #地址 4字节
        #长度 4字节
        erasetype = self.sequence[idx]["erase_flash"]
        #擦除类型，选择不擦除直接返回
        if erasetype >= 3:
            return True
        
        firstB = [address_size_len * 16 + data_size_len]
        databyte = bytes(firstB) + start_address.to_bytes(address_size_len,'little') + datalen.to_bytes(data_size_len, 'little')
        try:
            response = uds_client.start_routine(0xFF00, databyte)
            if response.valid == True and response.positive == True:
                # 解析响应
                response = udsoncan.services.RoutineControl.interpret_response(response)
                # 检查例程执行情况
                if response.service_data.routine_status_record[0] == 0x00:
                    self.signal_Respond.emit("Erase flash successfully!" + ' addr = ' + hex(start_address) + ' len = ' + hex(data_size_len), RESULT_STATUS_INFO)
                    return True
                else:
                    self.signal_NegRespond.emit("Erase flash failed! return code error..."  + ' addr = ' + hex(start_address) + ' len = ' + hex(data_size_len))
            else:
                self.signal_NegRespond.emit("Erase flash failed, neg response! Exit flashing..."  + ' addr = ' + hex(start_address) + ' len = ' + hex(data_size_len))
        except Exception as e:
            bret = False
            self.signal_NegRespond.emit(str(e))

        return False
    
    #请求下载函数
    def request_download(self, idx, uds_client, start_address, datalen, address_size_len = 4, data_size_len = 4, data_format_id = 0):
        memory_location = udsoncan.MemoryLocation(start_address,  datalen, address_size_len * 8, data_size_len * 8)
        data_format = udsoncan.DataFormatIdentifier(data_format_id & 0x0f,  (data_format_id >> 4) & 0x0f)
        
        try:
            response = uds_client.request_download(memory_location, data_format)

            if response.valid == True and response.positive == True:
                # 解析响应
                response = udsoncan.services.RequestDownload.interpret_response(response)
                # 记录最大可下载长度
                max_download_length = response.service_data.max_length
                # 请求下载成功
                self.signal_Respond.emit("Request download app successfully! Max Length: " + str(max_download_length), RESULT_STATUS_INFO)
                return max_download_length
            else:
                # 请求下载失败，退出编程
                self.signal_NegRespond.emit("Request download app failed! Exit flashing...")
                return 0
        except Exception as e:
            bret = False
            self.signal_NegRespond.emit(str(e))
  
    #传输数据函数
    def transfer_data(self, idx, uds_client, max_download_length, hex_file_size, hex_file_binary):
        # 循环下载
        current_download_position = 0
        current_hex_file_size = hex_file_size
        sequence_counter = 1
        sequence_counter_echo = 0
        index = 0
        download_status = 0
        bret = True
        interval = self.setting['intervalof36']/1000.0
        try:
            while 1:
                if self.bRun == False:
                    bret = False
                    self.signal_NegRespond.emit('User aborted the upgrade!')
                    break
                # 检查下载状态
                # 继续下载
                if download_status == 0:
                    # 计算当前下载长度
                    current_download_length = min(max_download_length, hex_file_size - current_download_position)

                    # 截取hex file binary数据到bytes
                    data = bytes(hex_file_binary[current_download_position:current_download_position + current_download_length])

                    # 传输数据
                    response = uds_client.transfer_data(sequence_counter, data)

                elif download_status == 1:
                    # 重新传输数据
                    response = uds_client.transfer_data(sequence_counter, data)
                
                # 检查响应
                if response.valid == True and response.positive == True:
                    # 解析响应
                    response = udsoncan.services.TransferData.interpret_response(response)

                    # 更新下载进度条
                    progress = int(current_download_position / hex_file_size * 100 + 1)
                    self.signal_Respond.emit(str(progress), RESULT_STATUS_UPDATE_PROCESS_BAR)
                    
                    # 更新下载位置
                    current_download_position += current_download_length                          

                    # 更新序列号计数器
                    sequence_counter += 1
                    if sequence_counter > 0xFF:
                        sequence_counter = 0x00
                    
                    # 更新当前剩余hex文件大小
                    current_hex_file_size -= current_download_length

                    # 判断是否继续下载
                    if current_hex_file_size > 0:
                        download_status = 0
                    else:
                        download_status = 2
                
                if interval > 0.0001:
                   time.sleep(interval)
                #退出传输数据
                if download_status == 2:
                    break
            #end while
        except Exception as e:
            bret = False
            self.signal_NegRespond.emit(str(e))
        return bret
        

        #计算crc，现在不用此代码，暂时在此备用
        # hex_file_binary = hex_file.tobinarray()
        # # 计算crc
        # checksum = common_cal_crc(hex_file_binary, 
        #                 self.sequence[idx]["crc_type"], 
        #                 self.sequence[idx]["crc_polynormial"], 
        #                 self.sequence[idx]["crc_initial"], 
        #                 self.sequence[idx]["crc_output_xor_value"], 
        #                 self.sequence[idx]["input_inversion_b"], 
        #                 self.sequence[idx]["output_inversion_b"])
        # self.signal_Respond.emit("Hex file CRC: " + hex(checksum), RESULT_STATUS_INFO)

        # bytes_checksum = checksum.to_bytes(4, 'little')
        # if self.sequence[idx]["crc_type"] == 1:
        #     bytes_checksum = checksum.to_bytes(2, 'little')
        # elif self.sequence[idx]["crc_type"] == 2:
        #     bytes_checksum = checksum.to_bytes(1, 'little')
        # self.download_crc = bytes_checksum