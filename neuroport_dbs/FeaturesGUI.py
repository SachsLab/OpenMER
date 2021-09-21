import sys
import argparse
from pathlib import Path
from qtpy import QtCore, QtGui, QtWidgets
from neuroport_dbs.settings import defaults, parse_ini_try_numeric, locate_ini
from neuroport_dbs.SettingsDialog import SettingsDialog
from serf.tools.db_wrap import DBWrapper, ProcessWrapper
from neuroport_dbs.feature_plots import *


class FeaturesGUI(QtWidgets.QMainWindow):
    status_icons = {
        k: Path(__file__).parents[0] / 'resources' / 'icons' / (v + '.png') for k, v in
        ((-2, 'depth_status_delay'), (-1, 'depth_status_in_use'), (1, 'depth_status_done'), (0, 'depth_status_off'))
    }

    def __init__(self, ini_file: str = None, **kwargs):
        """
        FeaturesGUI is the most complicated of all applications in this package.
        - Has a GUI to configure many different settings.
        - Sets up a sub-process (Depth_Process in serf package) to capture data from Central and store in the database
        - Sets up a sub-process (Features_Process in serf package) to compute features on new entries in the database
        - Visualizes raw segments and features from the database
        Args:
            ini_file:
            **kwargs:
        """
        super().__init__(**kwargs)

        self._plot_settings = {}
        self._subject_settings = {}
        self._procedure_settings = {}
        self._buffer_settings = {}
        self._features_settings = {}

        self._restore_from_settings(ini_file)
        self._setup_ui()
        self._setup_shmem()

    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)

    def _restore_from_settings(self, ini_file=None):
        ini_name = ini_file if ini_file is not None else (type(self).__name__ + '.ini')
        settings_path = locate_ini(ini_name)
        settings = QtCore.QSettings(str(settings_path), QtCore.QSettings.IniFormat)
        default_dims = defaults.WINDOWDIMS_DICT[type(self).__name__]
        settings.beginGroup("MainWindow")
        self.move(settings.value("pos", QtCore.QPoint(default_dims[0], default_dims[1])))
        size_xy = settings.value("size", QtCore.QSize(default_dims[2], default_dims[3]))
        self.resize(size_xy)
        self.setMaximumWidth(size_xy[0])
        if settings.value("fullScreen", 'false') == 'true':
            self.showFullScreen()
        elif settings.value("maximized", 'false') == 'true':
            self.showMaximized()
        if settings.value("frameless", 'false') == 'true':
            self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        settings.endGroup()

        # TODO: Other settings
        # theme
        # x_start
        # x_stop
        # y_range
        # do_hp
        # buffer_length  <-- Depth buffer duration (s)
        # sample_length  <-- Depth sample size (s)
        # delay_buffer   <-- Delay depth recording (s)
        # overwrite_depth <- Overwrite depth values
        # electrode_settings
        # chk_threshold

        # self._plot_settings['theme'] = theme
        # self._plot_settings['color_iterator'] = -1
        # self._plot_settings['x_start'] = plot.get('x_start', -4000)
        # self._plot_settings['x_stop'] = plot.get('x_stop', 120000)
        # self._plot_settings['y_range'] = plot.get('y_range', 250)
        # self._plot_settings['do_hp'] = True

    def _setup_ui(self):
        main_widget = QtWidgets.QWidget()
        main_widget.setLayout(QtWidgets.QVBoxLayout())
        self.setCentralWidget(main_widget)

        self._setup_control_panel()
        self._reset_widget_stack()

    def _setup_control_panel(self):
        # Top row
        lo_L1 = QtWidgets.QHBoxLayout()
        # Channel select
        lo_L1.addWidget(QtWidgets.QLabel("Electrode: ", alignment=QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight))
        chan_select_cb = QtWidgets.QComboBox()
        chan_select_cb.setObjectName("ChanSelect_ComboBox")
        chan_select_cb.setMinimumWidth(70)
        chan_select_cb.setEnabled(False)
        self._reset_chan_select_items()
        lo_L1.addWidget(chan_select_cb)
        # Feature select
        lo_L1.addSpacing(20)
        lo_L1.addWidget(QtWidgets.QLabel("Feature set: ", alignment=QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight))
        feat_select_cb = QtWidgets.QComboBox()
        feat_select_cb.setObjectName("FeatureSelect_ComboBox")
        feat_select_cb.setMinimumWidth(60)
        self._reset_feat_select_items()
        lo_L1.addWidget(feat_select_cb)

        # Second row
        lo_L2 = QtWidgets.QHBoxLayout()
        lo_L2.addSpacing(10)
        # Range Edit
        lo_L2.addWidget(QtWidgets.QLabel("+/- ", alignment=QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight))
        range_edit = QtWidgets.QLineEdit("{:.2f}".format(self._plot_settings['y_range']))
        range_edit.setObjectName("Range_LineEdit")
        range_edit.setMaximumWidth(50)
        range_edit.editingFinished.connect(self.on_range_edited)
        lo_L2.addWidget(range_edit)
        # HP
        lo_L2.addSpacing(30)
        hp_chk = QtWidgets.QCheckBox("HP")
        hp_chk.setObjectName("HP_CheckBox")
        hp_chk.setChecked(self._plot_settings['hp'])
        lo_L2.addWidget(hp_chk)
        # Match Sweep
        lo_L2.addSpacing(30)
        sweep_chk = QtWidgets.QCheckBox("Match SweepGUI")
        sweep_chk.setObjectName("Sweep_CheckBox")
        sweep_chk.setChecked(True)
        sweep_chk.setEnabled(True)
        sweep_chk.clicked.connect(self.on_sweep_clicked)
        lo_L2.addWidget(sweep_chk)

        lo_R = QtWidgets.QHBoxLayout()
        # Refresh button
        refresh_pb = QtWidgets.QPushButton("Refresh")
        refresh_pb.setObjectName("Refresh_PushButton")
        refresh_pb.setMaximumWidth(50)
        refresh_pb.clicked.connect(self.on_refresh_clicked)
        lo_R.addWidget(refresh_pb)
        lo_R.addSpacing(10)

        lo_L = QtWidgets.QVBoxLayout()
        lo_L.addLayout(lo_L1)
        lo_L.addSpacing(5)
        lo_L.addLayout(lo_L2)

        lo = QtWidgets.QHBoxLayout()
        lo.addLayout(lo_L)
        lo.addStretch()
        lo.addLayout(lo_R)
        self.centralWidget().layout().addLayout(lo)

    def _reset_feat_select_items(self):
        feat_combo = self.findChild(QtWidgets.QComboBox, "FeatureSelect_ComboBox")
        feat_combo.disconnect()
        feat_combo.clear()
        feat_combo.addItems(["Raw", "Mapping"])  # TODO: Put these in features_settings
        # TODO: feat_combo.addItems(self._features_settings['features'].keys())
        feat_combo.currentIndexChanged.connect(lambda idx: self.reset_stack())
        feat_combo.setCurrentIndex(0)

    def _reset_chan_select_items(self):
        chan_combo = self.findChild(QtWidgets.QComboBox, "ChanSelect_ComboBox")
        chan_combo.disconnect()
        chan_combo.clear()
        chan_combo.addItem("None")
        # TODO: chan_combo.addItems(self._depth_settings['electrode_settings'].keys())
        chan_combo.currentIndexChanged.connect(lambda idx: self.reset_stack())
        chan_combo.setCurrentIndex(0)

    def _reset_widget_stack(self):
        plot_stack = self.findChild(QtWidgets.QStackedWidget, "Plot_Stack")
        if plot_stack is None:
            plot_stack = QtWidgets.QStackedWidget()
            plot_stack.setObjectName("Plot_Stack")
            self.centralWidget().layout().addWidget(plot_stack)

        to_delete = [plot_stack.widget(_) for _ in range(plot_stack.count())]
        for wid in to_delete:
            plot_stack.removeWidget(wid)
            wid.deleteLater()

        self._widget_stack = {}
        plot_class_map = {
            'Raw': RawPlots, 'Mapping': MappingPlots, 'STN': STNPlots, 'LFP': LFPPlots, 'Spikes': SpikePlots,
            None: NullPlotWidget
        }
        n_feats = len(self._features_settings['features'])
        for chan_ix, chan_label in enumerate(["None"] + list(self._depth_settings['electrode_settings'].keys())):
            self._widget_stack[chan_label] = {}
            for feat_ix, feat_label in enumerate(self._features_settings['features'].keys()):
                self._widget_stack[chan_label][feat_label] = [n_feats*chan_ix + feat_ix, 0]
                w_cls = plot_class_map[feat_label] if feat_label in plot_class_map else NullPlotWidget
                plot_stack.addWidget(w_cls)(dict(self.plot_config))
        plot_stack.setCurrentIndex(0)

    def _setup_shmem(self):
        # shared memory to display the currently monitored electrode
        self.monitored_channel_mem = QtCore.QSharedMemory()
        self.monitored_channel_mem.setKey("MonitoredChannelMemory")
        self.monitored_channel_mem.attach(QtCore.QSharedMemory.ReadOnly)

    def manage_depth_process(self, on_off):
        # start process
        if on_off and not self._depth_process_running:
            self._depth_wrapper.start_worker()
            self._depth_process_running = True
        else:
            self._depth_wrapper.kill_worker()
            self._depth_process_running = False

    def manage_feature_process(self, on_off):
        if on_off and not self._features_process_running:
            self._features_wrapper.start_worker()
            self._features_process_running = True
        else:
            self._features_wrapper.kill_worker()
            self._features_process_running = False

    def reset_stack(self):
        plot_stack = self.findChild(QtWidgets.QStackedWidget, "Plot_Stack")
        chan_combo = self.findChild(QtWidgets.QComboBox, "ChanSelect_ComboBox")
        feat_combo = self.findChild(QtWidgets.QComboBox, "FeatureSelect_ComboBox")
        if plot_stack is not None and chan_combo is not None and feat_combo is not None:
            plot_stack.setCurrentIndex(self._widget_stack[chan_combo.currentText()][feat_combo.currentText()][0])

    def manage_refresh(self):
        plot_stack = self.findChild(QtWidgets.QStackedWidget, "Plot_Stack")
        chan_combo = self.findChild(QtWidgets.QComboBox, "ChanSelect_ComboBox")
        feat_combo = self.findChild(QtWidgets.QComboBox, "FeatureSelect_ComboBox")
        stack_item = self._widget_stack[chan_combo.currentText()][feat_combo.currentText()]
        plot_stack.widget(stack_item[0]).clear_plot()
        stack_item[1] = 0

    def on_range_edited(self):
        range_edit = self.findChild(QtWidgets.QLineEdit, "Range_LineEdit")
        self._plot_settings["y_range"] = float(range_edit.text())

    def on_sweep_clicked(self):
        sweep_control = self.findChild(QtWidgets.QCheckBox, "Sweep_CheckBox")
        chan_combo = self.findChild(QtWidgets.QComboBox, "ChanSelect_ComboBox")
        hp_chk = self.findChild(QtWidgets.QCheckBox, "HP_CheckBox")
        range_edit = self.findChild(QtWidgets.QLineEdit, "Range_LineEdit")
        for _ in [chan_combo, hp_chk, range_edit]:
            _.setEnabled(sweep_control.isChecked() and self.monitored_channel_mem.isAttached())
        if sweep_control.isChecked() and self.monitored_channel_mem.isAttached():
            self.read_from_shared_memory()

    def on_record_clicked(self):
        # kill
        if self._depth_process_running:
            self.manage_depth_process(False)
            self.manage_nsp(False)
        else:
            # if we terminate and re-start the processes, we need to re-enable the shared memory
            self._depth_wrapper.manage_shared_memory()

            # re-send the settings
            self._depth_wrapper.send_settings(self.depth_settings)

            # start nsp recording
            if self.manage_nsp(True) == 0:
                # re-start the worker
                self.manage_depth_process(True)

    def on_features_process_clicked(self):
        # kill
        if self._features_process_running:
            self.manage_feature_process(False)
        else:
            # if we terminate and re-start the processes, we need to re-enable the shared memory
            self._features_wrapper.manage_shared_memory()

            # re-send the settings
            self._features_wrapper.send_settings(self.features_settings)

            # re-start the worker
            self.manage_feature_process(True)

    def read_from_shared_memory(self):
        import numpy as np
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
            # self.sweep_control.setChecked(False)
            self.manage_sweep_control()


def main(**kwargs):
    app = QtWidgets.QApplication(sys.argv)
    window = FeaturesGUI(**kwargs)
    window.show()
    timer = QtCore.QTimer()
    timer.timeout.connect(window.update)
    timer.start(100)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        sys.exit(app.exec_())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="FeaturesGUI",
                                     description="Visualize MER trajectory segments and features.")
    parser.add_argument('-i', '--ini_file', nargs='?', help="Path to ini settings file.")
    args = parser.parse_args()
    main(**args.__dict__)
