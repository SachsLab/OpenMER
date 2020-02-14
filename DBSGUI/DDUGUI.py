import os
import sys
import serial
import serial.tools.list_ports
from cerebuswrapper import CbSdkConnection
from pylsl import stream_info, stream_outlet, IRREGULAR_RATE

# use the same GUI format as the other ones
from qtpy.QtWidgets import QComboBox, QLineEdit, QLabel, QLCDNumber, QDialog, QPushButton, \
                           QGridLayout, QDialogButtonBox, QCalendarWidget, QDoubleSpinBox, \
                           QCheckBox, QHBoxLayout, QWidget, QVBoxLayout

from qtpy.QtCore import Qt, QProcess, Signal, Slot
from qtpy.QtGui import QPixmap

import pyqtgraph as pg
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'dbsgui'))
# Note: If import dbsgui fails, then set the working directory to be this script's directory.
from dbsgui.my_widgets.custom import CustomGUI, CustomWidget, ConnectDialog, SAMPLINGGROUPS

# Import the test wrapper. Absolute path for now.
# TODO: proper package and import.
sys.path.append('D:\\Sachs_Lab\\DBS_dev\\expdb\\')
import DB_Wrap

DEPTHWINDOWDIMS = [1260, 0, 600, 1080]
XRANGE = 20


class DepthGUI(CustomGUI):

    def __init__(self):
        super(DepthGUI, self).__init__()
        self.setWindowTitle('Neuroport DBS - Electrodes Depth')
        self.plot_widget = {}

        # DB wrapper
        self.db_wrapper = DB_Wrap.DBWrapper()
        self.subject_id = None

    # defined in the CustomGUI class, is triggered when the "Add Plot" button
    # is pressed in the default GUI (Connect, Add Plot, Quit)
    def on_action_add_plot_triggered(self):
        # Open prompt to input subject details
        details_dict = AddSubjectDialog.do_add_subject_dialog()
        if details_dict is None:
            return

        # Returns the subject_id of either the created subject entry, or if an existing
        # one is found.
        self.subject_id = self.db_wrapper.create_subject(details_dict)

        # Configure CB SDK connection
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

        # Single window for all sub-widgets
        self.plot_window = QWidget()
        self.plot_window.setWindowFlags(Qt.FramelessWindowHint)
        self.plot_window.move(DEPTHWINDOWDIMS[0], DEPTHWINDOWDIMS[1])
        self.plot_window.resize(DEPTHWINDOWDIMS[2], DEPTHWINDOWDIMS[3])
        self.plot_window.show()

        self.layout = QVBoxLayout(self.plot_window)

        # Add widget to display depth
        # Same as the old DDUGUI plot.
        self.plot_widget['depth'] = DepthWidget(group_info)
        self.layout.addWidget(self.plot_widget['depth'])
        self.plot_widget['depth'].was_closed.connect(self.on_plot_closed)

        # NSP Buffer widget
        # this widget handles the process creation that scans depth values, buffers the data and sends it to the DB.
        self.plot_widget['nsp_buffer'] = NSPBufferWidget(group_info, subject_id=self.subject_id)
        self.layout.addWidget(self.plot_widget['nsp_buffer'])
        self.plot_widget['nsp_buffer'].was_closed.connect(self.on_plot_closed)

        # temp stretch to replace feature plots.
        self.layout.addStretch()

        # slots / signals
        # EMPTY

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
        # since all widgets have different use, they will each handle their own data collection.
        self.plot_widget['depth'].update()
        self.plot_widget['nsp_buffer'].update()


