import re

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
        self.ser = serial.Serial(timeout=1)
        self._is_v2 = False

    @property
    def is_v2(self):
        return self._is_v2

    @is_v2.setter
    def is_v2(self, value):
        self._is_v2 = value
        self._scale_factor = 0.001 if value else 1.0
        self.doubleSpinBox_offset.setValue(60.00 if value else 0.00)

    def do_open(self):
        super().do_open()
        self.ser.baudrate = self._baudrate
        if self._com_port not in serial.tools.list_ports.comports():
            print(f"Port {self._com_port} not found in list of comports.")
        if not self.ser.is_open:
            self.ser.port = self._com_port
            try:
                self.ser.open()  # TODO: Add error.
                # Quiet transmission for a minute
                self.ser.write("AXON-\r".encode())
                self.ser.write("V\r".encode())
                # readlines will capture until timeout
                pattern = "([0-9]+\.[0-9]+)"
                for line in self.ser.readlines():
                    match = re.search(pattern, line.decode("utf-8").strip())
                    if match is not None:
                        v = match.group()  # e.g., "2.20"
                        v_maj = int(v.split(".")[0])
                        self.is_v2 = v_maj >= 2
                        break
                # Resume transmission.
                self.ser.write("AXON+\r".encode())
                _ = self.ser.readline()  # Clear out the first response to AXON+
            except serial.serialutil.SerialException:
                print("Could not open serial port")

    def do_close(self):
        self.ser.close()

    def update(self):
        if self.ser.is_open:
            in_str = self.ser.readline().decode('utf-8').strip()
            if in_str:
                try:
                    raw_value = float(in_str) * (self._scale_factor or 1.0)
                    return raw_value

                except ValueError:
                    print("DDU result: {}".format(in_str))
        return None
