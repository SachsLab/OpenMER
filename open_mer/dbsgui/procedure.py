from pathlib import Path
from typing import Optional
import time
import json
import zmq
from qtpy import QtCore, QtWidgets, QtGui
from serf.tools.db_wrap import DBWrapper
from ..settings import defaults, locate_ini
from .widgets.SettingsDialog import SettingsDialog
import open_mer.data_source


class ProcedureGUI(QtWidgets.QMainWindow):

    def __init__(self, ini_file: str = None, **kwargs):
        super().__init__(**kwargs)
        self.status_icons = {
            k: QtGui.QPixmap(str(Path(__file__).parents[0] / 'resources' / 'icons' / (v + '.png'))) for k, v in
            {"accumulating": "depth_status_delay", "recording": "depth_status_in_use", "done": "depth_status_done", "notrecording": "depth_status_off"}.items()
        }
        self._b_recording = False
        self._data_source = None
        self._restore_from_settings(ini_file)
        self._setup_ui()
        self._setup_pubsub()

        self._subject_settings = {}
        self._procedure_settings = {}
        self._buffer_settings = {}
        self._features_settings = {}

        self._do_modal_settings()

    def closeEvent(self, *args, **kwargs):
        self.toggle_recording(False)

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

        # Infer data source from ini file, setup data source
        settings.beginGroup("data-source")
        src_cls = getattr(open_mer.data_source, settings.value("class"))
        # Get the _data_source. Note this might trigger on_source_connected before child
        #  finishes parsing settings.
        self._data_source = src_cls(scoped_settings=settings)
        self._recording_path = settings.value("basepath", defaults.BASEPATH, type=str)
        settings.endGroup()

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
        # Record button
        lo.addSpacing(5)
        record_pb = QtWidgets.QPushButton("Record")
        record_pb.setObjectName("Record_PushButton")
        record_pb.setMaximumWidth(50)
        record_pb.clicked.connect(lambda: self.toggle_recording(None))
        lo.addWidget(record_pb)
        # Status Label
        lo.addSpacing(20)
        status_label = QtWidgets.QLabel()
        status_label.setObjectName("Status_Label")
        status_label.setPixmap(self.status_icons["notrecording"])
        lo.addWidget(status_label)

        self.centralWidget().layout().addLayout(lo)

    def _setup_pubsub(self, zmq_ctrl_port=60001, zmq_depth_port=60002, zmq_feat_port=60004):
        context = zmq.Context()

        self._depth_sock = context.socket(zmq.SUB)
        self._depth_sock.connect(f"tcp://localhost:{zmq_depth_port}")
        self._depth_sock.setsockopt_string(zmq.SUBSCRIBE, "snippet_status")

        self._features_sock = context.socket(zmq.SUB)
        self._features_sock.connect(f"tcp://localhost:{zmq_feat_port}")
        self._features_sock.setsockopt_string(zmq.SUBSCRIBE, "features")

        self._procedure_sock = context.socket(zmq.PUB)
        self._procedure_sock.bind(f"tcp://*:{zmq_ctrl_port}")

    def _publish_settings(self):
        # Sanitize some settings for serialization.
        _proc_settings = {}
        for k, v in self._procedure_settings.items():
            if hasattr(v, "isoformat"):
                _proc_settings[k] = v.isoformat()
            elif hasattr(v, "tolist"):
                _proc_settings[k] = v.tolist()
            else:
                _proc_settings[k] = v

        send_dict = {
            "features": self._features_settings,
            "procedure": _proc_settings,
            "buffer": self._buffer_settings,
            "subject": {**self._subject_settings, "birthday": self._subject_settings["birthday"].isoformat()}
        }
        # TODO: features and buffer settings should just be in ini files. They don't change frequently.
        self._procedure_sock.send_string("procedure_settings " + json.dumps(send_dict))

    def _do_modal_settings(self):
        win = SettingsDialog(self._subject_settings,
                             self._procedure_settings,
                             # self._buffer_settings,
                             # self._features_settings
                             )
        result = win.exec_()
        if result == QtWidgets.QDialog.Accepted:
            win.update_settings()

            # Create or load subject
            # Returns subject_id/-1 whether subject is properly created or not
            sub_id = DBWrapper().load_or_create_subject(self._subject_settings)

            if sub_id == -1:
                print("Subject not created.")
                return False
            else:
                self._subject_settings['subject_id'] = sub_id
                self._procedure_settings['subject_id'] = sub_id
                tmp = DBWrapper()
                proc_id = tmp.load_or_create_procedure(self._procedure_settings)
                self._procedure_settings["procedure_id"] = proc_id

            self._publish_settings()
        else:
            return False

    def toggle_recording(self, on_off: Optional[bool] = None):
        on_off = on_off if on_off is not None else not self._b_recording
        if on_off:
            if self._b_recording:
                # Wants on but already recording. Stop then start again.
                self.toggle_recording(False)
                time.sleep(0.100)
            self._publish_settings()  # re-send the settings
            # start nsp recording
            self._run_recording(True)
        else:
            self._run_recording(False)

    def _run_recording(self, on_off: bool):
        # TODO: Use settings
        import os
        f_name, m_name, l_name = self.parse_patient_name(self._subject_settings['name'])
        file_info = {'filename': os.path.normpath(os.path.join(self._recording_path,
                                                  self._subject_settings['id'],
                                                  self._procedure_settings['date'].strftime('%m%d%y') + '_' +
                                                  self._subject_settings['id'] + '_' +
                                                  self._procedure_settings['target_name'] + '_' +
                                                  self._procedure_settings['recording_config'])),
                     'comment': self._subject_settings['NSP_comment'],
                     'patient_info': {'ID': self._subject_settings['id'],
                                      # if only single name, returned in l_name
                                      'firstname': f_name if f_name else l_name,
                                      'middlename': m_name,  # TODO: implement MiddleName
                                      'lastname': l_name,
                                      'DOBMonth': self._subject_settings['birthday'].month,
                                      'DOBDay': self._subject_settings['birthday'].day,
                                      'DOBYear': self._subject_settings['birthday'].year
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
        b_publish_settings = False
        try:
            received_msg = self._features_sock.recv_string(flags=zmq.NOBLOCK)[len("features") + 1:]
            b_publish_settings |= received_msg == "refresh"
        except zmq.ZMQError:
            pass

        try:
            # Check for an update from the depth process
            received_msg = self._depth_sock.recv_string(flags=zmq.NOBLOCK)[len("snippet_status")+1:]

            # Depth processor has (re)started since we last published our settings. Publish again.
            b_publish_settings |= received_msg == "startup"

            # Update the status.  TODO: Remove this or get the old code from FeaturesGUI.
            status_label = self.findChild(QtWidgets.QLabel, "Status_Label")
            status_label.setPixmap(self.status_icons[received_msg])
            
            # Change the color of the recording button.
            record_pb = self.findChild(QtWidgets.QPushButton, "Record_PushButton")
            rec_facecolor_map = {
                "startup": "orange",
                "notrecording": "gray",
                "recording": "red",
                "accumulating": "yellow",
                "done": "blue"
            }
            if received_msg in rec_facecolor_map:
                rec_facecolor = rec_facecolor_map[received_msg]
            else:
                rec_facecolor = "gray"
            record_pb.setStyleSheet("QPushButton { color: white; "
                                    f"background-color : {rec_facecolor}; "
                                    f"border-color : {rec_facecolor}; "
                                    "border-width: 2px}")
        except zmq.ZMQError:
            pass

        if b_publish_settings:
            self._publish_settings()
