from qtpy import QtCore
from ..settings import parse_ini_try_numeric


class MerDepthSource:
    def __init__(self, scoped_settings: QtCore.QSettings):
        # scale_factor should be 0.001 for FHC DDU V2, 1.0 otherwise.
        self.scale_factor = scoped_settings.value("scale_factor", 1.0, type=float)
        self.offset = scoped_settings.value("offset", 0.0, type=float)
        self.do_open()

    def do_open(self):
        raise NotImplementedError()

    def do_close(self):
        raise NotImplementedError()

    def update(self):
        raise NotImplementedError
