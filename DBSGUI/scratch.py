# Just some chunks of code to help with development.
import sys
import PyQt5
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import numpy as np
import pyqtgraph as pg


class MyGUI(QMainWindow):
    """
    This application is for monitoring activity from the Blackrock NSP.

    """

    def __init__(self):
        super(MyGUI, self).__init__()
        self.setup_ui()
        self.show()

    def __del__(self):
        pass

    def setup_ui(self):
        self.resize(1000, 800)
        self.setWindowTitle('Test')
        self.setCentralWidget(QWidget(self))  # This squeezes out docks.
        self.centralWidget().setLayout(QVBoxLayout())

        glw = pg.GraphicsLayoutWidget()
        glw.useOpenGL(True)
        self.centralWidget().layout().addWidget(glw)

        vtick = QPainterPath()
        vtick.moveTo(0, -0.5)
        vtick.lineTo(0, 0.5)

        p1 = glw.addPlot(row=0, col=0)
        p1.setXRange(-0.05, 1.05)
        p1.hideAxis('bottom')

        s1 = pg.ScatterPlotItem(pxMode=False)
        s1.setSymbol(vtick)
        s1.setSize(1)
        s1.setPen(QColor(*np.random.randint(0, 255 + 1, 3).tolist()))
        p1.addItem(s1)

        s2 = pg.ScatterPlotItem(pxMode=False, symbol=vtick, size=1,
                                pen=QColor(*np.random.randint(0, 255 + 1, 3).tolist()))
        p1.addItem(s2)

        p2 = glw.addPlot(row=1, col=0)

        self.spis = [s1, s2]

    def update(self):
        super(MyGUI, self).update()
        for spi_ix in range(len(self.spis)):
            self.spis[spi_ix].setData(np.random.rand(10), spi_ix + 0.5 + np.zeros((10,)))


if __name__ == '__main__':
    qapp = QApplication(sys.argv)
    aw = MyGUI()
    timer = QTimer()
    timer.timeout.connect(aw.update)
    timer.start(1)

    if (sys.flags.interactive != 1) or not hasattr(PyQt5.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()