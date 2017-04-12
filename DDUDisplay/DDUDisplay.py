# -*- coding: utf-8 -*-
import sys
import serial
import serial.tools.list_ports
import PyQt5
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from cerebus import cbpy
# from pympler import tracker


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
        # self.tr = tracker.SummaryTracker()

    def __del__(self):
        cbpy.close()
        self.ser.close()

    def connect_to_cbpy(self):
        if self.cb_button.text() == "Send":
            # Open the interface to the NSP #
            con_params = cbpy.defaultConParams()
            try:
                result, connect_info = cbpy.open(instance=0, connection='default', parameter=con_params)
                print("cbpy.open returned result: {}; connect_info: {}".format(result, connect_info))
            except RuntimeError as e:
                result = int(str(e).split(",")[0])
                print(e)
            if result == 0:
                self.cb_button.setText("Stop")
        elif self.cb_button.text() == "Stop":
            cbpy.close()
            self.cb_button.setText("Send")
    
    def connect_to_DDU(self):
        if not self.ser.is_open:
            self.ser.port = self.com_port_box.currentText()
            self.ser.open()  # TODO: Add timeout; Add error.
            self.connect_button.setText("Close")
        else:
            self.ser.close()
            self.connect_button.setText("Open")

    def setup_ui(self):
        self.resize(600, 250)
        self.setWindowTitle('IGN DDU')
        self.setCentralWidget(QWidget(self))
        self.centralWidget().setLayout(QVBoxLayout())

        cntrl_layout = QHBoxLayout()
        # UI elements for connecting to the serial port
        self.com_port_box = QComboBox()
        for port in serial.tools.list_ports.comports():
            self.com_port_box.addItem(port.device)
        cntrl_layout.addWidget(self.com_port_box)
        self.connect_button = QPushButton("Open")
        self.connect_button.clicked.connect(self.connect_to_DDU)
        cntrl_layout.addWidget(self.connect_button)
        # UI elements for controlling artificial offset
        cntrl_layout.addWidget(QLabel("Offset:"))
        self.offset_edit = QLineEdit()
        self.offset_edit.setValidator(QDoubleValidator(-100, 100, 2))
        self.offset_edit.setText("10.00")
        cntrl_layout.addWidget(self.offset_edit)
        self.cb_button = QPushButton("Send")
        self.cb_button.clicked.connect(self.connect_to_cbpy)
        cntrl_layout.addWidget(self.cb_button)
        #
        # tracker_button = QPushButton("tracker")
        # tracker_button.clicked.connect(self.print_tracker)
        # cntrl_layout.addWidget(tracker_button)
        #
        self.centralWidget().layout().addLayout(cntrl_layout)

        self.lcd = QLCDNumber()
        self.lcd.setDigitCount(7)
        self.centralWidget().layout().addWidget(self.lcd)
        
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

    # def print_tracker(self):
    #     self.tr.print_diff()

    def update(self):
        super(MyGUI, self).update()
        if self.ser.is_open:
            in_str = self.ser.readline().decode('utf-8').strip()
            if in_str:
                in_value = float(in_str)
                offset_value = float(self.offset_edit.text())
                display_string = "{0:.3f}".format(in_value + offset_value)
                self.lcd.display(display_string)

                if self.cb_button.text() == "Stop":
                    cbpy.set_comment("DTT:" + display_string, rgba_tuple=(0, 0, 0, 64))


if __name__ == '__main__':
    qapp = QApplication(sys.argv)
    aw = MyGUI()
    timer = QTimer()
    timer.timeout.connect(aw.update)
    timer.start(100)

    if (sys.flags.interactive != 1) or not hasattr(PyQt5.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()