import os
import sys
import numpy as np

# use the same GUI format as the other ones
from qtpy.QtWidgets import QComboBox, QLineEdit, QLabel, QDialog, QPushButton, \
                           QGridLayout, QDialogButtonBox, QCalendarWidget, QDoubleSpinBox, \
                           QCheckBox, QHBoxLayout, QFrame, QStackedWidget, QAction

from qtpy.QtCore import Qt, QSharedMemory, QDate, Signal

from qtpy.QtGui import QPixmap

from cerebuswrapper import CbSdkConnection

# Note: If import dbsgui fails, then set the working directory to be this script's directory.
from dbsgui.my_widgets.custom import CustomGUI, CustomWidget, SAMPLINGGROUPS, THEMES
from feature_plots import *

# Import the test wrapper.
# TODO: proper package and import.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'expdb')))
from DB_Wrap import DBWrapper, ProcessWrapper

WINDOWDIMS = [1260, 250, 660, 830]

XRANGE = [-1500, 120000]
YRANGE = 200.00
DEPTHRANGE = [-20, 5]

# TODO: ini file?
# Default settings. If finds a category of features with the same name, will apply the value here.
FEATURESETTINGS = {'DBS': True,
                   'LFP': True}

DEPTHSETTINGS = {'threshold': True,
                 'validity': 90.0}


class FeaturesGUI(CustomGUI):

    def __init__(self):
        super(FeaturesGUI, self).__init__()
        self.setWindowTitle('Neuroport DBS - Electrodes Depth')
        self.plot_widget = None

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
        if self.plot_widget:
            self.plot_widget.kill_processes()

            if self.plot_widget.awaiting_close:
                del self.plot_widget

        qapp.quit()

    # defined in the CustomGUI class, is triggered when the "Add Plot" button
    # is pressed in the default GUI (Connect, Add Plot, Quit)
    def on_action_add_plot_triggered(self):
        # Get all the available information for settings
        # NSP info, None if not connected
        self.group_info = self.cbsdk_conn.get_group_config(SAMPLINGGROUPS.index("30000"))

        # List all feature categories
        self.feature_categories = self.db_wrapper.all_features.keys()

        # Default settings for subject.
        self.subject_settings = {'name': '',
                                 'hemisphere': 'unknown',
                                 'pass': 1,
                                 'id': '',
                                 'sex': 'unknown',
                                 'handedness': 'unknown',
                                 'birthday': None}

        # default settings for depth process
        self.depth_settings = {'subject_id': None,
                               'hemisphere': 'unknown',
                               'pass': 1,
                               'buffer_length': '6.000',
                               'sample_length': '4.000',
                               'run_buffer': True,  # add the option to not run it to display a previous pass
                               'electrode_settings': {}}
        if self.group_info:
            for electrode in self.group_info:
                self.depth_settings['electrode_settings'][electrode['label'].decode('utf-8')] = DEPTHSETTINGS

        # default features settings
        self.features_settings = {'subject_id': None,
                                  'features': {}}

        # Check if default values are defined
        for cat in self.feature_categories:
            if cat in FEATURESETTINGS:
                self.features_settings['features'][cat] = FEATURESETTINGS[cat]
            else:
                self.features_settings['features'][cat] = False

        # Open settings dialog and update DBWrapper subject and settings dicts
        if not self.manage_settings():
            return

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

        # NSP Buffer widget
        # this widget handles the process creation that scans depth values, buffers the data and sends it to the DB.
        self.plot_widget = FeaturesPlotWidget(self.group_info)
        self.plot_widget.was_closed.connect(self.clean_exit)
        self.plot_widget.call_manage_settings.connect(self.get_settings)

        # send values to widgets
        self.send_settings()

    # The custom GUI class has an update function, which calls the
    # do_plot_update function. This function then calls the update
    # function of all display widgets.
    def do_plot_update(self):
        # since all widgets have different use, they will each handle their own data collection.
        self.plot_widget.update()

    def manage_settings(self):
        # Open prompt to input subject details
        AddSettingsDialog.do_add_settings_dialog(self.subject_settings,
                                                 self.depth_settings,
                                                 self.features_settings)

        # Create or load subject
        # Returns subject_id/-1 whether subject is properly created or not
        sub_id = self.db_wrapper.create_subject(self.subject_settings)

        if sub_id == -1:
            print("Subject not created.")
            return False
        else:
            self.subject_settings['subject_id'] = sub_id
            self.depth_settings['subject_id'] = sub_id
            self.features_settings['subject_id'] = sub_id

            self.depth_settings['hemisphere'] = self.subject_settings['hemisphere']
            self.depth_settings['pass'] = self.subject_settings['pass']

            # set hemisphere and pass information
            self.db_wrapper.set_current_hemisphere(self.subject_settings['hemisphere'])
            self.db_wrapper.set_current_pass(self.subject_settings['pass'])

            return True

    def get_settings(self):
        # open prompt and update values
        if self.manage_settings():
            # update values to widgets
            self.send_settings()

    def send_settings(self):
        self.plot_widget.process_settings(self.subject_settings,
                                          self.depth_settings,
                                          self.features_settings)


