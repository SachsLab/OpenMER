import os
import sys
import serial
import serial.tools.list_ports
import numpy as np

from cerebuswrapper import CbSdkConnection
from pylsl import stream_info, stream_outlet, IRREGULAR_RATE

# use the same GUI format as the other ones
from qtpy.QtWidgets import QComboBox, QLineEdit, QLabel, QLCDNumber, QDialog, QPushButton, \
                           QGridLayout, QDialogButtonBox, QCalendarWidget, QDoubleSpinBox, \
                           QCheckBox, QHBoxLayout, QWidget, QVBoxLayout, QFrame, QStackedWidget, QAction

from qtpy.QtCore import Qt, QSharedMemory
from qtpy.QtGui import QPixmap, QColor, QFont, QTransform
import pyqtgraph as pg

# Note: If import dbsgui fails, then set the working directory to be this script's directory.
from dbsgui.my_widgets.custom import CustomGUI, CustomWidget, SAMPLINGGROUPS, THEMES

# Import the test wrapper. Absolute path for now.
# TODO: proper package and import.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'expdb')))
from DB_Wrap import DBWrapper, ProcessWrapper

DEPTHWINDOWDIMS = [1305, 0, 600, 1080]
XRANGE = [-1, 120000]
YRANGE = 200.00
DEPTHRANGE = [-20, 5]

# TODO: ini file?
# Default settings. If finds a category of features with the same name, will apply the value here.
FEATURESETTINGS = {'DBS': True,
                   'LFP': True}

DEPTHSETTINGS = {'threshold': True,
                 'validity': 90.0}


class DepthGUI(CustomGUI):

    def __init__(self):
        super(DepthGUI, self).__init__()
        self.setWindowTitle('Neuroport DBS - Electrodes Depth')
        self.plot_widget = {}

        # DB wrapper
        self.db_wrapper = DBWrapper()

    # Override create actions to call the clean_exit script
    def create_actions(self):
        # Actions
        self.actions = {
            'Connect': QAction("Connect", self),
            'Quit': QAction("Quit", self),
            'AddPlot': QAction("Add Plot", self)
        }
        self.actions['Connect'].triggered.connect(self.on_action_connect_triggered)
        self.actions['Quit'].triggered.connect(self.clean_exit)
        self.actions['AddPlot'].triggered.connect(self.on_action_add_plot_triggered)

    def clean_exit(self):
        if 'nsp_buffer' in self.plot_widget.keys():
            self.plot_widget['nsp_buffer'].kill_processes()

        del_list = []
        for key in self.plot_widget:
            if self.plot_widget[key].awaiting_close:
                del_list.append(key)

        for key in del_list:
            del self.plot_widget[key]

        qapp.quit()

    # defined in the CustomGUI class, is triggered when the "Add Plot" button
    # is pressed in the default GUI (Connect, Add Plot, Quit)
    def on_action_add_plot_triggered(self):
        # Open prompt to input subject details
        subject_details = AddSubjectDialog.do_add_subject_dialog()
        if subject_details is None:
            return

        # Returns true/false whether subject is properly created or not
        if self.db_wrapper.create_subject(subject_details) == -1:
            print("Subject not created")

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

        # None if not connected
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
        self.plot_widget['depth'].was_closed.connect(self.clean_exit)

        # NSP Buffer widget
        # this widget handles the process creation that scans depth values, buffers the data and sends it to the DB.
        self.plot_widget['nsp_buffer'] = NSPBufferWidget(group_info)
        self.layout.addWidget(self.plot_widget['nsp_buffer'])
        self.plot_widget['nsp_buffer'].was_closed.connect(self.clean_exit)

        h_line = QLabel()
        h_line.setFrameShape(QFrame.HLine)
        self.layout.addWidget(h_line)

        # Features Plot Widget
        self.plot_widget['features'] = FeaturesPlotWidget(group_info)
        self.layout.addWidget(self.plot_widget['features'])
        self.plot_widget['features'].was_closed.connect(self.clean_exit)

        # temp stretch to replace feature plots.
        # self.layout.addSpacing(40)

    # The custom GUI class has an update function, which calls the
    # do_plot_update function. This function then calls the update
    # function of all display widgets.
    def do_plot_update(self):
        # since all widgets have different use, they will each handle their own data collection.
        self.plot_widget['depth'].update()
        self.plot_widget['nsp_buffer'].update()
        self.plot_widget['features'].update()


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

        layout.addSpacing(10)

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
        self.lcdNumber.display("{0:.3f}".format(-20))

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

                except ValueError:
                    print("DDU result: {}".format(in_str))

        # Push to LSL
        if self.do_LSL and new_value:
            self.depth_stream.push_sample([out_value])


