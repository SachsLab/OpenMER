"""
If the following PR has not been merged, then you will have to manually edit the VTickGroup.py file.
https://github.com/pyqtgraph/pyqtgraph/pull/485
"""
import sys
import numpy as np
import PyQt5
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtChart import *
import pyqtgraph as pg
from cbsdkConnection import CbSdkConnection
from custom import CustomWidget, ConnectDialog, SAMPLINGGROUPS, get_now_time, THEMES


# TODO: Make some of these settings configurable via UI elements
# TODO: Load these constants from a config file.
PLOTHEIGHT = 800
RASTDURATION = 0.5  # Seconds
RASTROWS = 8
LABEL_FONT_POINT_SIZE = 24
SIMOK = False  # Make this False for production. Make this True for development when NSP/NPlayServer are unavailable.


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
        self.cbsdk_conn.cbsdk_config ={
            'reset': True, 'get_events': True, 'get_comments': True,
            'buffer_parameter': {
                'comment_length': 10
            }
        }
        group_info = self.cbsdk_conn.get_group_config(SAMPLINGGROUPS.index("30000"))  # TODO: Or RAW, never both
        for gi_item in group_info:
            gi_item['label'] = gi_item['label'].decode('utf-8')
            gi_item['unit'] = gi_item['unit'].decode('utf-8')
        self.raster_widget = RasterWidget(group_info)
        self.raster_widget.was_closed.connect(self.on_raster_closed)

    def on_raster_closed(self):
        self.raster_widget = None
        self.cbsdk_conn.cbsdk_config = {'reset': True, 'get_events': False, 'get_comments': False}

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
                    self.raster_widget.update(label, data)

                comments = self.cbsdk_conn.get_comments()
                if comments:
                    pass
                    # self.raster_widget.chart.parse_comments(comments)


