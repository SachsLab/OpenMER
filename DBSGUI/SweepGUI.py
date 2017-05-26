import sys
import numpy as np
from scipy import signal
import pyaudio
import PyQt5
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from PyQt5.QtWidgets import QDialogButtonBox, QCheckBox, QLineEdit, QButtonGroup, QRadioButton, QApplication
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg
from cbsdkConnection import CbSdkConnection
from custom import CustomWidget, ConnectDialog, SAMPLINGGROUPS, get_now_time, THEMES, CustomGUI


# TODO: Make some of these settings configurable via UI elements
# TODO: Load these constants from a config file.
WINDOWDIMS = [0, 0, 620, 1080]
WINDOWDIMS_LFP = [1320, 220, 600, 860]
NPLOTSEGMENTS = 20  # Divide the plot into this many segments; each segment will be updated independent of rest.
XRANGE = 1.05 # seconds. Purposely slightly different to 1.0 so the NSS output doesn't overlap perfectly.
YRANGE = 800  # y-axis range per channel, use +- this value.
FILTERCONFIG = {'order': 4, 'cutoff': 250, 'type': 'highpass', 'output': 'sos'}
DSFAC = 100
SIMOK = False  # Make this False for production. Make this True for development when NSP/NPlayServer are unavailable.


class SweepGUI(CustomGUI):

    def __init__(self):
        super(SweepGUI, self).__init__()
        self.setWindowTitle('Neuroport DBS - Continuous Sweeps')
        self.plot_widget = {}

    def on_action_add_plot_triggered(self):
        group_ix, do_downsample = AddSamplingGroupDialog.do_samplinggroup_dialog()
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
        self.plot_widget[(group_ix, do_downsample)] = SweepWidget(group_info,
                                                                  group_ix=group_ix,
                                                                  downsample=do_downsample)
        self.plot_widget[(group_ix, do_downsample)].was_closed.connect(self.on_plot_closed)

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
        # Comment above and uncomment below to test if trying to exclude cbsdk.
        # for sweep_key in self.plot_widget:
        #     for gi in self.plot_widget[sweep_key].group_info:
        #         data = np.random.randint(-500, 500, size=(10000,), dtype=np.int16)
        #         self.plot_widget[sweep_key].update(gi['label'], data)


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

        # Check this box to create a new alternate window. This enables viewing the data twice (e.g., filtered and raw)
        self.downsample_checkbox = QCheckBox("Downsample")
        self.downsample_checkbox.setChecked(False)
        layout.addWidget(self.downsample_checkbox)

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
            return dialog.combo_box.currentIndex(), dialog.downsample_checkbox.checkState() == Qt.Checked
        return -1, False


