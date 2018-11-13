"""
chadwick.boulay@gmail.com
"""
import sys
import os
import numpy as np
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QPushButton, QLineEdit, QHBoxLayout, QLabel
import pyqtgraph as pg
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'dbsgui'))
# Note: If import dbsgui fails, then set the working directory to be this script's directory.
from dbsgui.my_widgets.custom import CustomGUI, CustomWidget, ConnectDialog, SAMPLINGGROUPS


# TODO: Make some of these settings configurable via UI elements
# TODO: Load these constants from a config file.
WINDOWDIMS = [920, 0, 400, 1080]
XRANGE = [-300, 1140]  # uSeconds
YRANGE = 250      # uV default
NWAVEFORMS = 20  # Max number of waveforms to plot.
SIMOK = False     # Make this False for production. Make this True for development when NSP/NPlayServer are unavailable.
WF_COLORS = ["white", "magenta", "cyan", "yellow", "purple", "green"]


class WaveformGUI(CustomGUI):

    def __init__(self):
        super(WaveformGUI, self).__init__()
        self.setWindowTitle('Neuroport DBS - Waveform Plot')

    def on_action_add_plot_triggered(self):
        self.cbsdk_conn.cbsdk_config ={
            'reset': True, 'get_events': False, 'get_comments': True,
            'buffer_parameter': {
                'comment_length': 10
            }
        }
        group_info = self.cbsdk_conn.get_group_config(SAMPLINGGROUPS.index("30000"))
        for gi_item in group_info:
            gi_item['label'] = gi_item['label'].decode('utf-8')
            gi_item['unit'] = gi_item['unit'].decode('utf-8')
        self.plot_widget = WaveformWidget(group_info)
        self.plot_widget.was_closed.connect(self.on_plot_closed)
        self.wf_config = self.cbsdk_conn.get_sys_config()  # {'spklength': 48, 'spkpretrig': 10, 'sysfreq': 30000}

    def on_plot_closed(self):
        self.plot_widget = None
        self.cbsdk_conn.cbsdk_config = {'reset': True, 'get_events': False, 'get_comments': False}

    def do_plot_update(self):
        for label in self.plot_widget.wf_info:
            this_info = self.plot_widget.wf_info[label]
            temp_wfs, unit_ids = self.cbsdk_conn.get_waveforms(this_info['chan_id'])
            self.plot_widget.update(label, [temp_wfs, unit_ids])

        # Fetching comments is SLOW!
        comments = self.cbsdk_conn.get_comments()
        if comments:
            self.plot_widget.parse_comments(comments)


class WaveformWidget(CustomWidget):

    def __init__(self, *args, **kwargs):
        super(WaveformWidget, self).__init__(*args, **kwargs)
        # super calls self.create_control_panel(), self.create_plots(**kwargs), self.refresh_axes()
        self.move(WINDOWDIMS[0], WINDOWDIMS[1])
        self.resize(WINDOWDIMS[2], WINDOWDIMS[3])
        self.DTT = None

    def create_control_panel(self):
        # Create control panel
        cntrl_layout = QHBoxLayout()
        # +/- amplitude range
        cntrl_layout.addWidget(QLabel("+/-"))
        self.range_edit = QLineEdit("{:.2f}".format(YRANGE))
        self.range_edit.editingFinished.connect(self.on_range_edit_editingFinished)
        cntrl_layout.addWidget(self.range_edit)
        # N Spikes
        cntrl_layout.addWidget(QLabel("N Spikes"))
        self.n_spikes_edit = QLineEdit("{}".format(NWAVEFORMS))
        self.n_spikes_edit.editingFinished.connect(self.on_n_spikes_edit_editingFinished)
        cntrl_layout.addWidget(self.n_spikes_edit)
        # Clear button
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear)
        cntrl_layout.addWidget(clear_button)
        # Finish
        self.layout().addLayout(cntrl_layout)

    def create_plots(self, theme='dark'):
        # Collect PlotWidget configuration
        self.plot_config = {
            'x_range': XRANGE,
            'y_range': YRANGE,
            'theme': theme,
            'color_iterator': -1,
            'n_wfs': NWAVEFORMS
        }
        # Create and add GraphicsLayoutWidget
        glw = pg.GraphicsLayoutWidget(parent=self)
        # self.glw.useOpenGL(True)
        self.layout().addWidget(glw)
        self.wf_info = {}  # Will contain one dictionary for each line/channel label.
        for chan_ix in range(len(self.group_info)):
            self.add_series(self.group_info[chan_ix])

    def add_series(self, chan_info):
        glw = self.findChild(pg.GraphicsLayoutWidget)
        new_plot = glw.addPlot(row=len(self.wf_info), col=0)

        # Appearance settings
        # my_theme = THEMES[self.plot_config['theme']]
        # self.plot_config['color_iterator'] = (self.plot_config['color_iterator'] + 1) % len(my_theme['pencolors'])
        # pen_color = QColor(my_theme['pencolors'][self.plot_config['color_iterator']])

        self.wf_info[chan_info['label']] = {
            'plot': new_plot,
            'line_ix': len(self.wf_info),
            'chan_id': chan_info['chan']
        }

    def refresh_axes(self):
        for wf_key in self.wf_info:
            plot = self.wf_info[wf_key]['plot']
            plot.setXRange(self.plot_config['x_range'][0], self.plot_config['x_range'][1])
            plot.setYRange(-self.plot_config['y_range'], self.plot_config['y_range'])
            plot.hideAxis('bottom')
            plot.hideAxis('left')

    def clear(self):
        for line_label in self.wf_info:
            self.wf_info[line_label]['plot'].clear()

    def on_range_edit_editingFinished(self):
        self.plot_config['y_range'] = float(self.range_edit.text())
        self.refresh_axes()

    def on_n_spikes_edit_editingFinished(self):
        self.plot_config['n_wfs'] = int(self.n_spikes_edit.text())
        self.refresh_axes()

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

        :param line_label: Label of the plot series
        :param data: Replace data in the plot with these data
        :return:
        """
        wfs, unit_ids = data
        x = (1000000 / self.samplingRate) * np.arange(wfs.shape[1]) + self.plot_config['x_range'][0]
        for ix in range(wfs.shape[0]):
            if np.sum(np.nonzero(wfs[ix])) > 0:
                c = pg.PlotCurveItem()
                pen_color = QColor(WF_COLORS[unit_ids[ix]])
                c.setPen(pen_color)
                self.wf_info[line_label]['plot'].addItem(c)
                c.setData(x=x, y=0.25*wfs[ix])
        data_items = self.wf_info[line_label]['plot'].listDataItems()
        if len(data_items) > self.plot_config['n_wfs']:
            for di in data_items[:-self.plot_config['n_wfs']]:
                self.wf_info[line_label]['plot'].removeItem(di)


if __name__ == '__main__':
    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import QTimer
    qapp = QApplication(sys.argv)
    aw = WaveformGUI()
    timer = QTimer()
    timer.timeout.connect(aw.update)
    timer.start(1)

    if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()