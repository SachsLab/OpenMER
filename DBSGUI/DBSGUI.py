import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from collections import namedtuple
from cerebus import cbpy
from pyqtgraph.dockarea import *

SpikeEventData = namedtuple("SpikeEventData",
                            ["chan", "unit", "ts", "arrival_ts"])
ContinuousData = namedtuple("ContinuousData",
                            ["chan", "samples", "arrival_ts"])
SAMPLERATE = 30000
NCHANNELS = 64
NUNITS = 6  # Units per channel


class MyGUI(QtGui.QMainWindow):
    counter = 0

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
        self.myMenubar.setGeometry(0,0,1200,21)
        self.myMenubar.setObjectName("MenuBar")
        fileMenu = self.myMenubar.addMenu('File')
        addChannelAction = QtGui.QAction('Add a channel',self)
        #selectChannelAction = QtGui.QAction('Select Channel',self)
        fileMenu.addAction(addChannelAction)
        channelList = fileMenu.addMenu('Channel List')
        addChannelAction.triggered.connect(self.AddChannelToPlot)
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

        # Setting spikes, raw and raster data buffers
        # self.my_spks = []
        # self.my_raws = []
        # self.my_rasters = []
        #self.n_chans_to_plot = 1
        self.spk_buffer = np.empty((0, 0))
        self.raw_buffer = np.empty((0, 0))
        self.raster_buffer = [np.empty((1,)), ]

    def AddChannelToPlot(self):
        totalNumber = self.dock_area.findAll()
        dock_index = len(totalNumber[0])
        print(totalNumber[0])
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
        self.dock_area.addDock(raster_dock, position='right', relativeTo=continuous_dock)
        self.raster_buffer.append(np.empty((1,)))

    def setupNeuroport(self):
        self.cbsdkConn = cbsdkConnection()

    def update(self):

        dock_info = []
        for dock_key in self.dock_area.docks.keys():
            dock_type, dock_num = dock_key.split(' ')
            this_dock = self.dock_area.docks[dock_key]
            combo_box = this_dock.findChild(QtGui.QComboBox)
            chan_ix = int(combo_box.currentText())
            dockplot = this_dock.findChild(name="RASTER" if dock_type == 'Raster' else "SPK")  #?
            #TODO: Search for children with name == "RASTER" or name == "SPK", set to dockplot
            dock_info.append({'type': dock_type, 'num': int(dock_num), 'chan': chan_ix, 'plot': dockplot})

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
        spk_index = -1
        gi_index = -1  # FIXME
        for dinf in dock_info:
            if dinf['type'] == 'Continuous':
                try:
                    buf_ix = dinf['num']
                    dat_ix = dinf['chan']
                    self.spk_buffer[buf_ix-1, -n_samples_to_add:] = contdat[cont_chans.index(dat_ix)][1]
                    tvec = np.arange(-self.spk_buffer.shape[1], 0) / SAMPLERATE

                    # Shrink spk_buffer to time >= -1
                    sample_mask = tvec >= -1
                    tvec = tvec[sample_mask]
                    self.spk_buffer = self.spk_buffer[:, sample_mask]

                    pi = dinf['plot'].getPlotItem()
                    dataItems = pi.listDataItems()
                    dataItems[0].setData(self.spk_buffer[dinf['num']-1, :].ravel(), x=tvec)
                except ValueError:
                    pass

            elif dinf['type'] == 'Raster':
                try:
                    this_ix = timestamp_chans.index(dinf['chan'])
                    this_timestamps = timestamps[this_ix][1]['timestamps']
                    raster_buf_ix = dinf['num']
                    raster_dat_ix = dinf['chan']
                except ValueError:
                    this_timestamps = [[]]

                #self.raster_buffer[raster_buf_ix-1] = np.append(self.raster_buffer[gi_index], this_timestamps[unit_ix])
                self.raster_buffer[raster_buf_ix-1] = this_timestamps[0]
                ts = (self.raster_buffer[raster_buf_ix-1] - ts_time) / SAMPLERATE

                # Only keep last 5 seconds
                keep_mask = ts > -5
                self.raster_buffer[raster_buf_ix-1] = self.raster_buffer[raster_buf_ix-1][keep_mask]  # Trim buffer (samples)
                ts = ts[keep_mask]  # Trim timestamps (seconds)

                xpos = np.mod(ts, 1)
                ypos = -np.ceil(ts) / 5 + 0.1
                positions = np.vstack((xpos, ypos)).T

                dinf['plot'].setData(pos=positions, symbolPen=self.mypens[0])