class SweepWidget(CustomWidget):
    def __init__(self, *args, **kwargs):
        self.plot_config = {}
        self.segmented_series = {}  # Will contain one array of curves for each line/channel label.
        super(SweepWidget, self).__init__(*args, **kwargs)
        this_dims = WINDOWDIMS
        if 'downsample' in self.plot_config and self.plot_config['downsample']:
            this_dims = WINDOWDIMS_LFP
        self.move(this_dims[0], this_dims[1])
        self.resize(this_dims[2], this_dims[3])
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
        # Checkbox for HP filter
        filter_checkbox = QCheckBox("HP")
        filter_checkbox.stateChanged.connect(self.on_hp_filter_changed)
        filter_checkbox.setChecked(True)
        cntrl_layout.addWidget(filter_checkbox)
        # Checkbox for Comb filter
        filter_checkbox = QCheckBox("LN")
        filter_checkbox.setEnabled(False)
        filter_checkbox.stateChanged.connect(self.on_ln_filter_changed)
        filter_checkbox.setChecked(False)
        cntrl_layout.addWidget(filter_checkbox)
        # Finish
        self.layout().addLayout(cntrl_layout)

    def on_hp_filter_changed(self, state):
        self.plot_config['do_hp'] = state == Qt.Checked

    def on_ln_filter_changed(self, state):
        self.plot_config['do_ln'] = state == Qt.Checked

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
                new_thresh = int(inf_line.getYPos())
                cbsdkconn = CbSdkConnection()
                cbsdkconn.set_channel_info(ss_info['chan_id'], {'spkthrlevel': new_thresh})

    def create_plots(self, theme='dark', downsample=False):
        # Collect PlotWidget configuration
        self.plot_config['downsample'] = downsample
        self.plot_config['x_range'] = XRANGE
        self.plot_config['y_range'] = YRANGE
        self.plot_config['theme'] = theme
        self.plot_config['color_iterator'] = -1
        self.plot_config['n_segments'] = NPLOTSEGMENTS
        if 'do_hp' not in self.plot_config:
            self.plot_config['do_hp'] = False
        self.plot_config['hp_sos'] = signal.butter(FILTERCONFIG['order'],
                                                   2 * FILTERCONFIG['cutoff'] / self.samplingRate,
                                                   btype=FILTERCONFIG['type'],
                                                   output=FILTERCONFIG['output'])
        if 'do_ln' not in self.plot_config:
            self.plot_config['do_ln'] = False
        self.plot_config['ln_filt'] = None  # TODO: comb filter coeffs

        # Create and add GraphicsLayoutWidget
        glw = pg.GraphicsLayoutWidget(parent=self)
        # glw.useOpenGL(True)  # Actually seems slower.
        self.layout().addWidget(glw)
        # Add add a plot with a series of many curve segments for each line.
        for chan_ix in range(len(self.group_info)):
            self.add_series(self.group_info[chan_ix])

    def add_series(self, chan_info):
        # Plot for this channel
        glw = self.findChild(pg.GraphicsLayoutWidget)
        new_plot = glw.addPlot(row=len(self.segmented_series), col=0, title=chan_info['label'], enableMenu=False)
        new_plot.setMouseEnabled(x=False, y=False)

        # Appearance settings
        my_theme = THEMES[self.plot_config['theme']]
        self.plot_config['color_iterator'] = (self.plot_config['color_iterator'] + 1) % len(my_theme['pencolors'])
        pen_color = QColor(my_theme['pencolors'][self.plot_config['color_iterator']])

        # Prepare plot data
        samples_per_segment = int(
            np.ceil(self.plot_config['x_range'] * self.samplingRate / self.plot_config['n_segments']))
        for ix in range(self.plot_config['n_segments']):
            if ix < (self.plot_config['n_segments'] - 1):
                seg_x = np.arange(ix * samples_per_segment, (ix + 1) * samples_per_segment, dtype=np.int16)
            else:
                # Last segment might not be full length.
                seg_x = np.arange(ix * samples_per_segment,
                                  int(self.plot_config['x_range'] * self.samplingRate), dtype=np.int16)
            if self.plot_config['downsample']:
                seg_x = seg_x[::DSFAC]
            c = new_plot.plot(parent=new_plot, pen=pen_color)  # PlotDataItem
            c.setData(x=seg_x, y=np.zeros_like(seg_x))  # Pre-fill.

        # Add threshold line
        thresh_line = pg.InfiniteLine(angle=0, movable=True)
        thresh_line.sigPositionChangeFinished.connect(self.on_thresh_line_moved)
        new_plot.addItem(thresh_line)

        self.segmented_series[chan_info['label']] = {
            'chan_id': chan_info['chan'],
            'line_ix': len(self.segmented_series),
            'plot': new_plot,
            'last_sample_ix': -1,
            'thresh_line': thresh_line,
            'hp_zi': signal.sosfilt_zi(self.plot_config['hp_sos']),
            'ln_zi': None
        }

    def refresh_axes(self):
        last_sample_ix = int(np.mod(get_now_time(), self.plot_config['x_range']) * self.samplingRate)
        for line_label in self.segmented_series:
            ss_info = self.segmented_series[line_label]

            # Fixup axes
            plot = ss_info['plot']
            plot.setXRange(0, self.plot_config['x_range'] * self.samplingRate)
            plot.setYRange(-self.plot_config['y_range'], self.plot_config['y_range'])
            plot.hideAxis('bottom')
            plot.hideAxis('left')

            # Reset data
            for seg_ix in range(self.plot_config['n_segments']):
                pci = plot.dataItems[seg_ix]
                old_x, old_y = pci.getData()
                pci.setData(x=old_x, y=np.zeros_like(old_x))
                ss_info['last_sample_ix'] = last_sample_ix

            # Get channel info from cbpy to determine threshold
            cbsdkconn = CbSdkConnection()
            full_info = cbsdkconn.get_channel_info(ss_info['chan_id'])
            ss_info['thresh_line'].setValue(full_info['spkthrlevel'])

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

    def update(self, line_label, data):
        """

        :param line_label: Label of the segmented series
        :param data: Replace data in the segmented series with these data
        :return:
        """
        ss_info = self.segmented_series[line_label]
        n_in = data.shape[0]
        if self.plot_config['do_hp']:
            data, ss_info['hp_zi'] = signal.sosfilt(self.plot_config['hp_sos'], data, zi=ss_info['hp_zi'])
        if self.plot_config['do_ln']:
            pass  # TODO: Line noise / comb filter
        if self.pya_stream:
            if 'chan_label' in self.audio and self.audio['chan_label']:
                if self.audio['chan_label'] == line_label:
                    write_indices = (np.arange(data.shape[0]) + self.audio['write_ix']) % self.audio['buffer'].shape[0]
                    self.audio['buffer'][write_indices] = (np.copy(data) * (2**15 / self.plot_config['y_range'])).astype(np.int16)
                    self.audio['write_ix'] = (self.audio['write_ix'] + data.shape[0]) % self.audio['buffer'].shape[0]

        # Assume new samples are consecutively added to old samples (i.e., no lost samples)
        sample_indices = np.arange(n_in, dtype=np.int32) + ss_info['last_sample_ix']

        # Wrap sample indices around our plotting limit
        n_plot_samples = int(self.plot_config['x_range'] * self.samplingRate)
        sample_indices = np.int32(np.mod(sample_indices, n_plot_samples))

        # If the data length is longer than one sweep then the indices will overlap. Trim to last n_plot_samples
        if sample_indices.size > n_plot_samples:
            sample_indices = sample_indices[-n_plot_samples:]
            data = data[-n_plot_samples:]

        # Go through each plotting segment and replace data with new data as needed.
        for pci in ss_info['plot'].dataItems:
            old_x, old_y = pci.getData()
            x_lims = [old_x[0], old_x[-1]]
            if self.plot_config['downsample']:
                x_lims[1] += (DSFAC - 1)
            data_bool = np.logical_and(sample_indices >= x_lims[0], sample_indices <= x_lims[-1])
            if np.where(data_bool)[0].size > 0:
                new_x, new_y = sample_indices[data_bool], data[data_bool]
                if self.plot_config['downsample']:
                    new_x = new_x[::DSFAC] - (new_x[0] % DSFAC) + (old_x[0] % DSFAC)
                    new_y = new_y[::DSFAC]
                old_bool = np.in1d(old_x, new_x, assume_unique=True)
                new_bool = np.in1d(new_x, old_x, assume_unique=True)
                old_y[old_bool] = new_y[new_bool]
                # old_y[np.where(old_bool)[0][-1]+1:] = 0  # Uncomment to zero out the end of the last seg.
                pci.setData(x=old_x, y=old_y)
        # Store last_sample_ix for next iteration.
        self.segmented_series[line_label]['last_sample_ix'] = sample_indices[-1]


if __name__ == '__main__':
    qapp = QApplication(sys.argv)
    aw = SweepGUI()
    timer = QTimer()
    timer.timeout.connect(aw.update)
    timer.start(1)

    if (sys.flags.interactive != 1) or not hasattr(PyQt5.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()