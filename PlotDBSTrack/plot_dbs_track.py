import os
import numpy as np
import brpylib
import matplotlib.pyplot as plt
from scipy import signal

record_number = '001'
data_folder = '20170419-153633'
seg_interval = [0.5, 4.5]
hp_cutoff = 250
beta_cutoff = np.asarray([16, 30])
rms_thresh = 4.0
dec_factor = 10
data_root = os.path.abspath(os.path.join(os.getcwd(), '..', '..', '..', '..', 'DBSData'))

nev_fn = os.path.join(data_root, data_folder, data_folder + '-' + record_number + '.nev')
nsx_fn = os.path.join(data_root, data_folder, data_folder + '-' + record_number + '.ns5')

nsx_file = brpylib.NsxFile(nsx_fn)
nsx_dict = nsx_file.getdata(elec_ids='all', start_time_s=0, data_time_s='all', downsample=1)
nsx_file.close()
fs = nsx_dict['samp_per_s']
si = 1 + np.arange(nsx_dict['data_headers'][0]['NumDataPoints'])
t = si / fs
nyquist = fs / 2
seg_sub_ind = np.arange(seg_interval[0] * fs, seg_interval[1] * fs, dtype=np.uint32)
seg_sub_ind_lfp = np.arange(seg_interval[0] * fs / dec_factor, seg_interval[1] * fs / dec_factor, dtype=np.uint32)

nev_file = brpylib.NevFile(nev_fn)
nev_dict = nev_file.getdata(elec_ids='all')
nev_file.close()

comm_ts = np.asarray(nev_dict['comments']['TimeStamps'])
comm_str = nev_dict['comments']['Comment']
comm_depths = np.asarray([float(x.split(':')[1]) for x in comm_str])
b_new_depth = np.hstack((False, np.diff(comm_depths) > 0))
b_long_enough = np.hstack((np.diff(comm_ts[b_new_depth]) >= (seg_interval[1] * fs), False))
seg_start_ts = comm_ts[b_new_depth][b_long_enough]
seg_stop_ts = comm_ts[b_new_depth][np.where(b_long_enough)[0] + 1] - 1
seg_start_depth = comm_depths[b_new_depth][b_long_enough]

# Analyze nsx_dict
sig = nsx_dict['data']

# HP filter raw data
sos_spk = signal.butter(8, hp_cutoff / nyquist, btype='highpass', output='sos')
data_spk = signal.sosfiltfilt(sos_spk, sig, axis=1)

# Beta filter data
sos_beta = signal.butter(8, beta_cutoff / nyquist, btype='bandpass', output='sos')
data_beta = signal.sosfiltfilt(sos_beta, sig, axis=1)

# Downsample for LFP spectra
data_lfp = signal.decimate(sig, dec_factor, axis=1, zero_phase=True)

rms = []
n_spikes = []
spec_den = []
# For each segment
for seg_ix in range(len(seg_start_ts)):
    b_seg = np.logical_and(si >= seg_start_ts[seg_ix], si <= seg_stop_ts[seg_ix])
    seg_sig = sig[:, b_seg][:, seg_sub_ind]

    # Calculate the RMS of the highpass
    seg_spk = data_spk[:, b_seg][:, seg_sub_ind]
    seg_rms = np.sqrt(np.mean(seg_spk**2, axis=1))
    rms.append(seg_rms)

    # Find threshold crossing events at rms_thresh * seg_rms
    seg_spk_offset = seg_spk + (rms_thresh * seg_rms[:, np.newaxis])
    b_spike = np.hstack((np.zeros((seg_spk_offset.shape[0], 1), dtype=np.bool),
                         np.logical_and(seg_spk_offset[:, :-1] >= 0, seg_spk_offset[:, 1:] < 0)))
    n_spikes.append(np.sum(b_spike, axis=1))

    # Calculate the spectrum
    b_seg_lfp = np.logical_and(si[::dec_factor] >= seg_start_ts[seg_ix], si[::dec_factor] <= seg_stop_ts[seg_ix])
    f, Pxx_den = signal.periodogram(data_lfp[:, b_seg_lfp][:, seg_sub_ind_lfp], fs / dec_factor, axis=1)
    # plt.semilogy(f, Pxx_den.T)
    spec_den.append(Pxx_den)

    # TODO: For each segment, calculate phase amplitude coupling (data_beta for phase bins, count threshold crossing events in each bin)

plt.subplot(311)
# TODO: Make stem plot
plt.plot(seg_start_depth, np.asarray(rms))
plt.subplot(312)
plt.plot(seg_start_depth, np.asarray(n_spikes))

n_chans = data_lfp.shape[0]
depthfreq = np.asarray(spec_den)
for chan_ix in range(n_chans):
    plt.subplot(3, n_chans, 2 * n_chans + chan_ix + 1)
    img_dat = np.squeeze(np.log10(depthfreq[:, chan_ix, f < 100]))
    plt.imshow(img_dat, aspect='auto', vmin=np.min(img_dat[:, 2:]), vmax=np.max(img_dat[:, 2:]),
               extent=[f[0], f[f < 100][-1], seg_start_depth[0], seg_start_depth[-1]])  # , cmap=plt.get_cmap('plasma')
    plt.gca().invert_yaxis()

