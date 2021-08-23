from qtpy import QtCore
from cerebuswrapper import CbSdkConnection
import serial
import serial.tools.list_ports
from neuroport_dbs.settings import parse_ini_try_numeric


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


class CBSDKPlayback(MerDepthSource):

    def __init__(self, scoped_settings: QtCore.QSettings):
        super().__init__(scoped_settings)

    def do_open(self):
        CbSdkConnection().connect()
        CbSdkConnection().cbsdk_config = {
            'reset': True, 'get_events': False, 'get_comments': True,
            'buffer_parameter': {
                'comment_length': 10
            }
        }

    def do_close(self):
        CbSdkConnection().disconnect()

    def update(self):
        cbsdk_conn = CbSdkConnection()
        if cbsdk_conn.is_connected:
            comments = cbsdk_conn.get_comments()
            if comments:
                comment_strings = [x[1].decode('utf8') for x in comments]
            else:
                comment_strings = ""
            dtts = []
            for comm_str in comment_strings:
                if 'DTT:' in comm_str:
                    dtts.append(float(comm_str[4:]))
            if len(dtts) > 0:
                raw_value = dtts[-1]
                return raw_value
        return None


class FHCSerial(MerDepthSource):

    def __init__(self, scoped_settings: QtCore.QSettings):
        super().__init__(scoped_settings)
        self._baudrate = parse_ini_try_numeric(scoped_settings, 'baudrate') or 19200
        self._com_port = scoped_settings.value("com_port")
        self.ser = serial.Serial()

    def do_open(self):
        super().do_open()
        self.ser.baudrate = self._baudrate
        if self._com_port not in serial.tools.list_ports.comports():
            print(f"Port {self._com_port} not found in list of comports.")
        if not self.ser.is_open:
            self.ser.port = self._com_port
            try:
                self.ser.open()  # TODO: Add timeout; Add error.
                self.ser.write('AXON+\r'.encode())
            except serial.serialutil.SerialException:
                print("Could not open serial port")

    def do_close(self):
        self.ser.close()

    def update(self):
        if self.ser.is_open:
            in_str = self.ser.readline().decode('utf-8').strip()
            if in_str:
                try:
                    raw_value = float(in_str) * self._scale_factor
                    return raw_value

                except ValueError:
                    print("DDU result: {}".format(in_str))
        return None
