import numpy as np
# use the same GUI format as the other ones
from qtpy.QtWidgets import QComboBox, QLineEdit, QLabel, QDialog, QVBoxLayout, QWidget, \
                           QGridLayout, QDialogButtonBox, QCalendarWidget, \
                           QCheckBox, QTabWidget, QTextEdit
from qtpy.QtCore import QDate, QRegularExpression, Qt, Signal
from qtpy.QtGui import QRegularExpressionValidator
from serf.tools.db_wrap import DBWrapper


class SubjectWidget(QWidget):
    subject_change = Signal(int)

    def __init__(self, subject_settings, parent=None):
        super().__init__(parent=parent)

        self._setup_ui()

        # Subject Settings
        self.subject_settings = subject_settings
        if not self.subject_settings:
            self.update_settings_from_db(-1)

        self.update_subj_widgets_from_settings()

    def _setup_ui(self):
        subject_layout = QGridLayout(self)
        subject_layout.setColumnMinimumWidth(2, 60)

        subject_layout.addWidget(QLabel("Id: "), 0, 0, 1, 1)
        self.id_combo = QComboBox()
        self.id_combo.setEditable(True)
        self.id_combo.addItem("")
        self.id_combo.addItems(DBWrapper().list_all_subjects())
        self.id_combo.currentIndexChanged.connect(self.load_subject)  # Which transitively calls check_subject
        self.id_combo.lineEdit().editingFinished.connect(self.check_subject)
        subject_layout.addWidget(self.id_combo, 0, 1, 1, 4)

        subject_layout.addWidget(QLabel("Name: "), 1, 0, 1, 1)
        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(135)
        subject_layout.addWidget(self.name_edit, 1, 1, 1, 4)

        _subj_enums = DBWrapper().return_enums("subject")
        subject_layout.addWidget(QLabel("Sex: "), 2, 0, 1, 1)
        self.sex_combo = QComboBox()
        self.sex_combo.addItems(_subj_enums["sex"] if "sex" in _subj_enums.keys() else [])
        self.sex_combo.setCurrentIndex(0)
        subject_layout.addWidget(self.sex_combo, 2, 1, 1, 1)

        subject_layout.addWidget((QLabel("Date of birth: ")), 3, 0, 1, 1)
        self.dob_calendar = QCalendarWidget()
        subject_layout.addWidget(self.dob_calendar, 3, 1, 1, 3)

        subject_layout.addWidget(QLabel("NSP file comment: "), 4, 0, 1, 1)
        self.file_comment = QTextEdit("")
        self.file_comment.setMaximumHeight(150)
        subject_layout.addWidget(self.file_comment, 4, 1, 1, 4)

    def update_subj_widgets_from_settings(self):
        self.name_edit.setText(self.subject_settings.get("name", ""))
        self.id_combo.setCurrentText(self.subject_settings.get("id", ""))
        self.sex_combo.setCurrentText(self.subject_settings.get("sex", ""))
        dob = self.subject_settings.get("birthday", "")
        if dob not in [None, ""]:
            q_dob = QDate.fromString(dob.isoformat() if hasattr(dob, "year") else dob, "yyyy-MM-d")
            self.dob_calendar.setSelectedDate(q_dob)
        else:
            self.dob_calendar.setSelectedDate(QDate.currentDate())

    def update_settings_from_db(self, idx):
        for key, value in DBWrapper().load_subject_details(idx).items():
            self.subject_settings[key] = value

    def load_subject(self):
        # id is a unique and mandatory field
        self.check_subject()
        self.update_subj_widgets_from_settings()

    def check_subject(self):
        # when changing the id in the combobox, can be modifying or entering an existing subject id. Check to load data
        # if so.
        curr_id = self.id_combo.currentText()
        if curr_id != "":
            self.update_settings_from_db(curr_id)
            self.subject_change.emit(self.subject_settings["subject_id"])
        else:
            self.update_settings_from_db(-1)
            self.subject_change.emit(-1)

    def to_dict(self):
        self.subject_settings["id"] = self.id_combo.currentText()
        self.subject_settings["name"] = self.name_edit.text()
        self.subject_settings["sex"] = self.sex_combo.currentText()
        self.subject_settings["birthday"] = self.dob_calendar.selectedDate().toPython()
        self.subject_settings["NSP_comment"] = self.file_comment.toPlainText()


