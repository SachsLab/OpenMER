from cerebus import cbpy
import numpy as np
# import time
# import os
# import sys
# if "__file__" in locals():
#     nsp_path = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
#                                              '..', '..', 'ExperimentSystem', 'SigProc', 'neurosigproc'))
# else:
#     nsp_path = os.path.realpath(os.path.join(os.getcwd(),
#                                              '..', '..', 'ExperimentSystem', 'SigProc', 'neurosigproc'))
# sys.path.append(nsp_path)
# from neurosigproc.generators.siggen import SignalGenerator

DBS_CHANS = 5
SIM_SUS = [np.random.randint(5) for ix in range(DBS_CHANS)]
SIMULATION_CONFIG = {
    5: {
        'sampling_freq': 30000.0,
        'n_channels': DBS_CHANS,
        'chan_ids': [1, 2, 3, 4, 5],
        'chan_labels': [b'Middle', b'Anterior', b'Lateral', b'Posterior', b'Medial'],
        'lfp': {
            'beta': {'freq': 20, 'amp': 100}
        },
        'multiunit': {
            'covariance': 'diagonal',
            'amp': [100.0]
        },
        'singleunit': {
            'nUnits': SIM_SUS,
            'rates': 3.0 + 77.0 * np.random.rand(np.sum(np.asarray(SIM_SUS))),
            'covariance': 'diagonal'
        },
        'pac': {
            'target': None,  # 'multiunit',
            'source': None,  # 'beta',
            'mod_strength': [1.0],
            'mod_scale': 'linear',
            'offset': -np.pi/2
        },
        'noise': {
            'type': 'pink',
            'amp': [20.0],
            'covariance': 'diagonal'
        }
    }
}


def singleton(cls):
    instances = {}

    def getinstance(**kwargs):
        if cls not in instances:
            instances[cls] = cls(**kwargs)
        return instances[cls]
    return getinstance


