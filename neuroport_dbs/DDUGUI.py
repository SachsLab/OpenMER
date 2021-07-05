import sys
import serial
import serial.tools.list_ports

# use the same GUI format as the other ones
import qtpy.QtCore
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QComboBox, QLabel, QLCDNumber, QPushButton, QDoubleSpinBox, \
                           QCheckBox, QHBoxLayout, QWidget, QVBoxLayout, QMainWindow, \
                           QFrame, QGridLayout

from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QTimer

from cerebuswrapper import CbSdkConnection
import pylsl

# settings
from neuroport_dbs.settings.defaults import WINDOWDIMS_DEPTH, DDUSCALEFACTOR


class DepthGUI(QMainWindow):

    def __init__(self):
        super(DepthGUI, self).__init__()

        self.display_string = None

        # Serial port config
        self.ser = serial.Serial()
        self.ser.baudrate = 19200

        self.depth_stream = None
        self._prev_port = None

        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle('Neuroport DBS - Electrodes Depth')
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.move(WINDOWDIMS_DEPTH[0], WINDOWDIMS_DEPTH[1])
        self.setFixedSize(WINDOWDIMS_DEPTH[2], WINDOWDIMS_DEPTH[3])

        self.show()

        self.plot_widget = QWidget()
        self.setCentralWidget(self.plot_widget)

        # define Qt GUI elements
        v_layout = QVBoxLayout()
        v_layout.setSpacing(0)
        v_layout.setContentsMargins(10, 0, 10, 10)

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
        self.doubleSpinBox_offset.setFixedWidth(60)
        h_layout.addWidget(self.doubleSpinBox_offset)

        h_layout.addStretch()

        h_layout.addWidget(QLabel("Stream to :"))

        self.chk_NSP = QCheckBox("NSP")
        self.chk_NSP.setChecked(True)
        h_layout.addWidget(self.chk_NSP)

        h_layout.addSpacing(5)

        self.chk_LSL = QCheckBox("LSL")
        self.chk_LSL.clicked.connect(self.on_chk_LSL_clicked)
        self.chk_LSL.click()  # default is enabled, click call to trigger LSL stream creation.
        h_layout.addWidget(self.chk_LSL)

        h_layout.addSpacing(5)

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send)

        h_layout.addWidget(send_btn)
        h_layout.addSpacing(5)

        quit_btn = QPushButton('X')
        quit_btn.setMaximumWidth(20)
        quit_btn.clicked.connect(QApplication.instance().quit)

        quit_btn.setStyleSheet("QPushButton { color: white; "
                               "background-color : red; "
                               "border-color : red; "
                               "border-width: 2px}")

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
        self.pushButton_open.clicked.connect(self.on_open_clicked)
        self.comboBox_com_port.currentIndexChanged.connect(self.on_comboBox_com_port_changed)
        # TODO: Add signal for comboBox_com_port --> when cbsdk playback, uncheck NSP then re-open connection.

    def on_chk_LSL_clicked(self, state):
        print(f"LSL clicked state: {state}")
        if self.chk_LSL.isChecked():
            outlet_info = pylsl.StreamInfo(name='electrode_depth', type='depth', channel_count=1,
                                           nominal_srate=pylsl.IRREGULAR_RATE, channel_format=pylsl.cf_float32,
                                           source_id='depth1214')
            self.depth_stream = pylsl.StreamOutlet(outlet_info)
        else:
            self.depth_stream = None

    def _do_close(self, from_port):
        if from_port == "cbsdk playback":
            CbSdkConnection().disconnect()
        else:
            self.ser.close()
        self.pushButton_open.setText("Open")

    def on_comboBox_com_port_changed(self, new_ix):
        # If a connection was already open, close it before proceeding.
        if self.pushButton_open.text() == "Close":
            self._do_close(self._prev_port)

        # at this point the Open/Close pushbutton should show: Open
        # we will only enable/disable the Send to NSP button to leave the current checked status.
        # The default should be checked.
        if self.comboBox_com_port.currentText() == "cbsdk playback":
            # If switching _to_ cbsdk playback, disable sending out comments.
            self.chk_NSP.setEnabled(False)

        elif self._prev_port == "cbsdk playback":
            # If switching _from_ cbsdk playback, re-enable sending out comments.
            self.chk_NSP.setEnabled(True)

        self._prev_port = self.comboBox_com_port.currentText()

    def on_open_clicked(self):
        com_port = self.comboBox_com_port.currentText()
        cmd_text = self.pushButton_open.text()
        if cmd_text == 'Open':

            if com_port == "cbsdk playback":
                CbSdkConnection().connect()
                CbSdkConnection().cbsdk_config = {
                    'reset': True, 'get_events': False, 'get_comments': True,
                    'buffer_parameter': {
                        'comment_length': 10
                    }
                }
                self.pushButton_open.setText("Close")
            else:
                if self.chk_NSP.isEnabled() and self.chk_NSP.isChecked():
                    CbSdkConnection().connect()
                    CbSdkConnection().cbsdk_config = {'reset': True, 'get_events': False, 'get_comments': False}

                if not self.ser.is_open:
                    self.ser.port = com_port
                    try:
                        self.ser.open()  # TODO: Add timeout; Add error.
                        self.ser.write('AXON+\r'.encode())
                    except serial.serialutil.SerialException:
                        print("Could not open serial port")
                    finally:
                        self.pushButton_open.setText("Close" if self.ser.is_open else "Open")
        else:
            self._do_close(com_port)

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
                    offset = self.doubleSpinBox_offset.value()
                    self.raw_ddu.display("{0:.3f}".format(out_value - offset))

        elif self.ser.is_open:
            in_str = self.ser.readline().decode('utf-8').strip()
            if in_str:
                try:
                    in_value = float(in_str)
                    # in_value /= DDUSCALEFACTOR  # Uncomment this for FHC DDU V2.

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
                        if self.chk_NSP.isChecked() and self.chk_NSP.isEnabled() and new_value:
                            cbsdk_conn.set_comments("DTT:" + display_string)
                    else:
                        # try connecting if not connected but button is active
                        if self.chk_NSP.isChecked() and self.chk_NSP.isEnabled():
                            cbsdk_conn.connect()
                            cbsdk_conn.cbsdk_config = {'reset': True, 'get_events': False, 'get_comments': False}
                        # set button to connection status
                        self.chk_NSP.setChecked(cbsdk_conn.is_connected)

                except ValueError:
                    print("DDU result: {}".format(in_str))

        # Push to LSL
        if self.depth_stream is not None and new_value:
            self.depth_stream.push_sample([out_value])

    def send(self):
        self.display_string = None  # make sure the update function runs
        self.update()


def main():
    _ = QApplication(sys.argv)
    window = DepthGUI()
    window.show()
    timer = QTimer()
    timer.timeout.connect(window.update)
    timer.start(100)

    if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()


if __name__ == '__main__':
    main()
