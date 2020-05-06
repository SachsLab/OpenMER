from qtpy.QtWidgets import QProgressDialog
from qtpy.QtCore import Qt
import sys
import time


class TestQProgressBar():
    def __init__(self):
        bar = QProgressDialog('Processing', 'stop', 0, 1000, None)
        bar.setWindowModality(Qt.WindowModal)
        bar.show()

        for x in range(0, 1000):
            bar.setValue(x)
            bar.setLabelText(str(x))
            # bar.update()
            time.sleep(0.01)



if __name__ == '__main__':
    from qtpy.QtWidgets import QApplication

    qapp = QApplication(sys.argv)
    # select file
    # fname = 'D:\\SachsLab\\NeuroPort_Dev\\Data\STN\\20200116-132739\\20200116-132739-001'
    fname = 'D:\\SachsLab\\NeuroPort_Dev\\Data\\STN\\20200114-132104\\20200114-132104-001'
    pb = TestQProgressBar()
