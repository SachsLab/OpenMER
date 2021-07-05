import sys
import os
import qtpy
import json
from qtpy.QtWidgets import QApplication, QHBoxLayout, QPushButton, QWidget, QCheckBox, QLabel
from qtpy.QtWidgets import QLineEdit, QGridLayout, QTextEdit
from qtpy.QtGui import QPixmap, QFont

from qtpy.QtCore import Qt
import pylsl

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), 'dbsgui'))
# Note: If import dbsgui fails, then set the working directory to be this script's directory.
from neuroport_dbs.dbsgui.my_widgets.custom import CustomGUI, CustomWidget, SAMPLINGGROUPS, THEMES

# Import settings
# TODO: Make some of these settings configurable via UI elements
from neuroport_dbs.settings.defaults import WINDOWDIMS_MAPPING, SAMPLINGRATE, MAPPINGSTIMULI


class MappingGUI(CustomGUI):

    def __init__(self):
        super(MappingGUI, self).__init__()
        self.setWindowTitle('MappingGUI')

    def on_action_add_plot_triggered(self):
        self.cbsdk_conn.cbsdk_config = {
            'reset': True, 'get_events': True, 'get_comments': True,
            'buffer_parameter': {
                'comment_length': 10
            }
        }
        # TODO: Or RAW, never both
        group_info = self.cbsdk_conn.get_group_config(SAMPLINGGROUPS.index(str(SAMPLINGRATE)))
        for gi_item in group_info:
            gi_item['label'] = gi_item['label'].decode('utf-8')
            gi_item['unit'] = gi_item['unit'].decode('utf-8')
        self.plot_widget = MappingWidget(group_info)
        self.plot_widget.was_closed.connect(self.on_plot_closed)

    def on_plot_closed(self):
        self.plot_widget = None
        self.cbsdk_conn.cbsdk_config = {'reset': True, 'get_events': False, 'get_comments': False}

    def do_plot_update(self):
        pass


