import sys
import numpy as np
import time
import PyQt5
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtChart import *
from cbsdkConnection import CbSdkConnection
from scipy import signal

# TODO: Make some of these settings configurable via UI elements
# TODO: Load these constants from a config file.
PLOTHEIGHT = 800
NPLOTSEGMENTS = 20  # Divide the plot into this many segments; each segment will be updated independent of rest.
RAWDURATION = 1.0
HPDURATION = 1.0
XRANGE = 1.0  # seconds
YRANGE = 2000  # y-axis range per channel, use +- this value.
RASTDURATION = 0.5
RASTROWS = 6
FILTERCONFIG = {'order': 4, 'cutoff': 250, 'type': 'highpass', 'output': 'sos'}
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
        self.sweep_widgets = {}
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
            "AddSweep": QAction("Add Sweep Plot", self),
            "AddRaster": QAction("Add Raster Plot", self),
        }
        self.actions["Connect"].triggered.connect(self.on_action_connect_triggered)
        self.actions["AddSweep"].triggered.connect(self.on_action_add_sweep_triggered)
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
        file_menu.addAction(self.actions["AddSweep"])
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

    def on_action_add_sweep_triggered(self):
        group_ix, do_filter = AddSamplingGroupDialog.do_samplinggroup_dialog()
        if group_ix == -1:
            print("Add group canceled")
            return

        self.cbsdk_conn.cbsdk_config = {'reset': True, 'get_continuous': True}

        group_info = self.cbsdk_conn.get_group_config(group_ix)

        for gi_item in group_info:
            gi_item['label'] = gi_item['label'].decode('utf-8')
            gi_item['unit'] = gi_item['unit'].decode('utf-8')

        # Chart container
        self.sweep_widgets[(group_ix, do_filter)] = SweepWidget(group_info, group_ix=group_ix, do_filter=do_filter)
        self.sweep_widgets[(group_ix, do_filter)].was_closed.connect(self.on_sweep_closed)

    def on_sweep_closed(self):
        del_list = []
        for key in self.sweep_widgets:
            if self.sweep_widgets[key].awaiting_close:
                del_list.append(key)

        for key in del_list:
            del self.sweep_widgets[key]

        if not self.sweep_widgets:
            self.cbsdk_conn.cbsdk_config = {'reset': True, 'get_continuous': False}

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
            if self.sweep_widgets:
                cont_data = self.cbsdk_conn.get_continuous_data()
                if cont_data is not None:
                    cont_chan_ids = [x[0] for x in cont_data]
                    for sweep_key in self.sweep_widgets:
                        chart_chan_ids = [x['chan'] for x in self.sweep_widgets[sweep_key].group_info]
                        match_chans = list(set(cont_chan_ids) & set(chart_chan_ids))
                        for chan_id in match_chans:
                            data = cont_data[cont_chan_ids.index(chan_id)][1]
                            label = self.sweep_widgets[sweep_key].group_info[chart_chan_ids.index(chan_id)]['label']
                            self.sweep_widgets[sweep_key].chart.update(label, data)

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


