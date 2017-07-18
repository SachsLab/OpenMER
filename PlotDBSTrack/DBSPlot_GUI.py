import os
import sys
import time
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
import numpy as np
from scipy import signal
import pyqtgraph as pg
import brpylib


DEF_ROOT_DIR = os.path.abspath(os.path.join(os.getcwd(), '..', '..', '..', '..', 'DBSData'))
DEF_SEG_INTERVAL = [0.5, 4.5]
THEMES = {
    'dark': {
        'pencolors': ["cyan", QtGui.QColor(0, 255, 0), "red", "magenta", "yellow", "white"],
        'bgcolor': QtCore.Qt.black,
        'labelcolor': QtCore.Qt.gray,
        'axiscolor': QtCore.Qt.gray,
        'axiswidth': 1
    }
}
hp_cutoff = 250
beta_cutoff = np.asarray([16, 30])
rms_thresh = 4.0
dec_factor = 10


def getRGBAFromCMap(x, c_inds, c_vals, mode='rgb'):
    """
    Args:
        x: value for which we want the colour float from 0 to 1
        c_inds: list of values at which the colormap is defined
        c_vals: list of PyQt4.QtGui.QColor for each of the above points
        mode: 'rgb' or 'hsv'
    Returns:
    """
    if x < np.min(c_inds):
        x = np.min(c_inds)

    ix_0 = (np.asarray(c_inds) <= x).nonzero()[0][0]
    x_0 = c_inds[ix_0]
    c_0 = c_vals[ix_0]

    if x >= np.max(c_inds):
        x = np.max(c_inds)
        ix_1 = c_inds.index(x)
    else:
        ix_1 = (np.asarray(c_inds) > x).nonzero()[0][0]
    x_1 = c_inds[ix_1]
    c_1 = c_vals[ix_1]
    dx = (x_1 - x_0)
    if dx == 0:
        f = 0.
    else:
        f = (x - x_0) / dx
    if mode == 'rgb':
        r = c_0.red() * (1. - f) + c_1.red() * f
        g = c_0.green() * (1. - f) + c_1.green() * f
        b = c_0.blue() * (1. - f) + c_1.blue() * f
        a = c_0.alpha() * (1. - f) + c_1.alpha() * f
        return r, g, b, a
    elif mode == 'hsv':
        h_0, s_0, v_0, _ = c_0.getHsv()
        h_1, s_1, v_1, _ = c_1.getHsv()
        h = h_0 * (1. - f) + h_1 * f
        s = s_0 * (1. - f) + s_1 * f
        v = v_0 * (1. - f) + v_1 * f
        c_out = QtGui.QColor()
        c_out.setHsv(h, s, v)
        return c_out.red(), c_out.green(), c_out.blue(), c_out.alpha()
    else:
        raise TypeError("mode must be 'rgb' or 'hsv'")


def getLUT(n_pts=512, cm_name='Spectral', cm_library='matplotlib', has_alpha=False):
    """

    :param n_pts:
    :param cm_name:
    :param cm_library:
    :param has_alpha:
    :return:
    """
    n_channels = 4 if has_alpha else 3
    lut = np.empty((n_pts, n_channels), dtype=np.ubyte)
    if cm_library == 'matplotlib':
        import matplotlib.cm as mplcm
        cmap = mplcm.get_cmap(cm_name)
        for i in range(n_pts):
            x = float(i) / (n_pts - 1)
            color = cmap(x)
            lut[i] = 255 * np.asarray(color[:n_channels])
    else:
        # pyqtgraph has its own colormap system but it is hidden deep inside its gradientEditor.
        # If we do not wish to invoke the gradientEditor then the code would look something like this.
        from pyqtgraph.Qt import QtGui
        from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
        grad_dict = Gradients[cm_name]
        c_inds = []
        c_vals = []
        for tick in grad_dict['ticks']:
            c_inds.append(tick[0])
            c_vals.append(QtGui.QColor(*tick[1]))
        c_inds, c_vals = zip(*sorted(zip(c_inds, c_vals)))  # Sort both accordings to c_inds
        for i in range(n_pts):
            x = float(i) / (n_pts - 1)
            lut[i] = getRGBAFromCMap(x, c_inds, c_vals, mode=grad_dict['mode'])[:n_channels]
    return lut


