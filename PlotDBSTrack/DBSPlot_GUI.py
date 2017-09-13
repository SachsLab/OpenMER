import os
import platform
import sys
import time
import fnmatch

import numpy as np
from scipy import signal, stats
import pyfftw.interfaces.numpy_fft as fft

import pyqtgraph as pg
from qtpy import (QtCore, QtGui, QtWidgets)

import brpylib
import quantities as pq
from neo.io.blackrockio import BlackrockIO
from utilities import segment_consecutive

from process import DBSTrackAnalysis
from widgets.plots_widget import PlotsWidget

# DEF_ROOT_DIR = os.path.abspath(os.path.join(os.getcwd(), '..', '..', '..', 'DBSData'))\
#     if platform.system() in ['Linux', 'Darwin'] else os.path.abspath('D:\DBSData')

DATA_DIR = None
PRJ_DIR = 'NeuroportDBS'
GUI_DIR = 'PlotDBSTrack'
DATANAME_DIR = [os.path.join('..','..','..','DBSData'), \
                os.path.join('..','..','data_collected'),\
                os.path.abspath('D:\DBSData')]

cwd = os.getcwd()
if cwd.split('/')[-1] == PRJ_DIR:
    CACHE_DIR = os.path.abspath(os.path.join(cwd, GUI_DIR, '__cache__'))
elif cwd.split('/')[-1] == GUI_DIR:
    CACHE_DIR = os.path.abspath(cwd, '__cache__')

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

for dataname in DATANAME_DIR:
    tmp = os.path.abspath(os.path.join(cwd, dataname))
    if os.path.exists(tmp):
        DATA_DIR = tmp

if DATA_DIR is None:
    DATA_DIR = cwd

THEMES = {
    'dark': {
        'pencolors': ["cyan", QtGui.QColor(0, 255, 0), "red", "magenta", "yellow", "white"],
        'bgcolor': QtCore.Qt.black,
        'labelcolor': QtCore.Qt.gray,
        'axiscolor': QtCore.Qt.gray,
        'axiswidth': 1
    }
}

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
        self.root_lineedit.setText(DATA_DIR)
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

        self.plots = PlotsWidget()
        layout.addWidget(self.plots)

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
            depth = event.currentItem.mapSceneToView(event.scenePos()).x()
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

        for traj in traj_list:
            self.base_fn = os.path.join(datadir, curr_sess + '-' + traj.text())
            self.find_data(version=1, save=True)

        self.refresh_pushbutton.setEnabled(True)

        # Plotting the data
        main_plot_names = ['rms', 'pac', 'spectra']
        title_label = {name: self.data['labels'] for name in main_plot_names}
        self.plots.setup_plots(len(main_plot_names), len(self.data['labels']), title=title_label, clickable=True)
        self.plots.clear()
        self.update_plots()

    def find_data(self, version=0, save=False):
        filename = os.path.abspath(os.path.join(CACHE_DIR,'__data__{}.npy'.format(self.base_fn.split('/')[-1])))
        found = False
        for tmp in os.listdir(CACHE_DIR):
            if fnmatch.fnmatch(tmp, filename.split('/')[-1]):
                found = True

        if found:
            self.data = np.load(filename)[()]

        else:
            self.dta = DBSTrackAnalysis(self.base_fn)
            self.data = self.dta.process(version=version)
            if save:
                np.save(filename, self.data)

    def update_plots(self):
        # TODO: Delete legend
        depths = np.asarray(self.data['depth'])
        resort = np.argsort(depths)
        depths = depths[resort]
        rms_dat = np.asarray(self.data['rms'])[resort, :]
        pac_dat = np.asarray(self.data['pac'])[resort, :]

        import matplotlib.pyplot as plt
        from matplotlib.colors import LogNorm

        spec_dat = np.asarray(self.data['spec_den'])[resort, :, :]

        plt.subplot(131)
        plt.imshow(self.data['spec_den'][:,0,:], aspect='auto')
        plt.subplot(132)
        plt.imshow(self.data['spec_den'][:,1,:], aspect='auto')
        plt.subplot(133)
        plt.imshow(self.data['spec_den'][:,2,:], aspect='auto')
        plt.show()

        b_freq = np.logical_and(self.data['f'][0] > 0, self.data['f'][0] <= 100)
        freqs = self.data['f'][0][b_freq]
        spec_dat = spec_dat[:, :, b_freq]  # Limit to between 0 and 100
        spec_dat = -np.log10(np.square(spec_dat))  # convert to dB; - because LUT has blue a hot (I think?)
        min_diff = np.min(np.diff(depths))
        spec_depths = np.arange(depths[0], depths[-1], min_diff)

        n_channels = rms_dat.shape[-1]
        img_dat = np.asarray([np.squeeze(spec_dat[:, ch, :].T) for ch in range(n_channels)])
        img_dat_interp = np.zeros((n_channels, img_dat.shape[1], len(spec_depths)))
        for ch in range(n_channels):
            for f_ix in range(len(freqs)):
                temp = stats.zscore(img_dat[ch, f_ix, :], axis=-1)
                img_dat_interp[ch, f_ix, :] = np.interp(spec_depths, depths, temp)

        spec_lim = np.max(np.abs(img_dat_interp))
        colors = [QtGui.QColor(THEMES['dark']['pencolors'][chan_ix]) for chan_ix in range(rms_dat.shape[-1])]
        for ch in range(n_channels):
            self.plots.bar(0, ch, label='rms {}'.format(ch+1), x=depths, height=rms_dat[:,ch], width=.2,
                            pen=pg.mkPen(colors[ch]), brush=colors[ch], highlight_pen=pg.mkPen(QtGui.QColor("white")))
            self.plots.bar(1, ch, label='pac {}'.format(ch+1), x=depths, height=pac_dat[:,ch], width=.2,
                            pen=pg.mkPen(colors[ch]), brush=colors[ch], highlight_brush=pg.mkPen(QtGui.QColor("white")))
            self.plots.imshow(2, ch, img_dat_interp[ch,:,:], label='spectra', set_pos=(freqs[0], spec_depths[0]),
                              scale=((freqs[-1] - freqs[0]) / img_dat_interp[ch,:,:].shape[0],
                                     (spec_depths[-1] - spec_depths[0]) / img_dat_interp[ch,:,:].shape[1]),
                              set_levels=(-spec_lim, spec_lim), set_aspect_locked=False, invert_y=True)


if __name__ == '__main__':
    qapp = QtWidgets.QApplication(sys.argv)
    mainwindow = DBSPlotGUI()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()