class MappingWidget(CustomWidget):
    def __init__(self, *args, **kwargs):
        super(MappingWidget, self).__init__(*args, **kwargs)
        self.move(WINDOWDIMS_MAPPING[0], WINDOWDIMS_MAPPING[1])
        self.resize(WINDOWDIMS_MAPPING[2], WINDOWDIMS_MAPPING[3])
        # configure lsl stream
        outlet_info = pylsl.StreamInfo(name='sensorimotor_mapping', type='map', channel_count=1,
                                       nominal_srate=pylsl.IRREGULAR_RATE, channel_format=pylsl.cf_string,
                                       source_id='mapping1214')
        self.map_stream = pylsl.StreamOutlet(outlet_info)

    def create_control_panel(self):
        pass

    def create_plots(self, theme='dark', **kwargs):
        bold_font = QFont()
        bold_font.setPixelSize(12)
        bold_font.setBold(True)

        self.layout().addStretch()
        self.layout().addWidget(QLabel("Channels: ", font=bold_font))
        self.layout().addSpacing(10)
        # Add check boxes for channels
        self.channels = {}
        for chan_ix in range(len(self.group_info)):
            chan_lbl = self.group_info[chan_ix]['label']
            chk_box = QCheckBox(chan_lbl)
            chk_box.stateChanged.connect(self.check_channel_and_stim)
            self.channels[chan_lbl] = chk_box
            self.layout().addWidget(chk_box)
        self.layout().addSpacing(10)
        bt_clear = QPushButton("Uncheck all")
        bt_clear.clicked.connect(lambda: self.uncheck_all(self.channels))
        self.layout().addWidget(bt_clear)
        self.layout().addSpacing(20)

        # Stimuli types
        self.layout().addWidget(QLabel("Stimuli: ", font=bold_font))
        self.layout().addSpacing(10)
        self.mapping_stimuli = {}

        for stim in MAPPINGSTIMULI:
            self.mapping_stimuli[stim] = QCheckBox(stim)
            self.mapping_stimuli[stim].stateChanged.connect(self.check_channel_and_stim)
            self.layout().addWidget(self.mapping_stimuli[stim])
        self.mapping_stimuli['Custom'] = QCheckBox()
        l = QHBoxLayout()
        self.custom_stimulus = QLineEdit("Custom")
        l.addWidget(self.mapping_stimuli['Custom'])
        l.addSpacing(3)
        l.addWidget(self.custom_stimulus)
        self.layout().addLayout(l)
        self.layout().addSpacing(10)
        bt_clear = QPushButton("Uncheck all")
        bt_clear.clicked.connect(lambda: self.uncheck_all(self.mapping_stimuli))
        self.layout().addWidget(bt_clear)
        self.layout().addSpacing(20)

        # side
        self.layout().addWidget(QLabel("Body Side: ", font=bold_font))
        self.layout().addSpacing(10)
        self.sides = {
            'Left': QCheckBox("Left"),
            'Right': QCheckBox("Right")
        }
        l = QHBoxLayout()
        l.addWidget(self.sides['Left'])
        l.addWidget(self.sides['Right'])
        self.layout().addLayout(l)
        self.layout().addSpacing(20)

        # Body part
        self.layout().addWidget(QLabel("Limb: ", font=bold_font))
        body_widget = QWidget(self)
        body_widget.setLayout(QGridLayout())
        body_widget.layout().setContentsMargins(0, 0, 0, 0)
        lbl = QLabel()
        lbl.setPixmap(QPixmap(os.path.join(os.path.dirname(__file__), 'icons', 'HalfBody.png')))
        body_widget.layout().addWidget(lbl, 0, 0, 20, 10)

        self.body_parts = {}
        cb = QCheckBox('')
        self.body_parts['Head'] = cb
        body_widget.layout().addWidget(cb, 1, 0, 1, 1)

        cb = QCheckBox('')
        self.body_parts['Arm'] = cb
        body_widget.layout().addWidget(cb, 8, 4, 1, 1)

        cb = QCheckBox('')
        self.body_parts['Hand'] = cb
        body_widget.layout().addWidget(cb, 10, 5, 1, 1)

        cb = QCheckBox('')
        self.body_parts['Leg'] = cb
        body_widget.layout().addWidget(cb, 14, 1, 1, 1)

        cb = QCheckBox('')
        self.body_parts['Foot'] = cb
        body_widget.layout().addWidget(cb, 18, 1, 1, 1)

        bt_clear = QPushButton("Uncheck all")
        bt_clear.clicked.connect(lambda: self.uncheck_all(self.body_parts))
        body_widget.layout().addWidget(bt_clear, 20, 0, 1, 10)

        self.layout().addWidget(body_widget)
        self.layout().addSpacing(20)

        self.bt_map = QPushButton("Submit Response")
        self.bt_map.setEnabled(False)
        self.bt_map.setMinimumHeight(40)
        self.bt_map.clicked.connect(self.submit_map)
        self.layout().addWidget(self.bt_map)

        self.layout().addSpacing(10)
        bt_clear = QPushButton("Clear Channel")
        bt_clear.setMinimumHeight(20)
        bt_clear.clicked.connect(self.clear_data)
        self.layout().addWidget(bt_clear)
        self.layout().addStretch()

        # manual notes
        self.layout().addWidget(QLabel("Note: ", font=bold_font))
        self.note_field = QTextEdit()
        self.note_field.setMaximumHeight(80)
        self.note_field.textChanged.connect(self.check_note)
        self.layout().addWidget(self.note_field)
        self.layout().addSpacing(10)
        self.bt_note = QPushButton("Submit Note")
        self.bt_note.setEnabled(False)
        self.bt_note.setMinimumHeight(20)
        self.bt_note.clicked.connect(self.submit_note)
        self.layout().addWidget(self.bt_note)
        self.layout().addStretch()

    def uncheck_all(self, d):
        for k, v in d.items():
            v.setChecked(False)

    def check_channel_and_stim(self):
        if any([x.isChecked() for x in self.channels.values()]) and \
         any([x.isChecked() for x in self.mapping_stimuli.values()]):
            self.bt_map.setEnabled(True)
        else:
            self.bt_map.setEnabled(False)

    def check_note(self):
        tmp = self.note_field.toPlainText()
        if len(tmp) > 0:
            self.bt_note.setEnabled(True)
        else:
            self.bt_note.setEnabled(False)

    def submit_map(self):
        out_dict = {}
        for chan in [s for s, c in self.channels.items() if c.isChecked()]:
            side = [s for s, c in self.sides.items() if c.isChecked()]
            if not side:
                side = ['Unspecified']

            limb = [l for l, c in self.body_parts.items() if c.isChecked()]
            if not limb:
                limb = ['Unspecified']
            out_dict[chan] = {
                'Stimuli': [s for s, c in self.mapping_stimuli.items() if c.isChecked()],
                'Sides': side,
                'Limbs': limb,
            }

        out_string = json.dumps(out_dict)
        self.map_stream.push_sample([out_string])

        # stims = ''
        # for stim, cb in self.mapping_stimuli.items():
        #     if cb.isChecked():
        #         if stim == "Custom":
        #             stims += self.custom_stimulus.text() + ','
        #         else:
        #             stims += stim + ','
        # stims = stims.rstrip(',')
        #
        # limbs = ''
        # for limb, cb in self.body_parts.items():
        #     if cb.isChecked():
        #         limbs += limb + ','
        # limbs = limbs.rstrip(',')
        #
        # for lbl, chan in self.channels.items():
        #     if chan.isChecked():
        #         if stims != '' and limbs != '':
        #             self.map_stream.push_sample([lbl, stims + '__' + limbs + ';'])
        #         else:
        #             self.map_stream.push_sample([lbl, 'Clear'])

    def submit_note(self):
        out_string = self.note_field.toPlainText()
        self.map_stream.push_sample([out_string])
        self.note_field.setPlainText("")

    def clear_data(self):
        out_dict = {}
        for chan in [s for s, c in self.channels.items() if c.isChecked()]:
            out_dict[chan] = 'Clear'

        out_string = json.dumps(out_dict)
        self.map_stream.push_sample([out_string])

    def refresh_axes(self):
        pass

    def clear(self):
        pass


def main():
    _ = QApplication(sys.argv)
    aw = MappingGUI()
    # timer = QTimer()
    # timer.timeout.connect(aw.update)
    # timer.start(1000)

    if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()


if __name__ == '__main__':
    main()
