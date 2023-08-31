import json
import numpy as np
from scipy import signal
import pyaudio
from qtpy import QtCore, QtWidgets
import pyqtgraph as pg
import zmq

from .utilities.pyqtgraph import parse_color_str, make_qcolor, get_colormap
from .widgets.custom import CustomWidget, CustomGUI
from ..data_source import get_now_time


class SweepGUI(CustomGUI):

    def __init__(self):
        super(SweepGUI, self).__init__()
        self.setWindowTitle('SweepGUI')

    @CustomGUI.widget_cls.getter
    def widget_cls(self):
        return SweepWidget

    def on_plot_closed(self):
        if self._plot_widget is not None and self._plot_widget.awaiting_close:
            del self._plot_widget
            self._plot_widget = None
        if not self._plot_widget:
            self._data_source.disconnect_requested()

    def do_plot_update(self):
        cont_data = self._data_source.get_continuous_data()
        if cont_data is not None:
            cont_chan_ids = [x[0] for x in cont_data]
            chart_chan_ids = [x['src'] for x in self._plot_widget.chan_states]
            match_chans = list(set(cont_chan_ids) & set(chart_chan_ids))
            for chan_id in match_chans:
                ch_ix = cont_chan_ids.index(chan_id)
                data = cont_data[ch_ix][1]
                label = self._plot_widget.chan_states[ch_ix]['name']
                self._plot_widget.update(label, data, ch_state=self._plot_widget.chan_states[ch_ix])


