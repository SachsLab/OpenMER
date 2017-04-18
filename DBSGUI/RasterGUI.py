import sys
import time
import numpy as np
import PyQt5
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtChart import *
from cbsdkConnection import CbSdkConnection


# TODO: Make some of these settings configurable via UI elements
# TODO: Load these constants from a config file.
PLOTHEIGHT = 800
RASTDURATION = 1.0
RASTROWS = 4
SAMPLINGGROUPS = ["0", "500", "1000", "2000", "10000", "30000", "RAW"]
THEMES = {
    'dark': {
        'pencolors': ["cyan", QColor(0, 255, 0), "red", "magenta", "yellow", "white"],
        'bgcolor': Qt.black,
        'labelcolor': Qt.gray,
        'axiscolor': Qt.gray,
        'axiswidth': 1
    }
}
SIMOK = False  # Make this False for production. Make this True for development when NSP/NPlayServer are unavailable.


def get_now_time():
    # Attempt to synchronize different series using machine time.
    cbsdk_conn = CbSdkConnection()
    if cbsdk_conn.is_connected:
        now = cbsdk_conn.time()
    else:
        now = time.time()
    return now


class MyGUI(QMainWindow):
    """
    This application is for monitoring activity from the Blackrock NSP.

    """

    def __init__(self):
        super(MyGUI, self).__init__()
        self.cbsdk_conn = CbSdkConnection(simulate_ok=SIMOK)
        self.actions = {}
        self.setup_ui()
        self.indicate_connection_state()
        self.show()
        self.raster_widget = None

    def __del__(self):
        # CbSdkConnection().disconnect() No need to disconnect because the instance will do so automatically.
        pass

    def setup_ui(self):
        self.resize(200, 150)
        self.setWindowTitle('Neuroport DBS')
        # self.setCentralWidget(QWidget(self))  # This squeezes out docks.
        # self.centralWidget().setLayout(QVBoxLayout())
        self.create_actions()
        self.create_menus()
        self.create_toolbars()

    def create_actions(self):
        # Actions
        self.actions = {
            "Connect": QAction("Connect", self),
            "AddRaster": QAction("Add Raster Plot", self),
        }
        self.actions["Connect"].triggered.connect(self.on_action_connect_triggered)
        self.actions["AddRaster"].triggered.connect(self.on_action_add_raster_triggered)
        # self.actions["Quit"] = QtWidgets.QAction("Quit", self)
        # self.actions["Quit"].triggered.connect(QtWidgets.qApp.quit)

        # TODO: Icons, tooltips, shortcuts, etc.
        # TODO: QActionGroup if many actions need to be grouped.

    def create_menus(self):
        # Menus
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('&File')
        file_menu.addAction(self.actions["Connect"])
        file_menu.addAction(self.actions["AddRaster"])

    def create_toolbars(self):
        # Toolbars
        for k, v in self.actions.items():
            toolbar_item = QToolBar(k)
            toolbar_item.addAction(v)
            self.addToolBar(Qt.LeftToolBarArea, toolbar_item)

    def indicate_connection_state(self):
        if self.cbsdk_conn.is_connected:
            msg_str = 'Connected to NSP'
            # TODO: Disable connect menu/toolbar
        elif self.cbsdk_conn.is_simulating:
            msg_str = 'Connected to NSP simulator'
        else:
            msg_str = 'Not connected'
            # TODO: Enable connect menu/toolbar
        self.statusBar().showMessage(msg_str)

    def on_action_connect_triggered(self):
        result = ConnectDialog.do_connect_dialog()
        if result == -1:
            print("Connection canceled.")
        self.indicate_connection_state()

    def on_action_add_raster_triggered(self):
        self.cbsdk_conn.cbsdk_config = {'reset': True, 'get_events': True}
        group_info = self.cbsdk_conn.get_group_config(SAMPLINGGROUPS.index("30000"))  # TODO: Or RAW, never both
        for gi_item in group_info:
            gi_item['label'] = gi_item['label'].decode('utf-8')
            gi_item['unit'] = gi_item['unit'].decode('utf-8')
        self.raster_widget = RasterWidget(group_info)
        self.raster_widget.was_closed.connect(self.on_raster_closed)

    def on_raster_closed(self):
        self.raster_widget = None
        self.cbsdk_conn.cbsdk_config = {'reset': True, 'get_events': False}

    def update(self):
        super(MyGUI, self).update()

        if self.cbsdk_conn.is_connected or self.cbsdk_conn.is_simulating:
            if self.raster_widget:
                ev_timestamps = self.cbsdk_conn.get_event_data()
                ev_chan_ids = [x[0] for x in ev_timestamps]
                chart_chan_ids = [x['chan'] for x in self.raster_widget.group_info]
                match_chans = list(set(ev_chan_ids) & set(chart_chan_ids))
                for chan_id in match_chans:
                    data = ev_timestamps[ev_chan_ids.index(chan_id)][1]['timestamps']
                    label = self.raster_widget.group_info[chart_chan_ids.index(chan_id)]['label']
                    self.raster_widget.chart.update(label, data)


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
        self.recBuffSpin.setMinimum(6 * 1024 * 1024)
        self.recBuffSpin.setMaximum(8 * 1024 * 1024)
        self.recBuffSpin.setSingleStep(1024 * 1024)
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


