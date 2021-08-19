from typing import Union, Tuple
from qtpy import QtCore
import numpy as np
from .interface import IDataSource
from cerebuswrapper import CbSdkConnection
from neuroport_dbs.settings import parse_ini_try_numeric


SAMPLINGGROUPS = ["0", "500", "1000", "2000", "10000", "30000"]  # , "RAW"]  RAW broken in cbsdk


class CerebusDataSource(IDataSource):

    def __init__(self, scoped_settings: QtCore.QSettings, **kwargs):
        super().__init__(**kwargs)  # Sets on_connect_cb

        self._cbsdk_conn = CbSdkConnection()
        conn_params = self._cbsdk_conn.con_params.copy()
        for key, orig_value in conn_params.items():
            conn_params[key] = scoped_settings.value(key, orig_value)
        self._cbsdk_conn.con_params = conn_params
        self._cbsdk_conn.connect()
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
        self._group_ix = SAMPLINGGROUPS.index(scoped_settings.value("sampling_group"))
        self._group_info = self._decode_group_info(self._cbsdk_conn.get_group_config(self._group_ix))
        self._on_connect_cb(self)

    @staticmethod
    def _decode_group_info(group_info: dict):
        for gi_item in group_info:
            gi_item['label'] = gi_item['label'].decode('utf-8')
            gi_item['unit'] = gi_item['unit'].decode('utf-8')
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

    def disconnect_requested(self):
        self._cbsdk_conn.cbsdk_config = {'reset': True, 'get_continuous': False}

    def update_monitor(self, chan_info, spike_only=False):
        _cbsdk_conn = CbSdkConnection()
        if _cbsdk_conn.is_connected:
            _cbsdk_conn.monitor_chan(chan_info['src'], spike_only=spike_only)

    def update_threshold(self, chan_info, new_value):
        cbsdkconn = CbSdkConnection()
        if cbsdkconn.is_connected:
            cbsdkconn.set_channel_info(chan_info['chan_id'], {'spkthrlevel': new_value})