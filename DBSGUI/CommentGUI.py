import os
import sys
from qtpy import QtCore, QtGui, QtWidgets
from qtpy import uic

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'dbsgui'))
import dbsgui
# Note: If import dbsgui fails, then set the working directory to be this script's directory.

ui_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'dbsgui', 'my_widgets', 'ui')
Ui_MainWindow, QtBaseClass = uic.loadUiType(os.path.join(ui_path, 'send_comments.ui'))


class MyGUI(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        # super(MyGUI, self).__init__()
        self.setupUi(self)

        # Connect signals & slots
        self.action_Connect.triggered.connect(self.on_connect)
        self.pushButton_Touch_Head.clicked.connect(lambda: self.on_button("Touch", "Head"))
        self.pushButton_Touch_Upper.clicked.connect(lambda: self.on_button("Touch", "Upper"))
        self.pushButton_Touch_Lower.clicked.connect(lambda: self.on_button("Touch", "Lower"))
        self.pushButton_Passive_Head.clicked.connect(lambda: self.on_button("Kinesthetic", "Head"))
        self.pushButton_Passive_Upper.clicked.connect(lambda: self.on_button("Kinesthetic", "Upper"))
        self.pushButton_Passive_Lower.clicked.connect(lambda: self.on_button("Kinesthetic", "Lower"))
        self.pushButton_Other_Head.clicked.connect(lambda: self.on_button("Other", "Head"))
        self.pushButton_Other_Upper.clicked.connect(lambda: self.on_button("Other", "Upper"))
        self.pushButton_Other_Lower.clicked.connect(lambda: self.on_button("Other", "Lower"))

    # No need to disconnect because the instance will do so automatically.
    # def __del__(self):
    #     from dbsgui.my_models.cbsdkConnection import CbSdkConnection
    #     CbSdkConnection().disconnect()

    def on_connect(self):
        from dbsgui.my_widgets.cbsdk_connect import ConnectDialog
        dlg = ConnectDialog()
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            dlg.do_connect()
        self.indicate_connection_state()

    def indicate_connection_state(self):
        from dbsgui.my_models.cbsdkConnection import CbSdkConnection
        msg_str = CbSdkConnection().get_connection_state()
        if msg_str == 'Connected to NSP':
            self.action_Connect.setEnabled(False)
        elif msg_str == 'Not connected':
            self.action_Connect.setEnabled(True)
        self.statusBar().showMessage(msg_str)

    def on_button(self, modality, region):
        import json
        from dbsgui.my_models.cbsdkConnection import CbSdkConnection
        if modality == 'Other':
            other_text = self.lineEdit_Other.text()
            if len(other_text) > 0:
                modality = other_text
        comment_dict = {
            'Side': 'L' if self.radioButton_L.isChecked() else 'R',
            'Region': region,
            'Modality': modality
        }
        conn = CbSdkConnection()
        if conn.is_connected:
            comment_string = json.dumps(comment_dict, sort_keys=True)
            conn.set_comments(comment_string)
            self.statusBar().showMessage("Sent: " + comment_string)


if __name__ == '__main__':
    import sys
    qapp = QtWidgets.QApplication(sys.argv)
    window = MyGUI()
    window.show()
    sys.exit(qapp.exec_())
