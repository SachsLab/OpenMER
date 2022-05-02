import sys
import argparse
from qtpy import QtCore, QtWidgets
from neuroport_dbs.dbsgui.process import ProcessGUI


def main(**kwargs):
    app = QtWidgets.QApplication(sys.argv)
    window = ProcessGUI(**kwargs)
    window.show()
    timer = QtCore.QTimer()
    timer.timeout.connect(window.update)
    timer.start(100)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        sys.exit(app.exec_())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="ProcessGUI",
                                     description="Manage subprocesses to store segments and compute features.")
    parser.add_argument('-i', '--ini_file', nargs='?', help="Path to ini settings file.")
    args = parser.parse_args()
    main(**args.__dict__)