class FeaturesPlotWidget(CustomWidget):
    call_manage_settings = Signal()

    def __init__(self, *args, **kwargs):

        # define status images
        self.status_off = QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_off.png'))
        self.status_done = QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_done.png'))
        self.status_in_use = QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_in_use.png'))

        # Settings
        self.subject_settings = None
        self.depth_settings = None
        self.features_settings = None

        # Plot options
        self.plot_config = {}
        self.y_range = YRANGE
        self.plot_stack = QStackedWidget()
        # generate a dict {chan_label: {Feature:[stack idx, latest_datum]}}
        self.stack_dict = {}

        # shared memory to display the currently monitored electrode
        self.monitored_channel_mem = QSharedMemory()
        self.monitored_channel_mem.setKey("MonitoredChannelMemory")
        self.monitored_channel_mem.attach(QSharedMemory.ReadOnly)

        # wrap up init
        super(FeaturesPlotWidget, self).__init__(*args, **kwargs)
        self.move(WINDOWDIMS[0], WINDOWDIMS[1])
        self.resize(WINDOWDIMS[2], WINDOWDIMS[3])
        self.setMaximumWidth(WINDOWDIMS[2])

        # initialize plots
        self.layout().addWidget(self.plot_stack)
        self.refresh_axes()  # Extra time on purpose.

        # Define and start processes
        # will only start processes when settings are received
        self.depth_wrapper = ProcessWrapper('Depth_Process')
        self.depth_process_running = False

        self.features_wrapper = ProcessWrapper('Features_Process')
        self.features_process_running = False

    def create_control_panel(self):
        # define Qt GUI elements
        layout = QHBoxLayout()
        layout.addSpacing(10)

        layout.addWidget(QLabel("Features: "))
        self.feature_select = QComboBox()
        self.feature_select.addItem('Raw')
        # self.feature_select.addItems(self.feature_categories)
        self.feature_select.setCurrentIndex(0)
        layout.addWidget(self.feature_select)

        layout.addSpacing(10)

        layout.addWidget(QLabel("for electrode: "))
        self.chan_select = QComboBox()
        self.chan_select.addItem("None")
        # if self.group_info:
        #     self.channel_labels = [x['label'].decode('utf-8') for x in self.group_info]
        # else:  # offline implementation
        #     self.channel_labels = DBWrapper().channel_labels()
        #     CbSdkConnection().is_simulating = True
        # self.chan_select.addItems(self.channel_labels)
        self.chan_select.setMinimumWidth(75)
        self.chan_select.setEnabled(False)
        layout.addWidget(self.chan_select)

        layout.addSpacing(20)

        layout.addWidget(QLabel("+/-"))
        self.range_edit = QLineEdit("{:.2f}".format(YRANGE))
        self.range_edit.setMaximumWidth(50)
        layout.addWidget(self.range_edit)

        layout.addSpacing(20)

        self.do_hp = QCheckBox('HP')
        self.do_hp.setChecked(True)
        layout.addWidget(self.do_hp)

        layout.addSpacing(20)

        self.sweep_control = QCheckBox("Match SweepGUI.")
        self.sweep_control.setChecked(True)
        self.sweep_control.setEnabled(self.monitored_channel_mem.isAttached())
        layout.addWidget(self.sweep_control)

        layout.addStretch()

        self.btn_settings = QPushButton("Settings")
        layout.addWidget(self.btn_settings)

        layout.addSpacing(20)

        self.status_label = QLabel()
        self.status_label.setPixmap(self.status_off)
        layout.addWidget(self.status_label)

        layout.addSpacing(10)

        self.layout().addLayout(layout)

        # callbacks
        self.btn_settings.clicked.connect(self.call_manage_settings.emit)
        self.chan_select.currentIndexChanged.connect(self.manage_feat_chan_select)
        self.feature_select.currentIndexChanged.connect(self.manage_feat_chan_select)
        self.sweep_control.clicked.connect(self.manage_sweep_control)
        self.range_edit.editingFinished.connect(self.manage_range_edit)

    # GUI Callbacks
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

    def manage_depth_process(self, on_off):
        # start process
        if on_off and not self.depth_process_running:
            self.depth_wrapper.start_worker()
            self.depth_process_running = True
        else:
            self.depth_wrapper.kill_worker()
            self.depth_process_running = False

    def manage_feature_process(self, on_off):
        if on_off and not  self.features_process_running:
            self.features_wrapper.start_worker()
            self.features_process_running = True
        else:
            self.features_wrapper.kill_worker()
            self.features_process_running = False

    def process_settings(self, sub_sett, depth_sett, feat_sett):
        self.subject_settings = dict(sub_sett)
        self.depth_settings = dict(depth_sett)
        self.features_settings = dict(feat_sett)

        # validate that we have some data in the electrode_settings. If the NSP is not connected we will have
        # to load the channel names from the DB. Also we want to keep the FeaturesGUI unaware of the DB channels.
        if len(self.depth_settings['electrode_settings']) == 0:
            self.depth_settings['electrode_settings'] = {}
            for lbl in DBWrapper().channel_labels():
                self.depth_settings['electrode_settings'][lbl] = DEPTHSETTINGS
            CbSdkConnection().is_simulating = True

        # set new features
        self.feature_select.setCurrentIndex(0)  # Raw
        while self.feature_select.count() > 1:
            self.feature_select.removeItem(1)
        self.feature_select.addItems(self.features_settings['features'].keys())

        # set new chanels
        self.chan_select.setCurrentIndex(0)  # None
        while self.chan_select.count() > 1:
            self.chan_select.removeItem(1)
        self.chan_select.addItems(self.depth_settings['electrode_settings'].keys())

        # clear and update stacked widget
        to_delete = [self.plot_stack.widget(x) for x in range(self.plot_stack.count())]
        for wid in to_delete:
            self.plot_stack.removeWidget(wid)
            wid.deleteLater()
            wid = None
        self.stack_dict = {}
        self.create_plots()

        self.depth_wrapper.send_settings(self.depth_settings)
        self.features_wrapper.send_settings(self.features_settings)

        if self.depth_settings['run_buffer'] and \
                CbSdkConnection().is_connected and \
                not self.depth_process_running:
            self.manage_depth_process(True)

        if not self.features_process_running:
            self.manage_feature_process(True)

        # self.clear()
        self.read_from_shared_memory()

    def create_plots(self, theme='dark', **kwargs):
        # Collect PlotWidget configuration
        self.plot_config['theme'] = theme
        self.plot_config['color_iterator'] = -1
        self.plot_config['x_range'] = XRANGE
        self.plot_config['y_range'] = YRANGE
        self.plot_config['depth_range'] = DEPTHRANGE
        self.plot_config['do_hp'] = True

        labels = []
        for ii in range(0, self.chan_select.count()):
            labels.append(self.chan_select.itemText(ii))
        # labels.extend(self.channel_labels)

        features = []
        for ii in range(0, self.feature_select.count()):
            features.append(self.feature_select.itemText(ii))

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

        self.plot_stack.setCurrentIndex(0)

    def refresh_axes(self):
        pass

    def clear(self):
        # set the current datum of all stacks to 0
        for lbl in self.stack_dict:
            for feat in self.stack_dict[lbl]:
                self.stack_dict[lbl][feat][1] = 0
                self.plot_stack.widget(self.stack_dict[lbl][feat][0]).clear_plot()

    def update(self):
        # Depth process
        output = self.depth_wrapper.worker_status()
        if output == -1:
            self.status_label.setPixmap(self.status_in_use)
        elif output == 1:
            self.status_label.setPixmap(self.status_done)
        else:
            self.status_label.setPixmap(self.status_off)

        if self.sweep_control.isChecked():
            self.read_from_shared_memory()

        # features plot
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

    def kill_processes(self):
        self.manage_depth_process(False)
        self.manage_feature_process(False)

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