class MyWidget(QWidget):
    """
    A simple skeleton widget.
    It is only useful if sub-classed.
    """
    was_closed = pyqtSignal()

    def __init__(self, group_info, group_ix=0, **kwargs):
        super(MyWidget, self).__init__(**kwargs)
        self.group_info = group_info
        self.awaiting_close = False

        # Get sampling rate from group_ix
        if (SAMPLINGGROUPS[group_ix] == "0") or (SAMPLINGGROUPS[group_ix] == "RAW"):
            group_ix = 5
        self.samplingRate = int(SAMPLINGGROUPS[group_ix])

        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(0)
        self.setLayout(chart_layout)

        self.labels = {}

        self.resize(600, PLOTHEIGHT)
        self.show()

    def closeEvent(self, evnt):
        super(MyWidget, self).closeEvent(evnt)
        self.awaiting_close = True
        self.was_closed.emit()


class RasterWidget(MyWidget):
    def __init__(self, *args, **kwargs):
        super(RasterWidget, self).__init__(*args, **kwargs)

        self.chart = RasterChart(sampling_rate=self.samplingRate)

        for chan_ix in range(len(self.group_info)):
            label_string = self.group_info[chan_ix]['label']
            self.chart.add_series(line_label=label_string)
        self.chart.refresh_axes()

        # TODO: Control panel to change row duration, number of rows, clear button
        cntrl_layout = QHBoxLayout()
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.on_clear_button_clicked)
        cntrl_layout.addWidget(clear_button)
        self.layout().addLayout(cntrl_layout)

        new_chart_view = QChartView(self.chart)
        self.layout().addWidget(new_chart_view)

    def on_clear_button_clicked(self):
        self.chart.clear()


class MyChart(QChart):
    def __init__(self, theme='dark', **kwargs):
        super(MyChart, self).__init__(**kwargs)
        self.theme = theme
        self.legend().hide()
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setBackgroundRoundness(0.)
        self.setDropShadowEnabled(False)
        # self.addAxis(QValueAxis(), Qt.AlignBottom)
        self.addAxis(QCategoryAxis(), Qt.AlignBottom)
        # self.addAxis(QValueAxis(), Qt.AlignLeft)
        self.addAxis(QCategoryAxis(), Qt.AlignLeft)
        self.apply_color_scheme()

    def apply_color_scheme(self, theme=None):
        if theme is not None:
            self.theme = theme
        # self.setBackgroundVisible(False)
        self.setBackgroundBrush(THEMES[self.theme]['bgcolor'])
        self.axisX().setLabelsBrush(THEMES[self.theme]['labelcolor'])
        self.axisY().setLabelsBrush(THEMES[self.theme]['labelcolor'])
        axis_pen = QPen(THEMES[self.theme]['axiscolor'])
        axis_pen.setWidth(THEMES[self.theme]['axiswidth'])
        # axis_pen.setStyle(Qt.DotLine)
        self.axisX().setLinePen(axis_pen)
        self.axisY().setLinePen(axis_pen)
        self.axisX().setGridLineVisible(False)
        # self.axisY().setGridLineVisible(False)
        self.axisY().setGridLinePen(axis_pen)
        self.color_iterator = -1


