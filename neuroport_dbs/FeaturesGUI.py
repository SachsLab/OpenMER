import os
import sys
import numpy as np
import qtpy.QtCore
from qtpy.QtWidgets import QApplication
from qtpy.QtWidgets import QComboBox, QLineEdit, QLabel, QDialog, QPushButton, \
                           QCheckBox, QHBoxLayout, QVBoxLayout, QStackedWidget, QAction
from qtpy.QtCore import QSharedMemory, Signal, QTimer, Qt
from qtpy.QtGui import QPixmap


from cerebuswrapper import CbSdkConnection

# Note: If import dbsgui fails, then set the working directory to be this script's directory.
from neuroport_dbs.dbsgui.my_widgets.custom import CustomGUI, CustomWidget, SAMPLINGGROUPS
from neuroport_dbs.feature_plots import *
from neuroport_dbs.SettingsDialog import SettingsDialog

from serf.tools.db_wrap import DBWrapper, ProcessWrapper

# Settings
from neuroport_dbs.settings.defaults import WINDOWDIMS_FEATURES, XRANGE_FEATURES, uVRANGE, BASEPATH, SAMPLINGRATE, \
                                            BUFFERLENGTH, SAMPLELENGTH, DELAYBUFFER, OVERWRITEDEPTH, DEPTHSETTINGS


class FeaturesGUI(CustomGUI):

    def __init__(self):
        super(FeaturesGUI, self).__init__()
        self.setWindowTitle('Neuroport DBS - Electrodes Depth')
        self.plot_widget = None

        # settings dictionaries
        self.subject_settings = {}
        self.procedure_settings = {}
        self.buffer_settings = {}
        self.features_settings = {}

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

        QApplication.instance().quit()

    # defined in the CustomGUI class, is triggered when the "Add Plot" button
    # is pressed in the default GUI (Connect, Add Plot, Quit)
    def on_action_add_plot_triggered(self):
        # Get all the available information for settings
        # NSP info, None if not connected
        sampling_group_id = SAMPLINGGROUPS.index(str(SAMPLINGRATE))
        self.group_info = self.cbsdk_conn.get_group_config(sampling_group_id)

        # we only need to set the default values for the depth buffer here since it requires electrode
        # information. The rest accepts empty dicts
        self.buffer_settings['sampling_rate'] = SAMPLINGRATE
        self.buffer_settings['sampling_group_id'] = sampling_group_id
        self.buffer_settings['buffer_length'] = '{:.3f}'.format(BUFFERLENGTH)
        self.buffer_settings['sample_length'] = '{:.3f}'.format(SAMPLELENGTH)
        self.buffer_settings['delay_buffer'] = '{:.3f}'.format(DELAYBUFFER)
        self.buffer_settings['overwrite_depth'] = OVERWRITEDEPTH
        self.buffer_settings['electrode_settings'] = {}

        if self.group_info:
            for electrode in self.group_info:
                self.buffer_settings['electrode_settings'][electrode['label'].decode('utf-8')] = DEPTHSETTINGS

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
        win = SettingsDialog(self.subject_settings,
                             self.procedure_settings,
                             self.buffer_settings,
                             self.features_settings)
        result = win.exec_()
        if result == QDialog.Accepted:
            win.update_settings()
        else:
            return False

        # Create or load subject
        # Returns subject_id/-1 whether subject is properly created or not
        sub_id = self.db_wrapper.load_or_create_subject(self.subject_settings)

        if sub_id == -1:
            print("Subject not created.")
            return False
        else:
            self.subject_settings['subject_id'] = sub_id
            self.procedure_settings['subject_id'] = sub_id
            proc_id = self.db_wrapper.load_or_create_procedure(self.procedure_settings)

            self.buffer_settings['procedure_id'] = proc_id
            self.features_settings['procedure_id'] = proc_id

            return True

    def get_settings(self):
        # open prompt and update values
        if self.manage_settings():
            # update values to widgets
            self.send_settings()

    def send_settings(self):
        self.plot_widget.process_settings(self.subject_settings,
                                          self.procedure_settings,
                                          self.buffer_settings,
                                          self.features_settings)


