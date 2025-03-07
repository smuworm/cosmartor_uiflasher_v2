from PyQt5.QtCore import QMutex, QMutexLocker,pyqtSignal,pyqtSlot,QVariant,QObject,QDateTime
import os
import json

class Config(QObject):
    def __init__(self): 
        super().__init__()
        self.devtype=0
        self.ch=0
        self.baud=4
        self.requid=0x712
        self.respid=0x711
        self.funcpid=0x7df
        self.flash_ver = 0
        self.flashsequencefile = ""
        self.flasher_edit_exe = ""
        return None
    
    def loadConfig(self):
        if os.path.exists("./config.json"):
            with open("./config.json", "r") as f:
                self.config = json.load(f)
                try:
                    self.devtype=self.config["devtype"]
                    self.ch=self.config["ch"]
                    self.baud=self.config["baud"]
                    self.requid=int(self.config["requid"],16)
                    self.respid=int(self.config["respid"],16)
                    self.funcpid=int(self.config["funcpid"],16)
                    self.flashsequencefile=self.config["flashsequencefile"]
                    self.flasher_edit_exe=self.config["flasher_edit_exe"]
                    self.flash_ver = self.config["flash_ver"]
                except:
                    pass

    def writeConfig(self):
        config = {
            "devtype": self.devtype,
            "ch": self.ch,
            "baud": self.baud,
            "requid": hex(self.requid),
            "respid": hex(self.respid),
            "funcpid": hex(self.funcpid),
            "flashsequencefile" : self.flashsequencefile,
            "flasher_edit_exe":self.flasher_edit_exe,
            "flash_ver":self.flash_ver
        }
        with open("./config.json", "w") as f:
            json.dump(config, f)
            f.close()


global_config = Config()