class NSPBufferWidget(CustomWidget):

    def __init__(self, *args, **kwargs):

        # set status images
        self.status_off = QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_off.png'))
        self.status_done = QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_done.png'))
        self.status_in_use = QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_in_use.png'))

        # read current subject value from the DBWrapper singleton.
        self.subject_id = DBWrapper().current_subject.subject_id

        self.depth_wrapper = ProcessWrapper('Depth_Process')
        self.depth_settings = {'subject_id': self.subject_id, 'electrode_settings': {}}

        self.features_wrapper = ProcessWrapper('Features_Process')
        self.features_settings = {'subject_id': self.subject_id, 'features': {}}

        # Check if default values are defined
        for cat in DBWrapper().all_features.keys():
            if cat in FEATURESETTINGS:
                self.features_settings['features'][cat] = FEATURESETTINGS[cat]
            else:
                self.features_settings['features'][cat] = False

        # do super class init here to set group info
        super(NSPBufferWidget, self).__init__(*args, **kwargs)

        # Start the features processing right now and keep going until the app is closed
        # we will stop the process when settings are changed and re-start it
        self.manage_feature_process(True)

        # default electrode settings
        if self.group_info:
            for electrode in self.group_info:
                self.depth_settings['electrode_settings'][electrode['label'].decode('utf-8')] = DEPTHSETTINGS
        else:
            self.depth_settings = None

    def create_control_panel(self):
        # define Qt GUI elements
        layout = QHBoxLayout()

        layout.addSpacing(10)

        layout.addWidget(QLabel("Depth buffer size (s): "))
        self.edit_buffer_length = QLineEdit("6.000")
        self.edit_buffer_length.setInputMask("0.000")
        self.edit_buffer_length.setFixedWidth(40)
        layout.addWidget(self.edit_buffer_length)

        layout.addSpacing(10)

        layout.addWidget(QLabel("Depth samples size (s): "))
        self.edit_sample_length = QLineEdit("4.000")
        self.edit_sample_length.setInputMask("0.000")
        self.edit_sample_length.setFixedWidth(40)
        layout.addWidget(self.edit_sample_length)

        layout.addSpacing(10)

        self.btn_settings = QPushButton("Settings")
        layout.addWidget(self.btn_settings)

        layout.addStretch()

        self.btn_start = QPushButton("Start")
        self.btn_start.setCheckable(True)
        layout.addWidget(self.btn_start)

        layout.addSpacing(10)

        self.status_label = QLabel()
        self.status_label.setPixmap(self.status_off)
        layout.addWidget(self.status_label)

        layout.addSpacing(10)

        self.layout().addLayout(layout)

        # callbacks
        self.btn_start.clicked.connect(self.manage_depth_process)
        self.btn_settings.clicked.connect(self.manage_settings)

    def manage_depth_process(self):
        # start process
        if self.btn_start.isChecked() and self.depth_settings:
            # Disable all Control menu elements
            self.edit_buffer_length.setEnabled(False)
            self.edit_sample_length.setEnabled(False)
            self.status_label.setPixmap(self.status_in_use)
            self.btn_start.setText("Stop")
            # NSP_DB_Process expects a dict:
            #   subject_id: set in __init__
            #   buffer_length: set here
            #   sample_length: set here
            #   electrode_settings: {label: [bool threshold, validity]}): set in manage_settings
            self.depth_settings['buffer_length'] = float(self.edit_buffer_length.text())
            self.depth_settings['sample_length'] = float(self.edit_sample_length.text())

            self.depth_wrapper.send_settings(self.depth_settings)

            self.depth_wrapper.start_worker()

        # stop process
        else:
            self.btn_start.setChecked(False)
            self.depth_wrapper.kill_worker()

            self.edit_buffer_length.setEnabled(True)
            self.edit_sample_length.setEnabled(True)
            self.status_label.setPixmap(self.status_off)
            self.btn_start.setText("Start")

    def manage_feature_process(self, on_off):
        if on_off:
            self.features_wrapper.send_settings(self.features_settings)
            self.features_wrapper.start_worker()
        else:
            self.features_wrapper.kill_worker()

    def manage_settings(self):
        # passes pointers to dictionaries so no need to return
        if AddSettingsDialog.do_add_settings_dialog(self.depth_settings, self.features_settings):
            self.depth_wrapper.send_settings(self.depth_settings)
            self.features_wrapper.send_settings(self.features_settings)

    # No GUI
    def create_plots(self, theme='dark', **kwargs):
        pass

    def refresh_axes(self):
        pass

    def clear(self):
        pass

    def update(self):
        # True means done, false is in_use, None
        output = self.depth_wrapper.worker_status()
        if output is not None:
            if output:
                self.status_label.setPixmap(self.status_done)
            else:
                self.status_label.setPixmap(self.status_in_use)

    def kill_processes(self):
        self.depth_wrapper.kill_worker()
        self.features_wrapper.kill_worker()