class FeaturesPlotWidget(CustomWidget):
    call_manage_settings = Signal()

    def __init__(self, *args, **kwargs):

        # define status images
        self.status_icons = {
            -2: QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_delay.png')),
            -1: QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_in_use.png')),
            1: QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_done.png')),
            0: QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_off.png')),
        }

        # Settings
        self.subject_settings = None
        self.procedure_settings = None
        self.depth_settings = None
        self.features_settings = None

        # Plot options
        self.plot_config = {}
        self.y_range = uVRANGE
        self.plot_stack = QStackedWidget()
        # generate a dict {chan_label: {Feature:[stack idx, latest_datum]}}
        self.stack_dict = {}

        # shared memory to display the currently monitored electrode
        self.monitored_channel_mem = QSharedMemory()
        self.monitored_channel_mem.setKey("MonitoredChannelMemory")
        self.monitored_channel_mem.attach(QSharedMemory.ReadOnly)

        # wrap up init
        super(FeaturesPlotWidget, self).__init__(*args, **kwargs)
        self.move(WINDOWDIMS_FEATURES[0], WINDOWDIMS_FEATURES[1])
        self.resize(WINDOWDIMS_FEATURES[2], WINDOWDIMS_FEATURES[3])
        self.setMaximumWidth(WINDOWDIMS_FEATURES[2])

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

        layout_L = QVBoxLayout()
        layout_L1 = QHBoxLayout()

        # layout_L1.addSpacing(10)
        layout_L1.addWidget(QLabel("Electrode: ", alignment=Qt.AlignVCenter | Qt.AlignRight))
        # Channel selection
        self.chan_select = QComboBox()
        self.chan_select.addItem("None")
        self.chan_select.setMinimumWidth(70)
        self.chan_select.setEnabled(False)
        layout_L1.addWidget(self.chan_select)

        layout_L1.addSpacing(20)

        # features selection
        layout_L1.addWidget(QLabel("Feature set: ", alignment=Qt.AlignVCenter | Qt.AlignRight))
        self.feature_select = QComboBox()
        self.feature_select.setMinimumWidth(60)
        self.feature_select.addItem('Raw')
        self.feature_select.setCurrentIndex(0)
        layout_L1.addWidget(self.feature_select)

        layout_L.addLayout(layout_L1)
        layout_L.addSpacing(5)

        layout_L2 = QHBoxLayout()
        layout_L2.addSpacing(10)
        layout_L2.addWidget(QLabel("+/- ", alignment=Qt.AlignVCenter | Qt.AlignRight))
        self.range_edit = QLineEdit("{:.2f}".format(uVRANGE))
        self.range_edit.setMaximumWidth(50)
        layout_L2.addWidget(self.range_edit)

        layout_L2.addSpacing(30)

        self.do_hp = QCheckBox('HP')
        self.do_hp.setChecked(True)
        layout_L2.addWidget(self.do_hp)

        layout_L2.addSpacing(30)

        self.sweep_control = QCheckBox("Match SweepGUI.")
        self.sweep_control.setChecked(True)
        self.sweep_control.setEnabled(self.monitored_channel_mem.isAttached())
        layout_L2.addWidget(self.sweep_control)

        layout_L.addLayout(layout_L2)

        layout_R = QHBoxLayout()
        self.btn_settings = QPushButton("Settings")
        self.btn_settings.setMaximumWidth(50)
        layout_R.addWidget(self.btn_settings)

        layout_R.addSpacing(20)

        self.features_process_btn = QPushButton('Features')
        self.features_process_btn.setMaximumWidth(50)
        self.features_process_btn.setStyleSheet("QPushButton { color: white; "
                                                "background-color : red; "
                                                "border-color : red; "
                                                "border-width: 2px}")
        self.features_process_btn.clicked.connect(self.features_process_btn_callback)
        layout_R.addWidget(self.features_process_btn)

        layout_R.addSpacing(5)

        self.depth_process_btn = QPushButton('Record')
        self.depth_process_btn.setMaximumWidth(50)
        self.depth_process_btn.setStyleSheet("QPushButton { color: white; "
                                             "background-color : red; "
                                             "border-color : red; "
                                             "border-width: 2px}")
        self.depth_process_btn.clicked.connect(self.depth_process_btn_callback)
        layout_R.addWidget(self.depth_process_btn)

        layout_R.addSpacing(20)

        self.status_label = QLabel()
        self.status_label.setPixmap(self.status_icons[0])
        layout_R.addWidget(self.status_label)
        layout_R.addSpacing(10)

        layout.addLayout(layout_L)
        layout.addStretch()
        layout.addLayout(layout_R)

        # layout.addSpacing(10)
        self.layout().addLayout(layout)

        # callbacks
        self.btn_settings.clicked.connect(self.call_manage_settings.emit)
        self.chan_select.currentIndexChanged.connect(self.manage_feat_chan_select)
        self.feature_select.currentIndexChanged.connect(self.manage_feat_chan_select)
        self.sweep_control.clicked.connect(self.manage_sweep_control)
        self.range_edit.editingFinished.connect(self.manage_range_edit)

    def depth_process_btn_callback(self):
        # kill
        if self.depth_process_running:
            self.manage_depth_process(False)
            self.manage_nsp(False)
        else:
            # if we terminate and re-start the processes, we need to re-enable the shared memory
            self.depth_wrapper.manage_shared_memory()

            # re-send the settings
            self.depth_wrapper.send_settings(self.depth_settings)

            # start nsp recording
            if self.manage_nsp(True) == 0:
                # re-start the worker
                self.manage_depth_process(True)

    def features_process_btn_callback(self):
        # kill
        if self.features_process_running:
            self.manage_feature_process(False)
        else:
            # if we terminate and re-start the processes, we need to re-enable the shared memory
            self.features_wrapper.manage_shared_memory()

            # re-send the settings
            self.features_wrapper.send_settings(self.features_settings)

            # re-start the worker
            self.manage_feature_process(True)

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

    @staticmethod
    def parse_patient_name(full_name):
        # parse the subject information
        names = full_name.split(' ')
        m_name = ''
        m_idx = -1
        l_idx = -1
        for idx, n in enumerate(names):
            if all([x.isupper() for x in n]):
                m_idx = idx
                l_idx = idx + 1
                m_name = n
                break

        f_name = str.join(' ', names[:m_idx])
        l_name = str.join(' ', names[l_idx:])
        return f_name, m_name, l_name

    def manage_nsp(self, on_off):
        f_name, m_name, l_name = self.parse_patient_name(self.subject_settings['name'])
        file_info = {'filename': os.path.normpath(os.path.join(BASEPATH,
                                                  self.subject_settings['id'],
                                                  str(self.procedure_settings['date']) + '_' +
                                                  str(self.depth_settings['procedure_id']))),
                     'comment': self.subject_settings['NSP_comment'],
                     'patient_info': {'ID': self.subject_settings['id'],
                                      # if only single name, returned in l_name
                                      'firstname': f_name if f_name else l_name,
                                      'middlename': m_name,  # TODO: implement MiddleName
                                      'lastname': l_name,
                                      'DOBMonth': self.subject_settings['birthday'].month,
                                      'DOBDay': self.subject_settings['birthday'].day,
                                      'DOBYear': self.subject_settings['birthday'].year
                                      }}

        if not CbSdkConnection().is_connected:
            CbSdkConnection().connect()

        return CbSdkConnection().set_recording_state(on_off, file_info)

    def manage_depth_process(self, on_off):
        # start process
        if on_off and not self.depth_process_running:
            self.depth_wrapper.start_worker()
            self.depth_process_running = True
        else:
            self.depth_wrapper.kill_worker()
            self.depth_process_running = False

    def manage_feature_process(self, on_off):
        if on_off and not self.features_process_running:
            self.features_wrapper.start_worker()
            self.features_process_running = True
        else:
            self.features_wrapper.kill_worker()
            self.features_process_running = False

    def process_settings(self, sub_sett, proc_sett, depth_sett, feat_sett):
        self.subject_settings = dict(sub_sett)
        self.procedure_settings = dict(proc_sett)
        self.depth_settings = dict(depth_sett)
        self.features_settings = dict(feat_sett)

        # validate that we have some data in the electrode_settings. If the NSP is not connected we will have
        # to load the channel names from the DB. Also we want to keep the FeaturesGUI unaware of the DB channels.
        if len(self.depth_settings['electrode_settings']) == 0:
            self.depth_settings['electrode_settings'] = {}
            for lbl in DBWrapper().list_channel_labels():
                self.depth_settings['electrode_settings'][lbl] = DEPTHSETTINGS
            CbSdkConnection().is_simulating = True

        # set new features
        self.feature_select.setCurrentIndex(0)  # Raw
        while self.feature_select.count() > 1:
            self.feature_select.removeItem(1)
        self.feature_select.addItems(self.features_settings['features'].keys())

        # set new channels
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

        if not self.features_process_running:
            self.manage_feature_process(True)

        # self.clear()
        self.read_from_shared_memory()

    def create_plots(self, theme='dark', **kwargs):
        # Collect PlotWidget configuration
        self.plot_config['theme'] = theme
        self.plot_config['color_iterator'] = -1
        self.plot_config['x_range'] = XRANGE_FEATURES
        self.plot_config['y_range'] = uVRANGE
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
                    self.plot_stack.addWidget(RawPlots(dict(self.plot_config)))
                elif feat == 'DBS':
                    self.plot_stack.addWidget(DBSPlots(dict(self.plot_config)))
                elif feat == 'LFP':
                    self.plot_stack.addWidget(LFPPlots(dict(self.plot_config)))
                elif feat == 'Spikes':
                    self.plot_stack.addWidget(SpikePlots(dict(self.plot_config)))
                else:
                    self.plot_stack.addWidget(NullPlotWidget(dict(self.plot_config)))
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
        self.status_label.setPixmap(self.status_icons[output])

        if self.depth_wrapper.is_running():
            self.depth_process_btn.setStyleSheet("QPushButton { color: white; "
                                                 "background-color : green; "
                                                 "border-color : green; "
                                                 "border-width: 2px}")
        else:
            self.depth_process_running = False
            self.depth_process_btn.setStyleSheet("QPushButton { color: white; "
                                                 "background-color : red; "
                                                 "border-color : red; "
                                                 "border-width: 2px}")

        if self.features_wrapper.is_running():
            self.features_process_btn.setStyleSheet("QPushButton { color: white; "
                                                    "background-color : green; "
                                                    "border-color : green; "
                                                    "border-width: 2px}")
        else:
            self.features_process_running = False
            self.features_process_btn.setStyleSheet("QPushButton { color: white; "
                                                    "background-color : red; "
                                                    "border-color : red; "
                                                    "border-width: 2px}")

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
                self.plot_stack.currentWidget().update_plot(dict(all_data))
                self.stack_dict[curr_chan_lbl][curr_feat][1] = max(all_data.keys())

    def kill_processes(self):
        self.manage_depth_process(False)
        self.manage_feature_process(False)

    def read_from_shared_memory(self):
        if self.monitored_channel_mem.isAttached():
            self.monitored_channel_mem.lock()
            settings = np.frombuffer(self.monitored_channel_mem.data(), dtype=np.float)[-3:]
            self.chan_select.setCurrentIndex(int(settings[0]))
            self.range_edit.setText(str(settings[1]))
            self.manage_range_edit()
            self.do_hp.setChecked(bool(settings[2]))
            self.monitored_channel_mem.unlock()
        else:
            self.monitored_channel_mem.attach()
            self.sweep_control.setChecked(False)
            self.manage_sweep_control()


def main():
    _ = QApplication(sys.argv)
    window = FeaturesGUI()
    window.show()
    timer = QTimer()
    timer.timeout.connect(window.update)
    timer.start(100)

    if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()


if __name__ == '__main__':
    main()
