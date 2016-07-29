import sys
import time
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

        self.resize(1200, 900)
        self.setWindowTitle('Neuroport DBS')
        self.statusBar().showMessage('Ready...')

        #TODO: Create NUNITS pens
        self.mypens = [pg.mkPen(cosmetic=False, width=0.5)]
        # mybrush = pg.mkBrush(QtGui.QBrush(QtGui.QColor(QtCore.Qt.blue), style=QtCore.Qt.VerPattern))
        mybrush = None

        self.my_spks = []
        self.my_raws = []
        self.my_rasters = []
        n_chans_to_plot = 1
        self.spk_buffer = np.empty((n_chans_to_plot, 0))
        self.raw_buffer = np.empty((n_chans_to_plot, 0))
        self.raster_buffer = [np.empty((1,)) for x in range(n_chans_to_plot)]
        for ch_ix in range(n_chans_to_plot):
            continuous_dock = Dock("Continuous " + str(ch_ix), size=(900, 300))
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
            self.my_spks.append(spk_plot)
            self.my_raws.append(raw_plot)

            raster_dock = Dock("Raster " + str(ch_ix), size=(300, 300))
            raster_layout = pg.LayoutWidget()
            combo2 = QtGui.QComboBox()
            for ch_id in range(NCHANNELS):
                combo2.addItem("{}".format(ch_id+1))
            raster_layout.addWidget(combo2)
            raster_item = pg.GraphItem(symbolPen=self.mypens[0], symbolBrush=mybrush)
            raster_plot = pg.PlotWidget()
            raster_plot.setLimits(xMin=0, xMax=1, yMin=0, yMax=1, minXRange=1.0, maxXRange=1.0, minYRange=1.0,
                                  maxYRange=1.0)
            raster_plot.addItem(raster_item)
            raster_layout.addWidget(raster_plot)
            raster_dock.addWidget(raster_layout)
            self.my_rasters.append(raster_item)  # TODO: Get rid of me when I figure out how to search for GraphItem
            #raster_dock.hideTitleBar()
            self.dock_area.addDock(raster_dock, position='right', relativeTo=continuous_dock)

    def setupNeuroport(self):
        self.cbsdkConn = cbsdkConnection()

    def update(self):
        # Get event timestamps
        timestamps, ts_time = self.cbsdkConn.get_event_data()
        timestamp_chans = [x[0] for x in timestamps]
        # Buffer updated inside dock loop

        # Get continuous
        contdat, cont_time = self.cbsdkConn.get_continuous_data()
        cont_chans = [x[0] for x in contdat]
        first_dat = contdat[0][1]
        n_samples_to_add = first_dat.size
        self.spk_buffer = np.concatenate((self.spk_buffer, np.nan*np.ones((self.spk_buffer.shape[0], n_samples_to_add), dtype=first_dat.dtype)), axis=1)

        # self.data1[:-1] = self.data1[1:]  # shift data in the array one sample left
        # self.data1[-1] = np.random.normal()
        # self.ptr1 += 1
        # self.curve1.setData(self.data1)
        # self.curve1.setPos(self.ptr1, 0)

        spk_index = -1
        gi_index = -1  # FIXME
        for dock_key in self.dock_area.docks.keys():
            this_dock = self.dock_area.docks[dock_key]
            dock_type = dock_key.split(' ')[0]
            combo_box = this_dock.findChild(QtGui.QComboBox)
            chan_ix = int(combo_box.currentText())
            if dock_type == 'Raster':
                gi_index += 1  # FIXME
                try:
                    this_ix = timestamp_chans.index(chan_ix)
                    this_timestamps = timestamps[this_ix][1]['timestamps']
                except ValueError:
                    this_timestamps = [[]]

                # for unit_ix in range(NUNITS):
                unit_ix = 0
                self.raster_buffer[gi_index] = np.append(self.raster_buffer[gi_index], this_timestamps[unit_ix])
                ts = (self.raster_buffer[gi_index] - ts_time) / SAMPLERATE

                # Only keep last 5 seconds
                keep_mask = ts > -5
                self.raster_buffer[gi_index] = self.raster_buffer[gi_index][keep_mask]  # Trim buffer (samples)
                ts = ts[keep_mask]  # Trim timestamps (seconds)

                xpos = np.mod(ts, 1)
                ypos = -np.ceil(ts)/5+0.1
                positions = np.vstack((xpos, ypos)).T

                gi = self.my_rasters[gi_index]
                gi.setData(pos=positions, symbolPen=self.mypens[0])

            elif dock_type == 'Continuous':
                spk_index += 1  #FIXME
                try:
                    this_ix = cont_chans.index(chan_ix)
                    self.spk_buffer[this_ix, -n_samples_to_add:] = contdat[this_ix][1]
                    tvec = np.arange(-self.spk_buffer.shape[1], 0) / SAMPLERATE

                    sample_mask = tvec >= -1
                    tvec = tvec[sample_mask]
                    self.spk_buffer = self.spk_buffer[:, sample_mask]

                    #pw = this_dock.children()[2].children()[1].children()[2]
                    pi = self.my_spks[spk_index].getPlotItem()
                    dataItems = pi.listDataItems()
                    dataItems[0].setData(self.spk_buffer.ravel(), x=tvec)
                except ValueError:
                    pass


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
    #spike1 = Spikes([4,5,6,7,8])
    #spike1.start()

    qapp = QtGui.QApplication(sys.argv)
    aw = MyGUI()

    timer = pg.QtCore.QTimer()
    timer.timeout.connect(aw.update)
    timer.start(50)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()