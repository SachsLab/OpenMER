from pathlib import Path
from qtpy import QtCore, QtWidgets, QtGui
from serf.tools.db_wrap import DBWrapper, ProcessWrapper
from ..settings import defaults, locate_ini
from .widgets.SettingsDialog import SettingsDialog


class ProcessGUI(QtWidgets.QMainWindow):

    def __init__(self, ini_file: str = None, **kwargs):
        super().__init__(**kwargs)
        self.status_icons = {
            k: QtGui.QPixmap(str(Path(__file__).parents[0] / 'resources' / 'icons' / (v + '.png'))) for k, v in
            ((-2, 'depth_status_delay'), (-1, 'depth_status_in_use'), (1, 'depth_status_done'), (0, 'depth_status_off'))
        }
        self._restore_from_settings(ini_file)
        self._setup_ui()
        self._setup_subproc()

        self._subject_settings = {}
        self._procedure_settings = {}
        self._buffer_settings = {}
        self._features_settings = {}

        self._do_modal_settings()

    def closeEvent(self, *args, **kwargs):
        self.run_record_process(False)
        self.run_feature_process(False)
        self._save_settings()

    def _restore_from_settings(self, ini_file=None):
        # Infer path to ini
        ini_name = ini_file if ini_file is not None else (type(self).__name__ + '.ini')
        self._settings_path = locate_ini(ini_name)
        settings = QtCore.QSettings(str(self._settings_path), QtCore.QSettings.IniFormat)
        default_dims = defaults.WINDOWDIMS_DICT[type(self).__name__]
        settings.beginGroup("MainWindow")
        self.move(settings.value("pos", QtCore.QPoint(default_dims[0], default_dims[1])))
        size_xy = settings.value("size", QtCore.QSize(default_dims[2], default_dims[3]))
        self.resize(size_xy)
        self.setMaximumWidth(size_xy.width())
        if settings.value("fullScreen", 'false') == 'true':
            self.showFullScreen()
        elif settings.value("maximized", 'false') == 'true':
            self.showMaximized()
        if settings.value("frameless", 'false') == 'true':
            self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        settings.endGroup()

        # TODO: Other settings

    def _save_settings(self):
        if self._settings_path.parents[0] == 'config' and self._settings_path.parents[1] == 'resources':
            # If this was loaded with the shipped settings, then write a new one in ~/.dbs_suite
            home_dir = Path(QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.HomeLocation))
            self._settings_path = home_dir / '.dbs_suite' / self._settings_path.name

        settings = QtCore.QSettings(str(self._settings_path), QtCore.QSettings.IniFormat)

        # Save MainWindow geometry.
        settings.beginGroup("MainWindow")
        settings.setValue("fullScreen", self.isFullScreen())
        settings.setValue("maximized", self.isMaximized())
        if not self.isFullScreen() and not self.isMaximized():
            settings.setValue("size", self.size())
            settings.setValue("pos", self.pos())
        settings.endGroup()

        # TODO: Save more settings.

        settings.sync()

    def _setup_ui(self):
        main_widget = QtWidgets.QWidget()
        main_widget.setLayout(QtWidgets.QVBoxLayout())
        self.setCentralWidget(main_widget)
        self._setup_control_panel()

    def _setup_control_panel(self):
        lo = QtWidgets.QHBoxLayout()
        # Settings button
        settings_pb = QtWidgets.QPushButton("Settings")
        settings_pb.setObjectName("Settings_PushButton")
        settings_pb.setMaximumWidth(50)
        settings_pb.clicked.connect(lambda state: self._do_modal_settings())
        lo.addWidget(settings_pb)
        # Features button
        lo.addSpacing(20)
        features_pb = QtWidgets.QPushButton("Features")
        features_pb.setObjectName("Features_PushButton")
        features_pb.setMaximumWidth(50)
        features_pb.clicked.connect(self._on_features_process_clicked)
        lo.addWidget(features_pb)
        # Record button
        lo.addSpacing(5)
        record_pb = QtWidgets.QPushButton("Record")
        record_pb.setObjectName("Record_PushButton")
        record_pb.setMaximumWidth(50)
        record_pb.clicked.connect(self._on_record_clicked)
        lo.addWidget(record_pb)
        # Status Label
        lo.addSpacing(20)
        status_label = QtWidgets.QLabel()
        status_label.setObjectName("Status_Label")
        status_label.setPixmap(self.status_icons[0])
        lo.addWidget(status_label)

        self.centralWidget().layout().addLayout(lo)

    def _setup_subproc(self):
        # Define and start processes
        # will only start processes when settings are received
        self._record_wrapper = ProcessWrapper('Depth_Process')
        self._record_process_running = False

        self._features_wrapper = ProcessWrapper('Features_Process')
        self._features_process_running = False

    def _do_modal_settings(self):
        win = SettingsDialog(self._subject_settings,
                             self._procedure_settings,
                             self._buffer_settings,
                             self._features_settings)
        result = win.exec_()
        if result == QtWidgets.QDialog.Accepted:
            win.update_settings()
        else:
            return False

    def _on_features_process_clicked(self):
        # kill
        if self._features_process_running:
            self.run_feature_process(False)
        else:
            # if we terminate and re-start the processes, we need to re-enable the shared memory
            self._features_wrapper.manage_shared_memory()

            # re-send the settings
            self._features_wrapper.send_settings(self.features_settings)

            # re-start the worker
            self.run_feature_process(True)

    def _on_record_clicked(self):
        # kill
        if self._record_wrapper.is_running():
            self.run_record_process(False)
            self._run_recording(False)
        else:
            # if we terminate and re-start the processes, we need to re-enable the shared memory
            self._record_wrapper.manage_shared_memory()

            # re-send the settings
            self._record_wrapper.send_settings(self.depth_settings)

            # start nsp recording
            if self._run_recording(True) == 0:
                # re-start the worker
                self.run_record_process(True)

    def run_record_process(self, on_off: bool):
        # start process
        if on_off and not self._record_wrapper.is_running():
            self._record_wrapper.start_worker()
        else:
            self._record_wrapper.kill_worker()

    def run_feature_process(self, on_off: bool):
        if on_off and not self._features_process_running:
            self._features_wrapper.start_worker()
            self._features_process_running = True
        else:
            self._features_wrapper.kill_worker()
            self._features_process_running = False

    def _run_recording(self, on_off: bool):
        # TODO: Use settings
        import os
        f_name, m_name, l_name = self.parse_patient_name(self.subject_settings['name'])
        file_info = {'filename': os.path.normpath(os.path.join(BASEPATH,
                                                  self.subject_settings['id'],
                                                  self.procedure_settings['date'].strftime('%m%d%y') + '_' +
                                                  self.subject_settings['id'] + '_' +
                                                  self.procedure_settings['target_name'] + '_' +
                                                  self.procedure_settings['recording_config'])),
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
        return self._data_source.set_recording_state(on_off, file_info)

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

    def update(self):
        status_label = self.findChild(QtWidgets.QLabel, "Status_Label")
        record_pb = self.findChild(QtWidgets.QPushButton, "Record_PushButton")
        features_pb = self.findChild(QtWidgets.QPushButton, "Features_PushButton")

        status_label.setPixmap(self.status_icons[self._record_wrapper.worker_status()])

        rec_facecolor = "green" if self._record_wrapper.is_running() else "red"
        record_pb.setStyleSheet("QPushButton { color: white; "
                                f"background-color : {rec_facecolor}; "
                                f"border-color : {rec_facecolor}; "
                                "border-width: 2px}")

        feat_facecolor = "green" if self._features_wrapper.is_running() else "red"
        features_pb.setStyleSheet("QPushButton { color: white; "
                                  f"background-color : {feat_facecolor}; "
                                  f"border-color : {feat_facecolor}; "
                                  "border-width: 2px}")
