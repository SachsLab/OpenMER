
class CbSdkConnection:
    
    _is_simulating = False

    def __init__(self, *args, **kwargs):
        pass

    def connect(self):
        return

    def set_recording_state(self, *args, **kwargs):
        return

    def get_group_config(self, *args, **kwargs):
        return 

    @property
    def is_connected(self):
        return False

    @property
    def is_simulating(self):
        return self._is_simulating

    @is_simulating.setter
    def is_simulating(self, value):
        self._is_simulating = value

    