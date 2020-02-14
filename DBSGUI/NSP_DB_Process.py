import os
import sys
import numpy as np
from cerebuswrapper import CbSdkConnection
from pylsl import stream_inlet, resolve_byprop
import datetime
import time
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

    def __init__(self, subject_id=12, buffer_length=6.0, sample_length=4.0, settings=dict()):
        super(NSPBufferWorker, self).__init__()

        # process inputs
        self.subject_id = subject_id
        # TODO: not hard-code the sampling rate?
        self.buffer_length = int(buffer_length * 30000)
        self.sample_length = int(sample_length * 30000)
        self.settings = settings

        # try to resolve LSL stream
        self.depth_inlet = None
        self.resolve_stream()

        # DB wrapper
        self.subject_id = subject_id
        self.db_wrapper = DB_Wrap.DBWrapper()
        self.db_wrapper.load_subject_from_id(subject_id)

        # cbSDK; connect using default parameters
        self.cbsdk_conn = CbSdkConnection(simulate_ok=False)
        self.cbsdk_conn.connect()

        # neural data buffer
        self.group_info = self.cbsdk_conn.get_group_config(SAMPLINGGROUPS.index("30000"))
        self.n_chan = len(self.group_info)

        # for each channel we will keep a bool array whether each sample point is valid or not
        # when a condition is met to trigger sending the sample to the DB we will pick the window
        # with highest validity count.
        self.start_time = datetime.datetime.now()
        self.buffer = np.zeros((self.n_chan, self.buffer_length), dtype=np.int16)
        self.validity = np.zeros((self.n_chan, self.buffer_length), dtype=bool)
        self.clear_buffer()

        # if a segment has >= 90% valid points, will keep
        self.threshold = [False] * self.n_chan
        self.validity_threshold = [self.sample_length * .9] * self.n_chan
        for ii, info in enumerate(self.group_info):
            label = info['label'].decode('utf-8')
            if label in self.settings:
                self.threshold[ii] = bool(self.settings[label][0])
                self.validity_threshold[ii] = float(self.settings[label][1]) / 100 * self.sample_length

        # electrode depth
        self.current_depth = 0.000

    def clear_buffer(self):
        self.buffer.fill(0)
        self.buffer_idx = 0

        self.validity.fill(False)
        # list of tuples: (index of validity value, value)
        # saves the index with largest validity across all channels
        self.valid_idx = (0, 0)

        self.update_buffer_status = True
        self.start_time = datetime.datetime.now()

    def resolve_stream(self):
        # will register to LSL stream to read electrode depth
        info = resolve_byprop('source_id', 'depth1214', timeout=1)
        if len(info) > 0:
            self.depth_inlet = stream_inlet(info[0])

    def run_buffer(self):
        # collect NSP data
        # data is a list of lists.
        # 1st level is a list of channels
        # 2nd level is a list [chan_id, np.array(data)]
        data = self.cbsdk_conn.get_continuous_data()

        if data and self.update_buffer_status:

            # all data segments should have the same length, so first check if we run out of buffer space
            data_length = data[0][1].shape[0]
            if (self.buffer_idx + data_length) >= self.buffer_length:
                # if we run out of buffer space before data has been sent to the DB few things could have gone wrong:
                #   - data in buffer is not good enough
                #   - the new data chunk is larger than the difference between buffer and sample length
                #       (e.g. 6s buffer and 4s sample, if the current buffer has 3s of data and it receives a 4s
                #       long chunk then the buffer would overrun, and still not have enough data to send to DB.
                #       Although unlikely in real-life, it happened during debugging.)

                # trim data to only fill the buffer, discarding the rest
                # TODO: is this the optimal solution? Slide buffer instead?
                data_length = self.buffer_length - self.buffer_idx

            # continue to validate received data
            for chan_idx, (chan, values) in enumerate(data):

                if data_length > 0:
                    # Validate data
                    valid = self.validate_data_sample(values[:data_length])

                    # append data to buffer
                    self.buffer[chan_idx,
                                self.buffer_idx:self.buffer_idx + data_length] = values[:data_length]

                    self.validity[chan_idx,
                                  self.buffer_idx:self.buffer_idx + data_length] = valid

            # increment buffer index, all data segments should have same length, if they don't, will match the first
            # channel
            self.buffer_idx += data_length

            # check if data length > sample length
            if self.buffer_idx >= self.sample_length:

                # compute total validity of last sample_length and if > threshold, send to DB
                sample_idx = self.buffer_idx - self.sample_length

                temp_sum = [np.sum(x[sample_idx:self.buffer_idx]) for x in self.validity]

                # check if validity is better than previous sample, if so, store it
                if np.sum(temp_sum) > self.valid_idx[1]:
                    self.valid_idx = (sample_idx, np.sum(temp_sum))

                if all(x >= y for x, y in zip(temp_sum, self.validity_threshold)) or \
                        self.buffer_idx >= self.buffer_length:
                    self.send_to_db()

        # check for new depth
        # At this point, the individual channels have either been sent to the DB or are still collecting waiting for
        # either of the following conditions: acquire sufficient data (i.e. sample_length) or acquire sufficiently clean
        # data (i.e. validity_threshold). If the channel is still acquiring data but has sufficiently long segments, we
        # will send the cleanest segment to the DB (i.e. valid_idx).
        if not self.depth_inlet:
            self.resolve_stream()
        else:
            sample = self.depth_inlet.pull_sample(0)
            # If new sample
            if sample[0]:
                # New depth
                if sample[0][0] != self.current_depth:
                    # check whether the channels are still acquiring data
                    # it can be because they have insufficient samples or because the samples do not have a high enough
                    # validity value. If this is the case, send the best one to the DB, even if possibly corrupted
                    if self.update_buffer_status:
                        self.send_to_db()

                    self.clear_buffer()
                    self.current_depth = sample[0][0]
                    print('in_use')

    def send_to_db(self):
        # TODO: actually send to DB
        # if we actually have a computed validity (i.e. segment is long enough)
        if self.valid_idx[1] != 0:
            # the info that needs to be sent the DB_wrapper is:
            #   Datum:
            #       - subject_id
            #       - is_good : to be determined by validity values
            #       - start_time / stop_time ?
            #   Datum Store:
            #       - channel_labels : from group_info
            #       - erp : actual data
            #       - n_channels and n_samples : determined by data size
            #       - x_vec: time ?
            #   DatumDetailValue:
            #       - detail_type: depth (fetch from DetailType
            #       - value: depth value
            self.db_wrapper.create_depth_datum(depth=self.current_depth,
                                               data=self.buffer[:,
                                                                self.valid_idx[0]:self.valid_idx[0]+self.sample_length],
                                               is_good=all(x >= y for x, y in zip(
                                                   np.sum(self.validity[:, self.valid_idx[0]:
                                                          self.valid_idx[0] + self.sample_length], axis=1),
                                                   self.validity_threshold)),
                                               group_info=self.group_info,
                                               start_time=self.start_time,
                                               stop_time=datetime.datetime.now())

            for data in self.buffer:
                plt.plot(data[self.valid_idx[0]:self.valid_idx[0] + self.sample_length])

            for data in self.validity:
                a = data[self.valid_idx[0]:self.valid_idx[0] + self.sample_length]
                plt.plot([50000 + (10000 * int(x)) for x in a])

            plt.title(str(self.current_depth) + " " + str(self.valid_idx[1]) + " " + str(self.buffer_idx))
            plt.show()
            # send 'done' to turn signal green.
            print('done')
        self.update_buffer_status = False

    @staticmethod
    def validate_data_sample(data):
        # TODO: implement other metrics
        # SUPER IMPORTANT: when cbpy returns an int16 value, it can be -32768, however in numpy:
        #     np.abs(-32768) = -32768 for 16 bit integers since +32768 does not exist.
        # We therefore can't use the absolute value for the threshold.
        threshold = 30000  # arbitrarily set for now
        validity = np.array([-threshold < x < threshold for x in data])

        return validity


if __name__ == '__main__':
    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import QTimer

    time.sleep(5)

    # parse arguments
    if len(sys.argv) >= 5:
        qapp = QApplication(sys.argv)
        electrode_settings = {}
        idx = 4
        while idx + 2 < len(sys.argv):
            electrode_settings[sys.argv[idx]] = [sys.argv[idx + 1], sys.argv[idx + 2]]
            idx += 3

        worker = NSPBufferWorker(subject_id=int(sys.argv[1]),
                                 buffer_length=float(sys.argv[2]),
                                 sample_length=float(sys.argv[3]),
                                 settings=electrode_settings)
        timer = QTimer()
        timer.timeout.connect(worker.run_buffer)

        timer.start(10)

        if (sys.flags.interactive != 1) or not hasattr(qtpy.QtCore, 'PYQT_VERSION'):
            QApplication.instance().exec_()
