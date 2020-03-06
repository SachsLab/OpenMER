import os
import sys
import numpy as np
# use the same GUI format as the other ones
from qtpy.QtWidgets import QComboBox, QLineEdit, QLabel, QLCDNumber, QDialog, QPushButton, \
                           QGridLayout, QDialogButtonBox, QCalendarWidget, QDoubleSpinBox, \
                           QCheckBox, QHBoxLayout, QWidget, QVBoxLayout, QFrame, QMainWindow
from qtpy.QtGui import QFont

import pyqtgraph as pg


class TestGUI(QMainWindow):

    def __init__(self):
        super(TestGUI, self).__init__()

        self.setWindowTitle('Neuroport DBS - Electrodes Depth')
        self.widget = TestWidget()
        self.setCentralWidget(self.widget)

    # The custom GUI class has an update function, which calls the
    # do_plot_update function. This function then calls the update
    # function of all display widgets.
    def do_plot_update(self):
        self.widget.new_depth()


class TestWidget(QWidget):
    def __init__(self):
        super(TestWidget, self).__init__()
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        depth_widget = pg.GraphicsLayoutWidget(parent=self)
        self.layout.addWidget(depth_widget, 0, 0, 8, 1)

        self.depth_plot = depth_widget.addPlot()
        self.depth_plot.plot(np.zeros(100), np.arange(-20, 5, .25))
        self.depth_plot.plot([-5, 5], [0, 0], pen='y')
        self.depth_bar = self.depth_plot.plot([-2.5, 2.5], [-20, -20], fillLevel=-20, brush=(255, 255, 255, 100))
        self.depth_plot.invertY()
        self.depth_plot.setMouseEnabled(x=False, y=False)
        self.depth_plot.setYRange(-20, 5, padding=0)
        self.depth_plot.setXRange(-5, 5, padding=0)
        self.depth_plot.getAxis('bottom').setStyle(tickLength=0, showValues=False)
        self.depth_plot.getAxis('bottom').setPen((255, 255, 255, 255))
        font = QFont()
        font.setPixelSize(20)
        font.setBold(True)
        self.depth_plot.getAxis('left').tickFont = font
        self.depth_plot.getAxis('left').setPen((255, 255, 255, 255))
        self.depth_plot.getAxis('left').setStyle(tickLength=0)

        self.data_layout = QVBoxLayout()
        self.layout.addLayout(self.data_layout, 0, 1, 8, 5)
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 5)
        self.depth = -20

        self.data_plots = []
        self.depth_data = {}

        for i in range(8):
            tmp = pg.GraphicsLayoutWidget()
            self.data_layout.addWidget(tmp)
            tmp = tmp.addPlot()
            tmp.hideAxis('bottom')
            tmp.hideAxis('left')
            tmp.setMouseEnabled(x=False, y=False)
            self.data_plots.append(tmp.plot())

    def new_depth(self):
        if self.depth < 5:
            new_depth = self.depth + 2*np.random.rand()
            data = np.ones((int(abs(new_depth))))

            self.depth_data[new_depth] = data

            # plot depth
            self.depth_plot.plot([0], [new_depth], symbol='o')

            # plot data
            all_depths = [x for x in self.depth_data.keys()]

            idx = 1
            while idx <= min(len(all_depths), 8):
                self.data_plots[-idx].setData(y=self.depth_data[all_depths[-idx]])
                idx += 1

            if len(all_depths) >= 8:
                fill_bar = all_depths[-8]
            else:
                fill_bar = -20
            self.depth_bar.setData(x=[-2.5, 2.5], y=[new_depth, new_depth], fillLevel=fill_bar)

            # assign depth
            self.depth = new_depth


if __name__ == '__main__':
    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import QTimer

    qapp = QApplication(sys.argv)
    window = TestGUI()
    window.show()
    timer = QTimer()
    timer.timeout.connect(window.do_plot_update)
    timer.start(5000)

    if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()
