import time
from pathlib import Path
from qtpy import QtWidgets, QtCore
from cerebuswrapper import CbSdkConnection

# Import settings
import neuroport_dbs
import neuroport_dbs.dbsgui.data_source
from neuroport_dbs.settings import defaults


def get_now_time():
    # Attempt to synchronize different series using machine time.
    cbsdk_conn = CbSdkConnection()
    if cbsdk_conn.is_connected:
        now = cbsdk_conn.time()
    else:
        now = time.time()
    return now


class CustomGUI(QtWidgets.QMainWindow):
    """
    This application is for monitoring continuous activity from a MER data source.
    """

    def __init__(self, ini_file=None):
        super(CustomGUI, self).__init__()

        # Infer path to ini
        ini_name = ini_file if ini_file is not None else (type(self).__name__ + '.ini')
        ini_path = Path(ini_name)
        if ini_path.exists():
            self._settings_path = ini_path
        else:
            # Try home / .dbs_suite first
            home_dir = Path(QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.HomeLocation))
            ini_path = home_dir / '.dbs_suite' / ini_path.name
            if ini_path.exists():
                self._settings_path = ini_path
            else:
                # Use default ini that ships with module.
                self._settings_path = Path(__file__).parents[2] / 'resources' / 'config' / ini_path.name

        self._plot_widget = None
        self._plot_config = None
        self._data_source = None
        self.restore_from_settings()
        self.show()

    def __del__(self):
        # CbSdkConnection().disconnect() No need to disconnect because the instance will do so automatically.
        pass

    def restore_from_settings(self):
        # Should be overridden in child class, but likely calling this super at top of override.
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

        # Infer data source from ini file, setup data source
        settings.beginGroup("data-source")
        src_cls = getattr(neuroport_dbs.dbsgui.data_source, settings.value("class"))
        # Get the _data_source. Note this might trigger on_source_connected before child
        #  finishes parsing settings.
        _data_source = src_cls(scoped_settings=settings, on_connect_cb=self.on_source_connected)
        settings.endGroup()

    @QtCore.Slot(QtCore.QObject)
    def on_source_connected(self, data_source):
        self.data_source = data_source  # Triggers setter --> self.try_reset_widget()

    @property
    def widget_cls(self):
        return NotImplemented  # Child class must override this attribute

    def update(self):
        super(CustomGUI, self).update()
        if self.data_source.is_connected and self._plot_widget:
            self.do_plot_update()

    def do_plot_update(self):
        # abc.abstractmethod not possible because ABC does not work with Qt-derived classes, so raise error instead.
        raise NotImplementedError("This method must be overridden by sub-class.")

    def try_reset_widget(self):
        if self._plot_widget is not None:
            # TODO: Close existing self._plot_widget
            print("TODO: Close existing self._plot_widget")
        if self.plot_config is not None and self.data_source is not None:
            src_dict = self.data_source.data_stats
            self._plot_widget = self.widget_cls(src_dict, **self.plot_config)
            self._plot_widget.was_closed.connect(self.on_plot_closed)
            self.setCentralWidget(self._plot_widget)

    @property
    def data_source(self):
        return self._data_source

    @data_source.setter
    def data_source(self, value):
        self._data_source = value
        self.try_reset_widget()

    @property
    def plot_config(self):
        return self._plot_config

    @plot_config.setter
    def plot_config(self, value):
        self._plot_config = value
        self.try_reset_widget()


class CustomWidget(QtWidgets.QWidget):
    """
    A simple skeleton widget.
    It is only useful if sub-classed.
    """
    was_closed = QtCore.Signal()

    def __init__(self, source_dict, **kwargs):
        super(CustomWidget, self).__init__()

        # Init member variables
        self.awaiting_close = False
        self.labels = source_dict['channel_names']
        self.chan_states = source_dict['chan_states']
        self.samplingRate = source_dict['srate']

        # Create UI elements
        plot_layout = QtWidgets.QVBoxLayout()
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(0)
        self.setLayout(plot_layout)
        self.create_control_panel()
        self.create_plots(**kwargs)
        self.refresh_axes()

    def create_control_panel(self):
        cntrl_layout = QtWidgets.QHBoxLayout()
        clear_button = QtWidgets.QPushButton("Clear")
        clear_button.clicked.connect(self.clear)
        clear_button.setMaximumWidth(200)
        cntrl_layout.addWidget(clear_button)
        self.layout().addLayout(cntrl_layout)

    def create_plots(self, theme='dark', **kwargs):
        raise TypeError("Must be implemented by sub-class.")

    def refresh_axes(self):
        raise TypeError("Must be implemented by sub-class.")

    def clear(self):
        raise TypeError("Must be implemented by sub-class.")

    def closeEvent(self, evnt):
        super(CustomWidget, self).closeEvent(evnt)
        self.awaiting_close = True
        self.was_closed.emit()
