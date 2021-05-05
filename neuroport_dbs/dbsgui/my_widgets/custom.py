import time
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QMainWindow, QAction, QToolBar, QPushButton, qApp
from qtpy.QtWidgets import QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QSpinBox, QDialogButtonBox, QDialog, QWidget
from qtpy.QtCore import Qt, Signal
from cerebuswrapper import CbSdkConnection

# Import settings
from neuroport_dbs.settings.defaults import SAMPLINGGROUPS, THEMES, SIMOK


def get_now_time():
    # Attempt to synchronize different series using machine time.
    cbsdk_conn = CbSdkConnection()
    if cbsdk_conn.is_connected:
        now = cbsdk_conn.time()
    else:
        now = time.time()
    return now


class CustomGUI(QMainWindow):
    """
    This application is for monitoring activity from the Blackrock NSP.
    """

    def __init__(self):
        super(CustomGUI, self).__init__()
        self.cbsdk_conn = CbSdkConnection(simulate_ok=SIMOK)
        self.setup_ui()
        self.indicate_connection_state()
        self.plot_widget = None
        self.show()

    def __del__(self):
        # CbSdkConnection().disconnect() No need to disconnect because the instance will do so automatically.
        pass

    def setup_ui(self):
        # self.setCentralWidget(QWidget(self))
        # self.centralWidget().setLayout(QVBoxLayout())
        self.create_actions()
        self.create_menus()
        self.create_toolbars()
        self.resize(250, 150)

    def create_actions(self):
        # Actions
        self.actions = {
            'Connect': QAction("Connect", self),
            'Quit': QAction("Quit", self),
            'AddPlot': QAction("Add Plot", self)
        }
        self.actions['Connect'].triggered.connect(self.on_action_connect_triggered)
        self.actions['Quit'].triggered.connect(qApp.quit)
        self.actions['AddPlot'].triggered.connect(self.on_action_add_plot_triggered)
        # TODO: Icons, tooltips, shortcuts, etc.
        # TODO: QActionGroup if many actions need to be grouped.

    def create_menus(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('&File')
        for action_key in self.actions:
            file_menu.addAction(self.actions[action_key])

    def create_toolbars(self):
        for k, v in self.actions.items():
            toolbar_item = QToolBar(k)
            toolbar_item.addAction(v)
            self.addToolBar(Qt.LeftToolBarArea, toolbar_item)

    def indicate_connection_state(self):
        if self.cbsdk_conn.is_connected:
            msg_str = 'Connected to NSP'
            # TODO: Disable connect menu/toolbar
        elif self.cbsdk_conn.is_simulating:
            msg_str = 'Connected to NSP simulator'
        else:
            msg_str = 'Not connected'
            # TODO: Enable connect menu/toolbar
        self.statusBar().showMessage(msg_str)

    def on_action_connect_triggered(self):
        result = ConnectDialog.do_connect_dialog()
        if result == -1:
            print("Connection canceled.")
        self.indicate_connection_state()

    def on_action_add_plot_triggered(self):
        # abc.abstractmethod not possible because ABC does not work with Qt-derived classes, so raise error instead.
        raise TypeError("This method must be overridden by sub-class.")

    def update(self):
        super(CustomGUI, self).update()

        if self.cbsdk_conn.is_connected or self.cbsdk_conn.is_simulating:
            if self.plot_widget:
                self.do_plot_update()

    def do_plot_update(self):
        # abc.abstractmethod not possible because ABC does not work with Qt-derived classes, so raise error instead.
        raise TypeError("This method must be overridden by sub-class.")


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
    was_closed = Signal()

    def __init__(self, group_info, group_ix=0, **kwargs):
        super(CustomWidget, self).__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Init member variables
        self.group_info = group_info
        self.awaiting_close = False
        self.labels = {}

        # Get sampling rate from group_ix
        if (SAMPLINGGROUPS[group_ix] == "0") or (SAMPLINGGROUPS[group_ix] == "RAW"):
            group_ix = 5
        self.samplingRate = int(SAMPLINGGROUPS[group_ix])

        # Create UI elements
        plot_layout = QVBoxLayout()
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(0)
        self.setLayout(plot_layout)
        self.create_control_panel()
        self.create_plots(**kwargs)
        self.refresh_axes()
        self.show()

    def create_control_panel(self):
        cntrl_layout = QHBoxLayout()
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear)
        clear_button.setMaximumWidth(200)
        cntrl_layout.addWidget(clear_button)
        self.layout().addLayout(cntrl_layout)

    def create_plots(self, theme='dark', **kwargs):
        raise TypeError("Must be implemented by sub-class.")

    def refresh_axes(self):
        raise TypeError("Must be implemented by sub-class.")

    def clear(self):
        raise TypeError("Must be implemented by sub-class.")

    def closeEvent(self, evnt):
        super(CustomWidget, self).closeEvent(evnt)
        self.awaiting_close = True
        self.was_closed.emit()