class FeaturesPlotWidget(CustomWidget):

    def __init__(self, *args, **kwargs):
        # Empty dict for plot options
        self.plot_config = {}
        self.y_range = YRANGE
        # base class calls create_control_panel. Need to have variables set before hand.

        # List all feature categories
        self.feature_categories = DBWrapper().all_features.keys()

        # shared memory to display the currently monitored electrode
        self.monitored_channel_mem = QSharedMemory()
        self.monitored_channel_mem.setKey("MonitoredChannelMemory")
        self.monitored_channel_mem.attach(QSharedMemory.ReadOnly)
        self.segmented_series = {}
        self.latest_datum = 0

        super(FeaturesPlotWidget, self).__init__(*args, **kwargs)

        self.read_from_shared_memory()
        self.refresh_axes()  # Extra time on purpose.

    def create_control_panel(self):
        # define Qt GUI elements
        layout = QHBoxLayout()

        layout.addSpacing(10)
        layout.addWidget(QLabel("Features: "))
        self.feature_select = QComboBox()
        self.feature_select.addItem('Raw')
        self.feature_select.addItems(self.feature_categories)
        self.feature_select.setCurrentIndex(0)
        layout.addWidget(self.feature_select)

        layout.addSpacing(10)

        layout.addWidget(QLabel("for electrode: "))
        self.chan_select = QComboBox()
        self.chan_select.addItem("None")

        if self.group_info:
            self.channel_labels = [x['label'].decode('utf-8') for x in self.group_info]

        else:  # offline implementation
            self.channel_labels = DBWrapper().channel_labels()
            CbSdkConnection().is_simulating = True

        self.chan_select.addItems(self.channel_labels)
        self.chan_select.setEnabled(False)

        # self.chan_select.setCurrentIndex(int(self.sweep_settings[0]) if self.sweep_settings is not None else 1)
        layout.addWidget(self.chan_select)
        layout.addSpacing(10)

        layout.addWidget(QLabel("+/-"))
        self.range_edit = QLineEdit("{:.2f}".format(YRANGE))
        layout.addWidget(self.range_edit)
        layout.addSpacing(10)

        self.do_hp = QCheckBox('HP')
        self.do_hp.setChecked(True)
        layout.addWidget(self.do_hp)
        layout.addSpacing(10)

        self.sweep_control = QCheckBox("Match SweepGUI channel.")
        self.sweep_control.setChecked(True)
        self.sweep_control.setEnabled(self.monitored_channel_mem.isAttached())
        layout.addWidget(self.sweep_control)

        layout.addSpacing(10)

        self.layout().addLayout(layout)

        # callbacks
        self.chan_select.currentIndexChanged.connect(self.manage_feat_chan_select)
        self.feature_select.currentIndexChanged.connect(self.manage_feat_chan_select)
        self.sweep_control.clicked.connect(self.manage_sweep_control)
        self.range_edit.editingFinished.connect(self.manage_range_edit)

    def manage_feat_chan_select(self):
        self.plot_stack.setCurrentIndex(
            self.stack_dict[self.chan_select.currentText()][self.feature_select.currentText()][0])

    def manage_sweep_control(self):
        if self.sweep_control.isChecked():
            self.chan_select.setEnabled(False)
            self.do_hp.setEnabled(False)
            self.range_edit.setEnabled(False)
            self.read_from_shared_memory()
        else:
            self.chan_select.setEnabled(True)
            self.do_hp.setEnabled(True)
            self.range_edit.setEnabled(True)

    def manage_range_edit(self):
        # need to do it like this because if we simply read the QLineEdit.text() on update calls, it breaks during
        # typing the new range values.
        self.y_range = float(self.range_edit.text())

    def create_plots(self, theme='dark'):
        # Collect PlotWidget configuration
        self.plot_config['theme'] = theme
        self.plot_config['color_iterator'] = -1
        self.plot_config['x_range'] = XRANGE
        self.plot_config['y_range'] = YRANGE
        self.plot_config['depth_range'] = DEPTHRANGE
        self.plot_config['do_hp'] = True

        self.plot_stack = QStackedWidget()

        self.stack_dict = {}
        # generate a dict {chan_label: {Feature:[stack idx, latest_datum]}}

        labels = ['None']
        labels.extend(self.channel_labels)
        features = ['Raw']
        features.extend(self.feature_categories)
        stack_idx = 0
        for lbl_idx, lbl in enumerate(labels):
            self.stack_dict[lbl] = {}
            self.plot_config['color_iterator'] = lbl_idx - 1
            self.plot_config['title'] = lbl
            for feat in features:
                self.stack_dict[lbl][feat] = [stack_idx, 0]
                # TODO: not hard-coding??
                if feat == 'Raw':
                    self.plot_stack.addWidget(RawPlotWidget(dict(self.plot_config)))
                elif feat == 'DBS':
                    self.plot_stack.addWidget(DBSPlotWidget(dict(self.plot_config)))
                elif feat == 'LFP':
                    self.plot_stack.addWidget(LFPPlotWidget(dict(self.plot_config)))
                stack_idx += 1

        self.layout().addWidget(self.plot_stack)
        self.plot_stack.setCurrentIndex(0)

    def refresh_axes(self):
        pass

    def clear(self):
        self.latest_datum = 0
        # self.new_plot.clear()

    def update(self):
        if self.sweep_control.isChecked():
            self.read_from_shared_memory()

        curr_chan_lbl = self.chan_select.currentText()
        if curr_chan_lbl != 'None':
            curr_feat = self.feature_select.currentText()
            do_hp = self.do_hp.isChecked()

            if do_hp != self.plot_stack.currentWidget().plot_config['do_hp'] or \
                    self.y_range != self.plot_stack.currentWidget().plot_config['y_range']:
                self.plot_stack.currentWidget().clear_plot()
                self.stack_dict[curr_chan_lbl][curr_feat][1] = 0
                self.plot_stack.currentWidget().plot_config['do_hp'] = do_hp
                self.plot_stack.currentWidget().plot_config['y_range'] = self.y_range

            curr_datum = self.stack_dict[curr_chan_lbl][curr_feat][1]
            if curr_feat == 'Raw':
                all_data = DBWrapper().load_depth_data(chan_lbl=curr_chan_lbl,
                                                       gt=curr_datum,
                                                       do_hp=do_hp,
                                                       return_uV=True)
            else:
                all_data = DBWrapper().load_features_data(category=curr_feat,
                                                          chan_lbl=curr_chan_lbl,
                                                          gt=curr_datum)

            if all_data:
                self.plot_stack.currentWidget().update_plot(all_data)
                self.stack_dict[curr_chan_lbl][curr_feat][1] = max(all_data.keys())

    def read_from_shared_memory(self):
        if self.monitored_channel_mem.isAttached():
            self.monitored_channel_mem.lock()
            settings = np.frombuffer(self.monitored_channel_mem.data(), dtype=np.float)[-3:]
            self.chan_select.setCurrentIndex(int(settings[0]))
            # if self.plot_config['y_range'] != settings[1] or self.plot_config['do_hp'] != bool(settings[2]):
            #     self.clear()
            self.range_edit.setText(str(settings[1]))
            self.manage_range_edit()
            self.do_hp.setChecked(bool(settings[2]))
            self.monitored_channel_mem.unlock()
        else:
            self.monitored_channel_mem.attach()
            self.sweep_control.setChecked(False)
            self.manage_sweep_control()


