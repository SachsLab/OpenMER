import sys
import serial
import serial.tools.list_ports
import numpy as np

# use the same GUI format as the other ones
from qtpy.QtWidgets import QComboBox, QLabel, QLCDNumber, QPushButton, QDoubleSpinBox, \
                           QCheckBox, QHBoxLayout, QWidget, QVBoxLayout, QMainWindow, QLineEdit

from qtpy.QtCore import Qt
from qtpy.QtGui import QPalette, QColor

from cerebuswrapper import CbSdkConnection
from pylsl import stream_info, stream_outlet, IRREGULAR_RATE

DEPTHWINDOWDIMS = [1260, 0, 660, 250]


class LSLDepthGUI(QMainWindow):

    def __init__(self):
        super(LSLDepthGUI, self).__init__()
        self.setup_ui()
        self.setup_ddu()

    def setup_ui(self):
        self.setWindowTitle('Neuroport DBS - Electrodes Depth')
        self.show()

        self.plot_widget = QWidget()
        self.setCentralWidget(self.plot_widget)

        # define Qt GUI elements
        v_layout = QVBoxLayout()

        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel('Depth: '))

        self.doubleSpinBox_depth = QDoubleSpinBox()
        self.doubleSpinBox_depth.setMinimum(-20.0)
        self.doubleSpinBox_depth.setMaximum(5.0)
        self.doubleSpinBox_depth.setSingleStep(.5)
        self.doubleSpinBox_depth.setDecimals(1)
        self.doubleSpinBox_depth.setValue(-20.0)
        self.doubleSpinBox_depth.setFixedWidth(80)
        h_layout.addWidget(self.doubleSpinBox_depth)

        self.pushButton_send = QPushButton("Send")
        h_layout.addWidget(self.pushButton_send)
        h_layout.addStretch()

        # quit_btn = QPushButton('X')
        # quit_btn.setMaximumWidth(20)
        # quit_btn.clicked.connect(qapp.quit)
        # pal = QPalette()
        # pal.setColor(QPalette.Button, QColor(255, 0, 0, 255))
        # quit_btn.setAutoFillBackground(True)
        # quit_btn.setPalette(pal)
        # h_layout.addWidget(quit_btn)

        v_layout.addLayout(h_layout)

        self.plot_widget.setLayout(v_layout)

        # Connect signals & slots
        self.pushButton_send.clicked.connect(self.send_value)

    def setup_ddu(self):
        # LSL outlet config
        self.do_LSL = True  # Default is on
        depth_info = stream_info(name='electrode_depth', type='depth', channel_count=1,
                                 nominal_srate=IRREGULAR_RATE, source_id='depth1214')
        self.depth_stream = stream_outlet(depth_info)

    def send_value(self):
        self.depth_stream.push_sample([self.doubleSpinBox_depth.value()])


if __name__ == '__main__':
    from qtpy.QtWidgets import QApplication

    qapp = QApplication(sys.argv)
    window = LSLDepthGUI()
    window.show()

    if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()
