import os
import sys
import numpy as np
import qtpy.QtCore
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QComboBox, QLineEdit, QLabel, QDialog, QPushButton, \
                           QCheckBox, QHBoxLayout, QStackedWidget, QAction
from qtpy.QtCore import QSharedMemory, Signal
from qtpy.QtGui import QPixmap

from cerebuswrapper import CbSdkConnection

# Note: If import dbsgui fails, then set the working directory to be this script's directory.
from neuroport_dbs.dbsgui.my_widgets.custom import CustomGUI, CustomWidget, SAMPLINGGROUPS, THEMES
from neuroport_dbs.feature_plots import *
from neuroport_dbs.SettingsDialog import SettingsDialog

from serf.tools.db_wrap import DBWrapper, ProcessWrapper


WINDOWDIMS = [1260, 250, 660, 830]

XRANGE = [-3500, 120000]  # 3500?, don't know why -1500 is not working anymore...
YRANGE = 200.00
DEPTHRANGE = [-20, 5]

# TODO: ini file?
# Default settings. If finds a category of features with the same name, will apply the value here.
DEPTHSETTINGS = {'threshold': True,
                 'validity': 90.0}


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
        self.group_info = self.cbsdk_conn.get_group_config(SAMPLINGGROUPS.index("30000"))

        # we only need to set the default values for the depth buffer here since it requires electrode
        # information. The rest accepts empty dicts
        self.buffer_settings['buffer_length'] = '6.000'
        self.buffer_settings['sample_length'] = '4.000'
        self.buffer_settings['run_buffer'] = False
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
        self.status_off = QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_off.png'))
        self.status_done = QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_done.png'))
        self.status_in_use = QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'depth_status_in_use.png'))

        # Settings
        self.subject_settings = None
        self.procedure_settings = None
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
        self.feature_select.setMinimumWidth(60)
        self.feature_select.addItem('Raw')
        # self.feature_select.addItems(self.feature_categories)
        self.feature_select.setCurrentIndex(0)
        layout.addWidget(self.feature_select)

        layout.addSpacing(10)

        layout.addWidget(QLabel("Electrode: "))
        self.chan_select = QComboBox()
        self.chan_select.addItem("None")

        self.chan_select.setMinimumWidth(75)
        self.chan_select.setEnabled(False)
        layout.addWidget(self.chan_select)

        layout.addSpacing(10)

        layout.addWidget(QLabel("+/-"))
        self.range_edit = QLineEdit("{:.2f}".format(YRANGE))
        self.range_edit.setMaximumWidth(50)
        layout.addWidget(self.range_edit)

        layout.addSpacing(10)

        self.do_hp = QCheckBox('HP')
        self.do_hp.setChecked(True)
        layout.addWidget(self.do_hp)

        layout.addSpacing(10)

        self.sweep_control = QCheckBox("Match SweepGUI.")
        self.sweep_control.setChecked(True)
        self.sweep_control.setEnabled(self.monitored_channel_mem.isAttached())
        layout.addWidget(self.sweep_control)

        # layout.addStretch()
        layout.addSpacing(10)

        self.btn_settings = QPushButton("Settings")
        layout.addWidget(self.btn_settings)

        layout.addSpacing(10)

        self.depth_process_btn = QPushButton('B')
        self.depth_process_btn.setMaximumWidth(15)
        self.depth_process_btn.setStyleSheet("QPushButton { color: white; "
                                             "background-color : red; "
                                             "border-color : red; "
                                             "border-width: 2px}")
        self.depth_process_btn.clicked.connect(self.depth_process_btn_callback)
        layout.addWidget(self.depth_process_btn)

        self.features_process_btn = QPushButton('F')
        self.features_process_btn.setMaximumWidth(15)
        self.features_process_btn.setStyleSheet("QPushButton { color: white; "
                                                "background-color : red; "
                                                "border-color : red; "
                                                "border-width: 2px}")
        self.features_process_btn.clicked.connect(self.features_process_btn_callback)
        layout.addWidget(self.features_process_btn)

        layout.addSpacing(10)

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

    def depth_process_btn_callback(self):
        # kill
        if self.depth_process_running:
            self.manage_depth_process(False)
        else:
            # if we terminate and re-start the processes, we need to re-enable the shared memory
            self.depth_wrapper.manage_shared_memory()

            # re-send the settings
            self.depth_wrapper.send_settings(self.depth_settings)

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
        if output == -1:
            self.status_label.setPixmap(self.status_in_use)
        elif output == 1:
            self.status_label.setPixmap(self.status_done)
        else:
            self.status_label.setPixmap(self.status_off)

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
