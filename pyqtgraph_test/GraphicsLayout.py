from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import pyqtgraph.functions as fn
import weakref
import pyqtgraph.console
from cerebus import cbpy
from pyqtgraph import UIGraphicsItem
import time

from pyqtgraph.dockarea import *

#res, conn_type = cbpy.open(instance = 0, connection = 'default', parameter = conn_params)

class raster(UIGraphicsItem):
    def __init__(self, xvals=None, yrange=None, pen=None):
        if yrange is None:
            yrange = [0, 1]
        if xvals is None:
            xvals = []

        UIGraphicsItem.__init__(self)

        if pen is None:
            pen = (200, 200, 200)

        self.path = QtGui.QGraphicsPathItem()
        self.ticks = []
        self.xvals = []
        self.yrange = [0, 1]
        self.setPen(pen)
        self.setYRange(yrange)
        self.setXVals(xvals)

    def setPen(self, *args, **kwargs):
        """Set the pen to use for drawing ticks. Can be specified as any arguments valid
        for :func:`mkPen<pyqtgraph.mkPen>`"""
        self.pen = fn.mkPen(*args, **kwargs)

    def setXVals(self, vals):
        self.xvals = vals
        self.rebuildTicks()
        # self.valid = False

    def setYRange(self, vals):
        """Set the y range [low, high] that the ticks are drawn on. 0 is the bottom of
        the view, 1 is the top."""
        self.yrange = vals
        self.rebuildTicks()

    def dataBounds(self, *args, **kargs):
        return None  ## item should never affect view autoscaling

    def yRange(self):
        return self.yrange

    def rebuildTicks(self):
        self.path = QtGui.QPainterPath()
        yrange = self.yRange()
        for x in self.xvals:
            self.path.moveTo(x, 0.)
            self.path.lineTo(x, 1.)

    def paint(self, p, *args):
        UIGraphicsItem.paint(self, p, *args)

        br = self.boundingRect()
        h = br.height()
        br.setY(br.y() + self.yrange[0] * h)
        br.setHeight(h - (1.0 - self.yrange[1]) * h)
        p.translate(0, br.y())
        p.scale(1.0, br.height())
        p.setPen(self.pen)
        p.drawPath(self.path)

class MyGUI(QtGui.QMainWindow):
    def __init__(self):
        super(MyGUI, self).__init__()
        self.setupUI()
        self.show()
        self.cbSDKconnect()

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
        self.w1 = pg.PlotWidget(title="Scrolling Plot")
        self.vt = raster(xvals=[0.1,0.3,0.4,0.7,0.9],yrange=[0,1])
        self.w1.addItem(self.vt)
        self.d1.addWidget(self.w1)

        # Make the raster plot
        self.w21 = pg.PlotWidget()
        self.vt1 = raster(xvals=np.random.normal(size=100),yrange=[0,1])
        self.w21.addItem(self.vt1)

        self.w22 = pg.PlotWidget()
        self.vt2 = raster(xvals=np.random.normal(size=100),yrange=[0,1])
        self.w22.addItem(self.vt2)

        self.w23 = pg.PlotWidget()
        self.vt3 = raster(xvals=np.random.normal(size=100),yrange=[0,1])
        self.w23.addItem(self.vt3)

        self.w24 = pg.PlotWidget()
        self.vt4 = raster(xvals=np.random.normal(size=100),yrange=[0,1])
        self.w24.addItem(self.vt4)

        self.w25 = pg.PlotWidget()
        self.vt5 = raster(xvals=np.random.normal(size=100),yrange=[0,1])
        self.w25.addItem(self.vt5)

        self.d2.addWidget(self.w21)
        self.d2.addWidget(self.w22)
        self.d2.addWidget(self.w23)
        self.d2.addWidget(self.w24)
        self.d2.addWidget(self.w25)

        self.d3.hideTitleBar()
        self.w3 = pg.PlotWidget()
        self.d3.addWidget(self.w3)
        self.data1 = np.random.normal(size=300)
        self.curve1 = self.w3.plot(self.data1)
        self.ptr1 = 0

    ## update1 function: show scrolling plot
    def update1(self):
        self.data1[:-1] = self.data1[1:]  # shift data in the array one sample left
        self.data1[-1] = np.random.normal()
        self.curve1.setData(self.data1)
        self.ptr1 += 1

    ## This is the main function of receiving data from NSP and show it on the each type of plot
    def cbSDKconnect(self):
        conn_params = {'inst-addr': '192.168.137.128',
                       'inst-port': 51001,
                       'client-addr': '255.255.255.255',
                       'client-port': 51002,
                       'receive-buffer-size': (4096 * 1536)}

        #res, conType = cbpy.open(instance = 0, connection = 'default', parameter = conn_params)
        #version_res, ver_dict = cbpy.version(instance = 0)
        connection = cbpy.get_connection_type(instance=0)
        #config_res, config_reset = cbpy.trial_config(instance = 0, reset = True,)
        #event_res, event_trial = cbpy.trial_event(instance = 0)
        # if res < 0:
        #     self.statusBar().showMessage('connection open faild, error %d' % res)

        self.w5 = QtGui.QLabel(str(connection))
        self.d5.addWidget(self.w5)

#res, reset = cbpy.trial_config(instance=0, reset=True)

        # def update():
        #     update1()
        # timer = pg.QtCore.QTimer()
        # timer.timeout.connect(update)
        # timer.start(50)

## Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    import sys

    qapp = QtGui.QApplication(sys.argv)
    aw = MyGUI()

    #res, conn_type = cbpy.open(instance = 0, connection = 'default', parameter = conn_params)
    timer = pg.QtCore.QTimer()
    timer.timeout.connect(aw.update1)
    timer.start(50)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()