class AddSamplingGroupDialog(QDialog):
    """
    A modal dialog window with widgets to select the channel group to add.
    """
    def __init__(self, parent=None):
        super(AddSamplingGroupDialog, self).__init__(parent)

        # Widgets to show/edit connection parameters.
        layout = QVBoxLayout(self)

        # Chan group layout
        chan_group_layout = QHBoxLayout()
        chan_group_layout.addWidget(QLabel("Sampling Group"))
        self.combo_box = QComboBox()
        self.combo_box.addItems(SAMPLINGGROUPS)
        self.combo_box.setCurrentIndex(SAMPLINGGROUPS.index("30000"))
        chan_group_layout.addWidget(self.combo_box)
        layout.addLayout(chan_group_layout)

        # Do filter
        self.filter_checkbox = QCheckBox("250 Hz hp filter")
        layout.addWidget(self.filter_checkbox)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def do_samplinggroup_dialog(parent=None):
        dialog = AddSamplingGroupDialog(parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            # Get channel group from widgets and return it
            return dialog.combo_box.currentIndex(), dialog.filter_checkbox.checkState() == Qt.Checked
        return -1, False


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


class SweepWidget(MyWidget):
    def __init__(self, *args, do_filter=False, **kwargs):
        super(SweepWidget, self).__init__(*args, **kwargs)

        # Initialize chart
        self.chart = SegmentedChart(sampling_rate=self.samplingRate)
        for chan_ix in range(len(self.group_info)):
            label_string = self.group_info[chan_ix]['label']
            self.chart.add_series(line_label=label_string,
                                  do_filter=do_filter)
        self.chart.refresh_axes()

        # Create control panel
        # +/- range
        cntrl_layout = QHBoxLayout()
        cntrl_layout.addWidget(QLabel("+/-"))
        self.range_edit = QLineEdit("{:.2f}".format(self.chart.y_range))
        self.range_edit.editingFinished.connect(self.on_range_edit_editingFinished)
        cntrl_layout.addWidget(self.range_edit)
        # buttons for audio monitoring
        cntrl_layout.addStretch(1)
        cntrl_layout.addWidget(QLabel("Monitor: "))
        monitor_group = QButtonGroup(parent=self)
        none_button = QRadioButton("None")
        none_button.setChecked(True)
        monitor_group.addButton(none_button)
        monitor_group.setId(none_button, 0)
        cntrl_layout.addWidget(none_button)
        for chan_ix in range(len(self.group_info)):
            new_button = QRadioButton(self.group_info[chan_ix]['label'])
            monitor_group.addButton(new_button)
            monitor_group.setId(new_button, chan_ix+1)
            cntrl_layout.addWidget(new_button)
        monitor_group.buttonClicked[int].connect(self.on_monitor_group_clicked)

        # Add control panel and chart to widget
        self.layout().addLayout(cntrl_layout)
        self.layout().addWidget(QChartView(self.chart))

    def on_range_edit_editingFinished(self):
        self.chart.y_range = float(self.range_edit.text())
        self.chart.refresh_axes()

    def on_monitor_group_clicked(self, button_id):
        if button_id == 0:
            chan_ix = None
        else:
            chan_ix = self.group_info[button_id-1]['chan']
        CbSdkConnection().monitor_chan(chan_ix)


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


class SegmentedChart(MyChart):
    """
    High-performance chart.
    Each series is an array of BufferSeries segments.
    Updates to the chart data will update only the necessary segments.
    """
    def __init__(self, total_duration=RAWDURATION, n_segments=NPLOTSEGMENTS, sampling_rate=None, **kwargs):
        super(SegmentedChart, self).__init__(**kwargs)
        self.x_range = XRANGE
        self.y_range = YRANGE
        self.segments_config = {
            'duration': total_duration,
            'sampling_rate': sampling_rate,
            'n_segments': n_segments,
        }
        self.segmented_series = {}  # Will contain one array of BufferSeries for each line/channel.
        self.refresh_axes()

    def refresh_axes(self):
        # Remove all existing labels
        for label in self.axisX().categoriesLabels():
            self.axisX().remove(label)
        for label in self.axisY().categoriesLabels():
            self.axisY().remove(label)

        # Add X-axis labels.
        n_samples = self.segments_config['duration'] * self.segments_config['sampling_rate']
        self.axisX().setRange(0, n_samples)
        self.axisX().setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
        self.axisX().append("0", 0)
        self.axisX().append("{:.1f}".format(self.segments_config['duration']), n_samples)

        # Add Y-axis labels. Note, categories have to be added in ascending order.
        min_y = (1 - 2 * len(self.segmented_series)) * self.y_range
        self.axisY().setRange(min_y, self.y_range)
        self.axisY().setStartValue(min_y)
        # Sort self.segmented_series according to -line_ix
        seg_series_list = sorted(self.segmented_series.items(), key=lambda x: x[1]['line_ix'], reverse=True)
        for kv_tup in seg_series_list:
            ss_info = self.segmented_series[kv_tup[0]]
            y_max = self.y_range - ss_info['line_ix'] * 2 * self.y_range
            self.axisY().append(kv_tup[0], y_max)

    def add_series(self, sampling_rate=30000, line_label="new line", do_filter=False):
        self.color_iterator = (self.color_iterator + 1) % len(THEMES[self.theme]['pencolors'])
        pen_color = THEMES[self.theme]['pencolors'][self.color_iterator]
        n_samples = int(self.segments_config['duration'] * sampling_rate)
        # zeros for y-axis
        # xdata = np.linspace(1. / sampling_rate, self.segments_config['duration'], n_samples)  # Time x-axis in s
        xdata = np.arange(n_samples, dtype=np.int32)  # Time x-axis in samples
        samples_per_segment = int(np.ceil(n_samples / self.segments_config['n_segments']))
        series_segments = []
        # TODO: Duplicate last sample in previous sequence as first in next to make line continuous
        for ix in range(self.segments_config['n_segments']):
            ix_offset = ix*samples_per_segment
            this_x = xdata[ix_offset:ix_offset+samples_per_segment]  # Last segment might not be full length.
            series_segment = BufferSeries(xdata=this_x, sample_offset=ix_offset, pen_color=pen_color)
            self.addSeries(series_segment)
            series_segment.attachAxis(self.axisX())
            series_segment.attachAxis(self.axisY())
            series_segments.append(series_segment)

        if do_filter:
            sos = signal.butter(FILTERCONFIG['order'], 2 * FILTERCONFIG['cutoff'] / sampling_rate,
                                btype=FILTERCONFIG['type'], output=FILTERCONFIG['output'])
            my_filter = {'sos': sos, 'zi': signal.sosfilt_zi(sos)}
        else:
            my_filter = None

        # Attempt to synchronize different series using machine time.
        last_sample_ix = int(np.mod(get_now_time(), self.segments_config['duration']) * sampling_rate)

        self.segmented_series[line_label] = {
            'segments': series_segments,
            'sampling_rate': sampling_rate,
            'filter': my_filter,
            'last_sample_ix': last_sample_ix,
            'line_ix': len(self.segmented_series)
        }
        # TODO: Per series y-scaling.

    def update(self, line_label, data):
        """

        :param line_label: Label of the segmented series
        :param data: Replace data in the segmented series with these data
        :return:
        """
        ss_info = self.segmented_series[line_label]
        fs = ss_info['sampling_rate']
        n_samples = data.shape[0]

        my_filter = ss_info['filter']
        if my_filter:
            data, my_filter['zi'] = signal.sosfilt(my_filter['sos'], data, zi=my_filter['zi'])

        y_offset = int(ss_info['line_ix'] * 2 * self.y_range)
        data -= y_offset

        sample_indices = ss_info['last_sample_ix'] + np.arange(n_samples, dtype=np.int32)
        max_ind = np.int32(fs * self.segments_config['duration'])
        sample_indices = np.int32(np.mod(sample_indices, max_ind))

        # If the data is longer than one sweep (e.g., was process sleeping while off-screen),
        # then the indices will overlap. So we find the last ones.
        if sample_indices.size > max_ind:
            sample_indices = sample_indices[-max_ind:]
            data = data[-max_ind:]

        seg_series = ss_info['segments']

        ss_offsets = np.asarray([ss.sample_offset for ss in seg_series])
        # Find the segment that includes the last sample that was updated.
        last_segment_ix = np.where(sample_indices[-1] >= ss_offsets)[0][-1]

        for seg_ix in range(len(seg_series)):
            ss = seg_series[seg_ix]
            seg_sample_indices = ss.sample_offset + np.arange(ss.count())
            data_bool = np.in1d(sample_indices, seg_sample_indices, assume_unique=True)
            if np.any(data_bool):
                seg_bool = np.in1d(seg_sample_indices, sample_indices, assume_unique=True)
                ss.replace_data(data[data_bool], sample_bool=seg_bool)

                # Clear out the rest of last_segment_ix
                if seg_ix == last_segment_ix:
                    clear_bool = np.logical_and(seg_sample_indices > sample_indices[-1],
                                                seg_sample_indices < sample_indices[-1]+10)
                    clear_dat = -y_offset * np.ones((np.sum(clear_bool), ), dtype=np.int32)
                    ss.replace_data(clear_dat, sample_bool=clear_bool)

        self.segmented_series[line_label]['last_sample_ix'] = sample_indices[-1]


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
                latest.append(spk, y_offset + 1.0/(self.config['n_rows'] + 1))
            data = data[np.logical_not(add_bool)]  # Remove from data

        # Remaining spike times should be added to a new line and old spike times shifted up.
        if data.shape[0] > 0:
            old = ss_info['old']

            # Shift old points up 1
            old_points = QPolygonF(old.pointsVector())  # Copy of data points in QVector<QPoint>
            if old_points.count() > 0:
                old_points.translate(0, 1.0/(self.config['n_rows'] + 1))  # Move them up 1
                # Remove out of range points.
                while old_points.first().y() >= (1 + y_offset):
                    old_points.remove(0)
                old.replace(old_points)

            # Shift new->old points up 1
            transfer_points = QPolygonF(latest.pointsVector())
            transfer_points.translate(0, 1.0/(self.config['n_rows'] + 1))
            old.append(transfer_points)

            latest.clear()
            for spk in data:
                latest.append(spk - self.x_lim, y_offset + 1.0/(self.config['n_rows'] + 1))

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


class BufferSeries(QLineSeries):
    # dtype = np.float
    dtype = np.int32

    def __init__(self, xdata=None, sample_offset=0, pen_color="blue", **kwargs):
        """
        :param xdata: X-axis values. Typically samples time in seconds.
        :param sample_offset:  If this is in a sequence of segments, how many samples precede this segment.
        :param pen_color: QColor or known color string ("blue", "red", "green", etc.)
        :param kwargs:  To pass on to QLineSeries initializer.
        """
        super(BufferSeries, self).__init__(**kwargs)
        self.qpoly = None
        self.np_buffer = None
        self.sample_offset = sample_offset
        pen_color = QColor(pen_color)
        # pen_color.setAlphaF(0.1)  # Does not work with setUseOpenGL
        self.setPen(QPen(pen_color))
        self.setUseOpenGL(True)  # Causes crash when moving dock around. Improves performance.
        self.reset_data(xdata)

    @property
    def x_offset(self):
        return self.at(0).x()

    def reset_data(self, xdata=None):
        """
        :param xdata: Will fill up the x-values of (QPolygon) self.qpoly. Also used to determine size.
        :return: no return
        """
        xdata = xdata if xdata is not None else np.asarray([])
        ydata = np.zeros(xdata.shape, dtype=self.dtype)
        n_samples = xdata.shape[0]
        # bytes_per_sample = np.finfo(self.dtype).dtype.itemsize
        bytes_per_sample = np.iinfo(self.dtype).dtype.itemsize
        # self.qpoly = QPolygonF(n_samples)
        self.qpoly = QPolygon(n_samples)
        pointer = self.qpoly.data()
        pointer.setsize(2 * self.qpoly.size() * bytes_per_sample)
        self.np_buffer = np.frombuffer(pointer, self.dtype)
        self.np_buffer[:(n_samples - 1) * 2 + 1:2] = xdata
        self.np_buffer[1:(n_samples - 1) * 2 + 2:2] = ydata
        self.replace(self.qpoly)

    def replace_data(self, ydata, sample_bool=None):
        old_ydata = self.np_buffer[1::2]
        if sample_bool is None:
            sample_bool = np.zeros(old_ydata.shape, dtype=np.bool)
            sample_bool[:ydata.shape[0]] = True
        if np.any(sample_bool):
            old_ydata[sample_bool] = ydata
            # old_ydata[np.logical_not(sample_bool)] = 0.
            self.replace(self.qpoly)  # Big memory leak
            return True
        else:
            return False


if __name__ == '__main__':
    qapp = QApplication(sys.argv)
    aw = MyGUI()
    timer = QTimer()
    timer.timeout.connect(aw.update)
    timer.start(1)

    if (sys.flags.interactive != 1) or not hasattr(PyQt5.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()