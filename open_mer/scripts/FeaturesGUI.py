import sys
import argparse
from qtpy import QtCore, QtWidgets
from open_mer.dbsgui.features import FeaturesGUI


def main(**kwargs):
    app = QtWidgets.QApplication(sys.argv)
    window = FeaturesGUI(**kwargs)
    window.show()
    timer = QtCore.QTimer()
    timer.timeout.connect(window.update)
    timer.start(100)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        sys.exit(app.exec_())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="FeaturesGUI",
                                     description="Visualize MER trajectory segments and features.")
    parser.add_argument('-i', '--ini_file', nargs='?', help="Path to ini settings file.")
    args = parser.parse_args()
    main(**args.__dict__)
