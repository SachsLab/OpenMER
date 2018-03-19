import numpy as np
import pyqtgraph as pg
from pyqtgraph import (GraphicsView, GraphicsLayout)
from qtpy import (QtCore, QtGui, QtWidgets)
import quantities as pq

from .image_properties import (getRGBAFromCMap, getLUT)
from .bar_widget import BarGraph

THEMES = {
    'dark': {
        'pencolors': ["cyan", QtGui.QColor(0, 255, 0), "magenta", "red", "yellow", "white"],
        'bgcolor': QtCore.Qt.black,
        'labelcolor': QtCore.Qt.gray,
        'axiscolor': QtCore.Qt.gray,
        'axiswidth': 1
    }
}


class PlotsWidget(QtGui.QWidget):
    """
    """
    def __init__(self):
        QtGui.QWidget.__init__(self)

        self.data = {}

        self.gv = pg.GraphicsView()
        self.gl = GraphicsLayout()

        self.gv.setCentralItem(self.gl)

        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.gv, 1, 1, 1, 1)

        self.setLayout(self.layout)

    def clear(self):
        for _, pl in np.ndenumerate(self.pl):
            pl.clear()

    def add_data(self, data, label='plot'):
        self.data[label] = {'x': data['time'], 'y': data['data']}

    def setup_plots(self, nrow, ncol, title=None, clickable=True):
        self.nrow = nrow
        self.ncol = ncol

        if title is not None:
            title_k = list(title.keys())

        self.pl = np.zeros((nrow, ncol), dtype=object)
        for i in range(nrow):
            for j in range(ncol):
                plot_title = "{}: {}".format(title_k[i], title[title_k[i]][j]) if title is not None else None
                self.pl[i, j] = self.gl.addPlot(title=plot_title, row=i, col=j, clickable=clickable)

    def plot(self, row_id, col_id, label=None, offset=(350, 30), **kwargs):
        self.pl[row_id, col_id].plot(**kwargs)

    def bar(self, row_id, col_id, label=None, offset=(350, 30), **kwargs):
        """
        Plotting the bar graphs onto Plot Items.
        """
        bar = BarGraph(label=label, **kwargs)
        self.pl[row_id, col_id].addItem(bar)

        bar.barClicked.connect(self.clickedBar)

    def imshow(self, row_id, col_id, im_data, label=None, set_pos=None, scale=None, set_levels=None,
               set_aspect_locked=False, invert_y=False, invert_x=False):

        self.lut = getLUT()
        img = pg.ImageItem()
        self.pl[row_id, col_id].addItem(img)

        # Update ImageView with new data.
        img_item = self.pl[row_id, col_id].items[-1]
        img_item.setImage(im_data, lut=self.lut)

        if set_pos is not None:
            img_item.setPos(*set_pos)

        if scale is not None:
            img_item.scale(*scale)

        if set_levels is not None:
            img_item.setLevels(set_levels)

        self.pl[row_id, col_id].setAspectLocked(set_aspect_locked)

        self.pl[row_id, col_id].invertY(invert_y)
        self.pl[row_id, col_id].invertX(invert_x)

    def clickedBar(self, message):

        tvec = self.data['plot']['x'][message._last_index]
        data = self.data['plot']['y'][message._last_index]

        dlg = QtWidgets.QDialog()
        dlg.setMinimumSize(800, 600)
        dlg.setLayout(QtWidgets.QVBoxLayout(dlg))
        glw = pg.GraphicsLayoutWidget(parent=dlg)
        dlg.layout().addWidget(glw)
        y_range = (np.min(data), np.max(data))
        x_range = (np.min(tvec), np.min(tvec) + 4)
        for ch in range(data.shape[0]):
            plt = glw.addPlot(row=ch, col=0)
            pen = QtGui.QColor(THEMES['dark']['pencolors'][ch])
            curve = plt.plot(x=tvec, y=data[ch, :], pen=pen)

            # curve = plt.plot(x=tvec, y= data[ch, :], name=self.data['labels'][ch], pen=pen)
            plt.setYRange(*y_range)
            plt.setXRange(*x_range)

        dlg.exec_()
