import __init__
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

from test_load import RMS_Analysis

THEMES = {
    'dark': {
        'pencolors': ["cyan", QtGui.QColor(0, 255, 0), "red", "magenta", "yellow", "white"],
        'bgcolor': QtCore.Qt.black,
        'labelcolor': QtCore.Qt.gray,
        'axiscolor': QtCore.Qt.gray,
        'axiswidth': 1
    }
}

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

base_fn = os.path.join(os.path.join(sys.path[-1], sys.path[-1].split('/')[-1] + '-001'))

def find_data(base_fn, version=1, save=False):
    filename = os.path.abspath(os.path.join(CACHE_DIR,'__data__{}.npy'.format(base_fn.split('/')[-1])))
    found = False
    for tmp in os.listdir(CACHE_DIR):
        if fnmatch.fnmatch(tmp, filename.split('/')[-1]):
            found = True

    if found:
        return np.load(filename)[()]

    else:
        dta = DBSTrackAnalysis(base_fn)
        data = dta.process(version=version)
        if save:
            np.save(filename, data)
        else:
            return data

data = find_data(base_fn, version=0)
rms_dat = data['rms']
depths = np.asarray(data['depth'])

class BarPlotGui(QtWidgets.QMainWindow):
    def __init__(self):
        super(BarPlotGui, self).__init__()
        self.last_ev_time = time.time()
        self.setup_ui()
        self.show()

    def setup_ui(self):
        self.setCentralWidget(QtWidgets.QWidget(self))
        layout = QtWidgets.QVBoxLayout()
        self.centralWidget().setLayout(layout)

        colors = [QtGui.QColor(THEMES['dark']['pencolors'][chan_ix]) for chan_ix in range(rms_dat.shape[-1])]

        self.plots = PlotsWidget()
        self.plots.setup_plots(1, 1, clickable=True)

        self.plots.bar(0, 0, label='rms 1', x=depths, height=rms_dat[:,0], width=.1,
                        pen=pg.mkPen(colors[0]), brush=colors[0])
        layout.addWidget(self.plots)

        self.resize(1000, 1000)


if __name__ == '__main__':
    qapp = QtWidgets.QApplication(sys.argv)
    mainwindow = BarPlotGui()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()
