import sys
import os
import numpy as np
# use the same GUI format as the other ones
from qtpy.QtWidgets import QComboBox, QLineEdit, QLabel, QDialog, QVBoxLayout, QWidget, \
                           QGridLayout, QDialogButtonBox, QCalendarWidget, \
                           QCheckBox, QTabWidget

from qtpy.QtCore import QDate, QRegExp, Qt, Signal
from qtpy.QtGui import QRegExpValidator

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'expdb')))
from DB_Wrap import DBWrapper


class SubjectWidget(QWidget):
    subject_change = Signal(int)

    def __init__(self, subject_settings):
        super(SubjectWidget, self).__init__()

        self.subject_enums = DBWrapper().return_enums('subject')

        subject_layout = QGridLayout(self)
        subject_layout.setColumnMinimumWidth(2, 60)

        subject_layout.addWidget(QLabel("Id: "), 0, 0, 1, 1)
        self.id_combo = QComboBox()
        self.id_combo.setEditable(True)
        self.id_combo.addItem('')
        self.id_combo.addItems(DBWrapper().list_all_subjects())
        self.id_combo.currentIndexChanged.connect(self.load_subject)
        self.id_combo.lineEdit().editingFinished.connect(self.check_subject)

        subject_layout.addWidget(self.id_combo, 0, 1, 1, 4)

        subject_layout.addWidget(QLabel("Name: "), 1, 0, 1, 1)
        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(135)
        subject_layout.addWidget(self.name_edit, 1, 1, 1, 4)

        subject_layout.addWidget(QLabel("Sex: "), 2, 0, 1, 1)
        self.sex_combo = QComboBox()
        self.sex_combo.addItems(self.subject_enums['sex'] if 'sex' in self.subject_enums.keys() else '')
        self.sex_combo.setCurrentIndex(0)
        subject_layout.addWidget(self.sex_combo, 2, 1, 1, 1)

        subject_layout.addWidget((QLabel("Date of birth: ")), 3, 0, 1, 1)
        self.dob_calendar = QCalendarWidget()
        subject_layout.addWidget(self.dob_calendar, 3, 1, 1, 4)

        # Subject Settings
        self.subject_settings = subject_settings
        if not self.subject_settings:
            self.update_settings_from_db(-1)

        self.update_subject()

    def update_subject(self):
        self.name_edit.setText(self.read_dict_value(self.subject_settings, 'name'))
        self.id_combo.setCurrentText(self.read_dict_value(self.subject_settings, 'id'))
        self.sex_combo.setCurrentText(self.read_dict_value(self.subject_settings, 'sex'))
        dob = self.read_dict_value(self.subject_settings, 'birthday')
        if dob not in [None, '']:
            q_dob = QDate.fromString(dob, 'yyyy-MM-d')
            self.dob_calendar.setSelectedDate(q_dob)
        else:
            self.dob_calendar.setSelectedDate(QDate.currentDate())

    def update_settings_from_db(self, idx):
        for key, value in DBWrapper().load_subject_details(idx).items():
            self.subject_settings[key] = value

    def load_subject(self):
        # id is a unique and mandatory field
        self.check_subject()
        self.update_subject()

    def check_subject(self):
        # when changing the id in the combobox, can be modifying or entering an existing subject id. Check to load data
        # if so.
        curr_id = self.id_combo.currentText()
        if curr_id != '':
            self.update_settings_from_db(curr_id)
            self.subject_change.emit(self.subject_settings['subject_id'])
        else:
            self.update_settings_from_db(-1)
            self.subject_change.emit(-1)

    @staticmethod
    def read_dict_value(dictionary, value):
        return str(dictionary[value]) if value in dictionary.keys() else ''

    def to_dict(self):
        self.subject_settings['id'] = self.id_combo.currentText()
        self.subject_settings['name'] = self.name_edit.text()
        self.subject_settings['sex'] = self.sex_combo.currentText()
        self.subject_settings['birthday'] = self.dob_calendar.selectedDate().toPyDate()


