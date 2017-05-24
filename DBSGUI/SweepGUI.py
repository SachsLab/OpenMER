import sys
import numpy as np
from scipy import signal
import pyaudio
import PyQt5
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMainWindow, QAction, QToolBar, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from PyQt5.QtWidgets import QDialogButtonBox, QCheckBox, QLineEdit, QButtonGroup, QRadioButton, QApplication
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg
from cbsdkConnection import CbSdkConnection
from custom import CustomWidget, ConnectDialog, SAMPLINGGROUPS, get_now_time, THEMES, CustomGUI


# TODO: Make some of these settings configurable via UI elements
# TODO: Load these constants from a config file.
WINDOWDIMS = [0, 0, 620, 1080]
NPLOTSEGMENTS = 20  # Divide the plot into this many segments; each segment will be updated independent of rest.
RAWDURATION = 1.0
HPDURATION = 1.0
XRANGE = 1.0  # seconds
YRANGE = 800  # y-axis range per channel, use +- this value.
FILTERCONFIG = {'order': 4 , 'cutoff': 250, 'type': 'highpass', 'output': 'sos'}
SIMOK = False  # Make this False for production. Make this True for development when NSP/NPlayServer are unavailable.


class SweepGUI(CustomGUI):

    def __init__(self):
        super(SweepGUI, self).__init__()
        self.setWindowTitle('Neuroport DBS - Continuous Sweeps')
        self.plot_widget = {}

    def on_action_add_plot_triggered(self):
        group_ix, do_filter = AddSamplingGroupDialog.do_samplinggroup_dialog()
        if group_ix == -1:
            print("Add group canceled")
            return

        self.cbsdk_conn.cbsdk_config = {'reset': True, 'get_continuous': True}

        group_info = self.cbsdk_conn.get_group_config(group_ix)

        if group_info is None:
            raise ValueError("No group info retrieved from cbsdk. Are you connected?")

        for gi_item in group_info:
            gi_item['label'] = gi_item['label'].decode('utf-8')
            gi_item['unit'] = gi_item['unit'].decode('utf-8')

        # Chart container
        self.plot_widget[(group_ix, do_filter)] = SweepWidget(group_info, group_ix=group_ix, do_filter=do_filter)
        self.plot_widget[(group_ix, do_filter)].was_closed.connect(self.on_plot_closed)

    def on_plot_closed(self):
        del_list = []
        for key in self.plot_widget:
            if self.plot_widget[key].awaiting_close:
                del_list.append(key)

        for key in del_list:
            del self.plot_widget[key]

        if not self.plot_widget:
            self.cbsdk_conn.cbsdk_config = {'reset': True, 'get_continuous': False}

    def do_plot_update(self):
        cont_data = self.cbsdk_conn.get_continuous_data()
        if cont_data is not None:
            cont_chan_ids = [x[0] for x in cont_data]
            for sweep_key in self.plot_widget:
                chart_chan_ids = [x['chan'] for x in self.plot_widget[sweep_key].group_info]
                match_chans = list(set(cont_chan_ids) & set(chart_chan_ids))
                for chan_id in match_chans:
                    data = cont_data[cont_chan_ids.index(chan_id)][1]
                    label = self.plot_widget[sweep_key].group_info[chart_chan_ids.index(chan_id)]['label']
                    self.plot_widget[sweep_key].update(label, data)


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
        self.filter_checkbox.setChecked(True)
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


