import os
import sys
import serial
import serial.tools.list_ports
from qtpy import QtCore, QtWidgets
from qtpy import uic
from cerebuswrapper import CbSdkConnection


# Load GUI from Qt designer .ui file.
ui_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'dbsgui', 'my_widgets', 'ui')
Ui_MainWindow, QtBaseClass = uic.loadUiType(os.path.join(ui_path, 'ddu_display.ui'))
WINDOWDIMS = [1260, 0, 600, 220]


class MyGUI(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self):
        super(MyGUI, self).__init__()
        # self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.move(WINDOWDIMS[0], WINDOWDIMS[1])
        self.resize(WINDOWDIMS[2], WINDOWDIMS[3])
        self.setupUi(self)

        self.display_string = None
        self.ser = serial.Serial()
        self.ser.baudrate = 19200
        for port in serial.tools.list_ports.comports():
            self.comboBox_com_port.addItem(port.device)
        self.comboBox_com_port.addItem("cbsdk playback")

        # Connect signals & slots
        self.pushButton_open.clicked.connect(self.open_DDU)
        self.pushButton_send.clicked.connect(self.connect_cbsdk)

    # No need to disconnect because the instance will do so automatically.
    # def __del__(self):
    #     from cerebuswrapper import CbSdkConnection
    #     CbSdkConnection().disconnect()

    def connect_cbsdk(self):
        if CbSdkConnection().connect() == 0:
            self.pushButton_send.setDisabled(True)

    def open_DDU(self):
        com_port = self.comboBox_com_port.currentText()
        cmd_text = self.pushButton_open.text()
        if cmd_text == 'Open':
            if com_port == "cbsdk playback":
                pass
            else:
                if not self.ser.is_open:
                    self.ser.port = com_port
                    try:
                        self.ser.open()  # TODO: Add timeout; Add error.
                        self.ser.write('AXON+\r'.encode())
                        self.pushButton_open.setText("Close")
                    except serial.serialutil.SerialException:
                        print("Could not open serial port")
        else:
            if com_port == "cbsdk playback":
                pass
            else:
                self.ser.close()

    def update(self):
        super(MyGUI, self).update()
        if self.comboBox_com_port.currentText() == "cbsdk playback":
            cbsdk_conn = CbSdkConnection()
            cbsdk_conn.cbsdk_config = {
                'reset': True, 'get_events': False, 'get_comments': True,
                'buffer_parameter': {
                    'comment_length': 10
                }
            }
            if cbsdk_conn.is_connected:
                comments = cbsdk_conn.get_comments()
                comment_strings = [x[1].decode('utf8') for x in comments]
                dtts = []
                for comm_str in comment_strings:
                    if 'DTT:' in comm_str:
                        dtts.append(float(comm_str[4:]))
                if len(dtts) > 0:
                    new_dtt = dtts[-1]
                    self.lcdNumber.display(new_dtt)
        elif self.ser.is_open:
            in_str = self.ser.readline().decode('utf-8').strip()
            if in_str:
                try:
                    in_value = float(in_str)
                    display_string = "{0:.3f}".format(in_value + self.doubleSpinBox_offset.value())
                    self.lcdNumber.display(display_string)

                    cbsdk_conn = CbSdkConnection()
                    if cbsdk_conn.is_connected and (display_string != self.display_string):
                        cbsdk_conn.set_comments("DTT:" + display_string)
                        self.display_string = display_string
                    else:
                        self.pushButton_send.setText("Send")
                except ValueError:
                    print("DDU result: {}".format(in_str))


if __name__ == '__main__':
    qapp = QtWidgets.QApplication(sys.argv)
    window = MyGUI()
    window.show()
    timer = QtCore.QTimer()
    timer.timeout.connect(window.update)
    timer.start(100)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()
