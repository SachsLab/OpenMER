import numpy as np
import pyqtgraph as pg
from pyqtgraph import (GraphicsView, GraphicsLayout, GraphicsObject)
from qtpy import (QtCore, QtGui)

from pyqtgraph.widgets.PlotWidget import PlotWidget

from pyqtgraph.graphicsItems.GraphicsObject import GraphicsObject
from pyqtgraph import getConfigOption
from pyqtgraph import functions as fn
import numpy as np

class BarGraph(pg.BarGraphItem):

    barClicked = QtCore.Signal(object)
    def __init__(self, **opts):
        self._last_index = None
        self._last_y = np.inf
        self._highlighted_bar = None
        self.highlight = dict(
            pen=pg.mkPen(QtGui.QColor("orange")),
            brush=pg.mkBrush(QtGui.QColor("orange"))
        )
        pg.BarGraphItem.__init__(self, **opts)

    def mouseClickEvent(self, event):
        if event.pos().y() != self._last_y:
            self.barClicked.emit(self)
            self._last_y = event.pos().y()

    def hoverEvent(self, event):
        view = self.getViewBox()
        index = np.argmin(np.abs(self.opts['x'] - event.pos().x()))

        if index != self._last_index:

            if self._highlighted_bar is not None:
                view.removeItem(self._highlighted_bar)
                self._highlighted_bar = None

            if event.isEnter():
                temp = pg.BarGraphItem(x=(self.opts['x'][index],),
                                       height=(self.opts['height'][index],),
                                       width=self.opts['width'],
                                       pen=self.highlight['pen'], brush=self.highlight['brush'])
                view.addItem(temp)
                self._highlighted_bar = temp
                self._last_index = index
