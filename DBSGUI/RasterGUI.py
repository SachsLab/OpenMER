"""
chadwick.boulay@gmail.com
"""
import sys
import numpy as np
import PyQt5
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import pyqtgraph as pg
from custom import CustomGUI, CustomWidget, ConnectDialog, SAMPLINGGROUPS, get_now_time, THEMES


# TODO: Make some of these settings configurable via UI elements
# TODO: Load these constants from a config file.
WINDOWDIMS = [620, 0, 300, 1080]
XRANGE = 0.5  # Seconds
YRANGE = 8  # Number of rows.
LABEL_FONT_POINT_SIZE = 24
SIMOK = False  # Make this False for production. Make this True for development when NSP/NPlayServer are unavailable.


class RasterGUI(CustomGUI):

    def __init__(self):
        super(RasterGUI, self).__init__()
        self.setWindowTitle('Neuroport DBS - Raster Plot')

    def on_action_add_plot_triggered(self):
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
        self.plot_widget = RasterWidget(group_info)
        self.plot_widget.was_closed.connect(self.on_plot_closed)

    def on_plot_closed(self):
        self.plot_widget = None
        self.cbsdk_conn.cbsdk_config = {'reset': True, 'get_events': False, 'get_comments': False}

    def do_plot_update(self):
        ev_timestamps = self.cbsdk_conn.get_event_data()
        ev_chan_ids = [x[0] for x in ev_timestamps]
        for chan_label in self.plot_widget.rasters:
            ri = self.plot_widget.rasters[chan_label]
            if ri['chan_id'] in ev_chan_ids:
                data = ev_timestamps[ev_chan_ids.index(ri['chan_id'])][1]['timestamps']
            else:
                data = [[], ]
            self.plot_widget.update(chan_label, data)

        comments = self.cbsdk_conn.get_comments()
        if comments:
            self.plot_widget.parse_comments(comments)


class RasterWidget(CustomWidget):
    frate_changed = pyqtSignal(str, float)
    vtick = QPainterPath()
    vtick.moveTo(0, -0.5)
    vtick.lineTo(0, 0.5)

    def __init__(self, *args, **kwargs):
        super(RasterWidget, self).__init__(*args, **kwargs)
        self.move(WINDOWDIMS[0], WINDOWDIMS[1])
        self.resize(WINDOWDIMS[2], WINDOWDIMS[3])
        self.DTT = None

    def create_plots(self, theme='dark'):
        # Collect PlotWidget configuration
        self.plot_config = {
            'x_range': XRANGE,
            'y_range': YRANGE,
            'theme': theme,
            'color_iterator': -1
        }
        # Create and add GraphicsLayoutWidget
        self.glw = pg.GraphicsLayoutWidget()
        self.glw.useOpenGL(True)
        self.layout().addWidget(self.glw)
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
        frate_annotation.setPos(0, self.plot_config['y_range'])
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
            plot.setYRange(-0.05, self.plot_config['y_range']+0.05)
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
            keep_bool = (old_y + 1) < self.plot_config['y_range']
            self.rasters[line_label]['old'].setData(x=old_x[keep_bool], y=old_y[keep_bool] + 1)
            self.rasters[line_label]['count'] -= np.sum(np.logical_not(keep_bool))
        latest_x, latest_y = self.rasters[line_label]['latest'].getData()
        if latest_x.size > 0:
            self.rasters[line_label]['old'].addPoints(x=latest_x, y=latest_y + 1)
            # self.rasters[line_label]['latest'].clear()
            self.rasters[line_label]['latest'].setData(np.empty(0, dtype=self.rasters[line_label]['latest'].data.dtype))
        self.rasters[line_label]['start_time'] = max(self.rasters[line_label]['start_time'],
                                                     self.rasters[line_label]['last_spike_time']
                                                     - (self.x_lim * self.plot_config['y_range']))


if __name__ == '__main__':
    qapp = QApplication(sys.argv)
    aw = RasterGUI()
    timer = QTimer()
    timer.timeout.connect(aw.update)
    timer.start(1)

    if (sys.flags.interactive != 1) or not hasattr(PyQt5.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()