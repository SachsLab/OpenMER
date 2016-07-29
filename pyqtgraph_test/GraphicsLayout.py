from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
from cerebus import cbpy
from pyqtgraph import UIGraphicsItem, AxisItem
import time
from pyqtgraph.dockarea import *

#res, conn_type = cbpy.open(instance = 0, connection = 'default', parameter = conn_params)



class MyGUI(QtGui.QMainWindow):
    counter = 0

    def __init__(self):
        super(MyGUI, self).__init__()
        self.setupUI()
        self.cbsdkconnect()
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
        self.w21 = pg.PlotWidget()

        # self.w21_p1 = pg.AxisItem('bottom', maxTickLength=-20)
        # self.w21.addItem(self.w21_p1, row=0, col=0)
        # self.w21_p2 = pg.AxisItem('bottom', maxTickLength=-20)
        # self.w21_p2.setRange(mn=0, mx=100000)
        # self.w21_p2.setStyle(tickTextOffset= 10, tickTextHeight= 20)
        # self.w21.addItem(self.w21_p2, row=3, col=0)
        # self.w21_p3 = pg.AxisItem('bottom', maxTickLength=-10)
        # self.w21.addItem(self.w21_p3, row=5, col=0)
        # self.w21_p4 = pg.AxisItem('bottom', maxTickLength=-10)
        # self.w21.addItem(self.w21_p4, row=7, col=0)
        # self.w21_p5 = pg.AxisItem('bottom', maxTickLength=-10)
        # self.w21.addItem(self.w21_p5, row=9, col=0)
        # self.w21_p6 = pg.AxisItem('bottom', maxTickLength=-10)
        # self.w21.addItem(self.w21_p6, row=10, col=0)
        # self.w21_p7 = pg.AxisItem('bottom', maxTickLength=-10)
        # self.w21.addItem(self.w21_p7, row=12, col=0)
        self.d2.addWidget(self.w21)

        self.d3.hideTitleBar()
        self.w3 = pg.PlotWidget()
        self.d3.addWidget(self.w3)
        self.data1 = np.random.normal(size=300)
        self.curve1 = self.w3.plot(self.data1)
        self.ptr1 = 0

    ## This is the main function of receiving data from NSP and show it on the each type of plot
    def cbsdkconnect(self):
        conn_params = { 'inst-addr': '192.168.137.128',
                        'inst-port': 51001,
                        'client-addr': '255.255.255.255',
                        'client-port': 51002,
                        'receive-buffer-size': (4096 * 1536)}

        res, con_type = cbpy.open(instance=0, connection='default', parameter=conn_params)
        if res < 0:
            self.statusBar().showMessage('connection open faild, error %d' % self.res)
        else:
            self.nsp_isopen = True

        config_res, config_reset = cbpy.trial_config(instance=0, reset=True, buffer_parameter={'absolute': True})
        if config_res == 0:
            self.nsp_config = True
        else:
            self.nsp_config = False

        self.event_res, self.event_trial = cbpy.trial_event(instance=0,reset=True)
        if self.event_res == 0:
            self.nsp_trial = True
        else:
            self.nsp_trial = False


    ## update1 function: show scrolling plot
    def update1(self):
        self.data1[:-1] = self.data1[1:]  # shift data in the array one sample left
        self.data1[-1] = np.random.normal()
        self.ptr1 += 1
        self.curve1.setData(self.data1)
        self.curve1.setPos(self.ptr1, 0)

    def update2(self):
        if not (self.nsp_isopen and self.nsp_config):

            conn_params = {'inst-addr': '192.168.137.128',
                           'inst-port': 51001,
                           'client-addr': '255.255.255.255',
                           'client-port': 51002,
                           'receive-buffer-size': (4096 * 1536)}

            # buff_params = {'absolute': True}

            res, con_type = cbpy.open(instance=0, connection='default', parameter=conn_params)
            config_res, config_reset = cbpy.trial_config(instance=0, reset=True, buffer_parameter={'absolute': True})
            res, self.nsp_reset_time = cbpy.time()
            result, event_trial = cbpy.trial_event(reset=True)

            timestamps = [event_trial[ch_ix][1]['timestamps'][0] for ch_ix in range(len(event_trial))]

            # TODO: Get list of all channels
            for ch_ix in range(len(event_trial)):
                self.combox.addItem("Channel ", timestamps[ch_ix][0])

            self.spike_times = [np.asarray([]) for x in range(len(event_trial))]  # TODO: Replace 64 with len(channel_list)
            self.nsp_isopen = True
            self.event_trial = event_trial
            self.nsp_config = True

        event_trial = self.event_trial
        print('calling cbpy.trial_event()')
        #res, event_trial = cbpy.trial_event(reset=True)
        for ch_event in event_trial:
            ch_id = ch_event[0]
            ch_timestamps = ch_event[1]['timestamps'][0] #TODO: Fix for online sorting
            self.spike_times[ch_id] = np.concatenate((self.spike_times[ch_id], ch_timestamps))
            self.spike_times[ch_id] = self.spike_times[ch_id][(self.spike_times[ch_id]-self.nsp_reset_time) < (30000*5)]

        # print('nsp.time: %d' % nsp_time)

        #self.nsp_reset_time

        # for i in range(len(trial)):
        #     print('samples:', trial[i][1]['timestamps'][0])

        temp = (self.spike_times[5] - self.nsp_reset_time) / 30000
        positions = np.empty((0, 2))  # return a new array of given shape and type
        joins = np.empty((0, 2), dtype=int)

        for start_time in range(5):
            interval_mask = np.logical_and(temp >= start_time, temp < start_time + 1)
            xvals = temp[interval_mask] - start_time
            this_ymax = (5 - start_time) / 5.0
            for x in xvals:
                positions = np.concatenate((positions, np.atleast_2d([x, this_ymax - 0.1])))

        # print 'calling cbpy.time()'
        # result, nsp_time = cbpy.time()
        # print('result:', result)
        # print('time:', nsp_time)
        # print('')

        mypen = pg.mkPen(cosmetic=False, width=0.5)
        # mybrush = pg.mkBrush(QtGui.QBrush(QtGui.QColor(QtCore.Qt.blue), style=QtCore.Qt.VerPattern))
        self.w21.clear()
        self.gi = pg.GraphItem(pos=positions, symbolPen=mypen, symbolBrush=None)  # , adj=joins)
        self.w21.addItem(self.gi)

    def __del__(self):
        res = cbpy.close(instance=0)

#res, reset = cbpy.trial_config(instance=0, reset=True)

    def update(self):
        self.update1()
        self.update2()

## Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    import sys

    qapp = QtGui.QApplication(sys.argv)
    aw = MyGUI()

    if aw.nsp_isopen and aw.nsp_config:
        time.sleep(1)
        timer = pg.QtCore.QTimer()
        timer.timeout.connect(aw.update)
        timer.start(1000)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        aw.__del__()
        QtGui.QApplication.instance().exec_()