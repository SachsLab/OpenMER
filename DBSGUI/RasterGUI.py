"""
chadwick.boulay@gmail.com
"""
import sys
import os
import numpy as np
import qtpy
from qtpy.QtGui import QColor, QFont
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import Qt, QTimer, Signal
import pyqtgraph as pg
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'dbsgui'))
# Note: If import dbsgui fails, then set the working directory to be this script's directory.
from dbsgui.my_widgets.custom import CustomGUI, CustomWidget, ConnectDialog, SAMPLINGGROUPS, get_now_time, THEMES


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
        self.cbsdk_conn.cbsdk_config = {
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

        # Fetching comments is slow!
        comments = self.cbsdk_conn.get_comments()
        if comments:
            self.plot_widget.parse_comments(comments)


class RasterWidget(CustomWidget):
    frate_changed = Signal(str, float)

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
        glw = pg.GraphicsLayoutWidget(parent=self)
        # glw.useOpenGL(True)
        self.layout().addWidget(glw)
        self.rasters = {}  # Will contain one dictionary for each line/channel label.
        for chan_ix in range(len(self.group_info)):
            self.add_series(self.group_info[chan_ix])

    def add_series(self, chan_info):
        glw = self.findChild(pg.GraphicsLayoutWidget)
        new_plot = glw.addPlot(row=len(self.rasters), col=0)
        # Appearance settings
        my_theme = THEMES[self.plot_config['theme']]
        self.plot_config['color_iterator'] = (self.plot_config['color_iterator'] + 1) % len(my_theme['pencolors'])
        pen_color = QColor(my_theme['pencolors'][self.plot_config['color_iterator']])
        # Create PlotCurveItem for latest spikes (bottom row) and slower-updating old spikes (upper rows)
        pcis = []
        for pci_ix in range(2):
            pci = pg.PlotCurveItem(parent=new_plot, connect='pairs')
            pci.setPen(pen_color)
            new_plot.addItem(pci)
            pcis.append(pci)
        # Create text for displaying firing rate. Placeholder text is channel label.
        frate_annotation = pg.TextItem(text=chan_info['label'],
                                       color=(255, 255, 255))
        frate_annotation.setPos(0, self.plot_config['y_range'])
        my_font = QFont()
        my_font.setPointSize(24)
        frate_annotation.setFont(my_font)
        new_plot.addItem(frate_annotation)
        # Store information
        self.rasters[chan_info['label']] = {
            'plot': new_plot,
            'old': pcis[0],
            'latest': pcis[1],
            'line_ix': len(self.rasters),
            'chan_id': chan_info['chan'],
            'frate_item': frate_annotation
        }
        self.clear()

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
            rs['old'].clear()
            rs['latest'].clear()
            rs['old_timestamps'] = np.empty(0, dtype=np.uint32)
            rs['latest_timestamps'] = np.empty(0, dtype=np.uint32)
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
        comment_strings = [x[1].decode('utf8') for x in comments]
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
        now_time = int(get_now_time())
        new_t0 = now_time - (now_time % self.x_lim)
        rs = self.rasters[line_label]
        # Process data
        data = np.uint32(np.concatenate(data))  # For now, put all sorted units into the same unit.
        data = data[data > rs['last_spike_time']]  # Only keep spikes we haven't seen before.
        rs['latest_timestamps'] = np.append(rs['latest_timestamps'], data)
        rs['count'] += data.size
        if data.size > 0:
            rs['last_spike_time'] = max(data)
        # Move spikes that do not belong in the bottom row to the upper section (latest)
        move_bool = rs['latest_timestamps'] < new_t0
        if np.any(move_bool):
            rs['old_timestamps'] = np.append(rs['old_timestamps'], rs['latest_timestamps'][move_bool])
            rs['latest_timestamps'] = rs['latest_timestamps'][np.logical_not(move_bool)]
        # Remove spikes that are outside the plot_range
        top_row_t0 = new_t0 - self.x_lim * (self.plot_config['y_range'] - 1)
        remove_bool = rs['old_timestamps'] < top_row_t0
        if np.any(remove_bool):
            rs['old_timestamps'] = rs['old_timestamps'][np.logical_not(remove_bool)]
            rs['count'] -= np.sum(remove_bool)
        # Update bottom section of plot (latest)
        if (data.size > 0) or np.any(move_bool) or (new_t0 != rs['latest_t0']):
            # Update latest
            x_vals = np.repeat(rs['latest_timestamps'] - rs['latest_t0'], 2)
            y_vals = 0.1 * np.ones_like(x_vals)
            y_vals[1::2] += 0.8
            rs['latest'].setData(x=x_vals, y=y_vals)
        # Update upper section of plot (old)
        if np.any(move_bool) or (new_t0 != rs['latest_t0']):
            # Update old
            x_vals = rs['old_timestamps'] % self.x_lim
            y_vals = 1.1 * np.ones_like(x_vals)
            for row_ix in range(1, self.plot_config['y_range']):
                row_cutoff = new_t0 - (row_ix * self.x_lim)
                y_vals[rs['old_timestamps'] < row_cutoff] += 1
            x_vals = np.repeat(x_vals, 2)
            y_vals = np.repeat(y_vals, 2)
            y_vals[1::2] += 0.8
            rs['old'].setData(x=x_vals, y=y_vals)
        # Save some variables
        rs['latest_t0'] = new_t0
        rs['start_time'] = max(rs['start_time'], rs['last_spike_time'] - top_row_t0)
        # Update frate annotation.
        samples_elapsed = rs['last_spike_time'] - rs['start_time']
        if samples_elapsed > 0:
            frate = self.rasters[line_label]['count'] * self.samplingRate / samples_elapsed
            self.modify_frate(line_label, frate)


if __name__ == '__main__':
    qapp = QApplication(sys.argv)
    aw = RasterGUI()
    timer = QTimer()
    timer.timeout.connect(aw.update)
    timer.start(1)

    if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()