import sys
from qtpy import QtCore, QtWidgets
from neuroport_dbs.dbsgui.raster import RasterGUI


def main():
    _ = QtWidgets.QApplication(sys.argv)
    aw = RasterGUI()
    timer = QtCore.QTimer()
    timer.timeout.connect(aw.update)
    timer.start(1)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()


if __name__ == '__main__':
    main()
