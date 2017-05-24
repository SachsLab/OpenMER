# Just some chunks of code to help with development.
import sys, os
import time
dbsgui_path = os.path.abspath(os.path.join('..', 'NeuroportDBS', 'DBSGUI'))
sys.path.append(dbsgui_path)
from cbsdkConnection import CbSdkConnection

SAMPLINGGROUPS = ["0", "500", "1000", "2000", "10000", "30000", "RAW"]

cbsdk_conn = CbSdkConnection(simulate_ok=False)
cbsdk_conn.connect()
cbsdk_conn.cbsdk_config = {
    'reset': True, 'get_events': False, 'get_comments': False, 'get_continuous': False,
    'buffer_parameter': {
        'comment_length': 0
    }
}
group_info = cbsdk_conn.get_group_config(SAMPLINGGROUPS.index("30000"))
sys_config = cbsdk_conn.get_sys_config()

# temp_ev = cbsdk_conn.get_event_data()
# temp_cont = cbsdk_conn.get_continuous_data()

chid = group_info[0]['chan']
n_valid = [0 for gi in group_info]
for get_ix in range(10):
    # for gi_ix in range(len(group_info)):
    gi_ix = 0
    temp_wfs, unit_ids, n_valid[gi_ix] = cbsdk_conn.get_waveforms(group_info[gi_ix]['chan'],
                                                                  valid_since=n_valid[gi_ix],
                                                                  spike_samples=sys_config['spklength'])
    print("chid: {}, n_spikes: {}, n_valid: {}".format(group_info[gi_ix]['chan'], temp_wfs.shape[0], n_valid[gi_ix]))
    time.sleep(1)
print("done")

# import matplotlib.pyplot as plt
# plt.ion()
# plt.plot(temp_wfs.T)

cbsdk_conn.disconnect()
