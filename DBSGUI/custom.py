import time
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QSpinBox, QDialogButtonBox, QDialog, QWidget
from PyQt5.QtCore import Qt, pyqtSignal
from cbsdkConnection import CbSdkConnection


SAMPLINGGROUPS = ["0", "500", "1000", "2000", "10000", "30000", "RAW"]
THEMES = {
    'dark': {
        'pencolors': ["cyan", QColor(0, 255, 0), "red", "magenta", "yellow", "white"],
        'bgcolor': Qt.black,
        'labelcolor': Qt.gray,
        'axiscolor': Qt.gray,
        'axiswidth': 1
    }
}

def get_now_time():
    # Attempt to synchronize different series using machine time.
    cbsdk_conn = CbSdkConnection()
    if cbsdk_conn.is_connected:
        now = cbsdk_conn.time()
    else:
        now = time.time()
    return now


class ConnectDialog(QDialog):
    """
    A modal dialog window with widgets for modifying connection parameters.
    Changes + OK will change the parameters in the CbSdkConnection singleton,
    but will not actually connect.
    """

    def __init__(self, parent=None):
        super(ConnectDialog, self).__init__(parent)
        # Get access to the CbSdkConnection instance, but don't connect yet.
        self.cbsdkConn = CbSdkConnection()

        # Widgets to show/edit connection parameters.
        layout = QVBoxLayout(self)

        # client-addr ip
        client_addr_layout = QHBoxLayout()
        client_addr_layout.addWidget(QLabel("client-addr"))
        self.clientIpEdit = QLineEdit(self.cbsdkConn.con_params['client-addr'])
        self.clientIpEdit.setInputMask("000.000.000.000;_")
        client_addr_layout.addWidget(self.clientIpEdit)
        layout.addLayout(client_addr_layout)

        # client-port int
        client_port_layout = QHBoxLayout()
        client_port_layout.addWidget(QLabel("client-port"))
        self.clientPortSpin = QSpinBox()
        self.clientPortSpin.setMinimum(0)
        self.clientPortSpin.setMaximum(99999)
        self.clientPortSpin.setSingleStep(1)
        self.clientPortSpin.setValue(self.cbsdkConn.con_params['client-port'])
        client_port_layout.addWidget(self.clientPortSpin)
        layout.addLayout(client_port_layout)

        # inst-addr ip
        inst_addr_layout = QHBoxLayout()
        inst_addr_layout.addWidget(QLabel("inst-addr"))
        self.instIpEdit = QLineEdit(self.cbsdkConn.con_params['inst-addr'])
        self.instIpEdit.setInputMask("000.000.000.000;_")
        inst_addr_layout.addWidget(self.instIpEdit)
        layout.addLayout(inst_addr_layout)

        # inst-port int
        inst_port_layout = QHBoxLayout()
        inst_port_layout.addWidget(QLabel("inst-port"))
        self.instPortSpin = QSpinBox()
        self.instPortSpin.setMinimum(0)
        self.instPortSpin.setMaximum(99999)
        self.instPortSpin.setSingleStep(1)
        self.instPortSpin.setValue(self.cbsdkConn.con_params['inst-port'])
        inst_port_layout.addWidget(self.instPortSpin)
        layout.addLayout(inst_port_layout)

        # receive-buffer-size int
        rec_buff_layout = QHBoxLayout()
        rec_buff_layout.addWidget(QLabel("receive-buffer-size"))
        self.recBuffSpin = QSpinBox()
        self.recBuffSpin.setMinimum(6 * 1024 * 1024)
        self.recBuffSpin.setMaximum(8 * 1024 * 1024)
        self.recBuffSpin.setSingleStep(1024 * 1024)
        self.recBuffSpin.setValue(self.cbsdkConn.con_params['receive-buffer-size'])
        rec_buff_layout.addWidget(self.recBuffSpin)
        layout.addLayout(rec_buff_layout)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def do_connect_dialog(parent=None):
        dialog = ConnectDialog(parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            dialog.cbsdkConn.disconnect()
            # Collect values from widgets and set them on dialog.cbsdkConn
            new_params = {
                'client-addr': dialog.clientIpEdit.text(),
                'client-port': dialog.clientPortSpin.value(),
                'inst-addr': dialog.instIpEdit.text(),
                'inst-port': dialog.instPortSpin.value(),
                'receive-buffer-size': dialog.recBuffSpin.value()
            }
            dialog.cbsdkConn.con_params = new_params
            return dialog.cbsdkConn.connect()
        return -1


class CustomWidget(QWidget):
    """
    A simple skeleton widget.
    It is only useful if sub-classed.
    """
    was_closed = pyqtSignal()

    def __init__(self, group_info, group_ix=0, **kwargs):
        super(CustomWidget, self).__init__(**kwargs)
        self.group_info = group_info
        self.awaiting_close = False

        # Get sampling rate from group_ix
        if (SAMPLINGGROUPS[group_ix] == "0") or (SAMPLINGGROUPS[group_ix] == "RAW"):
            group_ix = 5
        self.samplingRate = int(SAMPLINGGROUPS[group_ix])

        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(0)
        self.setLayout(chart_layout)

        self.labels = {}

        self.resize(600, 800)
        self.show()

    def closeEvent(self, evnt):
        super(CustomWidget, self).closeEvent(evnt)
        self.awaiting_close = True
        self.was_closed.emit()