import os
import sys
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
    nev_dict = nev_file.getdata(elec_ids='all')
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
        glw = pg.GraphicsLayoutWidget(parent=self)
        self.plots = {}
        self.plots['rms'] = glw.addPlot(row=0, col=0, title='RMS')
        self.plots['n_spikes'] = glw.addPlot(row=0, col=1, title='Spikes')
        layout.addWidget(glw)

        self.resize(1000, 800)

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
        self.plots['rms'].addLegend()
        self.plots['n_spikes'].addLegend()
        depths = np.asarray(self.data['depth'])
        rms_dat = np.asarray(self.data['rms'])
        nspk_dat = np.asarray(self.data['n_spikes'])
        spec_dat = np.asarray(self.data['spec_den'])
        for chan_ix in range(rms_dat.shape[1]):
            ch_label = self.data['labels'][chan_ix]
            pen = QtGui.QColor(THEMES['dark']['pencolors'][chan_ix])
            self.plots['rms'].plot(x=depths, y=rms_dat[:, chan_ix],
                                   name=ch_label, pen=pen)
            self.plots['n_spikes'].plot(x=depths, y=nspk_dat[:, chan_ix],
                                        name=ch_label, pen=pen)

            # TODO: depth-frequency plots using self.data['spec_den']


if __name__ == '__main__':
    qapp = QtWidgets.QApplication(sys.argv)
    mainwindow = DBSPlotGUI()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()