class DepthWidget(CustomWidget):

    def __init__(self, *args, **kwargs):
        # Empty dict for plot options
        self.plot_config = {}

        super(DepthWidget, self).__init__(*args, **kwargs)

        self.refresh_axes()  # Extra time on purpose.

        self.display_string = None

        # Serial port config
        self.ser = serial.Serial()
        self.ser.baudrate = 19200

        # NSP Config
        self.do_NSP = True

        # LSL outlet config
        self.do_LSL = True  # Default is on
        depth_info = stream_info(name='electrode_depth', type='depth', channel_count=1,
                                 nominal_srate=IRREGULAR_RATE, source_id='depth1214')
        self.depth_stream = stream_outlet(depth_info)

    def create_control_panel(self):
        # define Qt GUI elements
        layout = QHBoxLayout()
        self.comboBox_com_port = QComboBox()
        layout.addWidget(self.comboBox_com_port)

        self.pushButton_open = QPushButton("Open")
        layout.addWidget(self.pushButton_open)
        layout.addStretch()

        self.label_offset = QLabel("Offset: ")
        layout.addWidget(self.label_offset)

        self.doubleSpinBox_offset = QDoubleSpinBox()
        self.doubleSpinBox_offset.setMinimum(-100.00)
        self.doubleSpinBox_offset.setMaximum(100.00)
        self.doubleSpinBox_offset.setSingleStep(1.00)
        self.doubleSpinBox_offset.setDecimals(2)
        self.doubleSpinBox_offset.setValue(10.00)
        self.doubleSpinBox_offset.setFixedWidth(80)
        layout.addWidget(self.doubleSpinBox_offset)

        layout.addStretch()

        self.chk_NSP = QCheckBox("Send to NSP")
        self.chk_NSP.setChecked(True)
        layout.addWidget(self.chk_NSP)

        layout.addSpacing(20)

        self.chk_LSL = QCheckBox("Stream to LSL")
        self.chk_LSL.setChecked(True)
        layout.addWidget(self.chk_LSL)

        self.layout().addLayout(layout)

        # Populate control panel items
        for port in serial.tools.list_ports.comports():
            self.comboBox_com_port.addItem(port.device)
        self.comboBox_com_port.addItem("cbsdk playback")

        # Connect signals & slots
        self.pushButton_open.clicked.connect(self.open_DDU)
        self.chk_NSP.clicked.connect(self.connect_cbsdk)
        self.chk_LSL.clicked.connect(self.stream_lsl)

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
        if CbSdkConnection().connect() == 0:
            self.chk_NSP.setChecked(False)
        self.do_NSP = self.chk_NSP.isChecked()

    def stream_lsl(self):
        self.do_LSL = self.chk_LSL.isChecked()

    def create_plots(self, theme='dark'):
        self.plot_config['theme'] = theme

        # define Qt GUI elements
        self.lcdNumber = QLCDNumber()
        self.lcdNumber.setDigitCount(7)
        self.lcdNumber.setDecMode()
        self.lcdNumber.setFixedHeight(200)

        # set layout
        self.layout().addWidget(self.lcdNumber)

    def refresh_axes(self):
        pass

    def clear(self):
        pass

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
                    self.lcdNumber.display("{0:.3f}".format(out_value))

        elif self.ser.is_open:
            in_str = self.ser.readline().decode('utf-8').strip()
            if in_str:
                try:
                    in_value = float(in_str)
                    out_value = in_value + self.doubleSpinBox_offset.value()
                    display_string = "{0:.3f}".format(out_value)
                    self.lcdNumber.display(display_string)

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

                    # Push to LSL
                    if self.do_LSL and new_value:
                        self.depth_stream.push_sample([out_value])

                except ValueError:
                    print("DDU result: {}".format(in_str))

        if new_value and out_value:
            # TODO: remove in final version, this is to debug LSL
            self.depth_stream.push_sample([out_value])