class RawPlotWidget(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(RawPlotWidget, self).__init__(*args, **kwargs)

        self.plot_config = plot_config
        self.pen_color = QColor(THEMES[self.plot_config['theme']]['pencolors'][self.plot_config['color_iterator']])

        # Create and add GraphicsLayoutWidget
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create GLW for the depth plot
        depth_glw = pg.GraphicsLayoutWidget(parent=self)

        self.layout.addWidget(depth_glw, 0, 0, 8, 1)

        # depth_GLW settings
        self.depth_plot = depth_glw.addPlot(enableMenu=False)
        self.depth_plot.invertY()
        # self.depth_plot.setMouseEnabled(x=False, y=False)
        self.depth_plot.setYRange(self.plot_config['depth_range'][0], self.plot_config['depth_range'][1], padding=0)
        self.depth_plot.setXRange(-5, 5, padding=0)
        self.depth_plot.getAxis('bottom').setStyle(tickLength=0, showValues=False)
        self.depth_plot.getAxis('bottom').setPen((255, 255, 255, 255))
        font = QFont()
        font.setPixelSize(20)
        font.setBold(True)
        self.depth_plot.getAxis('left').tickFont = font
        self.depth_plot.getAxis('left').setPen((255, 255, 255, 255))
        self.depth_plot.getAxis('left').setStyle(tickLength=0)

        self.depth_plot.scene().sigMouseMoved.connect(self.mouse_moved)

        # Plot vertical line and "target" (i.e. 0) line
        self.depth_plot.plot(np.zeros(100), np.arange(self.plot_config['depth_range'][0],
                                                      self.plot_config['depth_range'][1],
                                                      .25))
        self.depth_plot.plot([-5, 5], [0, 0], pen='y')

        self.fill_bar = self.depth_plot.plot([-5, 5],
                                             [self.plot_config['depth_range'][0], self.plot_config['depth_range'][0]],
                                             fillLevel=self.plot_config['depth_range'][0], brush=(255, 255, 255, 100),
                                             movable=True)

        self.depth_bar = pg.InfiniteLine(angle=0,
                                         bounds=[self.plot_config['depth_range'][0],
                                                 self.plot_config['depth_range'][1]],
                                         pos=self.plot_config['depth_range'][0],
                                         movable=True,
                                         pen='w')
        self.depth_bar.sigDragged.connect(self.depth_bar_drag)

        self.depth_plot.addItem(self.depth_bar)
        #
        # self.fill_bar = pg.LinearRegionItem(values=[-18, -20], orientation=pg.LinearRegionItem.Horizontal,
        #                                     brush=(255, 255, 255, 100), movable=True, bounds=[-20, 5])
        # self.fill_bar_position = self.fill_bar.getRegion()
        # self.fill_bar.sigRegionChanged.connect(self.fill_bar_update)
        #
        # self.depth_plot.addItem(self.fill_bar)

        # Prepare plot data
        self.data_layout = QVBoxLayout()
        self.layout.addLayout(self.data_layout, 0, 1, 8, 5)
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 5)
        self.depth = self.plot_config['depth_range'][0]

        self.data_figures = []
        self.data_plots = []
        self.depth_data = {}

        for i in range(8):
            tmp = pg.GraphicsLayoutWidget()
            self.data_layout.addWidget(tmp)
            tmp = tmp.addPlot()
            tmp.hideAxis('bottom')
            tmp.hideAxis('left')
            tmp.setMouseEnabled(x=False, y=False)
            tmp.setXRange(plot_config['x_range'][0], self.plot_config['x_range'][1])
            tmp.setYRange(-self.plot_config['y_range'], self.plot_config['y_range'])
            self.data_figures.append(tmp)
            self.data_plots.append(tmp.plot(pen=self.pen_color, autoDownsample=True))

    def mouse_moved(self, evt):
        print(self.depth_plot.scene().itemAt(evt.x(), evt.y(), QTransform()))

    def fill_bar_update(self):
        # Set the current value depending on how the region is changed.
        # If dragged, will change to 4 values lower than the middle.
        # If top will change to 8 values below.
        # If bottom, will keep new value.

        all_depths = np.sort([x for x in self.depth_data.keys()])
        if len(all_depths) > 0:
            if self.fill_bar_position[0] != self.fill_bar.getRegion()[0] and \
               self.fill_bar_position[1] != self.fill_bar.getRegion()[1]:
                curr_value = np.mean(self.fill_bar.getRegion())
                offset = 3
            elif self.fill_bar_position[0] != self.fill_bar.getRegion()[0]:
                curr_value = self.fill_bar.getRegion()[0]
                offset = 7
            elif self.fill_bar_position[1] != self.fill_bar.getRegion()[1]:
                curr_value = self.fill_bar.getRegion()[1]
                offset = 0
            else:
                return

            diffs = abs(all_depths - curr_value)
            # lock to closest depth value
            idx, = np.where(diffs == min(diffs))[0]
            b_idx = min(len(all_depths)-1, idx + offset)
            t_idx = max(0, idx - 7)
            self.fill_bar_position = (all_depths[b_idx], all_depths[t_idx])
            self.fill_bar.setRegion((all_depths[b_idx], all_depths[t_idx]))

    def depth_bar_drag(self):
        # set fill area to be the first 8 depths found above the line
        all_depths = np.sort([x for x in self.depth_data.keys()])
        if len(all_depths) > 0:
            curr_value = self.depth_bar.value()
            diffs = abs(all_depths - curr_value)

            # lock to closest depth value
            idx, = np.where(diffs == min(diffs))[0]
            self.depth_bar.setValue(all_depths[idx])
            self.plot_depth_values()

    # Update plot is only for new datum
    def update_plot(self, all_data):
        if all_data is not None:
            # all_data is a dict {datum_id: [depth, np array of data]}
            for _, depth_data in all_data.items():
                # append data
                if depth_data[0] not in self.depth_data.keys():
                    self.depth_data[depth_data[0]] = depth_data[1]

                # plot depth
                symbolBrush = self.pen_color if depth_data[2] else None
                self.depth_plot.plot(x=[0], y=[depth_data[0]], symbol='o', symbolBrush=symbolBrush,
                                     symbolPen=self.pen_color)

                new_depth = depth_data[0]

            # assign depth
            self.depth = new_depth

            # move draggable bar to new depth
            self.depth_bar.setValue(new_depth)
            self.plot_depth_values()

    def plot_depth_values(self):
        # get current index of selected depth
        all_depths = np.sort([x for x in self.depth_data.keys()])
        curr_value = self.depth_bar.value()

        # lock to closest depth value
        idx, = np.where(all_depths == curr_value)[0]

        # plot last 8 depth data
        # make fill bar around 8 depths above the currently selected one
        top_idx = max(0, idx - 7)
        self.fill_bar.setData(x=[-5, 5], y=[all_depths[idx], all_depths[idx]], fillLevel=all_depths[top_idx])

        plot_idx = 1
        while plot_idx <= 8:
            if idx >= top_idx:
                self.data_plots[-plot_idx].setData(y=self.depth_data[all_depths[idx]])
                self.data_figures[-plot_idx].setYRange(-self.plot_config['y_range'], self.plot_config['y_range'])
            else:
                self.data_plots[-plot_idx].setData(y=[])
                self.data_figures[-plot_idx].setYRange(-self.plot_config['y_range'], self.plot_config['y_range'])
            idx -= 1
            plot_idx += 1

        # if len(all_depths) >= 8:
        #     fill_bar = all_depths[-8]
        # else:
        #     fill_bar = -20
        # # self.depth_bar.setData(x=[-2.5, 2.5], y=[new_depth, new_depth], fillLevel=fill_bar)

    def clear_plot(self):
        self.depth_data = {}


