from qtpy import QtCore, QtWidgets
from pathlib import Path
import pylsl
from ..settings import defaults
from ..depth_source import CBSDKPlayback
try:
    from cerebuswrapper import CbSdkConnection
except ModuleNotFoundError as e:
    print(e, "Try `pip install git+https://github.com/SachsLab/cerebuswrapper.git`.")

import open_mer.depth_source


class DepthGUI(QtWidgets.QMainWindow):

    def __init__(self, ini_file=None):
        super().__init__()

        # Infer path to ini
        ini_name = ini_file if ini_file is not None else (type(self).__name__ + '.ini')
        ini_path = Path(ini_name)
        if ini_path.exists():
            self._settings_path = ini_path
        else:
            # Try home / .open_mer first
            home_dir = Path(QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.HomeLocation))
            ini_path = home_dir / '.open_mer' / ini_path.name
            if ini_path.exists():
                self._settings_path = ini_path
            else:
                # Use default ini that ships with module.
                self._settings_path = Path(__file__).parents[1] / 'resources' / 'config' / ini_path.name

        self.display_string = None
        self._depth_stream = None
        self._mirror = {'lsl': None, 'nsp': None}
        self.restore_from_settings()
        self.setup_ui()

    def restore_from_settings(self):
        settings = QtCore.QSettings(str(self._settings_path), QtCore.QSettings.IniFormat)

        # Restore size and position.
        default_dims = defaults.WINDOWDIMS_DICT[type(self).__name__]
        settings.beginGroup("MainWindow")
        self.resize(settings.value("size", QtCore.QSize(default_dims[2], default_dims[3])))
        self.move(settings.value("pos", QtCore.QPoint(default_dims[0], default_dims[1])))
        if settings.value("fullScreen", 'false') == 'true':
            self.showFullScreen()
        elif settings.value("maximized", 'false') == 'true':
            self.showMaximized()
        if settings.value("frameless", 'false') == 'true':
            self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        settings.endGroup()

        # Infer depth source from ini file, setup data source
        settings.beginGroup("depth-source")
        src_cls = getattr(open_mer.depth_source, settings.value("class", "CBSDKPlayback"))
        self._depth_source = src_cls(scoped_settings=settings)
        settings.endGroup()

        settings.beginGroup("depth-mirror")
        self._mirror['lsl'] = bool(settings.value("lsl_mirror", False))
        self._mirror['nsp'] = bool(settings.value("lsl_mirror", False))
        settings.endGroup()

    def setup_ui(self):
        self.setWindowTitle('Neuroport DBS - Electrodes Depth')
        self.show()
        self.plot_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.plot_widget)

        # define Qt GUI elements
        v_layout = QtWidgets.QVBoxLayout()
        v_layout.setSpacing(0)
        v_layout.setContentsMargins(10, 0, 10, 10)
        h_layout = QtWidgets.QHBoxLayout()

        h_layout.addWidget(QtWidgets.QLabel("DTT: "))
        self._doubleSpinBox_DTT = QtWidgets.QDoubleSpinBox()
        self._doubleSpinBox_DTT = QtWidgets.QDoubleSpinBox()
        self._doubleSpinBox_DTT.setMinimum(-100.00)
        self._doubleSpinBox_DTT.setMaximum(100.00)
        self._doubleSpinBox_DTT.setSingleStep(1.00)
        self._doubleSpinBox_DTT.setDecimals(2)
        self._doubleSpinBox_DTT.setValue(0.00)
        self._doubleSpinBox_DTT.setFixedWidth(60)
        h_layout.addWidget(self._doubleSpinBox_DTT)
        
        # Manual offset added to the depth before display and mirroring
        h_layout.addWidget(QtWidgets.QLabel("Offset: "))
        self._doubleSpinBox_offset = QtWidgets.QDoubleSpinBox()
        self._doubleSpinBox_offset.setMinimum(-100.00)
        self._doubleSpinBox_offset.setMaximum(100.00)
        self._doubleSpinBox_offset.setSingleStep(1.00)
        self._doubleSpinBox_offset.setDecimals(2)
        self._doubleSpinBox_offset.setValue(0.00)
        self._doubleSpinBox_offset.setFixedWidth(60)
        h_layout.addWidget(self._doubleSpinBox_offset)

        h_layout.addStretch()

        # Widgets to manage mirroring the resulting value (including scale and offset) to other outputs
        h_layout.addWidget(QtWidgets.QLabel("Stream to :"))

        cb = QtWidgets.QCheckBox("NSP")
        cb.setObjectName("NSP_CheckBox")
        if isinstance(self._depth_source, CBSDKPlayback):
            cb.setChecked(False)
            cb.setEnabled(False)
        else:
            cb.setChecked(self._mirror['nsp'])
            cb.setEnabled(True)
            cb.clicked.connect(self.on_mirror_NSP_clicked)
            cb.click()
        h_layout.addWidget(cb)
        h_layout.addSpacing(5)

        cb = QtWidgets.QCheckBox("LSL")
        cb.setChecked(self._mirror['lsl'])
        cb.clicked.connect(self.on_mirror_LSL_clicked)
        cb.click()
        h_layout.addWidget(cb)
        h_layout.addSpacing(5)

        # Manual close button because window has no frame.
        quit_btn = QtWidgets.QPushButton('X')
        quit_btn.setMaximumWidth(20)
        quit_btn.clicked.connect(QtWidgets.QApplication.instance().quit)

        quit_btn.setStyleSheet("QPushButton { color: white; "
                               "background-color : red; "
                               "border-color : red; "
                               "border-width: 2px}")

        h_layout.addWidget(quit_btn)

        v_layout.addLayout(h_layout)

        # add a frame for the LCD numbers
        self.lcd_frame = QtWidgets.QFrame()
        self.lcd_frame.setFrameShape(QtWidgets.QFrame.Shape.Box)
        lcd_layout = QtWidgets.QGridLayout()
        self.lcd_frame.setLayout(lcd_layout)

        # RAW reading from DDU
        self.raw_ddu = QtWidgets.QLCDNumber()
        self.raw_ddu.setDigitCount(7)
        self.raw_ddu.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.raw_ddu.setSmallDecimalPoint(True)
        self.raw_ddu.setFixedHeight(50)
        self.raw_ddu.display("{0:.3f}".format(0))
        lcd_layout.addWidget(self.raw_ddu, 0, 3, 2, 3)

        # TODO: Use custom class and reimplement self.offset_ddu.mouseDoubleClickEvent(), then git rid of "Send!"
        self.offset_ddu = QtWidgets.QLCDNumber()
        self.offset_ddu.setDigitCount(7)
        self.offset_ddu.setFixedHeight(150)
        self.offset_ddu.display("{0:.3f}".format(-10))
        self.offset_ddu.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        lcd_layout.addWidget(self.offset_ddu, 2, 0, 5, 6)
        v_layout.addWidget(self.lcd_frame)

        self.plot_widget.setLayout(v_layout)

    def on_mirror_LSL_clicked(self, state):
        if state > 0:
            outlet_info = pylsl.StreamInfo(name='electrode_depth', type='depth', channel_count=1,
                                           nominal_srate=pylsl.IRREGULAR_RATE, channel_format=pylsl.cf_float32,
                                           source_id='depth1214')
            self._depth_stream = pylsl.StreamOutlet(outlet_info)
        else:
            self._depth_stream = None

    def on_mirror_NSP_clicked(self, state):
        if not isinstance(self._depth_source, CBSDKPlayback):
            if state > 0:
                CbSdkConnection().connect()
                CbSdkConnection().cbsdk_config = {'reset': True, 'get_events': False, 'get_comments': False}
                # cbsdk_conn.set_comments("DTT:" + display_string)
            else:
                CbSdkConnection().disconnect()

    def _do_close(self, from_port):
        self._depth_source.do_close()

    def update(self):
        # Added new_value handling for playback if we ever want to post-process depth
        # on previously recorded sessions.
        new_value = False

        value = self._depth_source.update()
        if value is not None:
            self.raw_ddu.display("{0:.3f}".format(value))
            value += self._doubleSpinBox_DTT.value() + self._doubleSpinBox_offset.value()
            display_string = "{0:.3f}".format(value)
            if display_string != self.display_string:
                new_value = True
                self.display_string = display_string
            self.offset_ddu.display(display_string)

        # Push to NSP (only if this is not NSP playback)
        nsp_cb = self.findChild(QtWidgets.QCheckBox, "NSP_CheckBox")
        if nsp_cb and nsp_cb.isChecked() and not isinstance(self._depth_source, CBSDKPlayback):
            cbsdk_conn = CbSdkConnection()
            if cbsdk_conn.is_connected:
                if self.chk_NSP.isChecked() and self.chk_NSP.isEnabled() and new_value:
                    cbsdk_conn.set_comments("DTT:" + display_string)
            else:
                # try connecting if not connected but button is active
                if self.chk_NSP.isChecked() and self.chk_NSP.isEnabled():
                    cbsdk_conn.connect()
                    cbsdk_conn.cbsdk_config = {'reset': True, 'get_events': False, 'get_comments': False}

        # Push to LSL
        if self._depth_stream is not None and new_value:
            self._depth_stream.push_sample([value])

    def send(self):
        self.display_string = None  # make sure the update function runs
        self.update()
