from pathlib import Path
from qtpy import QtCore
from .interface import IDataSource
from ..settings import parse_ini_try_numeric
try:
    from cerebuswrapper import CbSdkConnection
except ModuleNotFoundError as e:
    print(e, "Try `pip install git+https://github.com/SachsLab/cerebuswrapper.git`.")


SAMPLINGGROUPS = ["0", "500", "1000", "2000", "10000", "30000"]  # , "RAW"]  RAW broken in cbsdk


class CerebusDataSource(IDataSource):

    def __init__(self, scoped_settings: QtCore.QSettings, **kwargs):
        super().__init__(**kwargs)  # Sets on_connect_cb

        cbsdk_settings_path = Path(scoped_settings.fileName()).parents[0] / "CbSdkConnection.ini"
        conn_settings = QtCore.QSettings(str(cbsdk_settings_path), QtCore.QSettings.IniFormat)
        conn_settings.beginGroup("conn-params")

        self._cbsdk_conn = CbSdkConnection()
        conn_params = self._cbsdk_conn.con_params.copy()
        for key, orig_value in conn_params.items():
            new_value = conn_settings.value(key, orig_value)
            if key in ["inst-port", "client-port", "receive-buffer-size"]:
                new_value = int(new_value)
            conn_params[key] = new_value
        self._cbsdk_conn.con_params = conn_params
        result = self._cbsdk_conn.connect()
        if result != 0:
            raise ConnectionError("Could not connect to CerebusDataSource: {}".format(result))
        conn_config = {}
        for key in scoped_settings.allKeys():
            if key in ['class', 'sampling_group']:
                continue
            split_key = key.split('/')
            if len(split_key) > 1:
                if split_key[0] not in conn_config:
                    conn_config[split_key[0]] = {}
                conn_config[split_key[0]][split_key[1]] = parse_ini_try_numeric(scoped_settings, key)
            else:
                conn_config[key] = parse_ini_try_numeric(scoped_settings, key)

        # get_events, get_comments, get_continuous, buffer_parameter: comment_length
        self._cbsdk_conn.cbsdk_config = conn_config
        self._group_ix = SAMPLINGGROUPS.index(scoped_settings.value("sampling_group", type=str))
        self._group_info = self._decode_group_info(self._cbsdk_conn.get_group_config(self._group_ix))
        # self.wf_config = self.cbsdk_conn.get_sys_config()  # {'spklength': 48, 'spkpretrig': 10, 'sysfreq': 30000}
        self._on_connect_cb(self)

    @staticmethod
    def _decode_group_info(group_info: dict):
        for gi_item in group_info:
            gi_item['label'] = gi_item['label']
            gi_item['unit'] = gi_item['unit']
        return group_info

    @property
    def data_stats(self):
        chan_states = []
        chan_names = []
        srate = int(SAMPLINGGROUPS[self._group_ix])
        extra = {}

        # self._chan_states = pd.DataFrame(columns=['name', 'src', 'unit', 'type', 'pos'])
        for ch_ix, ch_dict in enumerate(self._group_info):
            chan_names.append(ch_dict['label'])
            ch_info = self._cbsdk_conn.get_channel_info(ch_dict['chan'])
            chan_states.append({
                'name': ch_dict['label'],
                'src': ch_dict['chan'],
                'unit': ch_dict['unit'],
                'gain': ch_dict['gain'],
                'spkthrlevel': ch_info['spkthrlevel']
            })
        # TODO: more chan_states, extra?

        return {'srate': srate, 'channel_names': chan_names, 'chan_states': chan_states, **extra}

    @property
    def is_connected(self):
        return self._cbsdk_conn.is_connected

    def get_continuous_data(self):
        return self._cbsdk_conn.get_continuous_data()

    def get_event_data(self):
        return self._cbsdk_conn.get_event_data()

    def get_comments(self):
        return self._cbsdk_conn.get_comments()

    def get_waveforms(self, chan_info):
        return self._cbsdk_conn.get_waveforms(chan_info['chan_id'])

    def disconnect_requested(self):
        self._cbsdk_conn.cbsdk_config = {'reset': True, 'get_continuous': False,
                                         'get_events': False, 'get_comments': False}
        self._cbsdk_conn.disconnect()

    def update_monitor(self, chan_info, spike_only=False):
        if not self._cbsdk_conn.is_connected:
            self._cbsdk_conn.connect()
        self._cbsdk_conn.monitor_chan(chan_info['src'], spike_only=spike_only)

    def update_threshold(self, chan_info, new_value):
        if not self._cbsdk_conn.is_connected:
            self._cbsdk_conn.connect()
        self._cbsdk_conn.set_channel_info(chan_info['chan_id'], {'spkthrlevel': new_value})

    def set_recording_state(self, on_off, file_info):
        if not self._cbsdk_conn.is_connected:
            self._cbsdk_conn.connect()
        return self._cbsdk_conn.set_recording_state(on_off, file_info)