class SweepWidget(CustomWidget):

    def __init__(self, *args, zmq_chan_port=60003, **kwargs):
        """
        *args typically contains a data_source dict with entries for 'srate', 'channel_names', 'chan_states'
        **kwargs typically contains dicts for configuring the plotter, including 'filter', 'plot', and 'theme'.
        """
        self._monitor_group = None  # QtWidgets.QButtonGroup(parent=self)
        self.plot_config = {}
        self.segmented_series = {}  # Will contain one array of curves for each line/channel label.

        context = zmq.Context()
        self._chanselect_sock = context.socket(zmq.PUB)
        self._chanselect_sock.bind(f"tcp://*:{zmq_chan_port}")

        super().__init__(*args, **kwargs)
        self.refresh_axes()  # Even though super __init__ calls this, extra refresh is intentional
        self.pya_manager = pyaudio.PyAudio()
        self.pya_stream = None
        self.audio = {}
        self.reset_audio()
        self.publish_chanselect()

    def keyPressEvent(self, e):
        valid_keys = [QtCore.Qt.Key_0, QtCore.Qt.Key_1, QtCore.Qt.Key_2, QtCore.Qt.Key_3, QtCore.Qt.Key_4, QtCore.Qt.Key_5, QtCore.Qt.Key_6, QtCore.Qt.Key_7, QtCore.Qt.Key_8,
                      QtCore.Qt.Key_9][:len(self.chan_states) + 1]
        current_button_id = self._monitor_group.checkedId()
        new_button_id = None
        if e.key() == QtCore.Qt.Key_Left:
            new_button_id = (current_button_id - 1) % (len(self.chan_states) + 1)
        elif e.key() == QtCore.Qt.Key_Right:
            new_button_id = (current_button_id + 1) % (len(self.chan_states) + 1)
        elif e.key() == QtCore.Qt.Key_Space:
            new_button_id = 0
        elif e.key() in valid_keys:
            new_button_id = valid_keys.index(e.key())

        if new_button_id is not None:
            button = self._monitor_group.button(new_button_id)
            button.setChecked(True)
            self.on_monitor_group_clicked(button)

    def closeEvent(self, evnt):
        if self.pya_stream:
            if self.pya_stream.is_active():
                self.pya_stream.stop_stream()
            self.pya_stream.close()
        self.pya_manager.terminate()
        super().closeEvent(evnt)

    def create_control_panel(self):
        # Create control panel
        # +/- range
        cntrl_layout = QtWidgets.QHBoxLayout()
        cntrl_layout.addWidget(QtWidgets.QLabel("+/- "))
        self.range_edit = QtWidgets.QLineEdit("{:.2f}".format(250))  # Value overridden in create_plots
        self.range_edit.editingFinished.connect(self.on_range_edit_editingFinished)
        self.range_edit.setMinimumHeight(23)
        self.range_edit.setMaximumWidth(80)
        cntrl_layout.addWidget(self.range_edit)
        # buttons for audio monitoring
        cntrl_layout.addStretch(1)
        cntrl_layout.addWidget(QtWidgets.QLabel("Monitor: "))
        self._monitor_group = QtWidgets.QButtonGroup(parent=self)
        none_button = QtWidgets.QRadioButton("None")
        none_button.setChecked(True)
        self._monitor_group.addButton(none_button)
        self._monitor_group.setId(none_button, 0)
        cntrl_layout.addWidget(none_button)
        for chan_ix, chan_label in enumerate(self.labels):
            new_button = QtWidgets.QRadioButton(chan_label)
            self._monitor_group.addButton(new_button)
            self._monitor_group.setId(new_button, chan_ix + 1)
            cntrl_layout.addWidget(new_button)
        self._monitor_group.buttonClicked.connect(self.on_monitor_group_clicked)
        # Checkbox for whether the audio out should be spike only
        spk_aud_checkbox = QtWidgets.QCheckBox("Spike Aud")
        spk_aud_checkbox.setObjectName("spkaud_CheckBox")
        spk_aud_checkbox.setTristate(False)
        spk_aud_checkbox.setChecked(True)
        spk_aud_checkbox.stateChanged.connect(self.on_spk_aud_changed)
        cntrl_layout.addWidget(spk_aud_checkbox)
        # Checkbox for HP filter
        filter_checkbox = QtWidgets.QCheckBox("HP")
        filter_checkbox.setObjectName("hpfilt_CheckBox")
        filter_checkbox.setTristate(False)
        filter_checkbox.setChecked(True)
        filter_checkbox.stateChanged.connect(self.on_hp_filter_changed)
        cntrl_layout.addWidget(filter_checkbox)
        # Checkbox for Comb filter
        filter_checkbox = QtWidgets.QCheckBox("LN")
        filter_checkbox.setObjectName("lnfilt_CheckBox")
        filter_checkbox.setTristate(False)
        filter_checkbox.setChecked(False)
        filter_checkbox.setEnabled(False)
        filter_checkbox.stateChanged.connect(self.on_ln_filter_changed)
        filter_checkbox.setVisible(False)
        cntrl_layout.addWidget(filter_checkbox)
        # Checkbox for lock thresholds
        threshlock_checkbox = QtWidgets.QCheckBox("Lk Thr")
        threshlock_checkbox.setObjectName("lkthr_CheckBox")
        threshlock_checkbox.setTristate(False)
        threshlock_checkbox.setChecked(False)
        cntrl_layout.addWidget(threshlock_checkbox)
        # Finish
        self.layout().addLayout(cntrl_layout)

    def update_monitor_channel(self, chan_state, spike_only):
        # Let other processes know we've changed the monitor channel
        self.parent()._data_source.update_monitor(chan_state, spike_only=spike_only)
        self.publish_chanselect()

    def on_spk_aud_changed(self, state):
        current_button_id = self._monitor_group.checkedId()
        if current_button_id > 0:
            chan_state = self.chan_states[current_button_id - 1]
            self.update_monitor_channel(chan_state, state == QtCore.Qt.Checked)

    def on_hp_filter_changed(self, state):
        self.plot_config['do_hp'] = state == QtCore.Qt.Checked
        self.publish_chanselect()

    def on_ln_filter_changed(self, state):
        self.plot_config['do_ln'] = state == QtCore.Qt.Checked

    def on_range_edit_editingFinished(self):
        self.plot_config['y_range'] = np.float64(self.range_edit.text())
        self.refresh_axes()
        self.publish_chanselect()

    def on_monitor_group_clicked(self, button):
        self.reset_audio()
        this_label = ''
        if button.text() == 'None':
            self.audio['chan_label'] = 'silence'
            chan_state = {'src': 0}
        else:
            this_label = button.text()
            button_idx = self.labels.index(this_label)
            self.audio['chan_label'] = this_label
            chan_state = self.chan_states[button_idx]

        # Reset plot titles
        active_kwargs = {'color': parse_color_str(self.plot_config['theme'].get('labelcolor_active', 'yellow')),
                         'size': str(self.plot_config['theme'].get('labelsize_active', 15)) + 'pt'}
        inactive_kwargs = {'color': self.plot_config['theme'].get('labelcolor_inactive', None),
                           'size': str(self.plot_config['theme'].get('labelsize_inactive', 11)) + 'pt'}
        if inactive_kwargs['color'] is not None:
            inactive_kwargs['color'] = parse_color_str(inactive_kwargs['color'])
        for label in self.labels:
            plot_item = self.segmented_series[label]['plot']
            label_kwargs = active_kwargs if label == this_label else inactive_kwargs
            plot_item.setTitle(title=plot_item.titleLabel.text, **label_kwargs)

        spk_aud_cb = self.findChild(QtWidgets.QCheckBox, name="spkaud_CheckBox")
        self.update_monitor_channel(chan_state, spk_aud_cb.checkState() == QtCore.Qt.Checked)

    def publish_chanselect(self):
        chan_labels = [_['name'] for _ in self.chan_states]
        if self.audio['chan_label'] in ['silence', None]:
            curr_channel = 0
        else:
            curr_channel = chan_labels.index(self.audio['chan_label']) + 1  # 0 == None
        self._chanselect_sock.send_string("channel_select " + json.dumps({
            "channel": curr_channel,
            "label": self.audio["chan_label"] or "",
            "range": self.plot_config['y_range'],
            "highpass": self.plot_config['do_hp']
        }))

    def on_thresh_line_moved(self, inf_line):
        new_thresh = None
        for line_label in self.segmented_series:
            ss_info = self.segmented_series[line_label]
            if ss_info['thresh_line'] == inf_line:
                new_thresh = int(inf_line.getYPos() / self.plot_config['unit_scaling'])
                # Let other processes know we've changed the threshold line.
                self.parent()._data_source.update_threshold(ss_info, new_thresh)
                # TODO: shared mem?
        lkthr_cb = self.findChild(QtWidgets.QCheckBox, name="lkthr_CheckBox")
        if new_thresh is not None and lkthr_cb.checkState() == QtCore.Qt.Checked:
            for line_label in self.segmented_series:
                ss_info = self.segmented_series[line_label]
                if ss_info['thresh_line'] != inf_line:
                    ss_info['thresh_line'].setPos(new_thresh * self.plot_config['unit_scaling'])
                    self.parent()._data_source.update_threshold(ss_info, new_thresh)

    def create_plots(self, plot={}, filter={}, theme={}, alt_loc=False):
        # Collect PlotWidget configuration
        self.plot_config['theme'] = theme
        self.plot_config['downsample'] = plot.get('downsample', 1)
        self.plot_config['x_range'] = plot.get('x_range', 1.0)
        self.plot_config['y_range'] = plot.get('y_range', 250)
        # Update the range_edit text, but block its signal when doing so
        prev_state = self.range_edit.blockSignals(True)
        self.range_edit.setText(str(self.plot_config['y_range']))
        self.range_edit.blockSignals(prev_state)
        self.plot_config['n_segments'] = plot.get('n_segments', 20)
        # Default scaling of 0.25 -- Data are 16-bit integers from -8192 uV to +8192 uV. We want plot scales in uV.
        self.plot_config['unit_scaling'] = plot.get('unit_scaling', 0.25)
        self.plot_config['alt_loc'] = alt_loc
        self.plot_config['color_iterator'] = -1
        self.plot_config['do_hp'] = filter.get('order', 4) > 0
        if self.plot_config['do_hp']:
            self.plot_config['hp_sos'] = signal.butter(filter.get('order', 4),
                                                       2 * filter.get('cutoff', 250) / self.samplingRate,
                                                       btype=filter.get('btype', 'highpass'),
                                                       output=filter.get('output', 'sos'))
        hp_filt_cb = self.findChild(QtWidgets.QCheckBox, name="hpfilt_CheckBox")

        hp_filt_cb.setCheckState(QtCore.Qt.Checked if self.plot_config['do_hp'] else QtCore.Qt.Unchecked)

        ln_filt_cb = self.findChild(QtWidgets.QCheckBox, name="lnfilt_CheckBox")
        self.plot_config['do_ln'] = bool(plot.get('do_ln', True))
        ln_filt_cb.setCheckState(QtCore.Qt.Checked if self.plot_config['do_ln'] else QtCore.Qt.Unchecked)
        self.plot_config['ln_filt'] = None  # TODO: comb filter coeffs

        spk_aud_cb = self.findChild(QtWidgets.QCheckBox, name="spkaud_CheckBox")
        spk_aud_cb.setCheckState(QtCore.Qt.Checked if bool(plot.get('spk_aud', True)) else QtCore.Qt.Unchecked)

        thrlk_cb = self.findChild(QtWidgets.QCheckBox, name="lkthr_CheckBox")
        thrlk_cb.setCheckState(QtCore.Qt.Checked if bool(plot.get('lock_threshold', False)) else QtCore.Qt.Unchecked)

        # Create and add GraphicsLayoutWidget
        glw = pg.GraphicsLayoutWidget(parent=self)  # show=False, size=None, title=None, border=None
        # glw.useOpenGL(True)  # Actually seems slower.
        if 'bgcolor' in self.plot_config['theme']:
            glw.setBackground(parse_color_str(self.plot_config['theme']['bgcolor']))
        self.layout().addWidget(glw)

        cmap = self.plot_config['theme']['colormap']
        if cmap != 'custom':
            self.plot_config['theme']['pencolors'] = get_colormap(self.plot_config['theme']['colormap'],
                                                                  len(self.chan_states))

        # Add add a plot with a series of many curve segments for each line.
        for chan_state in self.chan_states:
            self.add_series(chan_state)

    def add_series(self, chan_state):
        my_theme = self.plot_config['theme']

        # Plot for this channel
        glw = self.findChild(pg.GraphicsLayoutWidget)
        new_plot = glw.addPlot(row=len(self.segmented_series), col=0,
                               title=chan_state['name'], enableMenu=False)
        new_plot.setMouseEnabled(x=False, y=False)

        # Prepare plot
        self.plot_config['color_iterator'] = (self.plot_config['color_iterator'] + 1) % len(my_theme['pencolors'])
        pen_color = make_qcolor(my_theme['pencolors'][self.plot_config['color_iterator']])
        pen = pg.mkPen(pen_color, width=my_theme.get('linewidth', 1))
        samples_per_segment = int(
            np.ceil(self.plot_config['x_range'] * self.samplingRate / self.plot_config['n_segments']))
        for ix in range(self.plot_config['n_segments']):
            if ix < (self.plot_config['n_segments'] - 1):
                seg_x = np.arange(ix * samples_per_segment, (ix + 1) * samples_per_segment, dtype=np.int16)
            else:
                # Last segment might not be full length.
                seg_x = np.arange(ix * samples_per_segment,
                                  int(self.plot_config['x_range'] * self.samplingRate), dtype=np.int16)
            seg_x = seg_x[::self.plot_config['downsample']]
            c = new_plot.plot(parent=new_plot, pen=pen)  # PlotDataItem
            c.setData(x=seg_x, y=np.zeros_like(seg_x))  # Pre-fill.

        # Add threshold line
        thresh_color = make_qcolor(my_theme.get('threshcolor', 'yellow'))
        pen = pg.mkPen(color=thresh_color, width=my_theme.get('threshwidth', 1))
        thresh_line = pg.InfiniteLine(angle=0, pen=pen, movable=True, label="{value:.0f}", labelOpts={'position': 0.05})
        thresh_line.sigPositionChangeFinished.connect(self.on_thresh_line_moved)
        new_plot.addItem(thresh_line)

        self.segmented_series[chan_state['name']] = {
            'chan_id': chan_state['src'],
            'line_ix': len(self.segmented_series),
            'plot': new_plot,
            'last_sample_ix': -1,
            'thresh_line': thresh_line,
            'hp_zi': signal.sosfilt_zi(self.plot_config['hp_sos']),
            'ln_zi': None
        }

    def refresh_axes(self):
        last_sample_ix = int(np.mod(get_now_time(), self.plot_config['x_range']) * self.samplingRate)
        state_names = [_['name'] for _ in self.chan_states]
        for line_label in self.segmented_series:
            ss_info = self.segmented_series[line_label]
            chan_state = self.chan_states[state_names.index(line_label)]

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

            gain = chan_state['gain'] if 'gain' in chan_state else self.plot_config['unit_scaling']
            if 'spkthrlevel' in chan_state:
                ss_info['thresh_line'].setValue(chan_state['spkthrlevel'] * gain)

    def reset_audio(self):
        if self.pya_stream:
            if self.pya_stream.is_active():
                self.pya_stream.stop_stream()
            self.pya_stream.close()
        frames_per_buffer = 1 << (int(0.030*self.samplingRate) - 1).bit_length()
        self.audio['buffer'] = np.zeros(frames_per_buffer, dtype=np.int16)
        self.audio['write_ix'] = 0
        self.audio['read_ix'] = 0
        self.audio['chan_label'] = None
        self.pya_stream = self.pya_manager.open(format=pyaudio.paInt16,
                                                channels=1,
                                                rate=self.samplingRate,
                                                output=True,
                                                frames_per_buffer=frames_per_buffer,
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

    def update(self, line_label, data, ch_state=None):
        """

        :param line_label: Label of the segmented series
        :param data: Replace data in the segmented series with these data
        :return:
        """
        ss_info = self.segmented_series[line_label]
        n_in = data.shape[0]
        gain = ch_state['gain'] if ch_state is not None and 'gain' in ch_state else self.plot_config['unit_scaling']
        data = data * gain
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
            x_lims[1] += (self.plot_config['downsample'] - 1)
            data_bool = np.logical_and(sample_indices >= x_lims[0], sample_indices <= x_lims[-1])
            if np.where(data_bool)[0].size > 0:
                new_x, new_y = sample_indices[data_bool], data[data_bool]
                if self.plot_config['downsample'] > 1:
                    _dsfac = self.plot_config['downsample']
                    new_x = new_x[::_dsfac] - (new_x[0] % _dsfac) + (old_x[0] % _dsfac)
                    new_y = new_y[::_dsfac]
                old_bool = np.in1d(old_x, new_x, assume_unique=True)
                new_bool = np.in1d(new_x, old_x, assume_unique=True)
                old_y[old_bool] = new_y[new_bool]
                # old_y[np.where(old_bool)[0][-1]+1:] = 0  # Uncomment to zero out the end of the last seg.
                pci.setData(x=old_x, y=old_y)
        # Store last_sample_ix for next iteration.
        self.segmented_series[line_label]['last_sample_ix'] = sample_indices[-1]