class ProcedureWidget(QWidget):
    def __init__(self, procedure_settings):
        super(ProcedureWidget, self).__init__()

        # Settings
        self.procedure_settings = procedure_settings

        # populate with defaults if empty
        if not self.procedure_settings:
            self.update_settings_from_db(-1)

        self.proc_enums = DBWrapper().return_enums("procedure")
        proc_layout = QGridLayout(self)

        row = 0
        proc_layout.addWidget(QLabel("Previous procedures: "), row, 0, 1, 1)
        self.prev_proc = QComboBox()
        self.prev_proc.setEnabled(True)
        self.check_all_procedures(None, False)
        self.prev_proc.currentIndexChanged.connect(self.procedure_selection_change)
        proc_layout.addWidget(self.prev_proc, row, 1, 1, 3)

        row += 1
        proc_layout.addWidget(QLabel("Target name: "), row, 0, 1, 1)
        self.target_name = QLineEdit("")
        proc_layout.addWidget(self.target_name, row, 1, 1, 3)

        row += 1
        proc_layout.addWidget(QLabel("Type: "), row, 0, 1, 1)
        self.type_combo = self.combo_from_enum('type')
        proc_layout.addWidget(self.type_combo, row, 1, 1, 3)

        row += 1
        proc_layout.addWidget(QLabel("Recording configuration: "), row, 0, 1, 1)
        self.rec_combo = self.combo_from_enum('recording_config')
        proc_layout.addWidget(self.rec_combo, row, 1, 1, 3)

        row += 1
        proc_layout.addWidget(QLabel("Electrode configuration: "), row, 0, 1, 1)
        self.electrode_combo = self.combo_from_enum('electrode_config')
        proc_layout.addWidget(self.electrode_combo, row, 1, 1, 3)

        row += 1
        proc_layout.addWidget(QLabel("Distance to target: "), row, 0, 1, 1)
        self.dist_to_target = self.coord_line_edit()
        proc_layout.addWidget(self.dist_to_target, row, 1, 1, 1)

        row += 1
        proc_layout.addWidget(QLabel("Entry (x, y, z): "), row, 0, 1, 1)
        self.entry_x = self.coord_line_edit()
        proc_layout.addWidget(self.entry_x, row, 1, 1, 1)
        self.entry_y = self.coord_line_edit()
        proc_layout.addWidget(self.entry_y, row, 2, 1, 1)
        self.entry_z = self.coord_line_edit()
        proc_layout.addWidget(self.entry_z, row, 3, 1, 1)

        row += 1
        proc_layout.addWidget(QLabel("Target (x, y, z): "), row, 0, 1, 1)
        self.target_x = self.coord_line_edit()
        proc_layout.addWidget(self.target_x, row, 1, 1, 1)
        self.target_y = self.coord_line_edit()
        proc_layout.addWidget(self.target_y, row, 2, 1, 1)
        self.target_z = self.coord_line_edit()
        proc_layout.addWidget(self.target_z, row, 3, 1, 1)

        row += 1
        self.comp_dist_to_target = QLabel("Computed distance: 0.000 mm; Difference: 0.000 mm")
        proc_layout.addWidget(self.comp_dist_to_target, row, 0, 1, 2)

        row += 1
        proc_layout.addWidget(QLabel("A (x, y, z): "), row, 0, 1, 1)
        self.a_x = self.coord_line_edit()
        proc_layout.addWidget(self.a_x, row, 1, 1, 1)
        self.a_y = self.coord_line_edit()
        proc_layout.addWidget(self.a_y, row, 2, 1, 1)
        self.a_z = self.coord_line_edit()
        proc_layout.addWidget(self.a_z, row, 3, 1, 1)

        row += 1
        proc_layout.addWidget(QLabel("E (x, y, z): "), row, 0, 1, 1)
        self.e_x = self.coord_line_edit()
        proc_layout.addWidget(self.e_x, row, 1, 1, 1)
        self.e_y = self.coord_line_edit()
        proc_layout.addWidget(self.e_y, row, 2, 1, 1)
        self.e_z = self.coord_line_edit()
        proc_layout.addWidget(self.e_z, row, 3, 1, 1)

        row += 1
        proc_layout.addWidget(QLabel("Offset direction: "), row, 0, 1, 1)
        self.offset_direction_combo = self.combo_from_enum('offset_direction')
        proc_layout.addWidget(self.offset_direction_combo, row, 1, 1, 3)

        row += 1
        proc_layout.addWidget(QLabel("Offset size: "), row, 0, 1, 1)
        self.offset_size = self.coord_line_edit()
        proc_layout.addWidget(self.offset_size, row, 1, 1, 1)

        row += 1
        proc_layout.addWidget(QLabel("Medication status: "), row, 0, 1, 1)
        self.medic_combo = self.combo_from_enum('medication_status')
        proc_layout.addWidget(self.medic_combo, row, 1, 1, 3)

        row += 1
        proc_layout.addWidget(QWidget(), row, 1, 1, 3)

        self.update_proc_widgets_from_settings()

    def check_all_procedures(self, subject_id, block):
        self.prev_proc.blockSignals(block)
        self.all_procedures = DBWrapper().list_all_procedures(subject_id)
        self.prev_proc.clear()
        self.prev_proc.addItem('')
        self.prev_proc.addItems(
            [' '.join([x.target_name, x.recording_config, x.date.strftime('%Y-%m-%d')]) for x in self.all_procedures])
        self.prev_proc.setCurrentIndex(0)
        self.prev_proc.blockSignals(False)

    def combo_from_enum(self, enum_name):
        combo = QComboBox()
        combo.addItems(self.proc_enums[enum_name] if enum_name in self.proc_enums.keys() else [])
        combo.setCurrentText('none')
        return combo

    def coord_line_edit(self):
        template = QRegularExpression(r"[-]?\d*\.?\d{0,3}")
        validator = QRegularExpressionValidator(template)

        line = QLineEdit("0.0")
        line.setValidator(validator)
        line.setFixedWidth(60)
        # line.editingFinished.connect(self.update_dist_to_target)
        line.textChanged.connect(self.update_dist_to_target)

        return line

    def update_dist_to_target(self, new_string):
        if new_string not in ["-", ".", "", "-."]:
            ddt = np.sqrt((float(self.target_x.text()) - float(self.entry_x.text()))**2 +
                          (float(self.target_y.text()) - float(self.entry_y.text()))**2 +
                          (float(self.target_z.text()) - float(self.entry_z.text()))**2)
            diff = float(self.dist_to_target.text()) - ddt
            self.comp_dist_to_target.setText(
                "Computed distance: {:.3f} mm; Difference: {:.3f} mm".format(ddt, diff))

    def change_subject(self, sub_id, block=False):
        self.check_all_procedures(sub_id, block)

    def procedure_selection_change(self):
        id = -1
        if self.prev_proc.currentIndex() > 0:
            ix = self.prev_proc.currentIndex() - 1  # -1 because first entry is always blank.
            id = self.all_procedures[ix].procedure_id
        self.update_settings_from_db(id)
        self.update_proc_widgets_from_settings()

    def update_settings_from_db(self, idx):
        res_dict = dict({"procedure_id": idx}, **DBWrapper().load_procedure_details(idx, exclude=['subject', 'procedure_id']))
        self.procedure_settings.update(res_dict)

    def update_proc_widgets_from_settings(self):
        self.target_name.setText(self.procedure_settings.get("target_name", ""))
        self.type_combo.setCurrentText(self.procedure_settings.get("type", ""))
        self.rec_combo.setCurrentText(self.procedure_settings.get("recording_config", ""))
        self.electrode_combo.setCurrentText(self.procedure_settings.get("electrode_config", ""))
        self.medic_combo.setCurrentText(self.procedure_settings.get("medication_status", ""))
        self.offset_size.setText(str(self.procedure_settings.get("offset_size", None)))
        self.offset_direction_combo.setCurrentText(self.procedure_settings.get("offset_direction", ""))
        entry = self.procedure_settings.get("entry", None)
        if entry is None:
            entry = [0., 0., 0.]
        self.entry_x.setText(str(entry[0]))
        self.entry_y.setText(str(entry[1]))
        self.entry_z.setText(str(entry[2]))
        target = self.procedure_settings.get("target", None)
        if target is None:
            target = [0., 0., 0.]
        self.target_x.setText(str(target[0]))
        self.target_y.setText(str(target[1]))
        self.target_z.setText(str(target[2]))
        ddt = self.procedure_settings.get("distance_to_target", None)
        if ddt is None:
            ddt = 0.000
        self.dist_to_target.setText(str(ddt))
        # self.update_dist_to_target()
        a = self.procedure_settings.get("a", None)
        if a is None:
            a = [0., 0., 0.]
        self.a_x.setText(str(a[0]))
        self.a_y.setText(str(a[1]))
        self.a_z.setText(str(a[2]))
        e = self.procedure_settings.get("e", None)
        if e is None:
            e = [0., 0., 0.]
        self.e_x.setText(str(e[0]))
        self.e_y.setText(str(e[1]))
        self.e_z.setText(str(e[2]))

    def to_dict(self):
        self.procedure_settings["type"] = self.type_combo.currentText()
        self.procedure_settings["a"] = np.array([float(self.a_x.text()),
                                                 float(self.a_y.text()),
                                                 float(self.a_z.text())], dtype=float)
        self.procedure_settings["distance_to_target"] = float(self.dist_to_target.text())
        self.procedure_settings["e"] = np.array([float(self.e_x.text()),
                                                 float(self.e_y.text()),
                                                 float(self.e_z.text())], dtype=float)
        self.procedure_settings["electrode_config"] = self.electrode_combo.currentText()
        self.procedure_settings["entry"] = np.array([float(self.entry_x.text()),
                                                     float(self.entry_y.text()),
                                                     float(self.entry_z.text())], dtype=float)
        self.procedure_settings["medication_status"] = self.medic_combo.currentText()
        self.procedure_settings["target_name"] = self.target_name.text()
        self.procedure_settings["recording_config"] = self.rec_combo.currentText()
        self.procedure_settings["target"] = np.array([float(self.target_x.text()),
                                                     float(self.target_y.text()),
                                                     float(self.target_z.text())], dtype=float)
        self.procedure_settings["offset_direction"] = self.offset_direction_combo.currentText()
        self.procedure_settings["offset_size"] = float(self.offset_size.text())


class SettingsDialog(QDialog):
    def __init__(self, subject_settings: dict, procedure_settings: dict, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("Enter settings.")

        # settings dicts - we will mutate the input dictionaries
        self.subject_settings = subject_settings
        self.procedure_settings = procedure_settings

        # Widgets to show/edit parameters.
        self.settings_layout = QVBoxLayout(self)

        tab_widget = QTabWidget(self)
        self.subject_widget = SubjectWidget(self.subject_settings)
        tab_widget.addTab(self.subject_widget, 'Subject')

        self.proc_widget = ProcedureWidget(self.procedure_settings)
        tab_widget.addTab(self.proc_widget, 'Procedure')

        self.settings_layout.addWidget(tab_widget)

        # signals
        self.subject_widget.subject_change.connect(self.proc_widget.change_subject)

        # update procedures when re-opening settings window
        if "subject_id" not in self.subject_settings.keys():
            self.subject_widget.check_subject()
        elif self.subject_settings["subject_id"] not in [None, ""]:
            self.proc_widget.change_subject(self.subject_settings["subject_id"], block=True)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.settings_layout.addWidget(buttons, alignment=Qt.AlignHCenter)

    def update_settings(self):
        self.subject_widget.to_dict()
        self.proc_widget.to_dict()