class ProcedureWidget(QWidget):
    def __init__(self, procedure_settings):
        super(ProcedureWidget, self).__init__()

        # Settings
        self.procedure_settings = procedure_settings

        # populate with defaults if empty
        if not self.procedure_settings:
            self.update_settings_from_db(-1)

        self.proc_enums = DBWrapper().return_enums('procedure')
        proc_layout = QGridLayout(self)

        row = 0
        proc_layout.addWidget(QLabel("Previous procedures: "), row, 0, 1, 1)
        self.prev_proc = QComboBox()
        self.prev_proc.setEnabled(True)
        self.check_all_procedures(None, False)
        self.prev_proc.currentIndexChanged.connect(self.procedure_selection_change)
        proc_layout.addWidget(self.prev_proc, row, 1, 1, 3)

        row += 1
        proc_layout.addWidget(QLabel("Procedure name: "), row, 0, 1, 1)
        self.proc_name = QLineEdit("")
        proc_layout.addWidget(self.proc_name, row, 1, 1, 3)

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
        proc_layout.addWidget(QLabel("Distance to target: "), row, 0, 1, 1)
        self.dist_to_target = self.coord_line_edit()
        proc_layout.addWidget(self.dist_to_target, row, 1, 1, 1)

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
        proc_layout.addWidget(QLabel("Medication status: "), row, 0, 1, 1)
        self.medic_combo = self.combo_from_enum('medication_status')
        proc_layout.addWidget(self.medic_combo, row, 1, 1, 3)

        self.update_procedure()

    def check_all_procedures(self, subject_id, block):
        self.prev_proc.blockSignals(block)
        self.all_procedures = DBWrapper().list_all_procedures(subject_id)
        self.prev_proc.clear()
        self.prev_proc.addItem('')
        self.prev_proc.addItems(
            [' '.join([x.name, x.recording_config, x.date.strftime('%Y-%m-%d')]) for x in self.all_procedures])
        self.prev_proc.setCurrentIndex(0)
        self.prev_proc.blockSignals(False)

    def combo_from_enum(self, enum_name):
        combo = QComboBox()
        combo.addItems(self.proc_enums[enum_name] if enum_name in self.proc_enums.keys() else '')
        combo.setCurrentText('none')
        return combo

    def coord_line_edit(self):
        template = QRegExp(r"[-]?\d*\.?\d{0,3}")
        validator = QRegExpValidator(template)

        line = QLineEdit("0.0")
        line.setValidator(validator)
        line.setFixedWidth(60)
        line.editingFinished.connect(self.update_dist_to_target)
        return line

    def update_dist_to_target(self):
        ddt = np.sqrt((float(self.target_x.text()) - float(self.entry_x.text()))**2 +
                      (float(self.target_y.text()) - float(self.entry_y.text()))**2 +
                      (float(self.target_z.text()) - float(self.entry_z.text()))**2)
        diff = float(self.dist_to_target.text()) - ddt
        self.comp_dist_to_target.setText(
            "Computed distance: {:.3f} mm; Difference: {:.3f} mm".format(ddt, diff))

    def change_subject(self, sub_id, block=False):
        self.check_all_procedures(sub_id, block)

    def procedure_selection_change(self):
        if self.prev_proc.currentIndex() > 0:
            self.update_settings_from_db(
                self.all_procedures[self.prev_proc.currentIndex()-1].procedure_id)
        else:
            self.update_settings_from_db(-1)
        self.update_procedure()

    def update_settings_from_db(self, idx):
        self.procedure_settings.update(DBWrapper().load_procedure_details(idx, exclude=['subject', 'procedure_id']))

    def update_procedure(self):
        self.proc_name.setText(self.read_dict_value('name'))
        self.type_combo.setCurrentText(self.read_dict_value('type'))
        self.rec_combo.setCurrentText(self.read_dict_value('recording_config'))
        self.electrode_combo.setCurrentText(self.read_dict_value('electrode_config'))
        self.medic_combo.setCurrentText(self.read_dict_value('medication_status'))
        entry = self.read_dict_value('entry')
        if entry is None:
            entry = [0., 0., 0.]
        self.entry_x.setText(str(entry[0]))
        self.entry_y.setText(str(entry[1]))
        self.entry_z.setText(str(entry[2]))
        target = self.read_dict_value('target')
        if target is None:
            target = [0., 0., 0.]
        self.target_x.setText(str(target[0]))
        self.target_y.setText(str(target[1]))
        self.target_z.setText(str(target[2]))
        ddt = self.read_dict_value('distance_to_target')
        if ddt is None:
            ddt = 0.000
        self.dist_to_target.setText(str(ddt))
        self.update_dist_to_target()
        a = self.read_dict_value('a')
        if a is None:
            a = [0., 0., 0.]
        self.a_x.setText(str(a[0]))
        self.a_y.setText(str(a[1]))
        self.a_z.setText(str(a[2]))
        e = self.read_dict_value('e')
        if e is None:
            e = [0., 0., 0.]
        self.e_x.setText(str(e[0]))
        self.e_y.setText(str(e[1]))
        self.e_z.setText(str(e[2]))

    def read_dict_value(self, value):
        return self.procedure_settings[value] if value in self.procedure_settings.keys() else None

    def to_dict(self):
        self.procedure_settings['type'] = self.type_combo.currentText()
        self.procedure_settings['a'] = np.array([float(self.a_x.text()),
                                                 float(self.a_y.text()),
                                                 float(self.a_z.text())], dtype=np.float)
        self.procedure_settings['distance_to_target'] = float(self.dist_to_target.text())
        self.procedure_settings['e'] = np.array([float(self.e_x.text()),
                                                 float(self.e_y.text()),
                                                 float(self.e_z.text())], dtype=np.float)
        self.procedure_settings['electrode_config'] = self.electrode_combo.currentText()
        self.procedure_settings['entry'] = np.array([float(self.entry_x.text()),
                                                     float(self.entry_y.text()),
                                                     float(self.entry_z.text())], dtype=np.float)
        self.procedure_settings['medication_status'] = self.medic_combo.currentText()
        self.procedure_settings['name'] = self.proc_name.text()
        self.procedure_settings['recording_config'] = self.rec_combo.currentText()
        self.procedure_settings['target'] = np.array([float(self.target_x.text()),
                                                     float(self.target_y.text()),
                                                     float(self.target_z.text())], dtype=np.float)


