import sys
import qtpy
from neuroport_dbs.dbsgui.sweep import SweepGUI


def main():
    from qtpy import QtWidgets, QtCore
    _ = QtWidgets.QApplication(sys.argv)
    aw = SweepGUI()
    timer = QtCore.QTimer()
    timer.timeout.connect(aw.update)
    timer.start(1)

    if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()


if __name__ == '__main__':
    main()