class RasterChart(MyChart):
    """

    """
    frate_changed = pyqtSignal(str, float)

    def __init__(self, row_duration=RASTDURATION, sampling_rate=None, n_rows=RASTROWS, **kwargs):
        super(RasterChart, self).__init__(**kwargs)
        self.config = {
            'row_duration': row_duration,
            'sampling_rate': sampling_rate,
            'n_rows': n_rows
        }
        self.scatter_series = {}
        self.refresh_axes()

    def refresh_axes(self):
        # Remove all existing labels
        for label in self.axisX().categoriesLabels():
            self.axisX().remove(label)
        for label in self.axisY().categoriesLabels():
            self.axisY().remove(label)

        # Add X-axis labels.
        self.x_lim = self.config['row_duration'] * self.config['sampling_rate']
        self.axisX().setRange(0, self.x_lim)  # self.axisX().setRange(-0.5, self.x_lim + 0.5)
        self.axisX().setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
        self.axisX().append("0", 0)
        self.axisX().append("{:.1f}".format(self.config['row_duration']), self.x_lim)

        # Add Y-axis labels. Note, categories have to be added in ascending order.
        min_y = 1 - len(self.scatter_series)
        self.axisY().setRange(min_y, 1)
        self.axisY().setStartValue(min_y)
        # Sort self.segmented_series according to -line_ix
        series_list = sorted(self.scatter_series.items(), key=lambda x: x[1]['chan_ix'], reverse=True)
        label_ix = 0
        for kv_tup in series_list:
            ss_info = self.scatter_series[kv_tup[0]]
            y_max = 1 - ss_info['chan_ix']
            self.axisY().append(kv_tup[0], y_max)
            self.scatter_series[kv_tup[0]]['label_ix'] = label_ix
            label_ix += 1

        # Display settings
        for ax in [self.axisX(), self.axisY()]:
            ax.setLineVisible(False)

    def add_series(self, line_label="new line"):
        self.color_iterator = (self.color_iterator + 1) % len(THEMES[self.theme]['pencolors'])
        pen_color = QColor(THEMES[self.theme]['pencolors'][self.color_iterator])
        my_pen = QPen(pen_color)
        # pen_color.setAlphaF(0.1)  # Does not work with setUseOpenGL

        my_series = []
        for series_ix in range(2):
            new_series = QScatterSeries()
            new_series.setMarkerShape(QScatterSeries.MarkerShapeRectangle)
            new_series.setPen(my_pen)  # Outline. Not used by OpenGL
            new_series.setColor(pen_color)  # Fill
            new_series.setMarkerSize(6)
            self.addSeries(new_series)
            new_series.attachAxis(self.axisX())
            new_series.attachAxis(self.axisY())
            new_series.setUseOpenGL(True)
            my_series.append(new_series)

        self.scatter_series[line_label] = {
            'old': my_series[0],
            'latest': my_series[1],
            'last_sample_ix': 0,
            'chan_ix': len(self.scatter_series),  # To offset on y-axis
            'frate': 0,
            'hist_dur': 0.0
        }

    def clear(self):
        for key in self.scatter_series:
            ss = self.scatter_series[key]
            ss['old'].clear()
            ss['latest'].clear()
            ss['last_sample_ix'] = 0
            ss['hist_dur'] = 0.0
            self.modify_frate(key, 0)

    def modify_frate(self, ss_key, new_frate):
        ss = self.scatter_series[ss_key]
        ss['frate'] = new_frate
        old_label = self.axisY().categoriesLabels()[ss['label_ix']]
        new_label = "{0:.0f}.{1:d}".format(new_frate, ss['label_ix'])
        self.axisY().replaceLabel(old_label, new_label)
        self.frate_changed.emit(ss_key, new_frate)

    def update(self, line_label, data):
        """
        :param line_label:
        :param data: A list of 6 numpy arrays, one for each sorted unit, each containing uint32 timestamps.
        :return:
        """
        data = np.uint32(np.concatenate(data))  # For now, put all sorted units into the same series.
        data.sort()
        offset = data[0] - np.mod(data[0], self.x_lim)
        data = data - offset

        ss_info = self.scatter_series[line_label]

        y_offset = -ss_info['chan_ix']

        # Take spike times that should be added to the latest line.
        latest = ss_info['latest']
        if data[0] > ss_info['last_sample_ix']:
            add_bool = data < self.x_lim
            for spk in data[add_bool]:
                latest.append(spk, y_offset + 1.0 / (self.config['n_rows'] + 1))
            data = data[np.logical_not(add_bool)]  # Remove from data

        # Remaining spike times should be added to a new line and old spike times shifted up.
        if data.shape[0] > 0:
            old = ss_info['old']

            # Shift old points up 1
            old_points = QPolygonF(old.pointsVector())  # Copy of data points in QVector<QPoint>
            if old_points.count() > 0:
                old_points.translate(0, 1.0 / (self.config['n_rows'] + 1))  # Move them up 1
                # Remove out of range points.
                while old_points.first().y() >= (1 + y_offset):
                    old_points.remove(0)
                old.replace(old_points)

            # Shift new->old points up 1
            transfer_points = QPolygonF(latest.pointsVector())
            transfer_points.translate(0, 1.0 / (self.config['n_rows'] + 1))
            old.append(transfer_points)

            latest.clear()
            for spk in data:
                latest.append(spk - self.x_lim, y_offset + 1.0 / (self.config['n_rows'] + 1))

            # Calculate firing rate from old
            hist_dur = min(self.scatter_series[line_label]['hist_dur'] + 1, self.config['n_rows'] - 1)
            self.scatter_series[line_label]['hist_dur'] = hist_dur
            new_frate = old.count() / hist_dur
            self.scatter_series[line_label]['frate'] = new_frate

            # Update labels
            self.modify_frate(line_label, new_frate)

        latest_points = latest.pointsVector()
        if len(latest_points) > 0:
            self.scatter_series[line_label]['last_sample_ix'] = latest_points[-1].x()


if __name__ == '__main__':
    qapp = QApplication(sys.argv)
    aw = MyGUI()
    timer = QTimer()
    timer.timeout.connect(aw.update)
    timer.start(1)

    if (sys.flags.interactive != 1) or not hasattr(PyQt5.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()