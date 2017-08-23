import numpy as np
import pyqtgraph as pg
from pyqtgraph import (GraphicsView, GraphicsLayout, GraphicsObject)
from pyqtgraph.Qt import (QtCore, QtGui)
from pyqtgraph.widgets.PlotWidget import PlotWidget

from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph.graphicsItems.GraphicsObject import GraphicsObject
from pyqtgraph import getConfigOption
from pyqtgraph import functions as fn
import numpy as np

class BarGraph(pg.BarGraphItem):

    barClicked = QtCore.pyqtSignal(object)
    def __init__(self, **opts):

        self._last_index = np.asarray([0])
        self.highlight = dict(
            pen = pg.mkPen(QtGui.QColor("orange")),
            brush = pg.mkBrush(QtGui.QColor("orange"))
        )
        pg.BarGraphItem.__init__(self, **opts)

    def mouseClickEvent(self, event):
        self.barClicked.emit(self)

    def hoverEvent(self, event):
        view = self.getViewBox()

        index = self._last_index
        if event.isEnter():
            if event.currentItem is not None:
                lp = event.lastPos()
                p = event.pos()

            diff = np.abs(self.opts['x'] - p.x())
            index = np.where(diff == np.min(diff))[0]

            if index != self._last_index:
                self._current_bar = pg.BarGraphItem(x=self.opts['x'][index], height=self.opts['height'][index], width=self.opts['width'],
                                                    pen=self.highlight['pen'], brush=self.highlight['brush'])
                self._last_bar = pg.BarGraphItem(x=self.opts['x'][self._last_index], height=self.opts['height'][self._last_index], width=self.opts['width'],
                                                 pen=self.opts['pen'], brush=self.opts['brush'])

                view.addItem(self._current_bar)
                view.addItem(self._last_bar)

        self._last_index = index
