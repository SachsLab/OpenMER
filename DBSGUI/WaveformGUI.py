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
WINDOWDIMS = [920, 0, 400, 1080]
XRANGE = 1500  # uSeconds
YRANGE = 400   # uV default
SIMOK = False  # Make this False for production. Make this True for development when NSP/NPlayServer are unavailable.


class WaveformGUI(CustomGUI):

    def __init__(self):
        super(WaveformGUI, self).__init__()
        self.setWindowTitle('Neuroport DBS - Waveform Plot')

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
        self.plot_widget = WaveformWidget(group_info)
        self.plot_widget.was_closed.connect(self.on_plot_closed)

    def on_plot_closed(self):
        self.plot_widget = None
        self.cbsdk_conn.cbsdk_config = {'reset': True, 'get_events': False, 'get_comments': False}

    def do_plot_update(self):
        self.plot_widget.update(None, None)
        comments = self.cbsdk_conn.get_comments()
        if comments:
            self.plot_widget.parse_comments(comments)


class WaveformWidget(CustomWidget):

    def __init__(self, *args, **kwargs):
        super(WaveformWidget, self).__init__(*args, **kwargs)
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
        self.wf_info = {}  # Will contain one dictionary for each line/channel label.
        for chan_ix in range(len(self.group_info)):
            self.add_series(self.group_info[chan_ix])

    def add_series(self, chan_info):
        new_plot = self.glw.addPlot(row=len(self.wf_info), col=0)

        # Appearance settings
        my_theme = THEMES[self.plot_config['theme']]
        self.plot_config['color_iterator'] = (self.plot_config['color_iterator'] + 1) % len(my_theme['pencolors'])
        pen_color = QColor(my_theme['pencolors'][self.plot_config['color_iterator']])

        now_time = int(get_now_time())
        self.wf_info[chan_info['label']] = {
            'plot': new_plot,
            'line_ix': len(self.wf_info),
            'chan_id': chan_info['chan'],
            'count': 0,
            'last_spike_time': now_time
        }

    def refresh_axes(self):
        self.x_lim = int(self.plot_config['x_range'] * self.samplingRate / 1000000)
        for wf_key in self.wf_info:
            plot = self.wf_info[wf_key]['plot']
            plot.setXRange(0, self.x_lim)
            plot.setYRange(-self.plot_config['y_range'], self.plot_config['y_range'])
            plot.hideAxis('bottom')
            plot.hideAxis('left')

    def clear(self):
        pass

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
        pass


if __name__ == '__main__':
    qapp = QApplication(sys.argv)
    aw = WaveformGUI()
    timer = QTimer()
    timer.timeout.connect(aw.update)
    timer.start(1)

    if (sys.flags.interactive != 1) or not hasattr(PyQt5.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()