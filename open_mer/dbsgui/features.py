import json
from pathlib import Path

import zmq
from qtpy import QtCore, QtWidgets, QtGui
from serf.tools.db_wrap import DBWrapper, ProcessWrapper
from ..settings import defaults, locate_ini, parse_ini_try_numeric
from ..feature_plots import *


class FeaturesGUI(QtWidgets.QMainWindow):
    status_icons = {
        k: Path(__file__).parents[0] / 'resources' / 'icons' / (v + '.png') for k, v in
        ((-2, 'depth_status_delay'), (-1, 'depth_status_in_use'), (1, 'depth_status_done'), (0, 'depth_status_off'))
    }

    def __init__(self, ini_file: str = None, **kwargs):
        """
        - Visualizes raw segments and calculated features from the database
        - Widgets to navigate the visualizations
        - Subscribes to zmq messages to know which features to grab
        - Subscribes to zmq messages to know which channels to show
        - For semi-realtime application, you should be running Depth_Process and Features_Process (from serf package)
          in background.

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
        self._chan_labels = set([])
        
        self._db = DBWrapper()
        # TODO: Load ports from ini file
        self._zmq_ctrl_port = 60001
        self._zmq_chan_port = 60003
        self._zmq_feat_port = 60004
        self._restore_from_settings(ini_file)

        self._setup_pubsub()
        self._setup_ui()
        self._features_sock.send_string("features refresh")

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
        self.setMaximumWidth(size_xy.width())
        if settings.value("fullScreen", 'false') == 'true':
            self.showFullScreen()
        elif settings.value("maximized", 'false') == 'true':
            self.showMaximized()
        if settings.value("frameless", 'false') == 'true':
            self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        settings.endGroup()

        settings.beginGroup("plot")
        self._plot_settings['x_start'] = int(settings.value("x_start", -4000))
        self._plot_settings['x_stop'] = int(settings.value("x_stop", 120000))
        self._plot_settings['y_range'] = int(settings.value("y_range", 250))
        settings.endGroup()

        settings.beginGroup("features")
        add_features = []
        for feat_grp in settings.childKeys():
            b_add = settings.value(feat_grp, True, type=bool)
            if b_add:
                add_features.append(feat_grp)
        self._features_settings["features"] = add_features
        settings.endGroup()

        settings.beginGroup("buffer")
        self._plot_settings["highpass"] = settings.value("highpass", "true") == "true"
        # chk_threshold
        settings.endGroup()

        self._plot_settings["color_iterator"] = -1
        self._plot_settings["image_plot"] = False
        # theme
        settings.beginGroup("theme")
        self._plot_settings["theme"] = {}
        for k in settings.allKeys():
            if k == 'colormap' or k.lower().startswith('pencolors'):
                continue
            self._plot_settings["theme"][k] = parse_ini_try_numeric(settings, k)
        # theme > pencolors
        self._plot_settings["theme"]['colormap'] = settings.value('colormap', 'custom')
        if self._plot_settings["theme"]['colormap'] == "custom":
            pencolors = []
            settings.beginGroup("pencolors")
            for c_id in settings.childGroups():
                settings.beginGroup(c_id)
                cname = settings.value("name", None)
                if cname is not None:
                    cvalue = QtGui.QColor(cname)
                else:
                    cvalue = settings.value("value", "#ffffff")
                pencolors.append(cvalue)
                settings.endGroup()
            settings.endGroup()  # pencolors
            self._plot_settings["theme"]["pencolors"] = pencolors
        settings.endGroup()  # end theme

    def _setup_pubsub(self):
        context = zmq.Context()

        # Subscribe to channel-change notifications
        self._chan_sock = context.socket(zmq.SUB)
        self._chan_sock.connect(f"tcp://localhost:{self._zmq_chan_port}")
        self._chan_sock.setsockopt_string(zmq.SUBSCRIBE, "channel_select")

        # Subscribe to procedure set notifications -- react to procedure id
        self._procedure_sock = context.socket(zmq.SUB)
        self._procedure_sock.connect(f"tcp://localhost:{self._zmq_ctrl_port}")
        self._procedure_sock.setsockopt_string(zmq.SUBSCRIBE, "procedure_settings")

        # Publish refresh notification -- on startup and when refresh is clicked
        self._features_sock = context.socket(zmq.PUB)
        self._features_sock.bind(f"tcp://*:{self._zmq_feat_port}")

    def _setup_ui(self):
        main_widget = QtWidgets.QWidget(self)
        main_widget.setLayout(QtWidgets.QVBoxLayout())
        self.setCentralWidget(main_widget)

        self._setup_control_panel()
        self._reset_widget_stack()

    def _setup_control_panel(self):
        # Top row
        lo_L1 = QtWidgets.QHBoxLayout()
        # Channel select
        lo_L1.addWidget(QtWidgets.QLabel("Electrode: ", alignment=QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight))
        chan_select_cb = QtWidgets.QComboBox(self.centralWidget())
        chan_select_cb.setObjectName("ChanSelect_ComboBox")
        chan_select_cb.setMinimumWidth(70)
        chan_select_cb.setEnabled(False)
        chan_select_cb.currentIndexChanged.connect(lambda idx: self.reset_stack())
        self._reset_chan_select_items()
        lo_L1.addWidget(chan_select_cb)
        # Feature select
        lo_L1.addSpacing(20)
        lo_L1.addWidget(QtWidgets.QLabel("Feature set: ", alignment=QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight))
        feat_select_cb = QtWidgets.QComboBox(self.centralWidget())
        feat_select_cb.setObjectName("FeatureSelect_ComboBox")
        feat_select_cb.setMinimumWidth(60)
        self._reset_feat_select_items()
        feat_select_cb.currentIndexChanged.connect(lambda idx: self.reset_stack())
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
        hp_chk.setChecked(self._plot_settings["highpass"])
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
        feat_combo.blockSignals(True)
        feat_combo.clear()
        feat_combo.addItems(self._features_settings['features'])
        feat_combo.blockSignals(False)
        feat_combo.setCurrentIndex(0)

    def _reset_chan_select_items(self):
        chan_combo = self.findChild(QtWidgets.QComboBox, "ChanSelect_ComboBox")
        chan_combo.blockSignals(True)
        chan_combo.clear()
        chan_combo.addItem("None")
        chan_combo.addItems(self._chan_labels)
        chan_combo.blockSignals(False)
        chan_combo.setCurrentIndex(0)  # Triggers an emission --> reset_stack

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
        my_theme = self._plot_settings["theme"]
        for chan_ix, chan_label in enumerate({"None"}.union(self._chan_labels)):
            self._plot_settings["color_iterator"] = (self._plot_settings["color_iterator"] + 1) % len(my_theme['pencolors'])
            self._widget_stack[chan_label] = {}
            for feat_ix, feat_label in enumerate(self._features_settings["features"]):
                self._widget_stack[chan_label][feat_label] = [n_feats*chan_ix + feat_ix, 0]
                w_cls = plot_class_map[feat_label] if feat_label in plot_class_map else NullPlotWidget
                plot_stack.addWidget(w_cls(dict(self._plot_settings)))
        plot_stack.setCurrentIndex(0)

    def reset_stack(self):
        plot_stack = self.findChild(QtWidgets.QStackedWidget, "Plot_Stack")
        chan_combo = self.findChild(QtWidgets.QComboBox, "ChanSelect_ComboBox")
        feat_combo = self.findChild(QtWidgets.QComboBox, "FeatureSelect_ComboBox")
        if plot_stack is not None and chan_combo is not None and feat_combo is not None:
            chan_key = chan_combo.currentText()
            feat_key = feat_combo.currentText()
            idx = self._widget_stack[chan_key][feat_key][0]
            plot_stack.setCurrentIndex(idx)

    def handle_procedure_id(self, procedure_id):
        self._db.select_procedure(procedure_id)
        self._chan_labels = self._db.list_channel_labels()
        self._reset_chan_select_items()
        self._reset_widget_stack()

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
        b_enable = not sweep_control.isChecked()
        for _ in [chan_combo, hp_chk, range_edit]:
            _.setEnabled(b_enable)

    def on_refresh_clicked(self):
        self._features_sock.send_string("features refresh")

    def _check_subs(self):
        try:
            received_msg = self._chan_sock.recv_string(flags=zmq.NOBLOCK)[len("channel_select") + 1:]
            chan_settings = json.loads(received_msg)
            # ^ dict with k,v_type "channel":int, "range":[float, float], "highpass":bool
            # TODO: chan_combo set new idx
        except zmq.ZMQError:
            pass

        try:
            received_msg = self._procedure_sock.recv_string(flags=zmq.NOBLOCK)[len("procedure_settings") + 1:]
            procedure_settings = json.loads(received_msg)
            # ^ dict with settings for "procedure", "subject"
            if "procedure" in procedure_settings and "procedure_id" in procedure_settings["procedure"]:
                self.handle_procedure_id(procedure_settings["procedure"]["procedure_id"])
        except zmq.ZMQError:
            pass

    def update(self):
        plot_stack = self.findChild(QtWidgets.QStackedWidget, "Plot_Stack")
        chan_combo = self.findChild(QtWidgets.QComboBox, "ChanSelect_ComboBox")
        feat_combo = self.findChild(QtWidgets.QComboBox, "FeatureSelect_ComboBox")
        b_sweep_sync = self.findChild(QtWidgets.QCheckBox, "Sweep_CheckBox").isChecked()

        self._check_subs()

        curr_chan_lbl = chan_combo.currentText()
        curr_widget = plot_stack.currentWidget()
        if curr_chan_lbl != 'None':
            curr_feat = feat_combo.currentText()
            stack_item = self._widget_stack[curr_chan_lbl][curr_feat]
            do_hp = self._plot_settings["highpass"]
            y_range = self._plot_settings["y_range"]

            # If widget values don't match stored values
            if y_range != curr_widget.plot_config['y_range']\
                or do_hp != curr_widget.plot_config['highpass']:
                # Clear plots and update widgets with stored settings
                curr_widget.clear_plot()
                stack_item[1] = 0
                curr_widget.plot_config['highpass'] = do_hp
                curr_widget.plot_config['y_range'] = y_range

            curr_datum = stack_item[1]
            if curr_feat == 'Raw':
                all_data = self._db.load_depth_data(chan_lbl=curr_chan_lbl,
                                                    gt=curr_datum,
                                                    do_hp=do_hp,
                                                    return_uV=True)
            elif curr_feat == 'Mapping':
                all_data = self._db.load_mapping_response(chan_lbl=curr_chan_lbl,
                                                          gt=curr_datum)
            else:
                all_data = self._db.load_features_data(category=curr_feat,
                                                       chan_lbl=curr_chan_lbl,
                                                       gt=curr_datum)
            if all_data:
                plot_stack.currentWidget().update_plot(dict(all_data))
                stack_item[1] = max(all_data.keys())
