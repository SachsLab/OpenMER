import os
import sys
import qtpy.QtCore as QtCore
import qtpy.QtWidgets as QtWidgets
import numpy as np
import pyqtgraph as pg


DEFAULT_ROOT_DIR = os.path.abspath(os.path.join(os.getcwd(), '..', '..', '..', '..', 'DBSData'))
DEFAULT_SEG_INTERVAL = [0.5, 4.5]
hp_cutoff = 250
beta_cutoff = np.asarray([16, 30])
rms_thresh = 4.0
dec_factor = 10

record_number = '001'
data_folder = '20170419-153633'


class DBSPlotGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super(DBSPlotGUI, self).__init__()
        self.setup_ui()
        self.show()

    def setup_ui(self):
        self.setCentralWidget(QtWidgets.QWidget(self))
        layout = QtWidgets.QVBoxLayout()
        self.centralWidget().setLayout(layout)

        # Text box for data root dir and [...] push button QFileDialog QFileDialog.Directory
        folder_layout = QtWidgets.QHBoxLayout()
        root_label = QtWidgets.QLabel("Root folder:")
        folder_layout.addWidget(root_label)
        self.root_lineedit = QtWidgets.QLineEdit()
        self.root_lineedit.setText(DEFAULT_ROOT_DIR)
        folder_layout.addWidget(self.root_lineedit)
        root_pb = QtWidgets.QPushButton("...")
        root_pb.clicked.connect(self.get_root)
        folder_layout.addWidget(root_pb)
        layout.addLayout(folder_layout)

        # Combo box for date dir, defaults to most recent
        # And multi-select for recording number, defaults to most recent
        # And pushbutton for analysis.
        data_layout = QtWidgets.QHBoxLayout()
        self.traj_listwidget = QtWidgets.QListWidget()
        self.traj_listwidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.sub_combobox = QtWidgets.QComboBox()
        self.sub_combobox.currentIndexChanged.connect(self.sub_combo_changed)
        self.populate_sub_combobox()
        data_layout.addWidget(self.sub_combobox)

        #self.populate_traj_listwidget()
        data_layout.addWidget(self.traj_listwidget)
        go_pushbutton = QtWidgets.QPushButton("Go!")
        go_pushbutton.clicked.connect(self.analyze)
        data_layout.addWidget(go_pushbutton)
        layout.addLayout(data_layout)

        # TODO: Add pyqtgraph plot items to layout.
        glw = pg.GraphicsLayoutWidget(parent=self)
        layout.addWidget(glw)

        self.resize(1000, 800)

    def get_root(self):
        root_dir = QtWidgets.QFileDialog.getExistingDirectory(caption="Choose data parent directory.",
                                                              directory=self.root_lineedit.text())
        if root_dir:
            self.root_lineedit.setText(root_dir)
        self.populate_sub_combobox()

    def populate_sub_combobox(self):
        self.sub_combobox.clear()
        dirs = next(os.walk(self.root_lineedit.text()))[1]
        self.sub_combobox.addItems(dirs)
        # TODO: Set index to most recent.

    def sub_combo_changed(self):
        self.populate_traj_listwidget()

    def populate_traj_listwidget(self):
        self.traj_listwidget.clear()
        curr_sess = self.sub_combobox.currentText()
        subdir = os.path.join(self.root_lineedit.text(), curr_sess)
        contents = os.listdir(subdir)
        for c in contents:
            if c[-4:] == '.nev':
                traj_str = c[len(curr_sess)+1:-4]
                self.traj_listwidget.addItem(traj_str)
        self.traj_listwidget.setCurrentRow(self.traj_listwidget.count() - 1)
        self.traj_listwidget.setFixedSize(
            self.traj_listwidget.sizeHintForColumn(0) + 2 * self.traj_listwidget.frameWidth(),
            self.traj_listwidget.sizeHintForRow(
                0) * self.traj_listwidget.count() + 2 * self.traj_listwidget.frameWidth())

    def analyze(self):
        curr_sess = self.sub_combobox.currentText()
        datadir = os.path.join(self.root_lineedit.text(), curr_sess)
        traj_list = self.traj_listwidget.selectedItems()
        for traj in traj_list:
            base_fn = os.path.join(datadir, curr_sess + '-' + traj.text())
            print('TODO: Analyze ' + base_fn)


if __name__ == '__main__':
    qapp = QtWidgets.QApplication(sys.argv)
    mainwindow = DBSPlotGUI()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()