class NSPBufferWidget(CustomWidget):

    """
    The NSP Buffer Widget will run in a QThread since reading the NSP buffer and saving
    the data to the DB is unlikely to yield a GIL.
    """
    def __init__(self, *args, **kwargs):

        # set status images
        self.status_off = QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_off.png'))
        self.status_done = QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_done.png'))
        self.status_in_use = QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_in_use.png'))

        # parse arguments (group_info, subject ID)
        if 'subject_id' in kwargs:
            self.subject_id = kwargs['subject_id']
        else:
            self.subject_id = None

        # define process
        self.worker = QProcess()
        self.worker.setProcessChannelMode(QProcess.MergedChannels)

        self.settings = dict()

        # do super class init here to get group info
        super(NSPBufferWidget, self).__init__(*args, **kwargs)

        # default electrode settings
        for elec in self.group_info:
            self.settings[elec['label'].decode('utf-8')] = {
                'threshold': True,
                'validity': 90.0}

    def create_control_panel(self):
        # define Qt GUI elements
        layout = QHBoxLayout()

        layout.addSpacing(20)

        layout.addWidget(QLabel("Depth buffer size (s): "))
        self.edit_buffer_length = QLineEdit("6.000")
        self.edit_buffer_length.setInputMask("0.000")
        self.edit_buffer_length.setFixedWidth(40)
        layout.addWidget(self.edit_buffer_length)

        layout.addSpacing(20)

        layout.addWidget(QLabel("Depth samples size (s): "))
        self.edit_sample_length = QLineEdit("4.000")
        self.edit_sample_length.setInputMask("0.000")
        self.edit_sample_length.setFixedWidth(40)
        layout.addWidget(self.edit_sample_length)

        layout.addSpacing(20)

        self.btn_settings = QPushButton("Settings")
        layout.addWidget(self.btn_settings)

        layout.addSpacing(20)

        self.btn_start = QPushButton("Start")
        self.btn_start.setCheckable(True)
        layout.addWidget(self.btn_start)

        layout.addSpacing(20)

        self.status_label = QLabel()
        self.status_label.setPixmap(self.status_off)
        layout.addWidget(self.status_label)

        layout.addSpacing(20)

        self.layout().addLayout(layout)

        # callbacks
        self.btn_start.clicked.connect(self.manage_process)
        self.btn_settings.clicked.connect(self.manage_settings)

    def manage_process(self):
        # start process
        if self.btn_start.isChecked() and self.subject_id is not None:
            # Disable all Control menu elements
            self.edit_buffer_length.setEnabled(False)
            self.edit_sample_length.setEnabled(False)
            self.status_label.setPixmap(self.status_in_use)
            self.btn_start.setText("Stop")
            # NSP_DB_Process expects : subject_id, buffer_length, sample_length, ...
            # then label threshold validity for each electrode):
            electrode_settings = ""
            for key, value in self.settings.items():
                electrode_settings += key + " " + str(value['threshold']) + " " + str(value['validity']) + " "

            run_command = "python " + os.path.join(os.path.dirname(__file__),
                                                   "NSP_DB_Process.py " +
                                                   str(self.subject_id) + " " +
                                                   self.edit_buffer_length.text() + " " +
                                                   self.edit_sample_length.text() + " " +
                                                   electrode_settings)
            self.worker.start(run_command)

        # stop process
        else:
            self.btn_start.setChecked(False)
            # TODO: Figure out how to terminate gracefully?
            self.worker.kill()
            self.worker.waitForFinished()

            self.edit_buffer_length.setEnabled(True)
            self.edit_sample_length.setEnabled(True)
            self.status_label.setPixmap(self.status_off)
            self.btn_start.setText("Start")

    def manage_settings(self):
        details_dict = AddSettingsDialog.do_add_settings_dialog(self.settings)
        if details_dict is None:
            self.settings = details_dict

    # No GUI
    def create_plots(self, theme='dark', **kwargs):
        pass

    def refresh_axes(self):
        pass

    def clear(self):
        pass

    def update(self):
        # reads the stdout from the process. The script prints either 'in_use' or 'done' to show the current state of
        # the depth recording.
        if self.worker.bytesAvailable() > 0:
            output = self.worker.readAllStandardOutput().data().decode('UTF-8').strip()
            if output == 'in_use':
                self.status_label.setPixmap(self.status_in_use)
            elif output == 'done':
                self.status_label.setPixmap(self.status_done)


# Dialogs
class AddSubjectDialog(QDialog):

    """
    A modal dialog window with widgets to create a new subject entry in the DB.
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
                'birthday': dialog.dob_calendar.selectedDate().toPyDate()
            }

            return out_dict
        return None


class AddSettingsDialog(QDialog):

    """
    A modal dialog window with widgets to create settings for data filtering.
    """

    def __init__(self, default_settings, parent=None):
        super(AddSettingsDialog, self).__init__(parent)
        self.setWindowTitle("Enter channel settings.")

        self.dict_settings = default_settings
        # Widgets to show/edit connection parameters.
        self.settings_layout = QGridLayout(self)

        for idx, (label, sett) in enumerate(self.dict_settings.items()):
            self.settings_layout.addWidget(QLabel(label), idx, 0, 1, 1)
            self.dict_settings[label] = {}
            self.dict_settings[label]['chk_threshold'] = QCheckBox("Threshold")
            self.dict_settings[label]['chk_threshold'].setChecked(bool(sett['threshold']))
            self.dict_settings[label]['edit_validity'] = QLineEdit()
            self.dict_settings[label]['edit_validity'].setText(str(sett['validity']))

            self.settings_layout.addWidget(self.dict_settings[label]['chk_threshold'], idx, 1, 1, 1)
            self.settings_layout.addWidget(QLabel('Validity Threshold (%)'), idx, 2, 1, 1)
            self.settings_layout.addWidget(self.dict_settings[label]['edit_validity'], idx, 3, 1, 1)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.settings_layout.addWidget(buttons, 6, 0, 1, 2, alignment=Qt.AlignHCenter)

    @staticmethod
    def do_add_settings_dialog(settings, parent=None):
        dialog = AddSettingsDialog(settings, parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            # convert all fields to dictionary and return it
            for key, value in dialog.dict_settings.items():
                dialog.dict_settings[key] = {}
                dialog.dict_settings[key]['threshold'] = value['chk_threshold'].isChecked()
                dialog.dict_settings[key]['validity'] = float(value['edit_validity'].text())
                dialog.dict_settings[key]['chk_threshold'] = None
                dialog.dict_settings[key]['edit_validity'] = None
        return dialog.dict_settings


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
