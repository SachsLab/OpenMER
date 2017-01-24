import sys
from cerebus import cbpy

GENRATE = 30000  # TODO: Get this from cbsdk

def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

@singleton
class CbSdkConnection(object):
    def __init__(self, instance=0, con_params={}):
        self.instance = instance
        self.con_params = {**cbpy.defaultConParams(), **con_params}
        self.cbsdk_last_config_time = None
        self.is_connected = False
        self._cbsdk_config = {
            'instance': 0,
            'buffer_parameter': {'absolute': True},
            'range_parameter': {},
            'get_events': True,
            'get_continuous': True
        }  # See _do_cbsdk_config below.

    def __del__(self):
        self.disconnect()

    def connect(self):
        # Open the interface to the NSP #
        try:
            result, connect_info = cbpy.open(instance=self.instance, connection='default', parameter=self.con_params)
            self.is_connected = (result == 0)
            print("cbpy.open returned result: {}; connect_info: {}".format(result, connect_info))
            self.cbsdk_config = {'buffer_parameter': {'absolute': True}}  # TODO: Does this need to be updated?
        except RuntimeError as e:
            result = int(e.split(",")[0])
            self.is_connected = False
            connect_info = None
            print(e)

        return result

    def disconnect(self):
        # Close the interface to the NSP (or nPlay). #
        result = cbpy.close()

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

        if 'buffer_parameter' in indict:
            indict['buffer_parameter'] = {**self._cbsdk_config['buffer_parameter'], **indict['buffer_parameter']}
        if 'range_parameter' in indict:
            indict['range_parameter'] = {**self._cbsdk_config['range_parameter'], **indict['range_parameter']}

        self._cbsdk_config = {**self._cbsdk_config, **indict}
        self._do_cbsdk_config(**self._cbsdk_config)

    @property
    def is_running(self):
        return self.cbsdk_last_config_time is not None

    def _do_cbsdk_config(self, instance=0, reset=True, buffer_parameter={}, range_parameter={},
                         get_events=True, get_continuous=True):
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
        :param noevent: equivalent of setting 'event_length' to 0
        :param nocontinuous: equivalent of setting 'continuous_length' to 0
        :return:
        """
        res, was_reset = cbpy.trial_config(
            instance=instance, reset=reset,
            buffer_parameter=buffer_parameter,
            range_parameter=range_parameter,
            noevent=int(not get_events),
            nocontinuous=int(not get_continuous)
        )
        res, self.cbsdk_last_config_time = cbpy.time(instance=instance)

    def start_data(self):
        # Start the buffering of data. #
        self._do_cbsdk_config(**self._cbsdk_config)

    def stop_data(self):
        # Stop the buffering of data. #
        cbpy.trial_config(reset=False)
        self.cbsdk_last_config_time = None

    def get_event_data(self):
        # Spike event data. #
        if self.cbsdk_last_config_time:
            result, trial = cbpy.trial_event(instance=self.cbsdk_config['instance'], reset=True)
            if result != 0:
                print('failed to get trial event data. Error (%d)' % result)
                return False, False
            else:
                return trial, cbpy.time(instance=self.cbsdk_config['instance'])[1]
        else:
            return False, False

    def get_continuous_data(self):
        result, trial = cbpy.trial_continuous(instance=self.cbsdk_config['instance'], reset=True)
        return trial, cbpy.time(instance=self.cbsdk_config['instance'])[1]