import sys
import numpy as np
import time
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtChart import *
from cbsdkConnection import CbSdkConnection

# TODO: Make these settings configurable via UI elements
RAWDURATION = 1.0
HPDURATION = 1.0


class MyGUI(QMainWindow):

    def __init__(self):
        super(MyGUI, self).__init__()

        self.source = CbSdkSource()
        self.actions = {}

        self.setup_ui()
        self.indicate_connection_state()
        self.show()

    def __del__(self):
        # CbSdkConnection().disconnect() No need to disconnect because the instance will do so automatically.
        pass

    def setup_ui(self):
        self.resize(1200, 621)
        self.setWindowTitle('Neuroport DBS')
        # self.setCentralWidget(QtWidgets.QWidget(self))  # This squeezes out the docks.
        self.create_actions()  # TODO: Do I need to maintain a list of actions? If not then combine funcs for menu/tool
        self.create_menus()
        self.create_toolbars()

    def create_actions(self):
        # Actions
        self.actions = {
            "Connect": QAction("Connect", self),
            "AddChan": QAction("Add Chan", self)
        }
        self.actions["Connect"].triggered.connect(self.on_action_connect_triggered)
        self.actions["AddChan"].triggered.connect(self.on_action_add_chan_triggered)
        # self.actions["Quit"] = QtWidgets.QAction("Quit", self)
        # self.actions["Quit"].triggered.connect(QtWidgets.qApp.quit)

        # TODO: Icons, tooltips, shortcuts, etc.
        # TODO: QActionGroup if many actions need to be grouped.

    def create_menus(self):
        # Menus
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('&File')
        file_menu.addAction(self.actions["Connect"])

    def create_toolbars(self):
        # Toolbars
        for k, v in self.actions.items():
            toolbar_item = QToolBar(k)
            toolbar_item.addAction(v)
            self.addToolBar(Qt.LeftToolBarArea, toolbar_item)

    def indicate_connection_state(self):
        if self.source.cbSdkConn.is_connected:
            self.statusBar().showMessage('Connected.')
            # TODO: Disable connect menu/toolbar
        else:
            self.statusBar().showMessage('Not connected.')
            # TODO: Enable connect menu/toolbar

    def on_action_connect_triggered(self):
        result = ConnectDialog.do_connect_dialog()
        if result == -1:
            print("Connection canceled.")
        self.indicate_connection_state()

    def on_action_add_chan_triggered(self):
        # TODO: Launch dialog window to select channel + parameters.
        dock_widget = MERDockWidget("My MER Dock Widget", parent=self)  # TODO: Replace name with channel label.
        # dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea |
        #                           Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock_widget)
        # Seems to add top first, then bottom

        # self.viewMenu.addAction(dock.toggleViewAction())

    def update(self):
        self.source.update()

        # Update the docks
        my_docks = self.findChildren(MERDockWidget)
        for ix in range(len(my_docks)):
            if ix < len(self.source.raw_buffers):
                my_docks[ix].raw.series()[0].replace(self.source.raw_buffers[ix])


