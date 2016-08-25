import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from collections import namedtuple
from cerebus import cbpy
from pyqtgraph.dockarea import *
from cbsdkConnection import cbsdkConnection

SpikeEventData = namedtuple("SpikeEventData",
                            ["chan", "unit", "ts", "arrival_ts"])
ContinuousData = namedtuple("ContinuousData",
                            ["chan", "samples", "arrival_ts"])
SAMPLERATE = 30000
NCHANNELS = 64
NUNITS = 6  # Units per channel
KEEP_SECONDS_RASTERS = 5
SPK_SHRINK_TIME = -1

class MyGUI(QtGui.QMainWindow):

    def __init__(self):
        super(MyGUI, self).__init__()
        self.setupUI()
        self.setupNeuroport()
        self.show()

    def __del__(self):
        res = cbpy.close(instance=0)

    def setupUI(self):
        self.dock_area = DockArea(self)
        self.setCentralWidget(self.dock_area)
        self.resize(1200, 621)
        # Set menubar & whole widget appearance
        self.myMenubar = QtGui.QMenuBar(self)
        self.myMenubar.setGeometry(0, 0, 1200, 21)
        self.myMenubar.setObjectName("MenuBar")
        fileMenu = self.myMenubar.addMenu('File')
        addChannelAction = QtGui.QAction('Add a channel',self)
        #selectChannelAction = QtGui.QAction('Select Channel',self)
        fileMenu.addAction(addChannelAction)
        channelList = fileMenu.addMenu('Channel List')
        addChannelAction.triggered.connect(self.AddChannelToPlot)
        #addChannelAction.triggered.connect(self.get_dock_info)
        self.ChannelList = QtGui.QComboBox()
        for ch_id in range(NCHANNELS):
            self.ChannelList.addItem("{}".format(ch_id+1))

        self.setWindowTitle('Neuroport DBS')
        self.statusBar().showMessage('Ready...')

        #TODO: Create NUNITS pens
        self.mypens = [pg.mkPen( width=0, color='y')]
        #self.mypens[0] = pg.mkPen(color='y')
        # mybrush = pg.mkBrush(QtGui.QBrush(QtGui.QColor(QtCore.Qt.blue), style=QtCore.Qt.VerPattern))
        self.mybrush = None

        self.painter = QtGui.QPainter()
        #self.painter.setPen()
        #poly = QtGui.QPolygonF([QtCore.QPoint(0, 0), QtCore.QPoint(0, 1)])

        self.ticks = QtGui.QPainterPath()
        #self.ticks.addPolygon(poly)
        self.ticks.moveTo(0.0, 0.0)
        self.ticks.lineTo(0.0, 1.0)
        self.ticks.closeSubpath()

        #self.line = QtCore.QLineF(0,0,0,1)
        #self.painter.fillPath(self.ticks, QColor=(255,0,0))

        self.spk_buffer = np.empty((0, 0))
        self.raw_buffer = np.empty((0, 0))
        self.raster_buffer = []
        self.dock_info = []
        self.my_rasters = []

    def AddChannelToPlot(self):
        totalNumber = self.dock_area.findAll()
        dock_index = len(totalNumber[0])
        if len(totalNumber[0]) is 0:
            dock_index = 1
        continuous_dock = Dock("Continuous " + str(dock_index), size=(900, 200))

        continuous_layout = pg.LayoutWidget()
        combobox = QtGui.QComboBox()
        for ch_id in range(NCHANNELS):
            combobox.addItem("{}".format(ch_id+1))
        spk_plot = pg.PlotWidget(name="SPK")
        spk_plot.plotItem.plot([])
        raw_plot = pg.PlotWidget(name="RAW")
        raw_plot.plotItem.plot([])
        continuous_layout.addWidget(combobox)
        continuous_layout.addWidget(spk_plot)
        continuous_layout.addWidget(raw_plot)
        continuous_dock.addWidget(continuous_layout)
        self.dock_area.addDock(continuous_dock, position='bottom')
        self.spk_buffer = np.concatenate((self.spk_buffer, np.nan*np.ones((1,self.spk_buffer.shape[1]))), axis=0)

        raster_dock = Dock("Raster " + str(dock_index), size=(300, 200)) #Figure out how to show the current index of raster
        raster_layout = pg.LayoutWidget()
        combo2 = QtGui.QComboBox()
        for ch_id in range(NCHANNELS):
            combo2.addItem("{}".format(ch_id+1))
        raster_layout.addWidget(combo2)

        raster_item = pg.GraphItem(symbolPen=self.mypens[0], symbolBrush=self.mybrush, symbol='s')

        raster_plot = pg.PlotWidget(name="RASTER")
        raster_plot.setLimits(xMin=0, xMax=1, yMin=0, yMax=1, minXRange=1.0, maxXRange=1.0, minYRange=1.0,
                              maxYRange=1.0)
        raster_plot.addItem(raster_item)
        raster_layout.addWidget(raster_plot)
        raster_dock.addWidget(raster_layout)
        self.my_rasters.append(raster_item)
        self.dock_area.addDock(raster_dock, position='right', relativeTo=continuous_dock)
        self.raster_buffer.append(np.empty((1,)))
        self.get_dock_info()

    def get_dock_info(self):
        dock_info = []
        for dock_key in self.dock_area.docks.keys():
            dock_type, dock_num = dock_key.split(' ')
            this_dock = self.dock_area.docks[dock_key]
            combo_box = this_dock.findChild(QtGui.QComboBox)
            chan_ix = int(combo_box.currentText())
            if dock_type == 'Raster':
                dockplot = this_dock.findChild(pg.PlotWidget)
            else:
                dockplot = this_dock.findChild(pg.PlotWidget)
            #dockplot = this_dock.findChild(name="RASTER" if dock_type == 'Raster' else "SPK")  # ?
            # TODO: Search for children with name == "RASTER" or name == "SPK", set to dockplot
            dock_info.append({'type': dock_type, 'num': int(dock_num), 'chan': chan_ix, 'plot': dockplot})
        # self.dock_infomation = dock_info
        self.dock_info = dock_info

    def setupNeuroport(self):
        self.cbsdkConn = cbsdkConnection()

    def update(self):
        # Get event timestamps
        timestamps, ts_time = self.cbsdkConn.get_event_data()
        timestamp_chans = [x[0] for x in timestamps]

        # Get continuous
        contdat, cont_time = self.cbsdkConn.get_continuous_data()
        cont_chans = [x[0] for x in contdat]
        first_dat = contdat[0][1]
        n_samples_to_add = first_dat.size
        self.spk_buffer = np.concatenate((self.spk_buffer, np.nan*np.ones((self.spk_buffer.shape[0], n_samples_to_add),
                                                                          dtype=first_dat.dtype)), axis=1)
        # Add relevant data to spk_buffer
        if len(self.dock_info) is not 0:
            for dinf in self.dock_info:
                if dinf['type'] == 'Continuous':
                    try:
                        buf_ix = dinf['num']
                        dat_ix = dinf['chan']
                        this_plot = dinf['plot']
                        this_dock = this_plot.parent()
                        combo_box = this_dock.findChild(QtGui.QComboBox)
                        chan_ix = int(combo_box.currentText())
                        if chan_ix != dat_ix:
                            dat_ix = chan_ix
                        self.spk_buffer[buf_ix-1, -n_samples_to_add:] = contdat[cont_chans.index(dat_ix)][1]
                        tvec = np.arange(-self.spk_buffer.shape[1], 0) / SAMPLERATE

                        # Shrink spk_buffer to time >= -1
                        sample_mask = tvec >= SPK_SHRINK_TIME
                        tvec = tvec[sample_mask]
                        self.spk_buffer = self.spk_buffer[:, sample_mask]

                        pi = dinf['plot'].getPlotItem()
                        dataItems = pi.listDataItems()
                        dataItems[0].setData(self.spk_buffer[buf_ix-1].ravel(), x=tvec)
                    except ValueError:
                        pass

                elif dinf['type'] == 'Raster':
                    try:
                        raster_buf_ix = dinf['num']
                        raster_dat_ix = dinf['chan']
                        this_raster_plot = dinf['plot']
                        this_raster_dock = this_raster_plot.parent()
                        raster_combo_box = this_raster_dock.findChild(QtGui.QComboBox)
                        raster_chan_ix = int(raster_combo_box.currentText())
                        if raster_chan_ix != raster_dat_ix:
                            raster_dat_ix = raster_chan_ix

                        this_ix = timestamp_chans.index(raster_dat_ix)
                        this_timestamps = timestamps[this_ix][1]['timestamps']
                    except ValueError:
                        this_timestamps = [[]]

                    #self.raster_buffer[raster_buf_ix-1] = np.append(self.raster_buffer[gi_index], this_timestamps[unit_ix])
                    self.raster_buffer[raster_buf_ix-1] = np.append(self.raster_buffer[raster_buf_ix-1], this_timestamps[0])
                    ts = (self.raster_buffer[raster_buf_ix-1] - ts_time) / SAMPLERATE

                    # Only keep last 5 seconds
                    keep_mask = ts > -KEEP_SECONDS_RASTERS
                    self.raster_buffer[raster_buf_ix-1] = self.raster_buffer[raster_buf_ix-1][keep_mask]  # Trim buffer (samples)
                    ts = ts[keep_mask]  # Trim timestamps (seconds)

                    xpos = np.mod(ts, 1)
                    ypos = -np.ceil(ts) / 5 + 0.1
                    positions = np.vstack((xpos, ypos)).T

                    #gi = self.raster_buffer[raster_buf_ix-1]
                    gi = self.my_rasters[raster_buf_ix-1]
                    gi.setData(pos=positions, symbolPen=self.mypens[0])
        else:
            pass


if __name__ == '__main__':

    qapp = QtGui.QApplication(sys.argv)
    aw = MyGUI()

    timer = pg.QtCore.QTimer()
    timer.timeout.connect(aw.update)
    timer.start(50)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()