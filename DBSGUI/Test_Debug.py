import os
import sys

# use the same GUI format as the other ones
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QComboBox, QLineEdit, QHBoxLayout, QLabel, QLCDNumber, QDialog, QVBoxLayout, QPushButton, \
                           QGridLayout, QDialogButtonBox, QCalendarWidget
from qtpy.QtCore import Qt


class AddSubjectDialog(QDialog):
    """
    A modal dialog window with widgets to create a new subject entry in the DB.
    Will return the subject ID.
    """

    def __init__(self, parent=None):
        super(AddSubjectDialog, self).__init__(parent)
        self.setWindowTitle("Enter subject information.")

        # Widgets to show/edit connection parameters.
        self.subject_layout = QGridLayout(self)

        self.subject_layout.addWidget(QLabel("Name: "), 1, 0, 1, 1)
        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(135)
        self.subject_layout.addWidget(self.name_edit, 1, 1, 1, 1)

        self.subject_layout.addWidget(QLabel("ID: "), 2, 0, 1, 1)
        self.id_edit = QLineEdit()
        self.id_edit.setMaxLength(135)
        self.subject_layout.addWidget(self.id_edit, 2, 1, 1, 1)

        self.subject_layout.addWidget(QLabel("Sex: "), 3, 0, 1, 1)
        self.sex_combo = QComboBox()
        self.sex_combo.addItems(['unspecified', 'male', 'female', 'unknown'])
        self.sex_combo.setCurrentIndex(0)
        self.subject_layout.addWidget(self.sex_combo, 3, 1, 1, 1)

        self.subject_layout.addWidget(QLabel("Handedness: "), 4, 0, 1, 1)
        self.hand_combo = QComboBox()
        self.hand_combo.addItems(['unknown', 'right', 'left', 'equal'])
        self.hand_combo.setCurrentIndex(0)
        self.subject_layout.addWidget(self.hand_combo, 4, 1, 1, 1)

        self.subject_layout.addWidget((QLabel("Date of birth: ")), 5, 0, 1, 1)
        self.dob_calendar = QCalendarWidget()
        self.subject_layout.addWidget(self.dob_calendar, 5, 1, 1, 1)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.subject_layout.addWidget(buttons, 7, 0, 1, 2, alignment=Qt.AlignHCenter)

    @staticmethod
    def do_add_subject_dialog(parent=None):
        dialog = AddSubjectDialog(parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            # convert all fields to dictionary and return it
            out_dict = {
                'name': dialog.name_edit.text(),
                'id': dialog.id_edit.text(),
                'sex': dialog.sex_combo.currentText(),
                'handedness': dialog.hand_combo.currentText()
            }
            return out_dict
        return -1, False


if __name__ == '__main__':
    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import QTimer

    qapp = QApplication(sys.argv)
    subname = AddSubjectDialog.do_add_subject_dialog()
    print(subname)