class BufferWidget(QWidget):
    def __init__(self, buffer_settings):
        super(BufferWidget, self).__init__()

        # Settings
        self.buffer_settings = buffer_settings
        if not self.buffer_settings:
            self.buffer_settings['buffer_length'] = '6.000'
            self.buffer_settings['sample_length'] = '4.000'
            self.buffer_settings['electrode_settings'] = {}

        self.buffer_widgets = {}

        buffer_layout = QGridLayout(self)
        row = -1
        if 'electrode_settings' in self.buffer_settings.keys():
            for label, sett in self.buffer_settings['electrode_settings'].items():
                row += 1
                buffer_layout.addWidget(QLabel(label), row, 0, 1, 1)
                self.buffer_widgets[label] = {}
                self.buffer_widgets[label]['chk_threshold'] = QCheckBox("Threshold")
                self.buffer_widgets[label]['chk_threshold'].setChecked(bool(sett['threshold']))
                self.buffer_widgets[label]['edit_validity'] = QLineEdit()
                self.buffer_widgets[label]['edit_validity'].setText(str(sett['validity']))

                buffer_layout.addWidget(self.buffer_widgets[label]['chk_threshold'], row, 1, 1, 1)
                buffer_layout.addWidget(QLabel('Validity Threshold (%)'), row, 2, 1, 1)
                buffer_layout.addWidget(self.buffer_widgets[label]['edit_validity'], row, 3, 1, 1)


            row += 1
            buffer_layout.addWidget(QLabel("Depth buffer size (s): "), row, 0, 1, 1)
            self.edit_buffer_length = QLineEdit(self.buffer_settings['buffer_length'])
            self.edit_buffer_length.setInputMask("0.000")
            self.edit_buffer_length.setFixedWidth(40)
            buffer_layout.addWidget(self.edit_buffer_length, row, 1, 1, 1)

            row += 1
            buffer_layout.addWidget(QLabel("Depth samples size (s): "), row, 0, 1, 1)
            self.edit_sample_length = QLineEdit(self.buffer_settings['sample_length'])
            self.edit_sample_length.setInputMask("0.000")
            self.edit_sample_length.setFixedWidth(40)
            buffer_layout.addWidget(self.edit_sample_length, row, 1, 1, 1)

            row += 1
            self.run_buffer = QCheckBox('Run depth buffer')
            self.run_buffer.setChecked(len(self.buffer_settings['electrode_settings']) != 0)
            self.run_buffer.setEnabled(len(self.buffer_settings['electrode_settings']) != 0)
            buffer_layout.addWidget(self.run_buffer, row, 0, 1, 1)

    def to_dict(self):
        # convert all fields to dictionary and return it
        self.buffer_settings['buffer_length'] = self.edit_buffer_length.text()
        self.buffer_settings['sample_length'] = self.edit_sample_length.text()
        self.buffer_settings['run_buffer'] = self.run_buffer.isChecked()

        for key, value in self.buffer_widgets.items():
            self.buffer_settings['electrode_settings'][key] = {}
            self.buffer_settings['electrode_settings'][key]['threshold'] = value['chk_threshold'].isChecked()
            self.buffer_settings['electrode_settings'][key]['validity'] = float(value['edit_validity'].text())


