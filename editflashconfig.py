from PyQt5.QtCore import QMutex, QMutexLocker,pyqtSignal,pyqtSlot,QVariant,QObject,QDateTime
import os
import json

uds_define_descript ={
    0x10:"Diagnostic Session Control",
    0x11:"ECU Reset",
    0x14:"Clear Diagnostic Information",
    0x19:"Read DTC Information",
    0x22:"Read Data By Identifier",
    0x2E:"Write Data By Identifier",
    0x27:"Security Access",
    0x28:"Communication Control",
    0x31:"Routine Control",
    0x34:"Download",
    0x36:"Transfer Data",
    0x37:"Request Transfer Exit",
    0x85:"Control DTC Setting",
    0xfe:"Delay(ms)"
}

uds_define_sub = {
    0x10:{
       1:"01 Default Session",
       2:"02 Programming Session",
       3:"03 Extended Diagnostic Session",
       4:"04 Safety System Diagnostic Session"
    },
    0x11:{
       1:"01 Hard Reset",
       2:"02 Key Off On Reset",
       3:"03 Soft Reset",
       4:"04 Enable Rapid Power Shutdown",
       5:"05 Disable Rapid Power Shutdown"
    },
    0x14:{},
    0x19:{
        1:"01 Report Counts of DTC by Status Mask",
        2:"02 Report DTC By Status Mask",
        3:"03 Report DTC Snapshot Identification",
        4:"04 Report DTC Snapshot Record By DTC Number",
        5:"05 Report DTC Memory Data By Record NUmber",
        6:"06 Report DTC Extended Data Record By DTC Number",
        7:"07 Report DTC Number By Serious Mask Record",
        8:"08 Report DTC By Serious Mask Record",
        9:"09 Report DTC Serious Information",
        10:"0A Report DTC Supported"
    },
    0x22:{},
    0x2E:{},
    0x27:{},
    0x28:{
       0:"00 Enable Rx and Tx",
       1:"01 Enable Rx and Disable Tx",
       2:"02 Disable Rx and Enable Tx",
       3:"03 Disable Rx and Tx",
       4:"04 Enable Rx and Disable Tx With Enhanced Address Information",
       5:"05 Enable Rx and Tx With Enhanced Address Information"
    },
    0x31:{
       1:"01 Start Routine",
       2:"02 Stop Routine",
       3:"03 Request Routine Results",        
    },
    0x34:{},
    0x36:{},
    0x37:{},
    0x85:{
       1:"01 ON",
       2:"02 OFF",
    },
    0xfe:{}
}

class EditFlashConfig(QObject):
    signal_reload_sequence_config = pyqtSignal(str)
    def __init__(self): 
        super().__init__()
        self.moresettings = {}
        self.sequence = []
        return None
    
    def loadflashConfigFromStr(self, jsonStr):
        try:
            self.config = json.loads(jsonStr)
            self.moresettings = self.config["moresettings"]
            self.sequence = self.config["sequence"]
        except:
            self.moresettings = {}
            self.sequence = []
    
    def loadflashConfig(self, filename):
        try:
            if os.path.exists(filename):
                with open(filename, "r") as f:
                    self.config = json.load(f)
                    self.moresettings = self.config["moresettings"]
                    self.sequence = self.config["sequence"]
            else:
                self.moresettings = {}
                self.sequence = []                
        except:
            self.moresettings = {}
            self.sequence = []

    def writeflashConfig(self,filename):
        config = {
            "moresettings":self.moresettings,
            "sequence":self.sequence
        }
        with open(filename, "w") as f:
            json.dump(config, f)
            f.close()
    
    def dumpflashConfig(self):
        config = {
            "moresettings":self.moresettings,
            "sequence":self.sequence
        }
        jsonStr = json.dumps(config)
        return jsonStr
    
    def dumpMoresettingsToStr(self):
        jsonStr = json.dumps(self.moresettings)
        return jsonStr

    def getDataString(self, i, bHasBracket = False):
           sid = self.sequence[i]["sid"]
           sub = self.sequence[i]["sub"]
           if self.sequence[i]['suppress']:
              sub += 0x80

           if sid == 0x37:
              datastr = '37' + ' ' + self.sequence[i]["data_s"]
              if(bHasBracket):
                 datastr = "DATA[" + datastr + "]"
              return datastr
           
           elif sid == 0x27:
               tmpstr = 'Level:' + str(self.sequence[i]["level"]) + ' '
               datastr = tmpstr + str(self.sequence[i]["libfilename_s"])
               return datastr

           elif sid == 0x34:
               datastr = str(self.sequence[i]["hexfilename_s"])
               return datastr

           elif sid == 0xfe:
               datastr = str(self.sequence[i]["delay"])
               if(bHasBracket):
                  datastr = 'Delay: ' + datastr
               return datastr

           else:
               sidhexstr = format(sid,'02X')
               subhexstr=""
               if sub < 0xff and sub >= 0:
                  subhexstr = format(sub,'02X')
               datastr = sidhexstr + ' ' +  subhexstr + ' ' + self.sequence[i]["data_s"]
               if len(subhexstr) <= 0:
                   datastr = sidhexstr + ' ' + self.sequence[i]["data_s"]
               if(bHasBracket):
                   datastr = "DATA[" + datastr + "]"
               return datastr

global_executeflashconfig = EditFlashConfig()