class SweepWidget(CustomWidget):
    def __init__(self, *args, **kwargs):
        super(SweepWidget, self).__init__(*args, **kwargs)
        self.move(WINDOWDIMS[0], WINDOWDIMS[1])
        self.resize(WINDOWDIMS[2], WINDOWDIMS[3])
        self.refresh_axes()  # Extra time on purpose.
        self.pya_manager = pyaudio.PyAudio()
        self.pya_stream = None
        self.audio = {}
        self.reset_audio()

    def closeEvent(self, evnt):
        if self.pya_stream:
            if self.pya_stream.is_active():
                self.pya_stream.stop_stream()
            self.pya_stream.close()
        self.pya_manager.terminate()
        super(SweepWidget, self).closeEvent(evnt)

    def create_control_panel(self):
        # Create control panel
        # +/- range
        cntrl_layout = QHBoxLayout()
        cntrl_layout.addWidget(QLabel("+/-"))
        self.range_edit = QLineEdit("{:.2f}".format(YRANGE))
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
            monitor_group.setId(new_button, chan_ix + 1)
            cntrl_layout.addWidget(new_button)
        monitor_group.buttonClicked[int].connect(self.on_monitor_group_clicked)
        self.monitor_chan_label = None
        self.layout().addLayout(cntrl_layout)

    def create_plots(self, theme='dark', do_filter=True):
        # Collect PlotWidget configuration
        self.plot_config = {
            'x_range': XRANGE,
            'y_range': YRANGE,
            'theme': theme,
            'color_iterator': -1
        }
        self.plot_config['n_segments'] = NPLOTSEGMENTS
        self.plot_config['do_filter'] = do_filter
        # Create and add PlotWidget
        self.plotWidget = pg.PlotWidget()
        self.plotWidget.useOpenGL(True)
        self.layout().addWidget(self.plotWidget)
        self.segmented_series = {}  # Will contain one array of curves for each line/channel label.
        for chan_ix in range(len(self.group_info)):
            self.add_series(self.group_info[chan_ix],
                            sampling_rate=self.samplingRate,
                            do_filter=self.plot_config['do_filter'])

    def on_range_edit_editingFinished(self):
        self.plot_config['y_range'] = float(self.range_edit.text())
        self.refresh_axes()

    def on_monitor_group_clicked(self, button_id):
        self.reset_audio()
        if button_id == 0:
            self.audio['chan_label'] = 'silence'
            monitor_chan_id = 0
        else:
            self.audio['chan_label'] = self.group_info[button_id - 1]['label']
            monitor_chan_id = self.group_info[button_id - 1]['chan']
        CbSdkConnection().monitor_chan(monitor_chan_id)

    def on_thresh_line_moved(self, inf_line):
        for line_label in self.segmented_series:
            ss_info = self.segmented_series[line_label]
            if ss_info['thresh_line'] == inf_line:
                new_thresh = int(inf_line.getYPos() - ss_info['y_offset'])
                cbsdkconn = CbSdkConnection()
                cbsdkconn.set_channel_info(ss_info['chan_id'], {'spkthrlevel': new_thresh})

    def add_series(self, chan_info, sampling_rate=30000, do_filter=False):
        # Appearance settings
        my_theme = THEMES[self.plot_config['theme']]
        self.plot_config['color_iterator'] = (self.plot_config['color_iterator'] + 1) % len(my_theme['pencolors'])
        pen_color = QColor(my_theme['pencolors'][self.plot_config['color_iterator']])

        # Prepare plot data
        n_samples = int(self.plot_config['x_range'] * sampling_rate)
        xdata = np.arange(n_samples, dtype=np.int32)  # Time x-axis in samples
        samples_per_segment = int(np.ceil(n_samples / self.plot_config['n_segments']))
        curve_segments = []
        for ix in range(self.plot_config['n_segments']):
            ix_offset = ix * samples_per_segment
            this_x = xdata[ix_offset:ix_offset + samples_per_segment]  # Last segment might not be full length.
            c = pg.PlotCurveItem(pen=pen_color)
            self.plotWidget.addItem(c)
            c.setData(y=np.zeros(this_x.shape))  # Pre-fill. Use zeros because we do not know offset.
            curve_segments.append(c)

        if do_filter:
            sos = signal.butter(FILTERCONFIG['order'], 2 * FILTERCONFIG['cutoff'] / sampling_rate,
                                btype=FILTERCONFIG['type'], output=FILTERCONFIG['output'])
            my_filter = {'sos': sos, 'zi': signal.sosfilt_zi(sos)}
        else:
            my_filter = None

        # Attempt to synchronize different series using machine time.
        last_sample_ix = int(np.mod(get_now_time(), self.plot_config['x_range']) * sampling_rate)

        # Add threshold line
        thresh_line = pg.InfiniteLine(angle=0, movable=True)
        thresh_line.sigPositionChangeFinished.connect(self.on_thresh_line_moved)
        self.plotWidget.addItem(thresh_line)

        self.segmented_series[chan_info['label']] = {
            'segments': curve_segments,
            'sampling_rate': sampling_rate,  # Per-line sampling_rate not supported at this time.
            'filter': my_filter,
            'last_sample_ix': last_sample_ix,
            'line_ix': len(self.segmented_series),
            'thresh_line': thresh_line,
            'chan_id': chan_info['chan']
        }

    def reset_audio(self):
        if self.pya_stream:
            if self.pya_stream.is_active():
                self.pya_stream.stop_stream()
            self.pya_stream.close()
        self.audio['buffer'] = np.zeros(int(0.25*self.samplingRate), dtype=np.int16)
        self.audio['write_ix'] = 0
        self.audio['read_ix'] = 0
        self.audio['chan_label'] = None
        self.pya_stream = self.pya_manager.open(format=pyaudio.paInt16,
                                                channels=1,
                                                rate=self.samplingRate,
                                                output=True,
                                                stream_callback=self.pyaudio_callback)

    def pyaudio_callback(self,
                         in_data,  # recorded data if input=True; else None
                         frame_count,  # number of frames. 1024.
                         time_info,  # dictionary
                         status_flags):  # PaCallbackFlags
        # time_info: {'input_buffer_adc_time': ??, 'current_time': ??, 'output_buffer_dac_time': ??}
        # status_flags: https://people.csail.mit.edu/hubert/pyaudio/docs/#pacallbackflags
        read_indices = (np.arange(frame_count) + self.audio['read_ix']) % self.audio['buffer'].shape[0]
        out_data = self.audio['buffer'][read_indices].tobytes()
        self.audio['read_ix'] = (self.audio['read_ix'] + frame_count) % self.audio['buffer'].shape[0]
        flag = pyaudio.paContinue
        return out_data, flag

    def refresh_axes(self):
        n_samples = self.plot_config['x_range'] * self.samplingRate

        # X-axis
        x_ax_item = self.plotWidget.getPlotItem().getAxis('bottom')
        x_ax_item.setTicks([
            [(0, "0"), (n_samples, "{0:.2f}".format(n_samples / self.samplingRate))],
        ])
        x_ax_item.setLabel(name="Time", unit="s")
        self.plotWidget.setXRange(0, n_samples, padding=0)

        # Y-axis
        min_y = (1 - 2 * len(self.segmented_series)) * self.plot_config['y_range']
        self.plotWidget.setYRange(min_y, self.plot_config['y_range'])
        new_y_ticks = []
        samples_per_segment = int(np.ceil(n_samples / self.plot_config['n_segments']))
        for line_label in self.segmented_series:
            ss_info = self.segmented_series[line_label]
            y_offset = int(-ss_info['line_ix'] * 2 * self.plot_config['y_range'])
            ss_info['y_offset'] = y_offset
            new_y_ticks.append((y_offset, line_label))
            for ix in range(len(ss_info['segments'])):
                x_offset = ix * samples_per_segment
                ss_info['segments'][ix].setPos(x_offset, y_offset)

            # Get channel info from cbpy to determine threshold
            cbsdkconn = CbSdkConnection()
            full_info = cbsdkconn.get_channel_info(ss_info['chan_id'])
            ss_info['thresh_line'].setValue(y_offset + full_info['spkthrlevel'])

        y_ax_item = self.plotWidget.getPlotItem().getAxis('left')
        y_ax_item.setTicks([new_y_ticks])

    def update(self, line_label, data):
        """

        :param line_label: Label of the segmented series
        :param data: Replace data in the segmented series with these data
        :return:
        """
        ss_info = self.segmented_series[line_label]
        n_in = data.shape[0]

        my_filter = ss_info['filter']
        if my_filter:
            data, my_filter['zi'] = signal.sosfilt(my_filter['sos'], data, zi=my_filter['zi'])

        if self.pya_stream:
            if 'chan_label' in self.audio and self.audio['chan_label']:
                if self.audio['chan_label'] == line_label:
                    write_indices = (np.arange(data.shape[0]) + self.audio['write_ix']) % self.audio['buffer'].shape[0]
                    self.audio['buffer'][write_indices] = (np.copy(data) * (2**15 / self.plot_config['y_range'])).astype(np.int16)
                    self.audio['write_ix'] = (self.audio['write_ix'] + data.shape[0]) % self.audio['buffer'].shape[0]

        sample_indices = ss_info['last_sample_ix'] + np.arange(n_in, dtype=np.int32)
        max_ind = np.int32(ss_info['sampling_rate'] * self.plot_config['x_range'])
        sample_indices = np.int32(np.mod(sample_indices, max_ind))

        # If the data is longer than one sweep (e.g., process sleeping while off-screen),
        # then the indices will overlap. So we take only the samples that will be plotted..
        if sample_indices.size > max_ind:
            sample_indices = sample_indices[-max_ind:]
            data = data[-max_ind:]

        # Get the sample-offset for each segment.
        n_samples = int(self.plot_config['x_range'] * ss_info['sampling_rate'])
        samples_per_segment = int(np.ceil(n_samples / self.plot_config['n_segments']))
        x_offsets = np.asarray([ix * samples_per_segment for ix in range(self.plot_config['n_segments'])])

        # Find the segment that includes the last sample that was updated.
        last_segment_ix = np.where(sample_indices[-1] >= x_offsets)[0][-1]

        all_x = np.arange(n_samples, dtype=np.int32)  # Time x-axis in samples
        for seg_ix in range(self.plot_config['n_segments']):
            x_off = x_offsets[seg_ix]
            seg_x = all_x[x_off:x_off + samples_per_segment]
            data_bool = np.in1d(sample_indices, seg_x, assume_unique=True)
            if np.any(data_bool):
                seg_bool = np.in1d(seg_x, sample_indices, assume_unique=True)
                # Get old yData
                pci = ss_info['segments'][seg_ix]  # PlotCurveItem
                old_y = pci.yData
                old_y[seg_bool] = data[data_bool]

                # Clear out the rest of last_segment_ix
                if seg_ix == last_segment_ix:
                    clear_bool = np.logical_and(seg_x > sample_indices[-1],
                                                seg_x < sample_indices[-1] + 10)
                    old_y[clear_bool] = np.zeros((np.sum(clear_bool),), dtype=np.int32)

                # pci yData has been changed, but setData does more than just modify the data.
                pci.setData(old_y)

        self.segmented_series[line_label]['last_sample_ix'] = sample_indices[-1]

        # TODO: occasionally check channel config for spk thresh,
        # self.segmented_series[line_label]['thresh_line'].setValue(offset + thresh)


if __name__ == '__main__':
    qapp = QApplication(sys.argv)
    aw = SweepGUI()
    timer = QTimer()
    timer.timeout.connect(aw.update)
    timer.start(1)

    if (sys.flags.interactive != 1) or not hasattr(PyQt5.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()