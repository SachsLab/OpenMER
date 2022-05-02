from qtpy import QtCore
import serial
import serial.tools.list_ports
from .base import MerDepthSource
from neuroport_dbs.settings import parse_ini_try_numeric


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
