"""
chadwick.boulay@gmail.com
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
                for chan_label in self.raster_widget.rasters:
                    ri = self.raster_widget.rasters[chan_label]
                    if ri['chan_id'] in ev_chan_ids:
                        data = ev_timestamps[ev_chan_ids.index(ri['chan_id'])][1]['timestamps']
                    else:
                        data = [[], ]
                    self.raster_widget.update(chan_label, data)

                comments = self.cbsdk_conn.get_comments()
                if comments:
                    self.raster_widget.parse_comments(comments)


class RasterWidget(CustomWidget):
    frate_changed = pyqtSignal(str, float)
    vtick = QPainterPath()
    vtick.moveTo(0, -0.5)
    vtick.lineTo(0, 0.5)

    def __init__(self, *args, theme='dark', **kwargs):
        super(RasterWidget, self).__init__(*args, **kwargs)
        self.resize(600, PLOTHEIGHT)
        self.setup_control_panel()
        self.setup_plot_widget(theme=theme)
        self.refresh_axes()
        self.DTT = None

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
        # Create and add GraphicsLayoutWidget
        self.glw = pg.GraphicsLayoutWidget()
        # self.glw.useOpenGL(True)
        self.layout().addWidget(self.glw)

        # Configure the PlotWidget
        self.plot_config = {
            'x_range': RASTDURATION,
            'n_rows': RASTROWS,
            'theme': theme,
            'color_iterator': -1
        }

        self.rasters = {}  # Will contain one dictionary for each line/channel label.
        for chan_ix in range(len(self.group_info)):
            self.add_series(self.group_info[chan_ix])

    def add_series(self, chan_info):
        new_plot = self.glw.addPlot(row=len(self.rasters), col=0)

        # Appearance settings
        my_theme = THEMES[self.plot_config['theme']]
        self.plot_config['color_iterator'] = (self.plot_config['color_iterator'] + 1) % len(my_theme['pencolors'])
        pen_color = QColor(my_theme['pencolors'][self.plot_config['color_iterator']])

        spis = []
        for spi_ix in range(2):
            spi = pg.ScatterPlotItem(pxMode=False)
            spi.setSymbol(self.vtick)
            spi.setSize(0.8)
            spi.setPen(pen_color)
            new_plot.addItem(spi)
            spis.append(spi)

        frate_annotation = pg.TextItem(text=chan_info['label'],
                                       color=(255, 255, 255))
        frate_annotation.setPos(0, self.plot_config['n_rows'])
        my_font = QFont()
        my_font.setPointSize(24)
        frate_annotation.setFont(my_font)
        new_plot.addItem(frate_annotation)

        start_time = int(get_now_time())

        self.rasters[chan_info['label']] = {
            'plot': new_plot,
            'old': spis[0],
            'latest': spis[1],
            'line_ix': len(self.rasters),
            'chan_id': chan_info['chan'],
            'count': 0,
            'frate': 0,
            'frate_item': frate_annotation,
            'start_time': start_time,
            'latest_t0': start_time - (start_time % (self.plot_config['x_range'] * self.samplingRate)),
            'last_spike_time': start_time
        }

    def refresh_axes(self):
        self.x_lim = int(self.plot_config['x_range'] * self.samplingRate)
        for rs_key in self.rasters:
            plot = self.rasters[rs_key]['plot']
            plot.setXRange(0, self.plot_config['x_range'] * self.samplingRate)
            plot.setYRange(-0.05, self.plot_config['n_rows']+0.05)
            plot.hideAxis('bottom')
            plot.hideAxis('left')

    def clear(self):
        start_time = int(get_now_time())
        for key in self.rasters:
            rs = self.rasters[key]
            # rs['old'].clear()
            rs['old'].setData(np.empty(0, dtype=rs['old'].data.dtype))
            # rs['latest'].clear()
            rs['latest'].setData(np.empty(0, dtype=rs['latest'].data.dtype))
            rs['count'] = 0
            rs['start_time'] = start_time
            rs['latest_t0'] = start_time - (start_time % (self.plot_config['x_range'] * self.samplingRate))
            rs['last_spike_time'] = start_time
            self.modify_frate(key, 0)

    def modify_frate(self, rs_key, new_frate):
        self.rasters[rs_key]['frate'] = new_frate
        new_label = "{0:3.0f}".format(new_frate)
        self.rasters[rs_key]['frate_item'].setText(new_label)
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
        if len(data[0]) == 0:
            # If data is empty, get_now_time and shift up if necessary.
            now_time = int(get_now_time())
            while (now_time - self.rasters[line_label]['latest_t0']) > self.x_lim:
                self.shift_up(line_label)
        else:
            # Process data
            data = np.uint32(np.concatenate(data))  # For now, put all sorted units into the same series.
            data.sort()
            # Only keep recent spikes
            data = data[np.logical_and(data > self.rasters[line_label]['last_spike_time'],
                                       data > self.rasters[line_label]['latest_t0'])]

            # Process remaining spikes
            while data.size > 0:
                add_data_bool = np.logical_and(data > self.rasters[line_label]['latest_t0'],
                                               data <= self.rasters[line_label]['latest_t0'] + self.x_lim)
                add_count = np.sum(add_data_bool)
                if add_count > 0:
                    self.rasters[line_label]['latest'].addPoints(x=data[add_data_bool] % self.x_lim,
                                                                 y=0.5*np.ones(np.sum(add_data_bool)))
                    self.rasters[line_label]['last_spike_time'] = data[add_data_bool][-1]
                    self.rasters[line_label]['count'] += add_count
                    data = data[np.logical_not(add_data_bool)]

                if data.size > 0:
                    self.shift_up(line_label)

        samples_elapsed = self.rasters[line_label]['last_spike_time'] - self.rasters[line_label]['start_time']
        if samples_elapsed > 0:
            frate = self.rasters[line_label]['count'] * self.samplingRate / samples_elapsed
            self.modify_frate(line_label, frate)

    def shift_up(self, line_label):
        self.rasters[line_label]['latest_t0'] += self.x_lim
        old_x, old_y = self.rasters[line_label]['old'].getData()
        if old_x.size > 0:
            keep_bool = (old_y + 1) < self.plot_config['n_rows']
            self.rasters[line_label]['old'].setData(x=old_x[keep_bool], y=old_y[keep_bool] + 1)
            self.rasters[line_label]['count'] -= np.sum(np.logical_not(keep_bool))
        latest_x, latest_y = self.rasters[line_label]['latest'].getData()
        if latest_x.size > 0:
            self.rasters[line_label]['old'].addPoints(x=latest_x, y=latest_y + 1)
            # self.rasters[line_label]['latest'].clear()
            self.rasters[line_label]['latest'].setData(np.empty(0, dtype=self.rasters[line_label]['latest'].data.dtype))
        self.rasters[line_label]['start_time'] = max(self.rasters[line_label]['start_time'],
                                                     self.rasters[line_label]['last_spike_time']
                                                     - (self.x_lim * self.plot_config['n_rows']))


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