class FeaturesWidget(QWidget):
    def __init__(self, features_settings):
        super(FeaturesWidget, self).__init__()

        # Settings
        self.feature_categories = DBWrapper().all_features.keys()
        self.features_settings = features_settings
        if not self.features_settings:
            self.features_settings['features'] = {}

            # Check if default values are defined
            for cat in self.feature_categories:
                # defaults to true, compute all features
                self.features_settings['features'][cat] = True

        self.features_widgets = {}

        features_layout = QGridLayout(self)

        # Add an option to toggle all features
        self.all_features = QCheckBox('All')
        self.all_features.setChecked(False)
        self.all_features.clicked.connect(self.toggle_all)
        features_layout.addWidget(self.all_features, 0, 0, 1, 1)
        if 'features' in self.features_settings.keys():
            for idx, (label, sett) in enumerate(self.features_settings['features'].items()):
                self.features_widgets[label] = QCheckBox(label)
                self.features_widgets[label].setChecked(sett)
                self.features_widgets[label].clicked.connect(self.toggle)
                features_layout.addWidget(self.features_widgets[label], idx+1, 0, 1, 1)

    def toggle_all(self):
        for label, sett in self.features_widgets.items():
            self.features_widgets[label].setChecked(self.all_features.isChecked())

    def toggle(self):
        if any([not x.isChecked() for x in self.features_widgets.values()]):
            self.all_features.setChecked(False)

    def to_dict(self):
        for key, value in self.features_widgets.items():
            self.features_settings['features'][key] = value.isChecked()


class SettingsDialog(QDialog):
    def __init__(self, subject_settings, procedure_settings, buffer_settings, features_settings, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("Enter settings.")

        # settings dicts
        self.subject_settings = subject_settings
        self.procedure_settings = procedure_settings
        self.buffer_settings = buffer_settings
        self.features_settings = features_settings

        # Widgets to show/edit parameters.
        self.settings_layout = QVBoxLayout(self)

        tab_widget = QTabWidget(self)
        self.subject_widget = SubjectWidget(self.subject_settings)
        tab_widget.addTab(self.subject_widget, 'Subject')

        self.proc_widget = ProcedureWidget(self.procedure_settings)
        tab_widget.addTab(self.proc_widget, 'Procedure')

        self.buff_widget = BufferWidget(self.buffer_settings)
        tab_widget.addTab(self.buff_widget, 'Buffer')

        self.feat_widget = FeaturesWidget(self.features_settings)
        tab_widget.addTab(self.feat_widget, 'Features')

        self.settings_layout.addWidget(tab_widget)

        # signals
        self.subject_widget.subject_change.connect(self.proc_widget.change_subject)
        # update procedures when re-opening settings window
        if 'subject_id' not in self.subject_settings.keys():
            self.subject_widget.check_subject()
        elif self.subject_settings['subject_id'] not in [None, '']:
            self.proc_widget.change_subject(self.subject_settings['subject_id'], block=True)

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
        self.buff_widget.to_dict()
        self.feat_widget.to_dict()
