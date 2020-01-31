import os
import sys
import serial
import serial.tools.list_ports
from cerebuswrapper import CbSdkConnection

# use the same GUI format as the other ones
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QComboBox, QLineEdit, QHBoxLayout, QLabel, QLCDNumber, QDialog, QVBoxLayout, QPushButton, \
                           QGridLayout, QDialogButtonBox, QCalendarWidget

from qtpy.QtCore import Qt

import pyqtgraph as pg
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'dbsgui'))
# Note: If import dbsgui fails, then set the working directory to be this script's directory.
from dbsgui.my_widgets.custom import CustomGUI, CustomWidget, ConnectDialog, SAMPLINGGROUPS

# from qtpy import QtCore, QtWidgets
# from qtpy import uic

DEPTHWINDOWDIMS = [1260, 0, 600, 220]
FEATURESWINDOWDIMS = [1260, 220, 600, 860]
XRANGE = 20


class DepthGUI(CustomGUI):

    def __init__(self):
        super(DepthGUI, self).__init__()
        self.setWindowTitle('Neuroport DBS - Electrodes Depth')
        self.plot_widget = {}

    # defined in the CustomGUI class, is triggered when the "Add Plot" button
    # is pressed in the default GUI opened when launched (Connect, Add Plot, Quit)
    def on_action_add_plot_triggered(self):
        subname = AddSubjectDialog.do_add_subject_dialog()
        print(subname)

        self.cbsdk_conn.cbsdk_config = {
            'reset': True,
            'get_continuous': True,
            'get_events': False,
            'get_comments': True,
            'buffer_parameter': {
                'comment_length': 10
            }
        }

        group_info = self.cbsdk_conn.get_group_config(SAMPLINGGROUPS.index("30000"))

        self.plot_widget['depth'] = DepthWidget(group_info)

    def on_plot_closed(self):
        del_list = []
        for key in self.plot_widget:
            if self.plot_widget[key].awaiting_close:
                del_list.append(key)

        for key in del_list:
            del self.plot_widget[key]

        if not self.plot_widget:
            self.cbsdk_conn.cbsdk_config = {'reset': True, 'get_continuous': False}

    # The custom GUI class has an update function, which calls the
    # do_plot_update function. This function then calls the update
    # function of all display widgets.
    def do_plot_update(self):
            self.plot_widget.update()

        # self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        # self.move(WINDOWDIMS[0], WINDOWDIMS[1])
        # self.resize(WINDOWDIMS[2], WINDOWDIMS[3])
        # self.setupUi(self)

        # self.display_string = None
        # self.ser = serial.Serial()
        # self.ser.baudrate = 19200
        # for port in serial.tools.list_ports.comports():
        #     self.comboBox_com_port.addItem(port.device)
        # self.comboBox_com_port.addItem("cbsdk playback")

        # Connect signals & slots
        # self.pushButton_open.clicked.connect(self.open_DDU)
        # self.pushButton_send.clicked.connect(self.connect_cbsdk)

    # No need to disconnect because the instance will do so automatically.
    # def __del__(self):
    #     from cerebuswrapper import CbSdkConnection
    #     CbSdkConnection().disconnect()


class DepthWidget(CustomWidget):
    def __init__(self, *args, **kwargs):
        self.plot_config = {}
        super(DepthWidget, self).__init__(*args, **kwargs)

        self.segmented_series = {}  # Will contain one array of curves for each line/channel label.
        this_dims = DEPTHWINDOWDIMS

        self.move(this_dims[0], this_dims[1])
        self.resize(this_dims[2], this_dims[3])
        self.refresh_axes()  # Extra time on purpose.

    def closeEvent(self, evnt):
        print(evnt)

    def create_control_panel(self):
        print('createcontrolpanel')

    def connect_cbsdk(self):
        if CbSdkConnection().connect() == 0:
            self.pushButton_send.setDisabled(True)

    def create_plots(self, theme='dark', downsample=False, alt_loc=False):
        self.plot_config['theme'] = theme
        self.plot_config['alt_loc'] = alt_loc
        self.plot_config['downsample'] = downsample

        glw = pg.GraphicsLayoutWidget(parent=self)
        lcd = QLCDNumber(7, self)
        lcd.display(1234)
        self.layout().addWidget(lcd)

    def add_series(self, chan_info):
        print(self, chan_info)

    def refresh_axes(self):
        self.a = 2

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

    def update(self, data):
        if self.comboBox_com_port.currentText() == "cbsdk playback":
            cbsdk_conn = CbSdkConnection()

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


# Dialogs
class AddSubjectDialog(QDialog):

    """
    A modal dialog window with widgets to create a new subject entry in the DB.
    Will return the subject ID.
    """

    def __init__(self, parent=None):
        super(AddSubjectDialog, self).__init__(parent)
        self.setWindowTitle("Enter subject information.")

        # Widgets to show/edit connection parameters.
        self.subject_layout = QGridLayout(self)

        self.subject_layout.addWidget(QLabel("Name: "), 1, 0, 1, 1)
        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(135)
        self.subject_layout.addWidget(self.name_edit, 1, 1, 1, 1)

        self.subject_layout.addWidget(QLabel("ID: "), 2, 0, 1, 1)
        self.id_edit = QLineEdit()
        self.id_edit.setMaxLength(135)
        self.subject_layout.addWidget(self.id_edit, 2, 1, 1, 1)

        self.subject_layout.addWidget(QLabel("Sex: "), 3, 0, 1, 1)
        self.sex_combo = QComboBox()
        self.sex_combo.addItems(['unspecified', 'male', 'female', 'unknown'])
        self.sex_combo.setCurrentIndex(0)
        self.subject_layout.addWidget(self.sex_combo, 3, 1, 1, 1)

        self.subject_layout.addWidget(QLabel("Handedness: "), 4, 0, 1, 1)
        self.hand_combo = QComboBox()
        self.hand_combo.addItems(['unknown', 'right', 'left', 'equal'])
        self.hand_combo.setCurrentIndex(0)
        self.subject_layout.addWidget(self.hand_combo, 4, 1, 1, 1)

        self.subject_layout.addWidget((QLabel("Date of birth: ")), 5, 0, 1, 1)
        self.dob_calendar = QCalendarWidget()
        self.subject_layout.addWidget(self.dob_calendar, 5, 1, 1, 1)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.subject_layout.addWidget(buttons, 7, 0, 1, 2, alignment=Qt.AlignHCenter)

    @staticmethod
    def do_add_subject_dialog(parent=None):
        dialog = AddSubjectDialog(parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            # convert all fields to dictionary and return it
            out_dict = {
                'name': dialog.name_edit.text(),
                'id': dialog.id_edit.text(),
                'sex': dialog.sex_combo.currentText(),
                'handedness': dialog.hand_combo.currentText(),
                'birthday': dialog.dob_calendar.selectedDate()
            }
            return out_dict
        return -1, False


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