class ConnectDialog(QDialog):
    """
    A modal dialog window with widgets for modifying connection parameters.
    Changes + OK will change the parameters in the CbSdkConnection singleton,
    but will not actually connect.
    """
    def __init__(self, parent=None):
        super(ConnectDialog, self).__init__(parent)
        # Get access to the CbSdkConnection instance, but don't connect yet.
        self.cbsdkConn = CbSdkConnection()

        # Widgets to show/edit connection parameters.
        layout = QVBoxLayout(self)

        # client-addr ip
        client_addr_layout = QHBoxLayout()
        client_addr_layout.addWidget(QLabel("client-addr"))
        self.clientIpEdit = QLineEdit(self.cbsdkConn.con_params['client-addr'])
        self.clientIpEdit.setInputMask("000.000.000.000;_")
        client_addr_layout.addWidget(self.clientIpEdit)
        layout.addLayout(client_addr_layout)

        # client-port int
        client_port_layout = QHBoxLayout()
        client_port_layout.addWidget(QLabel("client-port"))
        self.clientPortSpin = QSpinBox()
        self.clientPortSpin.setMinimum(0)
        self.clientPortSpin.setMaximum(99999)
        self.clientPortSpin.setSingleStep(1)
        self.clientPortSpin.setValue(self.cbsdkConn.con_params['client-port'])
        client_port_layout.addWidget(self.clientPortSpin)
        layout.addLayout(client_port_layout)

        # inst-addr ip
        inst_addr_layout = QHBoxLayout()
        inst_addr_layout.addWidget(QLabel("inst-addr"))
        self.instIpEdit = QLineEdit(self.cbsdkConn.con_params['inst-addr'])
        self.instIpEdit.setInputMask("000.000.000.000;_")
        inst_addr_layout.addWidget(self.instIpEdit)
        layout.addLayout(inst_addr_layout)

        # inst-port int
        inst_port_layout = QHBoxLayout()
        inst_port_layout.addWidget(QLabel("inst-port"))
        self.instPortSpin = QSpinBox()
        self.instPortSpin.setMinimum(0)
        self.instPortSpin.setMaximum(99999)
        self.instPortSpin.setSingleStep(1)
        self.instPortSpin.setValue(self.cbsdkConn.con_params['inst-port'])
        inst_port_layout.addWidget(self.instPortSpin)
        layout.addLayout(inst_port_layout)

        # receive-buffer-size int
        rec_buff_layout = QHBoxLayout()
        rec_buff_layout.addWidget(QLabel("receive-buffer-size"))
        self.recBuffSpin = QSpinBox()
        self.recBuffSpin.setMinimum(6*1024*1024)
        self.recBuffSpin.setMaximum(8*1024*1024)
        self.recBuffSpin.setSingleStep(1024*1024)
        self.recBuffSpin.setValue(self.cbsdkConn.con_params['receive-buffer-size'])
        rec_buff_layout.addWidget(self.recBuffSpin)
        layout.addLayout(rec_buff_layout)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def do_connect_dialog(parent=None):
        dialog = ConnectDialog(parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            dialog.cbsdkConn.disconnect()
            # Collect values from widgets and set them on dialog.cbsdkConn
            new_params = {
                'client-addr': dialog.clientIpEdit.text(),
                'client-port': dialog.clientPortSpin.value(),
                'inst-addr': dialog.instIpEdit.text(),
                'inst-port': dialog.instPortSpin.value(),
                'receive-buffer-size': dialog.recBuffSpin.value()
            }
            dialog.cbsdkConn.con_params = new_params
            return dialog.cbsdkConn.connect()
        return -1


class MERDockWidget(QDockWidget):
    def __init__(self, name="MERDockWidget", parent=None):
        super(MERDockWidget, self).__init__(name, parent)

        # colors = ["red", "green", "blue"]

        # Chart container
        dock_widget = QWidget()
        dock_layout = QGridLayout()
        dock_layout.setContentsMargins(0, 0, 0, 0)
        dock_layout.setSpacing(0)
        dock_widget.setLayout(dock_layout)

        # Raw chart
        self.raw = QChart()
        self.raw.legend().hide()
        self.raw.addAxis(QValueAxis(), Qt.AlignBottom)
        self.raw.addAxis(QValueAxis(), Qt.AlignLeft)
        # self.raw.axisX().setRange(0, 30000)
        self.raw.axisY().setRange(-10000, 10000)
        raw_series = QLineSeries()
        # pen = QPen()
        # pen.setColor(QColor(colors[0]))
        # raw_series.setPen(pen)
        raw_series.setUseOpenGL(True)  # Causes crash when moving dock around.
        self.raw.addSeries(raw_series)
        # self.raw.createDefaultAxes()
        raw_series.attachAxis(self.raw.axisX())
        raw_series.attachAxis(self.raw.axisY())
        raw_view = QChartView(self.raw)
        dock_layout.addWidget(raw_view, 0, 0, 2, 1)

        # Highpass chart
        self.highpass = QChart()
        highpass_view = QChartView(self.highpass)
        dock_layout.addWidget(highpass_view, 0, 1, 2, 1)

        # Raster
        self.raster = QChart()
        raster_view = QChartView(self.raster)
        dock_layout.addWidget(raster_view, 0, 2, 1, 1)

        # Waveforms
        self.waveForms = QChart()
        waveform_view = QChartView(self.waveForms)
        dock_layout.addWidget(waveform_view, 1, 2, 1, 1)

        self.setWidget(dock_widget)


class CbSdkSource(object):
    """
    A wrapper around the cbsdk connection.
    Here we can make some assumptions about the data, and keep a local buffer.
    """
    default_rate = 30000.0
    dtype = np.float

    def __init__(self, buffer_duration=1.0, n_channels=6):
        self.last_time = time.time()
        self.raw_buffers = []
        self.raw_arrays = []
        self.new_cont_for_chans = []
        self.new_events_for_chans = []

        self.cbSdkConn = CbSdkConnection()
        self.reset_buffers(buffer_duration, self.default_rate, n_channels)

    def reset_buffers(self, buffer_duration, sampling_rate, n_channels):
        self.last_time = time.time()
        n_samples = int(buffer_duration * sampling_rate)

        # Default x-axis, zeros for y-axis
        xdata = np.linspace(1. / sampling_rate, buffer_duration, n_samples)
        # xdata = np.arange(n_samples, dtype=self.dtype)
        ydata = np.zeros(xdata.shape, dtype=self.dtype)

        # For PyQt5.Chart, plot data will be replaced with our QPolygon, backed by np buffer
        bytes_per_sample = np.finfo(self.dtype).dtype.itemsize
        self.raw_buffers = []
        self.raw_arrays = []
        for ix in range(n_channels):
            poly = QPolygonF(n_samples)
            pointer = poly.data()
            pointer.setsize(2 * poly.size() * bytes_per_sample)
            raw_mem = np.frombuffer(pointer, self.dtype)
            raw_mem[:(n_samples-1) * 2 + 1:2] = xdata
            raw_mem[1:(n_samples-1) * 2 + 2:2] = ydata
            self.raw_arrays.append(raw_mem)
            self.raw_buffers.append(poly)

    def update(self):
        if self.cbSdkConn.is_connected:
            contdat, cont_time = self.cbSdkConn.get_continuous_data()
            self.new_cont_for_chans = [x[0] for x in contdat]

            timestamps, ts_time = self.cbSdkConn.get_event_data()
            self.new_events_for_chans = [x[0] for x in timestamps]
        else:
            # Generate fake continuous data
            cont_time = time.time()
            time_elapsed = cont_time - self.last_time
            n_samples = int(time_elapsed * self.default_rate)
            contdat = [(ix, 10000*(np.random.rand(n_samples)-0.5))
                       for ix in range(len(self.raw_arrays))]
            self.last_time = cont_time

            # TODO: Generate fake event data

        # Operate on continuous data
        if cont_time:
            for x in contdat:
                cont_chan = x[0]
                new_ydata = x[1]
                n_old = int(self.raw_arrays[cont_chan].shape[0] / 2)
                old_ydata = self.raw_arrays[cont_chan][1::2]
                n_keep = old_ydata.shape[0] - new_ydata.shape[0]
                if n_keep < 0:
                    new_ydata = new_ydata[-n_old:]
                    n_keep = 0
                if n_keep > 0:
                    # Shift old samples
                    old_ydata[:n_keep] = old_ydata[-n_keep:]
                # Overwrite with new samples
                # This updates the buffer and therefore the polygon it is backing.
                old_ydata[n_keep:] = new_ydata

        # TODO: Put spiking data somewhere.

if __name__ == '__main__':

    qapp = QApplication(sys.argv)
    aw = MyGUI()

    timer = QTimer()
    timer.timeout.connect(aw.update)
    timer.start(30)

    if (sys.flags.interactive != 1) or not hasattr(PyQt5.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()