class RasterWidget(CustomWidget):
    frate_changed = pyqtSignal(str, float)

    def __init__(self, *args, theme='dark', **kwargs):
        super(RasterWidget, self).__init__(*args, **kwargs)
        self.resize(600, PLOTHEIGHT)
        self.setup_control_panel()
        self.setup_plot_widget(theme=theme)
        self.refresh_axes()
        self.refresh_axes()  # Twice on purpose.

    def on_clear_button_clicked(self):
        self.clear()

    def setup_control_panel(self):
        # Create control panel
        cntrl_layout = QHBoxLayout()
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.on_clear_button_clicked)
        cntrl_layout.addWidget(clear_button)
        self.layout().addLayout(cntrl_layout)

    def setup_plot_widget(self, theme='dark'):
        # Create and add PlotWidget
        self.plotWidget = pg.PlotWidget()
        # self.plotWidget.useOpenGL(True)
        self.layout().addWidget(self.plotWidget)

        # Configure the PlotWidget
        self.plot_config = {
            'x_range': RASTDURATION,
            'n_rows': RASTROWS,
            'theme': theme,
            'color_iterator': -1
        }

        self.raster_series = {}  # Will contain one array of curves for each line/channel label.
        for chan_ix in range(len(self.group_info)):
            self.add_series(self.group_info[chan_ix])

    def add_series(self, chan_info):
        n_total_series = len(self.raster_series) + 1
        y_per_chan = 1.0 / n_total_series
        y_per_row = 1.0 / (n_total_series * self.plot_config['n_rows'])

        # Go back through old series and adjust their yranges
        for chan_label in self.raster_series:
            chan_ix = self.raster_series[chan_label]['line_ix']
            y_chan_start = 1 - (chan_ix + 1) * y_per_chan
            for seg_ix in range(self.plot_config['n_rows']):
                y_range = [y_chan_start + seg_ix*y_per_row, y_chan_start + (seg_ix + 1) * y_per_row]
                self.raster_series[chan_label]['segments'][seg_ix].setYRange(y_range)

        # Appearance settings
        my_theme = THEMES[self.plot_config['theme']]
        self.plot_config['color_iterator'] = (self.plot_config['color_iterator'] + 1) % len(my_theme['pencolors'])
        pen_color = QColor(my_theme['pencolors'][self.plot_config['color_iterator']])

        # Prepare plot data
        rast_segments = []
        chan_ix = len(self.raster_series)
        y_chan_start = 1 - (chan_ix + 1) * y_per_chan
        for seg_ix in range(self.plot_config['n_rows']):
            xvals = None  # (seg_ix + np.random.rand(5)) / self.plot_config['n_rows']
            yrange = [y_chan_start + seg_ix * y_per_row, y_chan_start + (seg_ix + 1) * y_per_row]
            new_seg = pg.VTickGroup(xvals=xvals,
                                    yrange=yrange,
                                    pen=pen_color)
            self.plotWidget.addItem(new_seg)
            rast_segments.append(new_seg)

        start_time = int(get_now_time())
        #
        self.raster_series[chan_info['label']] = {
            'segments': rast_segments,
            'line_ix': len(self.raster_series),
            'chan_id': chan_info['chan'],
            'count': 0,
            'frate': 0,
            'start_time': start_time,
            'last_spike_time': start_time
        }

    def refresh_axes(self):
        self.x_lim = self.plot_config['x_range'] * self.samplingRate
        self.plotWidget.setXRange(0, self.x_lim, padding=0.01)

    def clear(self):
        start_time = int(get_now_time())
        for key in self.raster_series:
            rs = self.raster_series[key]
            # rs['old'].clear()
            # rs['latest'].clear()
            rs['count'] = 0
            rs['start_time'] = start_time
            rs['last_spike_time'] = start_time
            self.modify_frate(key, 0)

    def modify_frate(self, rs_key, new_frate):
        rs = self.raster_series[rs_key]
        rs['frate'] = new_frate
        # old_label = self.axisY().categoriesLabels()[ss['label_ix']]
        # new_label = "{0:3.0f}.{1:d}".format(new_frate, ss['label_ix'])
        # self.axisY().replaceLabel(old_label, new_label)
        self.frate_changed.emit(rs_key, new_frate)

    def parse_comments(self, comments):
        # comments is a list of lists: [[timestamp, string, rgba],]
        comment_strings = [x[1] for x in comments]
        dtts = []
        for comm_str in comment_strings:
            if 'DTT:' in comm_str:
                dtts.append(float(comm_str[4:]))
        if len(dtts) > 0:
            new_dtt = dtts[-1]
            if not self.DTT or self.DTT != new_dtt:
                self.clear()
                self.DTT = new_dtt

    def update(self, line_label, data):
        """

        :param line_label: Label of the segmented series
        :param data: Replace data in the segmented series with these data
        :return:
        """
        n_total_series = len(self.raster_series) + 1
        y_per_row = 1.0 / (n_total_series * self.plot_config['n_rows'])

        data = np.uint32(np.concatenate(data))  # For now, put all sorted units into the same series.
        data.sort()

        # Only keep spikes since last spike time
        rs_info = self.raster_series[line_label]
        last_spike_time = rs_info['last_spike_time']
        data = data[data > last_spike_time]

        # Process remaining spikes
        while data.size > 0:
            # Find spikes that fit on the most recent row.
            last_x_coord = last_spike_time % self.x_lim
            deltas = data - last_spike_time
            last_row_bool = (last_x_coord + deltas) <= self.x_lim

            seg_list = rs_info['segments']
            if np.any(last_row_bool):
                seg_list[0].xvals.extend(data[last_row_bool] % self.x_lim)
                self.raster_series[line_label]['last_spike_time'] = data[last_row_bool][-1]
                # Clear data that has already been added
                data = data[np.logical_not(last_row_bool)]

            # If there are any remaining spikes, shift all rows up.
            if data.size > 0:
                # Delete the oldest row
                self.plotWidget.removeItem(seg_list[-1])
                seg_list.pop()
                # Shift remaining rows up
                for vtg in seg_list:
                    vtg.setYRange([x+y_per_row for x in vtg.yRange()])
                # Add new empty row
                new_y_range = [x - y_per_row for x in seg_list[0].yRange()]
                new_vtg = pg.VTickGroup(xvals=None, yrange=new_y_range, pen=seg_list[0].pen)
                seg_list.insert(0, new_vtg)
                self.plotWidget.addItem(new_vtg)
                # update last_spike_time to beginning of new row
                self.raster_series[line_label]['last_spike_time'] -\
                    (self.raster_series[line_label]['last_spike_time'] % self.x_lim) + self.x_lim


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
        self.DTT = None
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
        yfont = self.axisY().labelsFont()
        yfont.setPointSize(LABEL_FONT_POINT_SIZE)
        self.axisY().setLabelsFont(yfont)

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

        start_time = int(get_now_time())
        self.scatter_series[line_label] = {
            'old': my_series[0],
            'latest': my_series[1],
            'chan_ix': len(self.scatter_series),  # To offset on y-axis
            'count': 0,
            'frate': 0,
            'start_time': start_time,
            'last_spike_time': start_time
        }

    def clear(self):
        start_time = int(get_now_time())
        for key in self.scatter_series:
            ss = self.scatter_series[key]
            ss['old'].clear()
            ss['latest'].clear()
            ss['count'] = 0
            ss['start_time'] = start_time
            ss['last_spike_time'] = start_time
            self.modify_frate(key, 0)

    def modify_frate(self, ss_key, new_frate):
        ss = self.scatter_series[ss_key]
        ss['frate'] = new_frate
        old_label = self.axisY().categoriesLabels()[ss['label_ix']]
        new_label = "{0:3.0f}.{1:d}".format(new_frate, ss['label_ix'])
        self.axisY().replaceLabel(old_label, new_label)
        self.frate_changed.emit(ss_key, new_frate)

    def parse_comments(self, comments):
        # comments is a list of lists: [[timestamp, string, rgba],]
        comment_strings = [x[1] for x in comments]
        dtts = []
        for comm_str in comment_strings:
            if 'DTT:' in comm_str:
                dtts.append(float(comm_str[4:]))
        if len(dtts) > 0:
            new_dtt = dtts[-1]
            if not self.DTT or self.DTT != new_dtt:
                self.clear()
                self.DTT = new_dtt

    def update(self, line_label, data):
        """
        :param line_label:
        :param data: A list of 6 numpy arrays, one for each sorted unit, each containing uint32 timestamps.
        :return:
        """
        data = np.uint32(np.concatenate(data))  # For now, put all sorted units into the same series.
        data.sort()

        ss_info = self.scatter_series[line_label]
        last_spike_time = ss_info['last_spike_time']
        data = data[data > last_spike_time]

        # Process remaining spikes
        if data.shape[0] > 0:
            y_offset = -ss_info['chan_ix']

            latest = ss_info['latest']  # QScatterSeries for most recent line
            old = ss_info['old']  # QScatterSeries for everything except most recent line

            # Add every spike, one by one
            for spk_x in data:
                spk_int = spk_x - last_spike_time  # num samples elapsed since last spike
                last_x_coord = last_spike_time % self.x_lim
                if (last_x_coord + spk_int) > self.x_lim:
                    # This spike goes on a new row.
                    # Move old points up
                    y_shift_old = np.floor((last_x_coord + spk_int) / self.x_lim)  # how many rows
                    old_points = QPolygonF(old.pointsVector())  # Copy of data points in QVector<QPoint>
                    if old_points.count() > 0:
                        old_points.translate(0, y_shift_old / (self.config['n_rows'] + 1))  # Move them up
                        old.replace(old_points)

                    # Transfer latest to old
                    transfer_points = QPolygonF(latest.pointsVector())
                    transfer_points.translate(0, y_shift_old / (self.config['n_rows'] + 1))
                    old.append(transfer_points)
                    latest.clear()

                    # Remove out of range points.
                    old_points = QPolygonF(old.pointsVector())  # Copy of data points in QVector<QPoint>
                    while old_points.count() > 0 \
                            and old_points.first().y() >= (y_offset + self.config['n_rows'] / (self.config['n_rows'] + 1)):
                        old_points.remove(0)
                    old.replace(old_points)

                latest.append(spk_x % self.x_lim,
                              y_offset + 1.0 / (self.config['n_rows'] + 1))
                last_spike_time = spk_x

            # Calculate and display firing rate. TODO: Slow down.
            new_count = ss_info['count'] + data.shape[0]
            new_frate = self.config['sampling_rate'] * new_count / (data[-1] - ss_info['start_time'])
            self.modify_frate(line_label, new_frate)  # Update labels

            # Store results
            self.scatter_series[line_label]['count'] = new_count
            self.scatter_series[line_label]['last_spike_time'] = data[-1]


if __name__ == '__main__':
    qapp = QApplication(sys.argv)
    aw = MyGUI()
    timer = QTimer()
    timer.timeout.connect(aw.update)
    timer.start(1)

    if (sys.flags.interactive != 1) or not hasattr(PyQt5.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()