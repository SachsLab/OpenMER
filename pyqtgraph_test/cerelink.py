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


class MyGUI(QtGui.QMainWindow):
    counter = 0

    def __init__(self):
        super(MyGUI, self).__init__()
        self.setupUI()
        self.cbsdkconnection()
        self.show()

    def setupUI(self):
        self.area = DockArea(self)
        self.setCentralWidget(self.area)
        self.resize(1000, 600)
        self.setWindowTitle('dockarea')
        self.statusBar().showMessage('Ready...')

        ## setting the central widget
        self.d1 = Dock("Scrolling Plot", size=(700, 200))     ## give this dock the minimum possible size
        self.d2 = Dock("Raster", size=(700, 200))
        self.d3 = Dock("Time Series", size=(700, 200))
        self.d4 = Dock("Dock4", size=(300, 200))
        self.d5 = Dock("Dock5", size=(300, 200))
        self.d6 = Dock("Dock6", size=(300, 200))
        self.d7 = Dock("Dock7", size=(300, 200))

        ## setting each dock's position
        self.area.addDock(self.d1, 'left')
        self.area.addDock(self.d2, 'bottom', self.d1)
        self.area.addDock(self.d3, 'bottom', self.d2)
        self.area.addDock(self.d4, 'right')
        self.area.addDock(self.d6, 'bottom', self.d4)
        self.area.addDock(self.d5, 'top', self.d4)
        self.area.addDock(self.d7, 'bottom', self.d6)

        self.area.moveDock(self.d4, 'above', self.d5)

        #Add widget in each Dock
        self.d1.hideTitleBar()
        self.w1 = pg.LayoutWidget()
        self.combox = QtGui.QComboBox()
        self.w1_plot = pg.GraphicsLayoutWidget()
        self.axisItem = pg.AxisItem('bottom',maxTickLength=-10)
        self.w1_plot.addItem(self.axisItem)
        #self.w1.plot.setYRange(0,1)
        self.w1.addWidget(self.combox, row=0, col=0)
        self.w1.addWidget(self.w1_plot, row=1, col=0)

        #self.vt = raster(xvals=[0.1,0.3,0.4,0.7,0.9],yrange=[0,1])
        #self.w1.addItem(self.vt)
        self.d1.addWidget(self.w1)

        # Make the raster plot
        self.d2.hideTitleBar()
        self.w21 = pg.PlotWidget()

        self.d2.addWidget(self.w21)

        self.d3.hideTitleBar()
        self.w3 = pg.PlotWidget()
        self.d3.addWidget(self.w3)
        self.data1 = np.random.normal(size=300)
        self.curve1 = self.w3.plot(self.data1)
        self.ptr1 = 0

    ## This is the main function of receiving data from NSP and show it on the each type of plot
    def __del__(self):
        res = cbpy.close(instance=0)

    def cbsdkconnection(self):

        conn_params = {'inst-addr': '192.168.137.128',
                       'inst-port': 51001,
                       'client-addr': '255.255.255.255',
                       'client-port': 51002,
                       'receive-buffer-size': (4096 * 1536)}

        result, return_dict = cbpy.open(connection='default', parameter=conn_params)
        if result < 0:
            self.nsp_IsOpen = False
        else:
            self.nsp_IsOpen = True

        buff_params = {'absolute': True}
        config_result, reset = cbpy.trial_config(buffer_parameter=buff_params)
        if config_result == 0:
            self.nsp_IsConfig = True
        else:
            self.nsp_IsConfig = False

        self.sleep_time = 1
        time.sleep(self.sleep_time)

    ## update1 function: show scrolling plot
    def update1(self):

        self.data1[:-1] = self.data1[1:]  # shift data in the array one sample left
        self.data1[-1] = np.random.normal()
        self.ptr1 += 1
        self.curve1.setData(self.data1)
        self.curve1.setPos(self.ptr1, 0)

    def update2(self):

        if self.nsp_IsOpen and self.nsp_IsConfig:

            print('calling cbpy.trial_event()')
            result, event_trial = cbpy.trial_event(reset=True)
            #t_start = time.time()

            if result == 0:
                timestamps = [event_trial[ch_ix][1]['timestamps'][0] for ch_ix in range(len(event_trial))]
                # for i in range(len(trial)):
                #     print('samples:', trial[i][1]['timestamps'][0])
                print('trial:', timestamps[42])

                result, nsp_time = cbpy.time()
                print('cbpy time:', nsp_time)

    def update(self):
        self.update1()
        self.update2()

