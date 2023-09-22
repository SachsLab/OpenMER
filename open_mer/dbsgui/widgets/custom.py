from pathlib import Path
import importlib.resources as pkg_resources
from qtpy import QtWidgets, QtCore, QtGui

import open_mer.data_source


class CustomGUI(QtWidgets.QMainWindow):
    """
    This application is for monitoring continuous activity from a MER data source.
    """

    def __init__(self):
        super().__init__()

        # Infer path to ini
        root_pkg = __package__.split(".")[0]
        ini_name = type(self).__name__ + '.ini'

        self._settings_paths: dict[str, Path] = {}
        with pkg_resources.path(f"{root_pkg}.resources", "settings") as base_default:
            ini_default = base_default / ini_name
        self._settings_paths["base"] = ini_default

        base_custom = Path.home() / f".{root_pkg}"
        ini_custom = base_custom / ini_name
        if ini_custom.exists():
            self._settings_paths["custom"] = ini_custom

        self._plot_widget = None
        self._data_source = None
        self._plot_config = {}
        self.parse_settings()
        self.try_reset_widget()
        self.show()

    def __del__(self):
        self._data_source.disconnect_requested()

    def parse_settings(self):
        """
        Parse ini files and populate ._plot_config.
        Note that some settings (MainWindow) will be applied immediately and won't be stored in _plot_config.

        This method should usually be followed by .try_reset_widget()
        """
        # Collect names of ini files in reverse importance.
        settings_paths = [self._settings_paths["base"].parent / "Style.ini", self._settings_paths["base"]]
        if "custom" in self._settings_paths:
            settings_paths += [self._settings_paths["custom"].parent / "Style.ini", self._settings_paths["custom"]]

        # theme
        if "theme" not in self._plot_config:
            self._plot_config["theme"] = {"colormap": None}

        for ini_path in settings_paths:

            settings = QtCore.QSettings(str(ini_path), QtCore.QSettings.IniFormat)

            # Apply MainWindow settings immediately.
            settings.beginGroup("MainWindow")
            keys: list = settings.allKeys()
            if "pos" in keys:
                self.move(settings.value("pos", type=QtCore.QPoint))
            if "size" in keys:
                size_xy: QtCore.QPoint = settings.value("size", type=QtCore.QPoint)
                self.resize(size_xy)
                self.setMaximumWidth(size_xy.width())
            if "fullScreen" in keys and settings.value("fullScreen", type=bool):
                self.showFullScreen()
            elif "maximized" in keys and settings.value("maximized", type=bool):
                self.showMaximized()
            if "frameless" in keys and settings.value("frameless", type=bool):
                self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
            settings.endGroup()

            # Immediately initiate connection with the data source. Connection outcome will be handled in the callback.
            settings.beginGroup("data-source")
            if "class" in settings.allKeys() and self._data_source is None:
                # Infer data source from ini file, setup data source
                src_cls = getattr(open_mer.data_source, settings.value("class", type=str))
                # Get the _data_source. Note this might trigger on_source_connected before child
                #  finishes parsing settings.
                _data_source = src_cls(scoped_settings=settings, on_connect_cb=self.on_source_connected)
            settings.endGroup()

            settings.beginGroup("theme")
            k_t = {
                "labelcolor_active": str, "labelsize_active": int,
                "labelcolor_inactive": str, "labelsize_inactive": int,
                "linewidth": int
            }
            keys = settings.allKeys()
            for k, t in k_t.items():
                if k in keys:
                    self._plot_config["theme"][k] = settings.value(k, type=t)

            # theme > pencolors
            if "colormap" in settings.allKeys():
                self._plot_config["theme"]["colormap"] = settings.value("colormap", "custom", type=str)
                self._plot_config["theme"].pop("pencolors", None)

            if self._plot_config["theme"]["colormap"] == "custom":
                settings.beginGroup("pencolors")
                chan_ids = [int(_) for _ in settings.childGroups()]
                if "pencolors" not in self._plot_config["theme"]:
                    self._plot_config["theme"]["pencolors"] = [None] * (max(chan_ids) + 1)
                for c_id in chan_ids:
                    settings.beginGroup(str(c_id))
                    if "name" in settings.allKeys():
                        name = settings.value("name", type=str)
                        self._plot_config["theme"]["pencolors"][c_id] = QtGui.QColor(name)
                    else:
                        color_hex = settings.value("value", defaultValue="#ffffff", type=str)
                        self._plot_config["theme"]["pencolors"][c_id] = QtGui.QColor(color_hex)
                    settings.endGroup()
                settings.endGroup()  # pencolors
            settings.endGroup()  # theme

    @QtCore.Slot(QtCore.QObject)
    def on_source_connected(self, data_source):
        self.data_source = data_source  # Triggers setter --> self.try_reset_widget()

    @property
    def widget_cls(self):
        return NotImplemented  # Child class must override this attribute

    def update(self):
        super().update()
        if self.data_source.is_connected and self._plot_widget:
            self.do_plot_update()

    def do_plot_update(self):
        # abc.abstractmethod not possible because ABC does not work with Qt-derived classes, so raise error instead.
        raise NotImplementedError("This method must be overridden by sub-class.")

    def on_plot_closed(self):
        raise NotImplementedError("This method must be overridden by sub-class.")

    def try_reset_widget(self):
        if self._plot_widget is not None:
            self._plot_widget.close()
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
        super().__init__()

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

    def create_plots(self, **kwargs):
        raise TypeError("Must be implemented by sub-class.")

    def refresh_axes(self):
        raise TypeError("Must be implemented by sub-class.")

    def clear(self):
        raise TypeError("Must be implemented by sub-class.")

    def closeEvent(self, evnt):
        super().closeEvent(evnt)
        self.awaiting_close = True
        self.was_closed.emit()
