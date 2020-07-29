import sys
import serial
import serial.tools.list_ports
import numpy as np

# use the same GUI format as the other ones
from qtpy.QtWidgets import QComboBox, QLabel, QLCDNumber, QPushButton, QDoubleSpinBox, \
                           QCheckBox, QHBoxLayout, QWidget, QVBoxLayout, QMainWindow, \
                           QFrame, QGridLayout

from qtpy.QtCore import Qt
from qtpy.QtGui import QPalette, QColor

from cerebuswrapper import CbSdkConnection
from pylsl import stream_info, stream_outlet, IRREGULAR_RATE

DEPTHWINDOWDIMS = [1260, 0, 660, 250]


class DepthGUI(QMainWindow):

    def __init__(self):
        super(DepthGUI, self).__init__()
        self.setup_ui()
        self.setup_ddu()

    def setup_ui(self):
        self.setWindowTitle('Neuroport DBS - Electrodes Depth')
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.move(DEPTHWINDOWDIMS[0], DEPTHWINDOWDIMS[1])
        self.setFixedSize(DEPTHWINDOWDIMS[2], DEPTHWINDOWDIMS[3])

        self.show()

        self.plot_widget = QWidget()
        self.setCentralWidget(self.plot_widget)

        # define Qt GUI elements
        v_layout = QVBoxLayout()

        h_layout = QHBoxLayout()
        self.comboBox_com_port = QComboBox()
        h_layout.addWidget(self.comboBox_com_port)

        self.pushButton_open = QPushButton("Open")
        h_layout.addWidget(self.pushButton_open)
        h_layout.addStretch()

        self.label_offset = QLabel("Offset: ")
        h_layout.addWidget(self.label_offset)

        self.doubleSpinBox_offset = QDoubleSpinBox()
        self.doubleSpinBox_offset.setMinimum(-100.00)
        self.doubleSpinBox_offset.setMaximum(100.00)
        self.doubleSpinBox_offset.setSingleStep(1.00)
        self.doubleSpinBox_offset.setDecimals(2)
        self.doubleSpinBox_offset.setValue(-10.00)
        self.doubleSpinBox_offset.setFixedWidth(80)
        h_layout.addWidget(self.doubleSpinBox_offset)

        h_layout.addStretch()

        self.chk_NSP = QCheckBox("Send to NSP")
        self.chk_NSP.setChecked(True)
        h_layout.addWidget(self.chk_NSP)

        h_layout.addSpacing(10)

        self.chk_LSL = QCheckBox("Stream to LSL")
        self.chk_LSL.setChecked(True)
        h_layout.addWidget(self.chk_LSL)

        h_layout.addSpacing(10)

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send)

        h_layout.addWidget(send_btn)
        h_layout.addSpacing(10)

        quit_btn = QPushButton('X')
        quit_btn.setMaximumWidth(20)
        quit_btn.clicked.connect(qapp.quit)
        pal = QPalette()
        pal.setColor(QPalette.Button, QColor(255, 0, 0, 255))
        quit_btn.setAutoFillBackground(True)
        quit_btn.setPalette(pal)
        h_layout.addWidget(quit_btn)

        v_layout.addLayout(h_layout)

        # define Qt GUI elements
        # add a frame for the LCD numbers
        self.lcd_frame = QFrame()
        self.lcd_frame.setFrameShape(1)
        lcd_layout = QGridLayout()
        self.lcd_frame.setLayout(lcd_layout)

        # RAW reading from DDU
        self.raw_ddu = QLCDNumber()
        self.raw_ddu.setDigitCount(7)
        self.raw_ddu.setFrameShape(0)
        self.raw_ddu.setSmallDecimalPoint(True)
        self.raw_ddu.setFixedHeight(50)
        self.raw_ddu.display("{0:.3f}".format(0))
        lcd_layout.addWidget(self.raw_ddu, 0, 3, 2, 3)

        self.offset_ddu = QLCDNumber()
        self.offset_ddu.setDigitCount(7)
        self.offset_ddu.setFixedHeight(150)
        self.offset_ddu.display("{0:.3f}".format(-10))
        self.offset_ddu.setFrameShape(0)
        lcd_layout.addWidget(self.offset_ddu, 2, 0, 5, 6)
        v_layout.addWidget(self.lcd_frame)

        self.plot_widget.setLayout(v_layout)

        # Populate control panel items
        for port in serial.tools.list_ports.comports():
            self.comboBox_com_port.addItem(port.device)
        self.comboBox_com_port.addItem("cbsdk playback")

        # Connect signals & slots
        self.pushButton_open.clicked.connect(self.open_DDU)
        self.chk_NSP.clicked.connect(self.connect_cbsdk)
        self.chk_LSL.clicked.connect(self.stream_lsl)

    def setup_ddu(self):
        self.display_string = None

        # Serial port config
        self.ser = serial.Serial()
        self.ser.baudrate = 19200

        # NSP Config
        self.do_NSP = True
        self.connect_cbsdk()

        # LSL outlet config
        self.do_LSL = True  # Default is on
        depth_info = stream_info(name='electrode_depth', type='depth', channel_count=1,
                                 nominal_srate=IRREGULAR_RATE, source_id='depth1214')
        self.depth_stream = stream_outlet(depth_info)

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

    def connect_cbsdk(self):
        if CbSdkConnection().connect() != 0:
            self.chk_NSP.setChecked(False)
        self.do_NSP = self.chk_NSP.isChecked()

    def stream_lsl(self):
        self.do_LSL = self.chk_LSL.isChecked()

    def update(self):
        # Added new_value handling for playback if we ever want to post-process depth
        # on previously recorded sessions.
        new_value = False
        out_value = None

        if self.comboBox_com_port.currentText() == "cbsdk playback":
            cbsdk_conn = CbSdkConnection()

            if cbsdk_conn.is_connected:
                comments = cbsdk_conn.get_comments()
                if comments:
                    comment_strings = [x[1].decode('utf8') for x in comments]
                else:
                    comment_strings = ""
                dtts = []
                for comm_str in comment_strings:
                    if 'DTT:' in comm_str:
                        dtts.append(float(comm_str[4:]))
                if len(dtts) > 0:
                    out_value = dtts[-1]
                    new_value = True
                    self.offset_ddu.display("{0:.3f}".format(out_value))
                    self.raw_ddu.display("{0:.3f}".format(out_value))

        elif self.ser.is_open:
            in_str = self.ser.readline().decode('utf-8').strip()
            if in_str:
                try:
                    in_value = float(in_str)
                    self.raw_ddu.display("{0:.3f}".format(in_value))

                    out_value = in_value + self.doubleSpinBox_offset.value()
                    display_string = "{0:.3f}".format(out_value)
                    self.offset_ddu.display(display_string)

                    # Check if new value
                    if display_string != self.display_string:
                        new_value = True
                        self.display_string = display_string

                    # Push to NSP
                    cbsdk_conn = CbSdkConnection()
                    if cbsdk_conn.is_connected:
                        if self.do_NSP and new_value:
                            cbsdk_conn.set_comments("DTT:" + display_string)
                    else:
                        self.chk_NSP.setChecked(False)

                except ValueError:
                    print("DDU result: {}".format(in_str))

        # Push to LSL
        if self.do_LSL and new_value:
            self.depth_stream.push_sample([out_value])

    def send(self):
        self.display_string = None  # make sure the update function runs
        self.update()


if __name__ == '__main__':
    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import QTimer

    qapp = QApplication(sys.argv)
    window = DepthGUI()
    window.show()
    timer = QTimer()
    timer.timeout.connect(window.update)
    timer.start(100)

    if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()