# Dialogs
class AddSettingsDialog(QDialog):
    def __init__(self, subject_settings, depth_settings, features_settings, parent=None):
        super(AddSettingsDialog, self).__init__(parent)
        self.setWindowTitle("Enter settings.")

        # settings dicts
        self.subject_settings = subject_settings

        self.depth_settings = depth_settings
        self.depth_widgets = {}

        self.features_settings = features_settings
        self.features_widgets = {}

        # Widgets to show/edit parameters.
        self.settings_layout = QGridLayout(self)

        # Subject Settings =============================================================================================
        subject_layout = QGridLayout()
        subject_layout.setColumnMinimumWidth(2, 60)

        subject_layout.addWidget(QLabel("Name: "), 1, 0, 1, 1)
        self.name_edit = QComboBox()
        self.name_edit.setEditable(True)
        self.name_edit.addItem('')
        self.name_edit.addItems(DBWrapper().load_all_subjects())
        self.name_edit.currentIndexChanged.connect(self.load_subject)
        subject_layout.addWidget(self.name_edit, 1, 1, 1, 4)

        self.id_edit = QLineEdit()
        self.id_edit.setMaxLength(50)
        subject_layout.addWidget(QLabel("Id: "), 2, 0, 1, 1)
        subject_layout.addWidget(self.id_edit, 2, 1, 1, 4)

        self.hem_edit = QComboBox()
        self.hem_edit.addItems(["left", "right", "unknown"])
        subject_layout.addWidget(QLabel("Hemisphere: "), 3, 0, 1, 1)
        subject_layout.addWidget(self.hem_edit, 3, 1, 1, 1)

        subject_layout.addWidget(QLabel("Pass: "), 3, 3, 1, 1)
        self.pass_edit = QDoubleSpinBox()
        self.pass_edit.setMinimum(0)
        self.pass_edit.setDecimals(0)
        self.pass_edit.setMaximumWidth(80)
        subject_layout.addWidget(self.pass_edit, 3, 4, 1, 1)

        subject_layout.addWidget(QLabel("Sex: "), 4, 0, 1, 1)
        self.sex_combo = QComboBox()
        self.sex_combo.addItems(['unspecified', 'male', 'female', 'unknown'])
        subject_layout.addWidget(self.sex_combo, 4, 1, 1, 1)

        subject_layout.addWidget(QLabel("Handedness: "), 4, 3, 1, 1)
        self.hand_combo = QComboBox()
        self.hand_combo.addItems(['unknown', 'right', 'left', 'equal'])
        self.hand_combo.setMaximumWidth(80)
        subject_layout.addWidget(self.hand_combo, 4, 4, 1, 1)

        subject_layout.addWidget((QLabel("Date of birth: ")), 5, 0, 1, 1)
        self.dob_calendar = QCalendarWidget()
        subject_layout.addWidget(self.dob_calendar, 5, 1, 1, 4)

        self.settings_layout.addWidget(QLabel("Subject settings."), 0, 0, 1, 5)
        subject_frame = QFrame()
        subject_frame.setFrameShape(QFrame.StyledPanel)
        subject_frame.setLayout(subject_layout)
        self.settings_layout.addWidget(subject_frame, 1, 0, 5, 5)

        self.update_subject()

        # Electrode settings ===========================================================================================
        self.settings_layout.addWidget(QLabel('Depth process settings'), 0, 6, 1, 5)

        depth_layout = QGridLayout()
        if self.depth_settings:
            if 'electrode_settings' in self.depth_settings.keys():
                for idx, (label, sett) in enumerate(self.depth_settings['electrode_settings'].items()):
                    depth_layout.addWidget(QLabel(label), idx, 0, 1, 1)
                    self.depth_widgets[label] = {}
                    self.depth_widgets[label]['chk_threshold'] = QCheckBox("Threshold")
                    self.depth_widgets[label]['chk_threshold'].setChecked(bool(sett['threshold']))
                    self.depth_widgets[label]['edit_validity'] = QLineEdit()
                    self.depth_widgets[label]['edit_validity'].setText(str(sett['validity']))

                    depth_layout.addWidget(self.depth_widgets[label]['chk_threshold'], idx, 1, 1, 1)
                    depth_layout.addWidget(QLabel('Validity Threshold (%)'), idx, 2, 1, 1)
                    depth_layout.addWidget(self.depth_widgets[label]['edit_validity'], idx, 3, 1, 1)

            depth_layout.addWidget(QLabel("Depth buffer size (s): "), 6, 0, 1, 1)
            self.edit_buffer_length = QLineEdit(self.depth_settings['buffer_length'])
            self.edit_buffer_length.setInputMask("0.000")
            self.edit_buffer_length.setFixedWidth(40)
            depth_layout.addWidget(self.edit_buffer_length, 6, 1, 1, 1)

            depth_layout.addWidget(QLabel("Depth samples size (s): "), 7, 0, 1, 1)
            self.edit_sample_length = QLineEdit(self.depth_settings['sample_length'])
            self.edit_sample_length.setInputMask("0.000")
            self.edit_sample_length.setFixedWidth(40)
            depth_layout.addWidget(self.edit_sample_length, 7, 1, 1, 1)

            self.run_buffer = QCheckBox('Run depth buffer')
            self.run_buffer.setChecked(len(self.depth_settings['electrode_settings']) != 0)
            self.run_buffer.setEnabled(len(self.depth_settings['electrode_settings']) != 0)
            depth_layout.addWidget(self.run_buffer, 8, 0, 1, 1)

        depth_frame = QFrame()
        depth_frame.setFrameShape(QFrame.StyledPanel)
        self.settings_layout.addWidget(depth_frame, 1, 6, 2, 5)
        depth_frame.setLayout(depth_layout)

        # Features settings ============================================================================================
        self.settings_layout.addWidget(QLabel('Features settings'), 3, 6, 1, 5)

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

        features_frame = QFrame()
        features_frame.setFrameShape(QFrame.StyledPanel)
        features_frame.setLayout(features_layout)
        self.settings_layout.addWidget(features_frame, 4, 6, 2, 5)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.settings_layout.addWidget(buttons, 7, 0, 1, 10, alignment=Qt.AlignHCenter)

    def update_subject(self):
        self.name_edit.setCurrentText(self.read_dict_value(self.subject_settings, 'name'))
        self.id_edit.setText(self.read_dict_value(self.subject_settings, 'id'))
        self.hem_edit.setCurrentText(self.read_dict_value(self.subject_settings, 'hemisphere'))
        pass_value = self.read_dict_value(self.subject_settings, 'pass')
        self.pass_edit.setValue(int(pass_value) if pass_value != '' else 1)
        self.sex_combo.setCurrentText(self.read_dict_value(self.subject_settings, 'sex'))
        self.hand_combo.setCurrentText(self.read_dict_value(self.subject_settings, 'handedness'))
        dob = self.read_dict_value(self.subject_settings, 'birthday')
        if dob not in [None, '']:
            q_dob = QDate.fromString(dob, 'yyyy-MM-d')
            self.dob_calendar.setSelectedDate(q_dob)
        else:
            self.dob_calendar.setSelectedDate(QDate.currentDate())

    def load_subject(self):
        curr_name = self.name_edit.currentText()
        if curr_name != '':
            self.subject_settings = DBWrapper().load_subject_details(curr_name)
        else:
            self.subject_settings = {}

        self.update_subject()

    @staticmethod
    def read_dict_value(dictionary, value):
        return str(dictionary[value]) if value in dictionary.keys() else ''

    def toggle_all(self):
        for label, sett in self.features_widgets.items():
            self.features_widgets[label].setChecked(self.all_features.isChecked())

    def toggle(self):
        if any([not x.isChecked() for x in self.features_widgets.values()]):
            self.all_features.setChecked(False)

    @staticmethod
    def do_add_settings_dialog(subject_settings, depth_settings, features_settings, parent=None):
        dialog = AddSettingsDialog(subject_settings, depth_settings, features_settings, parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            # subject
            subject_settings['name'] = dialog.name_edit.currentText()
            subject_settings['hemisphere'] = dialog.hem_edit.currentText()
            subject_settings['pass'] = '{:.0f}'.format(dialog.pass_edit.value())
            subject_settings['id'] = dialog.id_edit.text()
            subject_settings['sex'] = dialog.sex_combo.currentText()
            subject_settings['handedness'] = dialog.hand_combo.currentText()
            subject_settings['birthday'] = dialog.dob_calendar.selectedDate().toPyDate()

            # convert all fields to dictionary and return it
            depth_settings['buffer_length'] = dialog.edit_buffer_length.text()
            depth_settings['sample_length'] = dialog.edit_sample_length.text()
            depth_settings['run_buffer'] = dialog.run_buffer.isChecked()

            for key, value in dialog.depth_widgets.items():
                depth_settings['electrode_settings'][key] = {}
                depth_settings['electrode_settings'][key]['threshold'] = value['chk_threshold'].isChecked()
                depth_settings['electrode_settings'][key]['validity'] = float(value['edit_validity'].text())

            for key, value in dialog.features_widgets.items():
                features_settings['features'][key] = value.isChecked()
            return True
        else:
            return False


if __name__ == '__main__':
    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import QTimer

    qapp = QApplication(sys.argv)
    window = FeaturesGUI()
    window.show()
    timer = QTimer()
    timer.timeout.connect(window.update)
    timer.start(50)

    if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()
