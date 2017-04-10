# -*- coding: utf-8 -*-
import sys
import numpy as np
import time
import serial
import serial.tools.list_ports
import PyQt5
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtChart import *
#from cbsdkConnection import CbSdkConnection


class MyGUI(QMainWindow):
    """
    This application is for monitoring activity from the Blackrock NSP.
    
    """

    def __init__(self):
        super(MyGUI, self).__init__()
#        self.cbsdk_conn = CbSdkConnection(simulate_ok=False)
        self.ser = serial.Serial()
        self.ser.baudrate = 19200
        self.actions = {}
        self.setup_ui()
        self.show()

    def __del__(self):
        # CbSdkConnection().disconnect() No need to disconnect because the instance will do so automatically.
        pass
    
    def connect_to_DDU(self):
        self.ser.port = self.com_port_box.currentText()
        self.ser.open()

    def setup_ui(self):
        self.resize(600, 400)
        self.setWindowTitle('IGN DDU')
        self.setCentralWidget(QWidget(self))
        
        my_layout = QVBoxLayout()
        
        com_layout = QHBoxLayout()
        self.com_port_box = QComboBox()
        for port in serial.tools.list_ports.comports():
            self.com_port_box.addItem(port.device)
        com_layout.addWidget(self.com_port_box)
        connect_button = QPushButton("Connect")
        com_layout.addWidget(connect_button)
        my_layout.addLayout(com_layout)
        
        self.setLayout(my_layout)
        
        # self.setCentralWidget(QtWidgets.QWidget(self))  # This squeezes out docks.
        self.create_actions()
        self.create_menus()
        self.create_toolbars()

    def create_actions(self):
        pass

    def create_menus(self):
        pass

    def create_toolbars(self):
        pass

    def update(self):
        super(MyGUI, self).update()
        
        
if __name__ == '__main__':
    qapp = QApplication(sys.argv)
    aw = MyGUI()
    timer = QTimer()
    timer.timeout.connect(aw.update)
    timer.start(1)

    if (sys.flags.interactive != 1) or not hasattr(PyQt5.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()