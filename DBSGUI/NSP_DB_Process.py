import os
import sys
import numpy as np
from cerebuswrapper import CbSdkConnection
from pylsl import stream_inlet, resolve_byprop
import datetime

# use the same GUI format as the other ones
from qtpy.QtWidgets import QMainWindow
import matplotlib.pyplot as plt


# Import the test wrapper. Absolute path for now.
# TODO: proper package and import.
sys.path.append('D:\\Sachs_Lab\\DBS_dev\\expdb\\')
import DB_Wrap

SIMOK = False
SAMPLINGGROUPS = ["0", "500", "1000", "2000", "10000", "30000"]  # , "RAW"]  RAW broken in cbsdk


class NSPBufferWorker(QMainWindow):

    def __init__(self, subject_id=12, buffer_length=5.0, sample_length=4.0, de_noise=False):
        super(NSPBufferWorker, self).__init__()

        # process inputs
        self.subject_id = subject_id
        self.buffer_length = int(buffer_length * 30000)
        self.sample_length = int(sample_length * 30000)
        self.de_noise = de_noise

        # try to resolve LSL stream
        self.depth_inlet = None
        self.resolve_stream()

        # DB wrapper
        self.subject_id = subject_id
        self.db_wrapper = DB_Wrap.DBWrapper()

        # cbSDK; connect using default parameters
        self.cbsdk_conn = CbSdkConnection(simulate_ok=False)
        self.cbsdk_conn.connect()

        # neural data buffer
        self.group_info = self.cbsdk_conn.get_group_config(SAMPLINGGROUPS.index("30000"))
        self.n_chan = len(self.group_info)

        self.buffer = np.zeros((self.n_chan, self.buffer_length))
        self.buffer_idx = 0
        self.update_buffer_status = True

        # electrode depth
        self.current_depth = 0.000

    def resolve_stream(self):
        # will register to LSL stream to read electrode depth
        info = resolve_byprop('source_id', 'depth1214')
        if len(info) > 0:
            self.depth_inlet = stream_inlet(info[0])

    def check_buffer(self):
        # this will check the current status of the buffer to determine
        # whether there is sufficient data to send to the DB:
        # 1: snippet is long enough
        # 2: no artifacts (i.e. saturation)
        pass

    def run_buffer(self):
        # collect NSP data
        # data is a list of lists.
        # 1st level is a list of channels
        # 2nd level is a list [chan_id, np.array(data)]
        data = self.cbsdk_conn.get_continuous_data()

        # check for new depth
        if not self.depth_inlet:
            self.resolve_stream()
        else:
            sample = self.depth_inlet.pull_sample(0)
            # If new sample
            if sample[0]:
                # New depth
                if sample[0][0] != self.current_depth:
                    print('in_use')
                    self.buffer.fill(0)
                    self.buffer_idx = 0
                    self.update_buffer_status = True
                    self.current_depth = sample[0][0]

        if self.update_buffer_status:
            # append NSP data
            if len(data) > 0:
                data_length = data[0][1].shape[0]
                # if self.buffer_idx + data_length > self.buffer_length:
                #    self.check_buffer()
                #    self.buffer_idx = 0
                # else:
                for idx, dat in enumerate(data):
                    self.buffer[idx, self.buffer_idx:self.buffer_idx + data_length] = dat[1]
                self.buffer_idx += data_length

            # check if data length > sample length
            if self.buffer_idx >= self.sample_length:
                plt.plot(self.buffer[0, :])
                plt.show()

                print('done')
                self.update_buffer_status = False
                self.buffer_idx = 0
                self.buffer.fill(0)


if __name__ == '__main__':
    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import QTimer

    qapp = QApplication(sys.argv)
    worker = NSPBufferWorker()
    timer = QTimer()
    timer.timeout.connect(worker.run_buffer)
    timer.start(1)

    if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
        QApplication.instance().exec_()
