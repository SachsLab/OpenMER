import os
import platform
import sys
import time
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
import numpy as np
from scipy import signal
import pyfftw.interfaces.numpy_fft as fft
import pyqtgraph as pg
import brpylib
import quantities as pq
from neo.io.blackrockio import BlackrockIO
from utilities import segment_consecutive

DEF_ROOT_DIR = os.path.abspath(os.path.join(os.getcwd(), '..', '..', '..', 'DBSData'))\
    if platform.system() in ['Linux', 'Darwin'] else os.path.abspath('D:\DBSData')

DEF_SEG_INTERVAL = [0.5, 4.5] * pq.s
THEMES = {
    'dark': {
        'pencolors': ["cyan", QtGui.QColor(0, 255, 0), "red", "magenta", "yellow", "white"],
        'bgcolor': QtCore.Qt.black,
        'labelcolor': QtCore.Qt.gray,
        'axiscolor': QtCore.Qt.gray,
        'axiswidth': 1
    }
}

num_tap = 8000
hp_cutoff = 250
beta_cutoff = np.asarray([16, 30])
rms_thresh = 4.0
dec_factor = 50


def olafilt(b, x, axis=-1, zi=None):
    ax0, ax1 = x.shape

    L_I = b.shape[0]
    # Find power of 2 larger that 2*L_I (from abarnert on Stackoverflow)
    L_F = 2<<(L_I-1).bit_length()
    L_S = L_F - L_I + 1
    L_sig = x.shape[axis]
    offsets = range(0, L_sig, L_S)

    # blockwise frequency domain multiplication
    if np.iscomplexobj(b) or np.iscomplexobj(x):
        FDir = np.fft.fft(b, n=L_F)
        tempresult = [np.fft.ifft(np.fft.fft(x[:, n:n+L_S], n=L_F, axis=-1)*FDir[np.newaxis, :])
                      for n in offsets]
        res = np.zeros(ax0, L_sig+L_F, dtype=np.complex128)
    else:
        FDir = np.fft.rfft(b, n=L_F)
        tempresult = [np.fft.irfft(np.fft.rfft(x[:, n:n+L_S], n=L_F, axis=-1)*FDir[np.newaxis, :])
                      for n in offsets]
        res = np.zeros((ax0, L_sig+L_F))

    # overlap and add
    for i, n in enumerate(offsets):
        res[:, n:n+L_F] += tempresult[i]

    if zi is not None:
        res[:, :zi.shape[0]] = res[:, :zi.shape[0]] + zi
        return res[:, :L_sig], res[:, L_sig:]
    else:
        return res[:, :L_sig]


def empty_data_dict():
    return {'labels': [], 'spk': [], 'tvec': [], 'depth': [],
            'rms': [], 'n_spikes': [], 'spec_den': [], 'f': []}


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


def load_blackrock_data_neo(base_fn):
    neo_io = BlackrockIO(filename=base_fn)
    neo_block = neo_io.read_block(lazy=False, cascade=True,
                                  n_starts=None, n_stops=None, channels='all',
                                  nsx_to_load=5, scaling='voltage',
                                  units='none', load_waveforms=False, load_events=True)

    return {'ana_times': neo_block.segments[0].analogsignals[0].times,
            'ana_data': np.asarray([x for x in neo_block.segments[0].analogsignals])[:, :, 0],
            'chan_labels': [x.name.decode('utf8') for x in neo_block.segments[0].analogsignals],
            'ev_times': neo_block.segments[0].events[0].times,
            'ev_depths': np.asarray([float(x.split(':')[1]) for x in neo_block.segments[0].events[0].labels])}


def load_blackrock_data_brpy(base_fn):
    data_ = {'nsx': [], 'nev': []}
    file_ = {'nsx': [], 'nev': []}
    file_['nsx'] = brpylib.NsxFile(base_fn + '.ns5')
    data_['nsx'] = file_['nsx'].getdata(elec_ids='all', start_time_s=0, data_time_s='all', downsample=1)
    file_['nsx'].close()

    file_['nev'] = brpylib.NevFile(base_fn + '.nev')
    data_['nev'] = file_['nev'].getdata(elec_ids='all', get_waveforms=False)
    file_['nev'].close()

    fs = data_['nsx']['samp_per_s']
    return {'ana_times': (1 + np.arange(data_['nsx']['data_headers'][0]['NumDataPoints'])) / fs * pq.s,
            'ana_data': data_['nsx']['data'],
            'chan_labels': [x['ElectrodeLabel'] for x in file_['nsx'].extended_headers],
            'ev_times': np.asarray(data_['nev']['comments']['TimeStamps']) / fs * pq.s,
            'ev_depths': np.asarray([float(tmp.split(':')[-1]) for tmp in data_['nev']['comments']['Comment']])}


def segment_data_by_depth(data_dict, slice_times):

    sig = data_dict['ana_data']

    dtt = data_dict['ev_depths']
    dtt_sample_ix = data_dict['ev_times']

    label = np.nonzero(dtt[:-1]-dtt[1:])[0]
    tmp = np.ones(dtt.size, dtype=bool)
    tmp[label] = False
    label = tmp.copy()
    label_sorted = segment_consecutive(np.nonzero(label)[0], stepsize=3)

    fs = np.mean(np.diff(data_dict['ana_times']))
    nyquist = fs / 2

    count = 0
    tvecs = np.zeros((num_depth,), dtype=object) * np.nan
    sigs = np.zeros((num_depth,), dtype=object) * np.nan
    edts = np.zeros((num_depth,)) * np.nan
    for v in label_sorted:
        ix0, ix1 = dtt_sample_ix[v[0]], dtt_sample_ix[v[-1]]
        if (ix1-ix0)/fs > 3:
            sigs[count] = sig[:,ix0:ix1]
            tvecs[count] = t[ix0:ix1]
            edts[count] = np.round(dtt[v[0]], 3)
            count += 1

    sigs = sigs[np.equal(np.zeros(edts.size, dtype=bool),np.isnan(edts))]
    edts = edts[np.equal(np.zeros(edts.size, dtype=bool),np.isnan(edts))]

    return sigs, edts, tvecs


