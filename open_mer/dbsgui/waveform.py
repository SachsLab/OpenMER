import numpy as np
from qtpy import QtWidgets
import pyqtgraph as pg
from .utilities.pyqtgraph import parse_color_str, get_colormap
from .widgets.custom import CustomGUI, CustomWidget


class WaveformGUI(CustomGUI):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('WaveformGUI')

    @CustomGUI.widget_cls.getter
    def widget_cls(self):
        return WaveformWidget

    def on_plot_closed(self):
        self._plot_widget = None
        self._data_source.disconnect_requested()

    def do_plot_update(self):
        for label in self._plot_widget.wf_info:
            this_info = self._plot_widget.wf_info[label]
            temp_wfs, unit_ids = self._data_source.get_waveforms(this_info)
            self._plot_widget.update(label, [temp_wfs, unit_ids])

        comments = self._data_source.get_comments()
        if comments:
            self._plot_widget.parse_comments(comments)


class WaveformWidget(CustomWidget):

    def __init__(self, *args, **kwargs):
        self.DTT = None
        self.plot_config = {}
        super().__init__(*args, **kwargs)

    def create_control_panel(self):
        # Create control panel
        cntrl_layout = QtWidgets.QHBoxLayout()
        # +/- amplitude range
        cntrl_layout.addWidget(QtWidgets.QLabel("+/- "))
        self.range_edit = QtWidgets.QLineEdit("{:.2f}".format(250))  # Value overridden in create_plots
        self.range_edit.setMaximumWidth(80)
        self.range_edit.setMinimumHeight(23)
        self.range_edit.editingFinished.connect(self.on_range_edit_editingFinished)
        cntrl_layout.addWidget(self.range_edit)
        cntrl_layout.addStretch()

        # N Spikes
        cntrl_layout.addWidget(QtWidgets.QLabel("N Spikes "))
        self.n_spikes_edit = QtWidgets.QLineEdit("{}".format(100))  # Value overridden in create_plots
        self.n_spikes_edit.setMaximumWidth(80)
        self.n_spikes_edit.setMinimumHeight(23)
        self.n_spikes_edit.editingFinished.connect(self.on_n_spikes_edit_editingFinished)
        cntrl_layout.addWidget(self.n_spikes_edit)
        cntrl_layout.addStretch()

        # Clear button
        clear_button = QtWidgets.QPushButton("Clear")
        clear_button.clicked.connect(self.clear)
        clear_button.setMaximumWidth(80)
        cntrl_layout.addWidget(clear_button)
        # Finish
        self.layout().addLayout(cntrl_layout)

    def create_plots(self, plot={}, theme={}):
        # Collect PlotWidget configuration
        self.plot_config['theme'] = theme
        self.plot_config['x_range'] = (plot.get('x_start', -300), plot.get('x_stop', 1140))
        self.plot_config['y_range'] = plot.get('y_range', 250)
        self.plot_config['n_waveforms'] = plot.get('n_waveforms', 200)
        self.plot_config['unit_scaling'] = plot.get('unit_scaling', 0.25)

        # Update widget values without triggering signals
        prev_state = self.range_edit.blockSignals(True)
        self.range_edit.setText(str(self.plot_config['y_range']))
        self.range_edit.blockSignals(prev_state)
        prev_state = self.n_spikes_edit.blockSignals(True)
        self.n_spikes_edit.setText(str(self.plot_config['n_waveforms']))
        self.n_spikes_edit.blockSignals(prev_state)

        # Create and add GraphicsLayoutWidget
        glw = pg.GraphicsLayoutWidget(parent=self)
        # self.glw.useOpenGL(True)
        if 'bgcolor' in self.plot_config['theme']:
            glw.setBackground(parse_color_str(self.plot_config['theme']['bgcolor']))

        cmap = self.plot_config['theme']['colormap']
        if cmap != 'custom':
            cmap_colors = get_colormap(self.plot_config['theme']['colormap'],
                                       plot.get('n_colors', 6))
            self.plot_config['theme']['pencolors'] = np.vstack((255 * np.ones_like(cmap_colors[0]), cmap_colors))

        self.layout().addWidget(glw)
        self.wf_info = {}  # Will contain one dictionary for each line/channel label.
        for chan_state in self.chan_states:
            self.add_series(chan_state)

    def add_series(self, chan_state):
        glw = self.findChild(pg.GraphicsLayoutWidget)
        new_plot = glw.addPlot(row=len(self.wf_info), col=0, enableMenu=False)
        new_plot.setMouseEnabled(x=False, y=False)

        self.wf_info[chan_state['name']] = {
            'plot': new_plot,
            'line_ix': len(self.wf_info),
            'chan_id': chan_state['src']
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
        self.plot_config['n_waveforms'] = int(self.n_spikes_edit.text())
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
                pen_color = self.plot_config['theme']['pencolors'][unit_ids[ix]]
                c.setPen(pen_color)
                self.wf_info[line_label]['plot'].addItem(c)
                c.setData(x=x, y=self.plot_config['unit_scaling']*wfs[ix])
        data_items = self.wf_info[line_label]['plot'].listDataItems()
        if len(data_items) > self.plot_config['n_waveforms']:
            for di in data_items[:-self.plot_config['n_waveforms']]:
                self.wf_info[line_label]['plot'].removeItem(di)