def get_data(base_fn, dest=None):
    if dest is None:
        dest = {'labels': [], 'spk': [], 'tvec': [],
                'rms': [], 'n_spikes': [], 'spec_den': [], 'f': []}

    nsx_file = brpylib.NsxFile(base_fn + '.ns5')
    nsx_dict = nsx_file.getdata(elec_ids='all', start_time_s=0, data_time_s='all', downsample=1)
    nsx_file.close()
    dest['labels'] = [x['ElectrodeLabel'] for x in nsx_file.extended_headers]
    fs = nsx_dict['samp_per_s']
    si = 1 + np.arange(nsx_dict['data_headers'][0]['NumDataPoints'])
    t = si / fs
    nyquist = fs / 2
    seg_sub_ind = np.arange(DEF_SEG_INTERVAL[0] * fs, DEF_SEG_INTERVAL[1] * fs, dtype=np.uint32)
    seg_sub_ind_lfp = np.arange(DEF_SEG_INTERVAL[0] * fs / dec_factor,
                                DEF_SEG_INTERVAL[1] * fs / dec_factor,
                                dtype=np.uint32)

    nev_file = brpylib.NevFile(base_fn + '.nev')
    nev_dict = nev_file.getdata(elec_ids='all', get_waveforms=False)
    nev_file.close()
    comm_ts = np.asarray(nev_dict['comments']['TimeStamps'])
    comm_str = nev_dict['comments']['Comment']
    comm_depths = np.asarray([float(x.split(':')[1]) for x in comm_str])
    b_new_depth = np.hstack((False, np.diff(comm_depths) > 0))
    b_long_enough = np.hstack((np.diff(comm_ts[b_new_depth]) >= (DEF_SEG_INTERVAL[1] * fs), False))
    seg_start_ts = comm_ts[b_new_depth][b_long_enough]
    seg_stop_ts = comm_ts[b_new_depth][np.where(b_long_enough)[0] + 1] - 1
    seg_start_depth = comm_depths[b_new_depth][b_long_enough]

    sig = nsx_dict['data']

    # HP filter raw data
    sos_spk = signal.butter(8, hp_cutoff / nyquist, btype='highpass', output='sos')
    data_spk = signal.sosfiltfilt(sos_spk, sig, axis=1)

    # Beta filter data
    sos_beta = signal.butter(8, beta_cutoff / nyquist, btype='bandpass', output='sos')
    data_beta = signal.sosfiltfilt(sos_beta, sig, axis=1)

    # Downsample for LFP spectra
    data_lfp = signal.decimate(sig, dec_factor, axis=1, zero_phase=True)

    for seg_ix in range(len(seg_start_ts)):
        b_seg = np.logical_and(si >= seg_start_ts[seg_ix], si <= seg_stop_ts[seg_ix])
        seg_sig = sig[:, b_seg][:, seg_sub_ind]

        # Calculate the RMS of the highpass
        seg_spk = data_spk[:, b_seg][:, seg_sub_ind]
        dest['spk'].append(seg_spk)
        dest['tvec'].append(t[b_seg][seg_sub_ind])

        seg_rms = np.sqrt(np.mean(seg_spk ** 2, axis=1))
        dest['rms'].append(seg_rms)

        # Find threshold crossing events at rms_thresh * seg_rms
        seg_spk_offset = seg_spk + (rms_thresh * seg_rms[:, np.newaxis])
        b_spike = np.hstack((np.zeros((seg_spk_offset.shape[0], 1), dtype=np.bool),
                             np.logical_and(seg_spk_offset[:, :-1] >= 0, seg_spk_offset[:, 1:] < 0)))
        dest['n_spikes'].append(np.sum(b_spike, axis=1))

        # Calculate the spectrum
        b_seg_lfp = np.logical_and(si[::dec_factor] >= seg_start_ts[seg_ix], si[::dec_factor] <= seg_stop_ts[seg_ix])
        f, Pxx_den = signal.periodogram(data_lfp[:, b_seg_lfp][:, seg_sub_ind_lfp], fs / dec_factor, axis=1)
        # plt.semilogy(f, Pxx_den.T)
        dest['spec_den'].append(Pxx_den)
        dest['f'].append(f)

    dest['depth'] = seg_start_depth

    return dest


class DBSPlotGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super(DBSPlotGUI, self).__init__()
        self.last_ev_time = time.time()
        self.setup_ui()
        self.show()

    def setup_ui(self):
        self.setCentralWidget(QtWidgets.QWidget(self))
        layout = QtWidgets.QVBoxLayout()
        self.centralWidget().setLayout(layout)

        # Text box for data root dir and [...] push button QFileDialog QFileDialog.Directory
        folder_layout = QtWidgets.QHBoxLayout()
        root_label = QtWidgets.QLabel("Root folder:")
        folder_layout.addWidget(root_label)
        self.root_lineedit = QtWidgets.QLineEdit()
        self.root_lineedit.setText(DEF_ROOT_DIR)
        folder_layout.addWidget(self.root_lineedit)
        root_pb = QtWidgets.QPushButton("...")
        root_pb.clicked.connect(self.get_root)
        folder_layout.addWidget(root_pb)
        layout.addLayout(folder_layout)

        # Combo box for date dir, defaults to most recent
        # And multi-select for recording number, defaults to most recent
        # And pushbutton for analysis.
        data_layout = QtWidgets.QHBoxLayout()
        self.traj_listwidget = QtWidgets.QListWidget()
        self.traj_listwidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.sub_combobox = QtWidgets.QComboBox()
        self.sub_combobox.currentIndexChanged.connect(self.sub_combo_changed)
        self.populate_sub_combobox()
        data_layout.addWidget(self.sub_combobox)
        # self.populate_traj_listwidget()  # Not necessary on first iteration.
        data_layout.addWidget(self.traj_listwidget)
        go_pushbutton = QtWidgets.QPushButton("Go!")
        go_pushbutton.clicked.connect(self.analyze)
        data_layout.addWidget(go_pushbutton)
        self.refresh_pushbutton = QtWidgets.QPushButton("Refresh")
        self.refresh_pushbutton.clicked.connect(self.update_plots)
        self.refresh_pushbutton.setEnabled(False)
        data_layout.addWidget(self.refresh_pushbutton)
        layout.addLayout(data_layout)

        # TODO: Add pyqtgraph plot items to layout.
        self.glw = pg.GraphicsLayoutWidget(parent=self)
        self.plots = {}
        self.plots['rms'] = self.glw.addPlot(row=0, col=0, colspan=2, title='RMS', clickable=True)
        self.plots['rms'].scene().sigMouseClicked.connect(self.on_scene_clicked)
        self.plots['n_spikes'] = self.glw.addPlot(row=0, col=2, colspan=2, title='Spikes', clickable=True)
        self.plots['n_spikes'].scene().sigMouseClicked.connect(self.on_scene_clicked)
        self.plots['spectra'] = []  # We don't yet know how many there will be.
        layout.addWidget(self.glw)

        self.resize(1000, 1000)

    def get_root(self):
        root_dir = QtWidgets.QFileDialog.getExistingDirectory(caption="Choose data parent directory.",
                                                              directory=self.root_lineedit.text())
        if root_dir:
            self.root_lineedit.setText(root_dir)
        self.populate_sub_combobox()

    def populate_sub_combobox(self):
        self.sub_combobox.clear()
        dirs = next(os.walk(self.root_lineedit.text()))[1]
        self.sub_combobox.addItems(dirs)
        # TODO: Set index to most recent.

    def sub_combo_changed(self):
        self.populate_traj_listwidget()

    def populate_traj_listwidget(self):
        self.traj_listwidget.clear()
        curr_sess = self.sub_combobox.currentText()
        subdir = os.path.join(self.root_lineedit.text(), curr_sess)
        contents = os.listdir(subdir)
        for c in contents:
            if c[-4:] == '.nev':
                traj_str = c[len(curr_sess)+1:-4]
                self.traj_listwidget.addItem(traj_str)
        self.traj_listwidget.setCurrentRow(self.traj_listwidget.count() - 1)
        self.traj_listwidget.setFixedSize(
            self.traj_listwidget.sizeHintForColumn(0) + 2 * self.traj_listwidget.frameWidth(),
            self.traj_listwidget.sizeHintForRow(
                0) * self.traj_listwidget.count() + 2 * self.traj_listwidget.frameWidth())

    def on_scene_clicked(self, event):
        if isinstance(event.currentItem, pg.ViewBox) and (event.time() != self.last_ev_time):
            self.last_ev_time = event.time()
            depth = event.currentItem.mapSceneToView(event.scenePos()).y()
            depth_ix = np.argmin(np.abs(depth - self.data['depth']))
            tvec = self.data['tvec'][depth_ix]
            data = self.data['spk'][depth_ix]

            dlg = QtWidgets.QDialog()
            dlg.setMinimumSize(800, 600)
            dlg.setLayout(QtWidgets.QVBoxLayout(dlg))
            glw = pg.GraphicsLayoutWidget(parent=dlg)
            dlg.layout().addWidget(glw)
            for chan_ix in range(data.shape[0]):
                plt = glw.addPlot(row=chan_ix, col=0)
                pen = QtGui.QColor(THEMES['dark']['pencolors'][chan_ix])
                curve = plt.plot(x=tvec, y= data[chan_ix, :], name=self.data['labels'][chan_ix], pen=pen)
                plt.setYRange(np.min(data), np.max(data))
            dlg.exec_()

    def analyze(self):
        curr_sess = self.sub_combobox.currentText()
        datadir = os.path.join(self.root_lineedit.text(), curr_sess)
        traj_list = self.traj_listwidget.selectedItems()
        self.data = {'labels': [], 'spk': [], 'tvec': [],
                     'rms': [], 'n_spikes': [], 'spec_den': [], 'f': []}
        for traj in traj_list:
            base_fn = os.path.join(datadir, curr_sess + '-' + traj.text())
            self.data = get_data(base_fn, dest=self.data)
        self.refresh_pushbutton.setEnabled(True)
        self.update_plots()

    def update_plots(self):
        # TODO: Delete legend
        self.plots['rms'].clear()
        self.plots['n_spikes'].clear()
        self.plots['rms'].addLegend(offset=(350, 30))
        self.plots['n_spikes'].addLegend(offset=(350, 30))
        depths = np.asarray(self.data['depth'])
        rms_dat = np.asarray(self.data['rms'])
        nspk_dat = np.asarray(self.data['n_spikes'])
        spec_dat = np.asarray(self.data['spec_den'])
        b_freq = np.logical_and(self.data['f'][0] > 0, self.data['f'][0] <= 100)
        freqs = self.data['f'][0][b_freq]
        spec_dat = spec_dat[:, :, b_freq]  # Limit to between 0 and 100
        spec_dat = np.log10(np.square(spec_dat))  # convert to dB
        min_diff = np.min(np.diff(depths))
        spec_depths = np.arange(depths[0], depths[-1], min_diff)
        my_lut = getLUT()
        levels = np.min(-spec_dat), np.max(-spec_dat)
        for chan_ix in range(rms_dat.shape[1]):
            ch_label = self.data['labels'][chan_ix]
            pen = QtGui.QColor(THEMES['dark']['pencolors'][chan_ix])
            curve = self.plots['rms'].plot(x=rms_dat[:, chan_ix], y=depths,
                                           name=ch_label, pen=pen, clickable=True)
            curve.getViewBox().invertY(True)
            curve = self.plots['n_spikes'].plot(x=nspk_dat[:, chan_ix], y=depths,
                                                name=ch_label, pen=pen, clickable=True)
            curve.getViewBox().invertY(True)

            if len(self.plots['spectra']) <= chan_ix:
                self.plots['spectra'].append(self.glw.addPlot(row=2, col=chan_ix, title=ch_label))
                # view = pg.ImageView(view=self.plots['spectra'][chan_ix])
                img = pg.ImageItem()
                self.plots['spectra'][chan_ix].addItem(img)
            # Update ImageView with new data.
            img_dat = np.squeeze(spec_dat[:, chan_ix, :].T)
            img_dat_interp = np.zeros((img_dat.shape[0], len(spec_depths)))
            for f_ix in range(len(freqs)):
                img_dat_interp[f_ix, :] = np.interp(spec_depths, depths, img_dat[f_ix, :])
            img_item = self.plots['spectra'][chan_ix].items[0]
            img_item.setImage(-img_dat_interp, lut=my_lut)  # - on img_dat because LUT has blue a hot (I think?)
            img_item.setPos(freqs[0], spec_depths[0])
            img_item.scale((freqs[-1] - freqs[0]) / img_dat_interp.shape[0],
                           (spec_depths[-1] - spec_depths[0]) / img_dat_interp.shape[1])
            img_item.setLevels(levels)
            self.plots['spectra'][chan_ix].setAspectLocked(False)
            self.plots['spectra'][chan_ix].invertY(True)


if __name__ == '__main__':
    qapp = QtWidgets.QApplication(sys.argv)
    mainwindow = DBSPlotGUI()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()