class cbsdkConnection(object):

    def __init__(self):
        self.parameters = dict()
        self.parameters['inst-addr'] = '192.168.137.128'
        self.parameters['inst-port'] = 51001
        self.parameters['client-port'] = 51002

        if sys.platform == 'win32':  # Windows
            print('Using Windows settings for cbpy')
            self.parameters['client-addr'] = '255.255.255.255'
            self.parameters['receive-buffer-size'] = (4096 * 1536)

        self._init = False

    def connect(self):
        # Open the interface to the NSP #

        print('calling cbpy.open in cerelink.connect()')
        result, return_dict = cbpy.open(connection='default', parameter=self.parameters)
        print('cbpy.open result:', result)
        print('cbpy.open return_dict:', return_dict)
        print('')

        # return_dict = cbpy.open('default', self.parameters)  # old cbpy

        self._init = True

    def select_channels(self, channels):
        # Sets the channels on which to receive event/continuous data.
        # Parameters
        # ----------
        # channels : array_like
        #     A sorted list of channels on which you want to receive data.

        if not self._init:
            raise ValueError("Please open the interface to Central/nPlay first.")

        buffer_parameter = {'absolute': True}  # want absolute timestamps

        # ability to select desired channels not yet implemented in cbpy #
        range_parameter = dict()
        range_parameter['begin_channel'] = channels[0]
        range_parameter['end_channel'] = channels[-1]

        print('calling cbpy.trial_config in cerelink.select_channels()')
        result, reset = cbpy.trial_config(buffer_parameter=buffer_parameter, reset=True)
        print('cbpy.trial_config result:', result)
        print('cbpy.trial_config reset:', reset)
        print('')

    def start_data(self):
        # Start the buffering of data. #

        if not self._init:
            raise ValueError("Please open the interface to Central/nPlay first.")

        self.streaming = True

    def stop_data(self):
        # Stop the buffering of data. #

        if not self._init:
            raise ValueError("Please open the interface to Central/nPlay first.")

        print('calling cbpy.trial_config in cerelink.stop()')
        result, reset = cbpy.trial_config(reset=False)
        print('cbpy.trial_config result:', result)
        print('cbpy.trial_config reset:', reset)
        print('')

        self.streaming = False

    def countChannels(self):
        # count the total channels in received trial event (unfinished)#

        if not self._init:
            raise ValueError("Please open the interface to Central/nPlay first.")

    def disconnect(self):
        # Close the interface to the NSP (or nPlay). #

        if not self._init:
            raise ValueError("Please open the interface to Central/nPlay first.")

        print('calling cbpy.close in cerelink.disconnect()')
        result = cbpy.close()
        print('result:', result)
        print('')

        self._init = False

    def __del__(self):
        self.disconnect()

    def get_event_data(self):
        # Spike event data. #

        sleep_time = 1
        time.sleep(sleep_time)

        while self.streaming:

            result, trial = cbpy.trial_event(instance=0, reset=True)
            res, nsp_time = cbpy.time()
            if result != 0:
                print('failed to get trial event data. Error (%d)' % result)

            # for list_ in trial:
            #     chan = list_[0]
            #     for unit, unit_ts in enumerate(list_[1]['timestamps']):
            #         for ts in unit_ts:
            #             # blackrock unit numbers are actually 0-based
            #             # however, within Python code, web interface, etc., use 1-based numbering for unit number
            #             yield SpikeEventData(chan=chan - self.channel_offset, unit=unit + 1, ts=ts,
            #                                  arrival_ts=arrival_ts)

            timestamps = [trial[ch_ix][1]['timestamps'][0] for ch_ix in range(len(trial))]
            print('timestamps:', timestamps[8])
            print('time:', nsp_time)

            time.sleep(sleep_time)

    def get_continuous_data(self):

        sleep_time = 0

        while self.streaming:
            result, trial = cbpy.trial_continuous(reset=True)
            arrival_ts = time.time()

            continous = [trial[ch_ix] for ch_ix in range (len(trial))]
            chan = continous[0]
            continous_data = continous[1]

            time.sleep(sleep_time)


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
    timer.start(aw.sleep_time * 1000)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        aw.__del__()
        QtGui.QApplication.instance().exec_()