class DBSPlotWidget(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(DBSPlotWidget, self).__init__(*args, **kwargs)

        self.plot_config = plot_config
        self.pen_color = QColor(THEMES[self.plot_config['theme']]['pencolors'][self.plot_config['color_iterator']])

        # Create and add GraphicsLayoutWidget
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create GLW for the depth plot
        rms_glw = pg.GraphicsLayoutWidget(parent=self)
        self.layout.addWidget(rms_glw, 0, 0, 1, 1)

        beta_pwr_glw = pg.GraphicsLayoutWidget(parent=self)
        self.layout.addWidget(beta_pwr_glw, 1, 0, 1, 1)

        pac_glw = pg.GraphicsLayoutWidget(parent=self)
        self.layout.addWidget(pac_glw, 2, 0, 1, 1)

        # spacer
        # self.layout.addWidget(QLabel(), 3, 0, 1, 1)
        self.layout.setRowStretch(0, 1)
        self.layout.setRowStretch(1, 1)
        self.layout.setRowStretch(2, 1)

        # rms settings
        self.rms_plot = rms_glw.addPlot(enableMenu=False)
        self.configure_plot(self.rms_plot, 'Noise RMS (uV)', False)

        # beta pwr settings
        self.bp_plot = beta_pwr_glw.addPlot(enableMenu=False)
        self.configure_plot(self.bp_plot, 'Beta Power (dB)', False)

        # PAC settings
        self.pac_plot = pac_glw.addPlot(enableMenu=False)
        self.configure_plot(self.pac_plot, 'PAC', True)

        self.depth_data = {}
        self.depth = -20.000

    def configure_plot(self, plot, title, show_values):
        plot.setTitle(title=title, **{'color': 'w', 'size': '16pt'})
        plot.addItem(pg.InfiniteLine(angle=90,
                                     pos=0.0,
                                     movable=False,
                                     pen='y'))
        plot.setMouseEnabled(x=False, y=False)
        plot.setXRange(self.plot_config['depth_range'][0], self.plot_config['depth_range'][1], padding=0)

        font = QFont()
        font.setPixelSize(20)
        font.setBold(True)

        plot.getAxis('bottom').setStyle(showValues=show_values)
        plot.getAxis('bottom').tickFont = font
        plot.getAxis('bottom').setPen((255, 255, 255, 255))
        plot.getAxis('bottom').setStyle(tickTextOffset=10)

        plot.getAxis('left').tickFont = font
        plot.getAxis('left').setPen((255, 255, 255, 255))

    def update_plot(self, all_data):
        if all_data is not None:
            # all_data is a dict {datum_id: [depth, np array of data]}
            for idx, depth_data in all_data.items():
                # append data
                for key in depth_data:
                    if key != 'depth':
                        self.depth_data[depth_data['depth']] = {key: depth_data[key]}

                # plot depth
                if depth_data['NoiseRMS'][2]:
                    symbolBrush = self.pen_color
                else:
                    symbolBrush = None

                self.rms_plot.plot(x=[depth_data['depth']], y=[depth_data['NoiseRMS'][1][0]], symbol='o',
                                   symbolBrush=symbolBrush, symbolPen=self.pen_color)

                if depth_data['BetaPower'][2]:
                    symbolBrush = self.pen_color
                else:
                    symbolBrush = None

                self.bp_plot.plot(x=[depth_data['depth']], y=10*np.log10([depth_data['BetaPower'][1][0]]),
                                  symbol='o', symbolBrush=symbolBrush, symbolPen=self.pen_color)

                new_depth = depth_data['depth']

            # assign depth
            self.depth = new_depth

    def clear_plot(self):
        self.depth_data = {}


class LFPPlotWidget(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(LFPPlotWidget, self).__init__(*args, **kwargs)

        self.plot_config = plot_config
        self.pen_color = QColor(THEMES[self.plot_config['theme']]['pencolors'][self.plot_config['color_iterator']])

        # Create and add GraphicsLayoutWidget
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create GLW for the depth plot
        alpha_glw = pg.GraphicsLayoutWidget(parent=self)
        self.layout.addWidget(alpha_glw, 0, 0, 1, 1)

        self.layout.addWidget(QLabel(), 1, 0, 1, 1)
        self.layout.setRowStretch(0, 1)
        self.layout.setRowStretch(1, 1)

        # beta pwr settings
        self.alpha_plot = alpha_glw.addPlot(enableMenu=False)
        self.alpha_plot.setTitle(title='Spectrum slope (alpha)', **{'color': 'w', 'size': '16pt'})
        self.alpha_plot.plot([0, 0], [0, 10], pen='y')
        self.alpha_plot.setMouseEnabled(x=False, y=False)
        self.alpha_plot.setYRange(0, 10, padding=0)
        self.alpha_plot.setXRange(self.plot_config['depth_range'][0], self.plot_config['depth_range'][1], padding=0)

        font = QFont()
        font.setPixelSize(20)
        font.setBold(True)

        # X Axis
        self.alpha_plot.getAxis('bottom').setStyle(showValues=True)
        self.alpha_plot.getAxis('bottom').tickFont = font
        self.alpha_plot.getAxis('bottom').setStyle(tickTextOffset=10)
        self.alpha_plot.getAxis('bottom').setPen((255, 255, 255, 255))

        # Y Axis
        self.alpha_plot.getAxis('left').tickFont = font
        self.alpha_plot.getAxis('left').setPen((255, 255, 255, 255))

        self.depth_data = {}

    # Update plot is only for new datum
    def update_plot(self, all_data):
        if all_data is not None:
            # all_data is a dict {datum_id: [depth, [xvec, data]}
            for idx, depth_data in all_data.items():
                # append data
                for key in depth_data:
                    if key != 'depth':
                        self.depth_data[depth_data['depth']] = {key: depth_data[key]}

                # f_range = [1, 120]
                f_stops = [(-np.Inf, 1.0), (58, 62), (116, 124), (150, np.Inf)]

                freqs = self.depth_data[depth_data['depth']]['MultiTaperSpectrum'][0]
                b_freqs = np.ones((len(freqs),), dtype=bool)
                for f_s in f_stops:
                    b_freqs[np.logical_and(freqs >= f_s[0], freqs <= f_s[1])] = False

                pwr = self.depth_data[depth_data['depth']]['MultiTaperSpectrum'][1]
                # b_freqs = np.logical_and(freqs >= f_range[0], freqs <= f_range[1])
                #
                # freqs = freqs[tuple(f_slice)] * np.ones(blk[b_freqs, ...].shape)
                A = np.vstack([-np.log(freqs[b_freqs].flatten()), np.ones(freqs[b_freqs].size)]).T
                alpha, b = np.linalg.lstsq(A,
                                           np.log(pwr[b_freqs].flatten()), rcond=None)[0]
                # plt.scatter(-np.log(freqs.flatten()), np.log(blk[b_freqs, ...].data.flatten()))
                tmp = np.arange(-5, 0, 0.1)

                self.alpha_plot.plot(x=[depth_data['depth']], y=[alpha], symbol='o',
                                   symbolBrush=self.pen_color, pen=self.pen_color)

                # plot depth
                # self.depth_plot.plot(x=[0], y=[depth_data['depth']], symbol='o', symbolBrush=self.pen_color,
                #                      pen=self.pen_color)
                new_depth = depth_data['depth']

            # assign depth
            self.depth = new_depth

            # move draggable bar to new depth
            # self.depth_bar.setValue(new_depth)
            # self.plot_depth_values()

    # def plot_depth_values(self):
    #     # get current index of selected depth
    #     all_depths = np.sort([x for x in self.depth_data.keys()])
    #     # curr_value = self.depth_bar.value()
    #
    #     # lock to closest depth value
    #     if len(all_depths) > 0:
    #
    #         # if curr_value not in all_depths:
    #         #     curr_value = all_depths[-1]
    #         #     self.depth_bar.setValue(curr_value)
    #
    #         # idx, = np.where(all_depths == curr_value)[0]
    #
    #         # plot last 8 depth data
    #         # make fill bar around 8 depths above the currently selected one
    #         # top_idx = max(0, idx - 7)
    #         # self.fill_bar.setData(x=[-5, 5], y=[all_depths[idx], all_depths[idx]], fillLevel=all_depths[top_idx])
    #
    #         plot_idx = 1
    #         while plot_idx <= 8:
    #             if idx >= top_idx:
    #                 f_range = [1, 120]
    #                 freqs = self.depth_data[all_depths[idx]]['MultiTaperSpectrum'][0]
    #                 pwr = self.depth_data[all_depths[idx]]['MultiTaperSpectrum'][1]
    #                 b_freqs = np.logical_and(freqs >= f_range[0], freqs <= f_range[1])
    #                 #
    #                 # freqs = freqs[tuple(f_slice)] * np.ones(blk[b_freqs, ...].shape)
    #                 A = np.vstack([-np.log(freqs[b_freqs].flatten()), np.ones(freqs[b_freqs].size)]).T
    #                 alpha, b = np.linalg.lstsq(A,
    #                                            np.log(pwr[b_freqs].flatten()))[0]
    #                 # plt.scatter(-np.log(freqs.flatten()), np.log(blk[b_freqs, ...].data.flatten()))
    #                 tmp = np.arange(-5, 0, 0.1)
    #                 # plt.plot(tmp, tmp*alpha + b)
    #                 self.data_plots[-plot_idx].setData(x=-np.log(freqs[b_freqs].flatten()),
    #                                                    y=np.log(pwr[b_freqs].flatten()))
    #                 legend = self.data_figures[-plot_idx].addLegend()
    #                 legend.addItem(self.data_plots[-plot_idx], str(alpha))
    #                 # self.data_plots[-plot_idx].setData(x=tmp,
    #                 #                                    y=tmp*alpha + b)
    #                 self.data_figures[-plot_idx].setXRange(-5, 0)
    #                 self.data_figures[-plot_idx].setYRange(0, 25)
    #             else:
    #                 self.data_plots[-plot_idx].setData(y=[])
    #                 # self.data_figures[-plot_idx].setYRange(-self.plot_config['y_range'], self.plot_config['y_range'])
    #             idx -= 1
    #             plot_idx += 1
    #
    #         # if len(all_depths) >= 8:
    #         #     fill_bar = all_depths[-8]
    #         # else:
    #         #     fill_bar = -20
    #         # # self.depth_bar.setData(x=[-2.5, 2.5], y=[new_depth, new_depth], fillLevel=fill_bar)

    def clear_plot(self):
        self.depth_data = {}


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
        self.name_edit.setText("Guilmer")
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
    def __init__(self, electrode_settings, feature_settings, parent=None):
        super(AddSettingsDialog, self).__init__(parent)
        self.setWindowTitle("Enter settings.")

        # settings dicts
        self.electrodes_settings = electrode_settings
        self.electrodes_widgets = {}

        self.features_settings = feature_settings
        self.features_widgets = {}

        # Widgets to show/edit connection parameters.
        self.settings_layout = QVBoxLayout(self)

        # Electrode settings
        self.settings_layout.addWidget(QLabel('Electrodes settings'))

        electrodes_frame = QFrame()
        electrodes_frame.setFrameShape(QFrame.StyledPanel)
        self.settings_layout.addWidget(electrodes_frame)
        electrodes_layout = QGridLayout()
        if self.electrodes_settings:
            if 'electrode_settings' in self.electrodes_settings.keys():
                for idx, (label, sett) in enumerate(self.electrodes_settings['electrode_settings'].items()):
                    electrodes_layout.addWidget(QLabel(label), idx, 0, 1, 1)
                    self.electrodes_widgets[label] = {}
                    self.electrodes_widgets[label]['chk_threshold'] = QCheckBox("Threshold")
                    self.electrodes_widgets[label]['chk_threshold'].setChecked(bool(sett['threshold']))
                    self.electrodes_widgets[label]['edit_validity'] = QLineEdit()
                    self.electrodes_widgets[label]['edit_validity'].setText(str(sett['validity']))

                    electrodes_layout.addWidget(self.electrodes_widgets[label]['chk_threshold'], idx, 1, 1, 1)
                    electrodes_layout.addWidget(QLabel('Validity Threshold (%)'), idx, 2, 1, 1)
                    electrodes_layout.addWidget(self.electrodes_widgets[label]['edit_validity'], idx, 3, 1, 1)

        electrodes_frame.setLayout(electrodes_layout)

        # Features settings
        self.settings_layout.addWidget(QLabel('Features settings'))

        features_frame = QFrame()
        features_frame.setFrameShape(QFrame.StyledPanel)
        self.settings_layout.addWidget(features_frame)
        features_layout = QGridLayout()

        # Add an option to toggle all features
        self.all_features = QCheckBox('All')
        self.all_features.setChecked(False)
        self.all_features.clicked.connect(self.toggle_all)
        features_layout.addWidget(self.all_features, 0, 0, 1, 1)
        if 'features' in self.features_settings.keys():
            for idx, (label, sett) in enumerate(self.features_settings['features'].items()):
                self.features_widgets[label] = QCheckBox(label)
                self.features_widgets[label].setChecked(sett)
                self.features_widgets[label].clicked.connect(self.toggle)
                features_layout.addWidget(self.features_widgets[label], idx+1, 0, 1, 1)

        features_frame.setLayout(features_layout)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.settings_layout.addWidget(buttons, alignment=Qt.AlignHCenter)

    def toggle_all(self):
        for label, sett in self.features_widgets.items():
            self.features_widgets[label].setChecked(self.all_features.isChecked())

    def toggle(self):
        if any([not x.isChecked() for x in self.features_widgets.values()]):
            self.all_features.setChecked(False)

    @staticmethod
    def do_add_settings_dialog(electrode_settings, features_settings, parent=None):
        dialog = AddSettingsDialog(electrode_settings, features_settings, parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            # convert all fields to dictionary and return it
            for key, value in dialog.electrodes_widgets.items():
                dialog.electrodes_settings['electrode_settings'][key] = {}
                dialog.electrodes_settings['electrode_settings'][key]['threshold'] = value['chk_threshold'].isChecked()
                dialog.electrodes_settings['electrode_settings'][key]['validity'] = float(value['edit_validity'].text())

            for key, value in dialog.features_widgets.items():
                dialog.features_settings['features'][key] = value.isChecked()
            return True
        else:
            return False


if __name__ == '__main__':
    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import QTimer

    qapp = QApplication(sys.argv)
    window = DepthGUI()
    window.show()
    timer = QTimer()
    timer.timeout.connect(window.update)
    timer.start(50)

    if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()