class cbsdkConnection(object):

    def __init__(self, inst_addr='192.168.137.128', inst_port=51001, client_port=51002,
                 client_addr='192.168.137.255' if sys.platform == 'linux2' else '255.255.255.255',
                 receive_buffer_size=(4096 * 1536) if sys.platform == 'win32' else (4096 * 1536)):
        #TODO: Find the correct buffer size and client_addr for all platforms.
        #linux buffer size might be 8388608

        self._cbsdk_config = {'instance': 0, 'buffer_parameter': {'absolute': True},
                              'range_parameter': {}, 'get_events': True, 'get_continuous': True}
        self.cbsdk_last_config_time = None

        self.parameters = {'inst-addr': inst_addr, 'inst-port': inst_port, 'client-port': client_port,
                           'client-addr': client_addr, 'receive-buffer-size': receive_buffer_size}
        #self.parameters = kwargs
        self.connect()

    def __del__(self):
        self.disconnect()

    def connect(self):
        # Open the interface to the NSP #
        print('calling cbpy.open in cerelink.connect()')
        result, return_dict = cbpy.open(connection='default', parameter=self.parameters)
        print("cbpy.open returned result: {}; return_dict: {}".format(result, return_dict))

        self.cbsdk_config = {'buffer_parameter': {'absolute': True}}

    def disconnect(self):
        # Close the interface to the NSP (or nPlay). #
        print('calling cbpy.close in cerelink.disconnect()')
        result = cbpy.close()
        print("result: {}".format(result))

    @property
    def cbsdk_config(self):
        return self._cbsdk_config

    @cbsdk_config.setter
    def cbsdk_config(self, indict):
        if not isinstance(indict, dict):
            try:
                indict = dict(indict)
            except TypeError:
                print("Value passed to cbsdk_config must be a dictionary")

        if 'buffer_parameter' in indict:
            indict['buffer_parameter'] = {**self._cbsdk_config['buffer_parameter'], **indict['buffer_parameter']}
        if 'range_parameter' in indict:
            indict['range_parameter'] = {**self._cbsdk_config['range_parameter'], **indict['range_parameter']}

        self._cbsdk_config = {**self._cbsdk_config, **indict}
        self._do_cbsdk_config(**self._cbsdk_config)

    @property
    def is_running(self):
        return self.cbsdk_last_config_time is not None

    def _do_cbsdk_config(self, instance=0, reset=True, buffer_parameter={}, range_parameter={}, get_events=True, get_continuous=True):
        """
        :param instance:
        :param reset: True to clear buffer and start acquisition, False to stop acquisition
        :param buffer_parameter - (optional) dictionary with following keys (all optional)
               'double': boolean, if specified, the data is in double precision format
               'absolute': boolean, if specified event timing is absolute (new polling will not reset time for events)
               'continuous_length': set the number of continuous data to be cached
               'event_length': set the number of events to be cached
               'comment_length': set number of comments to be cached
               'tracking_length': set the number of video tracking events to be cached
        :param range_parameter - (optional) dictionary with following keys (all optional)
               'begin_channel': integer, channel to start polling if certain value seen
               'begin_mask': integer, channel mask to start polling if certain value seen
               'begin_value': value to start polling
               'end_channel': channel to end polling if certain value seen
               'end_mask': channel mask to end polling if certain value seen
               'end_value': value to end polling
        :param noevent: equivalent of setting 'event_length' to 0
        :param nocontinuous: equivalent of setting 'continuous_length' to 0
        :return:
        """
        res, was_reset = cbpy.trial_config(instance=instance, reset=reset, buffer_parameter=buffer_parameter,
                                      range_parameter=range_parameter, noevent=int(not get_events),
                                      nocontinuous=int(not get_continuous))

        res, self.cbsdk_last_config_time = cbpy.time(instance=instance)

    def start_data(self):
        # Start the buffering of data. #
        self._do_cbsdk_config(**self._cbsdk_config)

    def stop_data(self):
        # Stop the buffering of data. #
        cbpy.trial_config(reset=False)
        self.cbsdk_last_config_time = None

    def get_event_data(self):
        # Spike event data. #
        if self.cbsdk_last_config_time:
            result, trial = cbpy.trial_event(instance=self.cbsdk_config['instance'], reset=True)
            if result != 0:
                print('failed to get trial event data. Error (%d)' % result)
                return False, False
            else:
                return trial, cbpy.time(instance=self.cbsdk_config['instance'])[1]
        else:
            return False, False

    def get_continuous_data(self):
        result, trial = cbpy.trial_continuous(instance=self.cbsdk_config['instance'], reset=True)
        return trial, cbpy.time(instance=self.cbsdk_config['instance'])[1]


class Spikes:

    update_freq = 30000.

    def __init__(self, channels):
        self.conn = cbsdkConnection()
        self.conn.connect()
        self.conn.select_channels(channels)

    def start(self):
        self.conn.start_data()
        self.conn.get_event_data()

    def stop(self):
        self.conn.stop_data()


if __name__ == '__main__':

    qapp = QtGui.QApplication(sys.argv)
    aw = MyGUI()

    timer = pg.QtCore.QTimer()
    timer.timeout.connect(aw.update)
    timer.start(50)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()