def get_data(base_fn, dest=None):
    if dest is None:
        dest = empty_data_dict()

    data_dict = load_blackrock_data_brpy(base_fn)
    # data_dict = load_blackrock_data_neo(base_fn)  # About 4 times slower than modified brPY

    fs = 1 / np.mean(np.diff(data_dict['ana_times']))
    nyquist = fs / 2
    hfir1 = signal.firwin(num_tap + 1, hp_cutoff, nyq=nyquist, pass_zero=False)
    hfir0 = signal.firwin(num_tap + 1, (2, hp_cutoff), nyq=nyquist, pass_zero=True)

    b_new_depth = np.diff(np.hstack((-np.inf, data_dict['ev_depths']))) > 0
    b_long_enough = np.hstack((np.diff(data_dict['ev_times'][b_new_depth]) > DEF_SEG_INTERVAL[1], False))
    dest['depth'] = data_dict['ev_depths'][b_new_depth][b_long_enough]

    seg_start_ix = np.where(b_new_depth)[0][b_long_enough]
    seg_stop_ix = np.hstack((np.where(b_new_depth)[0][1:],data_dict['ev_times'].size))[b_long_enough]
    n_segs = len(seg_start_ix)
    for seg_ix in range(n_segs):
        seg_start_time = data_dict['ev_times'][seg_start_ix[seg_ix]]
        seg_stop_time = data_dict['ev_times'][seg_stop_ix[seg_ix]] - (1/fs)
        b_seg = np.logical_and(data_dict['ana_times'] >= seg_start_time, data_dict['ana_times'] < seg_stop_time)
        sig = data_dict['ana_data'][:, b_seg]
        tvec = data_dict['ana_times'][b_seg]
        tvec -= tvec[0]
        b_interval = np.logical_and(tvec >= DEF_SEG_INTERVAL[0], tvec < (DEF_SEG_INTERVAL[1] - 0.5/fs))

        seg_spk = np.atleast_2d(olafilt(hfir1, sig[:, b_interval], zi=None))
        seg_psd = np.atleast_2d(olafilt(hfir0, sig[:, b_interval], zi=None))[:, ::dec_factor]

        dest['spk'].append(seg_spk)
        dest['tvec'].append(data_dict['ana_times'][b_seg][b_interval])

        # Calculate the RMS of the highpass
        seg_rms = np.sqrt(np.mean(seg_spk ** 2, axis=-1))
        dest['rms'].append(seg_rms)

        # Find threshold crossing events at rms_thresh * seg_rms
        seg_spk_offset = seg_spk + (rms_thresh * seg_rms[:, np.newaxis])
        b_spike = np.hstack((np.zeros((seg_spk_offset.shape[0], 1), dtype=np.bool),
                             np.logical_and(seg_spk_offset[:, :-1] >= 0, seg_spk_offset[:, 1:] < 0)))
        dest['n_spikes'].append(np.sum(b_spike, axis=1))

        # Calculate the spectrum
        f, Pxx_den = signal.periodogram(seg_psd, fs / dec_factor, axis=1)
        dest['spec_den'].append(Pxx_den)
        dest['f'].append(f)

    dest['spk'] = np.asarray(dest['spk'])
    dest['rms'] = np.asarray(dest['rms'])
    dest['spec_den'] = np.asarray(dest['spec_den'])
    dest['f'] = np.asarray(dest['f'])
    dest['n_spikes'] = np.asarray(dest['n_spikes'])

    if (len(dest['labels']) > 0) and (dest['labels'] != data_dict['chan_labels']):
        # TODO: Raise error that channel labels do not match across files.
        return dest
    else:
        dest['labels'] = data_dict['chan_labels']

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
        if os.path.isdir(self.root_lineedit.text()):
            dirs = next(os.walk(self.root_lineedit.text()))[1]
        else:
            dirs = []
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
            depth_ix = np.argmin(np.abs(depth - np.asarray(self.data['depth'])))
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
        self.data = empty_data_dict()
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
        resort = np.argsort(depths)
        depths = depths[resort]
        rms_dat = np.asarray(self.data['rms'])[resort, :]
        nspk_dat = np.asarray(self.data['n_spikes'])[resort, :]
        spec_dat = np.asarray(self.data['spec_den'])[resort, :, :]
        b_freq = np.logical_and(self.data['f'][0] > 0, self.data['f'][0] <= 100)
        freqs = self.data['f'][0][b_freq]
        spec_dat = spec_dat[:, :, b_freq]  # Limit to between 0 and 100
        spec_dat = -np.log10(np.square(spec_dat))  # convert to dB; - because LUT has blue a hot (I think?)
        min_diff = np.min(np.diff(depths))
        spec_depths = np.arange(depths[0], depths[-1], min_diff)
        my_lut = getLUT()
        levels = np.min(spec_dat), np.max(spec_dat)
        for chan_ix in range(rms_dat.shape[1]):
            ch_label = self.data['labels'][chan_ix]
            pen = QtGui.QColor(THEMES['dark']['pencolors'][chan_ix])
            curve = self.plots['rms'].plot(x=rms_dat[:, chan_ix], y=depths,
                                           name=ch_label, pen=pen, clickable=True)
            curve.getViewBox().invertY(True)
            self.plots['rms'].setXRange(0, 80)
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
            img_item.setImage(img_dat_interp, lut=my_lut)
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
