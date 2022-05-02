from qtpy import QtCore
from ..settings import parse_ini_try_numeric


class MerDepthSource:
    def __init__(self, scoped_settings: QtCore.QSettings):
        # scale_factor should be 0.001 for FHC DDU V2, 1.0 otherwise.
        self._scale_factor = parse_ini_try_numeric(scoped_settings, 'scale_factor') or 1.0
        self.do_open()

    def do_open(self):
        raise NotImplementedError()

    def do_close(self):
        raise NotImplementedError()

    def update(self):
        raise NotImplementedError