@singleton
class CbSdkConnection(object):
    def __init__(self, instance=0, con_params=None, simulate_ok=False):
        """
        :param instance: integer id of cbsdk instance.
        :param con_params: {
            'client-addr': '192.168.137.1' if directly connected or '255.255.255.255' if through a switch,
            'client-port': cbNET_UDP_PORT_BCAST,
            'inst-addr': cbNET_UDP_ADDR_CNT.decode("utf-8"),
            'inst-port': cbNET_UDP_PORT_CNT,
            'receive-buffer-size': (8 * 1024 * 1024) if sys.platform == 'win32' else (6 * 1024 * 1024)
        }
        :param simulate_ok: Not yet implemented
        """
        if con_params is None:
            con_params = {}
        self.instance = instance
        self.con_params = {**cbpy.defaultConParams(), **con_params}  # default params, updated with provided params
        self.is_connected = False
        self.is_simulating = simulate_ok
        self.sig_gens = {}
        self._cbsdk_config = {
            'instance': 0,
            'buffer_parameter': {
                'absolute': True
            },
            'range_parameter': {},
            'get_events': True,
            'get_continuous': True
        }  # See self._do_config for description.

    def __del__(self):
        self.disconnect()

    def connect(self):
        # Open the interface to the NSP #
        try:
            result, connect_info = cbpy.open(instance=self.instance, connection='default', parameter=self.con_params)
            self.is_connected = (result == 0 or result == 1)
            print("cbpy.open returned result: {}; connect_info: {}".format(result, connect_info))
            self.cbsdk_config = {
                'buffer_parameter': {'absolute': True}
            }  # TODO: Does this need to be updated?
        except RuntimeError as e:
            result = int(str(e).split(",")[0])
            self.is_connected = False
            print(e)

        # if self.is_simulating:
        #     self.is_simulating = not self.is_connected
        #     result = 0
        #
        # if self.is_simulating:
        #     self.sig_gens = {}
        #     for key in SIMULATION_CONFIG:
        #         sig_params = SIMULATION_CONFIG[key].copy()
        #         sig_params.pop('chan_ids', None)
        #         sig_params.pop('chan_labels', None)
        #         self.sig_gens[key] = SignalGenerator(**sig_params)

        return result

    def disconnect(self):
        # Close the interface to the NSP (or nPlay). #
        cbpy.close()
        self.is_connected = False

    @property
    def cbsdk_config(self):
        return self._cbsdk_config

    @cbsdk_config.setter
    def cbsdk_config(self, indict):
        if not isinstance(indict, dict):
            try:
                indict = dict(indict)
            except TypeError:
                print("Value passed to cbsdk_config must be a dictionary")

        # Update the provided parameters with missing parameters.
        if 'buffer_parameter' in indict:
            indict['buffer_parameter'] = {**self._cbsdk_config['buffer_parameter'], **indict['buffer_parameter']}
        if 'range_parameter' in indict:
            indict['range_parameter'] = {**self._cbsdk_config['range_parameter'], **indict['range_parameter']}

        self._cbsdk_config = {**self._cbsdk_config, **indict}  # Store parameters
        self._do_cbsdk_config(**self._cbsdk_config)  # Use the parameters.

    def _do_cbsdk_config(self, instance=0, reset=True, buffer_parameter=None, range_parameter=None,
                         get_events=False, get_continuous=False, get_comments=False):
        """
        :param instance:
        :param reset: True to clear buffer and start acquisition, False to stop acquisition
        :param buffer_parameter - (optional) dictionary with following keys (all optional)
               'double': boolean, if specified, the data is in double precision format
               'absolute': boolean, if specified event timing is absolute (new polling will not reset time for events)
               'continuous_length': set the number of continuous data to be cached
               'event_length': set the number of events to be cached
               'comment_length': set number of comments to be cached
               'tracking_length': set the number of video tracking events to be cached
        :param range_parameter - (optional) dictionary with following keys (all optional)
               'begin_channel': integer, channel to start polling if certain value seen
               'begin_mask': integer, channel mask to start polling if certain value seen
               'begin_value': value to start polling
               'end_channel': channel to end polling if certain value seen
               'end_mask': channel mask to end polling if certain value seen
               'end_value': value to end polling
        :param 'get_events': If False, equivalent of setting buffer_parameter['event_length'] to 0
        :param 'get_continuous': If False, equivalent of setting buffer_parameter['continuous_length'] to 0
        :param 'get_comments': If False, equivalent of setting buffer_parameter['comment_length'] to 0
        :return:
        """
        if buffer_parameter is None:
            buffer_parameter = {}
        if range_parameter is None:
            range_parameter = {}
        if self.is_connected:
            cbpy.trial_config(
                instance=instance, reset=reset,
                buffer_parameter=buffer_parameter,
                range_parameter=range_parameter,
                noevent=int(not get_events),
                nocontinuous=int(not get_continuous),
                nocomment=int(not get_comments)
            )
        # if self.is_simulating:
        #     for key in self.sig_gens:
        #         self.sig_gens[key].last_time = time.time()

    def get_event_data(self):
        # Spike event data. #
        if self.cbsdk_config['get_events']:
            if self.is_connected:
                result, data = cbpy.trial_event(instance=self.cbsdk_config['instance'], reset=True)
                if result == 0:
                    return data
                else:
                    print('failed to get trial event data. Error (%d)' % result)
            # elif self.is_simulating:
            #     data = []
            #     for key in self.sig_gens:
            #         sg_parms = SIMULATION_CONFIG[key]
            #         data.extend(
            #             [
            #                 [
            #                     sg_parms['chan_ids'][chan_ix],
            #                     {
            #                         'events': [],
            #                         'timestamps': [np.array(), np.array(), np.array()]  # TODO: get array per unit
            #                     }
            #                 ] for chan_ix in range(len(sg_parms['chan_ids']))
            #             ]
            #         )
            #     return data
        return None

    def get_continuous_data(self):
        if self.cbsdk_config['get_continuous']:
            if self.is_connected and self.cbsdk_config['get_continuous']:
                result, data = cbpy.trial_continuous(instance=self.cbsdk_config['instance'], reset=True)
                if result == 0:
                    return data
                else:
                    print('failed to get trial continuous data. Error (%d)' % result)
            # elif self.is_simulating:
            #     data = []
            #     for key in self.sig_gens:
            #         signal = self.sig_gens[key].generate()
            #         signal = signal.astype(np.int16)
            #         sg_parms = SIMULATION_CONFIG[key]
            #         data.extend(
            #             [
            #                 [sg_parms['chan_ids'][chan_ix], signal[:, chan_ix]] for chan_ix in range(signal.shape[1])
            #             ]
            #         )
            #     return data
        return None

    def get_comments(self):
        if self.is_connected and self.cbsdk_config['get_comments']:
            result, comments = cbpy.trial_comment(instance=self.cbsdk_config['instance'], reset=True)
            if result == 0:
                return comments
            else:
                print('Failed to get trial comments. Error (%d)' % result)
        return None

    def get_group_config(self, group_ix):
        if self.is_connected:
            result, group_info = cbpy.get_sample_group(group_ix, instance=self.cbsdk_config['instance'])
            if result == 0:
                return group_info
            else:
                print('failed to get trial group config. Error (%d)' % result)
        # elif self.is_simulating:
        #     # TODO: group_ix specific channel info
        #     group_info = [
        #         {
        #             'chid': 32768,
        #             'chan': SIMULATION_CONFIG[group_ix]['chan_ids'][ch_ix],
        #             'proc': 1,
        #             'bank': 1,
        #             'term': SIMULATION_CONFIG[group_ix]['chan_ids'][ch_ix],
        #             'gain': 0.25,
        #             'label': SIMULATION_CONFIG[group_ix]['chan_labels'][ch_ix],
        #             'unit': b'uV'
        #         } for ch_ix in range(len(SIMULATION_CONFIG[group_ix]['chan_ids']))
        #     ]
        #     return group_info
        return None

    def get_channel_info(self, chan_id):
        if self.is_connected:
            result, chan_info = cbpy.get_channel_config(chan_id, instance=self.cbsdk_config['instance'])
            if result == 0:
                return chan_info
            else:
                print('Failed to get channel info. Error (%d)' % result)
        return None

    def set_channel_info(self, chan_id, new_info):
        if self.is_connected:
            result = cbpy.set_channel_config(chan_id, chaninfo=new_info)

    def time(self):
        if self.is_connected:
            res, time = cbpy.time(instance=self.instance)
            return time
        else:
            return None

    def monitor_chan(self, chan_ix):
        if self.is_connected:
            cbpy.analog_out(149, chan_ix, track_last=True, spike_only=False, instance=self.cbsdk_config['instance'])
