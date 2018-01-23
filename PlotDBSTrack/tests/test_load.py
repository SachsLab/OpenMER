import os
import platform
import sys
import time
import numpy as np
from scipy import signal
import pyfftw.interfaces.numpy_fft as fft
import brpylib
import quantities as pq
from neo.io.blackrockio import BlackrockIO
from utilities import segment_consecutive
from filterbank import FastFilterBank

DEF_SEG_INTERVAL = [0.5, 4.5] * pq.s

num_tap = 8000
hp_cutoff = 250
beta_cutoff = np.asarray([16, 30])
rms_thresh = 4.0
dec_factor = 50

class RMS_Analysis(object):

    def __init__(self, base_fn, load_method='brpy', dest=None):

        self.data_analysis = self.empty_data_dict() if dest is None else dest
        self.base_fn = base_fn[:-1] if base_fn[-1] == '-' else base_fn

        load_ = self.load_blackrock_data_brpy if load_method=='brpy' else self.load_blackrock_data_neo
        self.data_dict = load_(self.base_fn)

        self.fs = self.data_dict['samp_per_s']

        nyquist = self.fs / 2
        Nch = self.data_dict['ana_data'].shape[0]

        self.hfir1 = signal.firwin(num_tap + 1, hp_cutoff, nyq=nyquist, pass_zero=False)
        self.hfir0 = signal.firwin(num_tap + 1, (2, hp_cutoff), nyq=nyquist, pass_zero=True)

    def process(self, version=1):

        if version:
            b_new_depth = np.diff(np.hstack((-np.inf, self.data_dict['ev_depths']))) > 0
            b_long_enough = np.hstack((np.diff(self.data_dict['ev_times'][b_new_depth]) > DEF_SEG_INTERVAL[1], False))
            self.data_analysis['depth'] = self.data_dict['ev_depths'][b_new_depth][b_long_enough]

            seg_start_ix = np.where(b_new_depth)[0][b_long_enough]
            seg_stop_ix = np.hstack((np.where(b_new_depth)[0][1:],self.data_dict['ev_times'].size))[b_long_enough]
            n_segs = len(seg_start_ix)

            for seg_ix in range(n_segs):

                seg_start_time = self.data_dict['ev_times'][seg_start_ix[seg_ix]]
                seg_stop_time = self.data_dict['ev_times'][seg_stop_ix[seg_ix]] - (1/self.fs)
                b_seg = np.logical_and(self.data_dict['ana_times'] >= seg_start_time, self.data_dict['ana_times'] < seg_stop_time)
                sig  = self.data_dict['ana_data'][:, b_seg]
                tvec = self.data_dict['ana_times'][b_seg]
                tvec -= tvec[0]
                b_interval = np.logical_and(tvec >= DEF_SEG_INTERVAL[0], tvec < (DEF_SEG_INTERVAL[1] - 0.5/self.fs))

                seg_spk = np.atleast_2d(olafilt(self.hfir1, sig[:, b_interval], zi=None))[:,num_tap//2:]
                seg_psd = np.atleast_2d(olafilt(self.hfir0, sig[:, b_interval], zi=None))[:,num_tap//2:][:, ::dec_factor]

                lo = self.ffb0.process(sig[:, b_interval])
                hi = self.ffb1.process(sig[:, b_interval])

                self.data_analysis['spk'].append(seg_spk)
                self.data_analysis['tvec'].append(self.data_dict['ana_times'][b_seg][b_interval][num_tap//2:])

                # Calculate the RMS of the highpass
                seg_rms = np.sqrt(np.mean(seg_spk ** 2, axis=-1))
                self.data_analysis['rms'].append(seg_rms)

        else:

            self.segment_data_by_depth(num_depth=100)
            t0 = time.time()
            for i, sig in enumerate(self.signals):
                ix  = np.arange(sig.shape[-1])
                idx = np.logical_and(ix >= .5 * self.fs, ix < 4.5 * self.fs)

                seg_spk = np.atleast_2d(olafilt(self.hfir1, sig[:,idx], zi=None))[:,5000:]
                seg_psd = np.atleast_2d(olafilt(self.hfir0, sig[:,idx], zi=None))[:,5000:][:,::dec_factor]

                if seg_spk.shape[-1] >= self.fs * pq.s * 4 - 5000:

                    self.data_analysis['spk'].append(seg_spk)
                    self.data_analysis['depth'].append(self.depths[i])
                    self.data_analysis['tvec'].append(self.tvecs[i][idx][5000:])

                    # Calculate the RMS of the highpass
                    seg_rms = np.sqrt(np.mean(seg_spk ** 2, axis=-1))
                    self.data_analysis['rms'].append(seg_rms)

            print(time.time()-t0)
        self.data_analysis['spk'] = np.asarray(self.data_analysis['spk'])
        self.data_analysis['rms'] = np.asarray(self.data_analysis['rms'])

        if (len(self.data_analysis['labels']) > 0) and (self.data_analysis['labels'] != self.data_dict['chan_labels']):
            # TODO: Raise error that channel labels do not match across files.
            return self.data_analysis
        else:
            self.data_analysis['labels'] = self.data_dict['chan_labels']

        return self.data_analysis

    def segment_data_by_depth(self, num_depth=100):

        t   = self.data_dict['ana_times']
        sig = self.data_dict['ana_data']
        dtt = self.data_dict['ev_depths']
        dtt_sample_ix = np.asarray(self.data_dict['ev_times'] * self.fs * pq.s, dtype=np.int32)

        label = np.nonzero(dtt[:-1]-dtt[1:])[0]
        tmp = np.ones(dtt.size, dtype=bool)
        tmp[label] = False
        label = tmp.copy()
        label_sorted = segment_consecutive(np.nonzero(label)[0], stepsize=3)

        count = 0
        self.tvecs   = np.zeros((num_depth,), dtype=object) * np.nan
        self.signals = np.zeros((num_depth,), dtype=object) * np.nan
        self.depths  = np.zeros((num_depth,)) * np.nan
        for v in label_sorted:
            ix0, ix1 = dtt_sample_ix[v[0]], dtt_sample_ix[v[-1]]
            if (ix1-ix0)/self.fs > 3:
                self.signals[count] = sig[:,ix0:ix1]
                self.tvecs[count]   = t[ix0:ix1]
                self.depths[count]  = np.round(dtt[v[0]], 3)
                count += 1

        self.signals = self.signals[np.equal(np.zeros(self.depths.size, dtype=bool),np.isnan(self.depths))]
        self.tvecs  = self.tvecs[np.equal(np.zeros(self.depths.size, dtype=bool),np.isnan(self.depths))]
        self.depths  = self.depths[np.equal(np.zeros(self.depths.size, dtype=bool),np.isnan(self.depths))]

    @staticmethod
    def load_blackrock_data_neo(base_fn):
        neo_io = BlackrockIO(filename=base_fn)
        neo_block = neo_io.read_block(lazy=False, cascade=True,
                                      n_starts=None, n_stops=None, channels='all',
                                      nsx_to_load=5, scaling='voltage',
                                      units='none', load_waveforms=False, load_events=True)

        return {'ana_times': neo_block.segments[0].analogsignals[0].times,
                'ana_data': np.asarray([x for x in neo_block.segments[0].analogsignals])[:, :, 0],
                'samp_per_s': neo_block.segments[0].analogsignals[0].sampling_rate,
                'chan_labels': [x.name.decode('utf8') for x in neo_block.segments[0].analogsignals],
                'ev_times': neo_block.segments[0].events[0].times,
                'ev_depths': np.asarray([float(x.split(':')[1]) for x in neo_block.segments[0].events[0].labels])}


    @staticmethod
    def load_blackrock_data_brpy(base_fn):
        data_ = {'nsx': [], 'nev': []}
        file_ = {'nsx': [], 'nev': []}
        file_['nsx'] = brpylib.NsxFile(base_fn + '.ns5')
        data_['nsx'] = file_['nsx'].getdata(elec_ids='all', start_time_s=0, data_time_s='all', downsample=1)
        file_['nsx'].close()

        file_['nev'] = brpylib.NevFile(base_fn + '.nev')
        data_['nev'] = file_['nev'].getdata(elec_ids='all', get_waveforms=False)
        file_['nev'].close()

        fs = data_['nsx']['samp_per_s']
        return {'ana_times': (1 + np.arange(data_['nsx']['data_headers'][0]['NumDataPoints'])) / fs * pq.s,
                'ana_data': data_['nsx']['data'],
                'samp_per_s': fs * (1/pq.s),
                'chan_labels': [x['ElectrodeLabel'] for x in file_['nsx'].extended_headers],
                'ev_times': np.asarray(data_['nev']['comments']['TimeStamps']) / fs * pq.s,
                'ev_depths': np.asarray([float(tmp.split(':')[-1]) for tmp in data_['nev']['comments']['Comment']])}

    @staticmethod
    def empty_data_dict():
        return {'labels': [], 'spk': [], 'tvec': [], 'depth': [],
                'rms': [], 'n_spikes': [], 'spec_den': [], 'f': [],
                'pac': [], 'comod': []}

def olafilt(b, x, axis=-1, zi=None):
    ax0, ax1 = x.shape

    L_I = b.shape[0]
    # Find power of 2 larger that 2*L_I (from abarnert on Stackoverflow)
    L_F = 2<<(L_I-1).bit_length()
    L_S = L_F - L_I + 1
    L_sig = x.shape[axis]
    offsets = range(0, L_sig, L_S)

    # blockwise frequency domain multiplication
    if np.iscomplexobj(b) or np.iscomplexobj(x):
        FDir = np.fft.fft(b, n=L_F)
        tempresult = [np.fft.ifft(np.fft.fft(x[:, n:n+L_S], n=L_F, axis=-1)*FDir[np.newaxis, :])
                      for n in offsets]
        res = np.zeros(ax0, L_sig+L_F, dtype=np.complex128)
    else:
        FDir = np.fft.rfft(b, n=L_F)
        tempresult = [np.fft.irfft(np.fft.rfft(x[:, n:n+L_S], n=L_F, axis=-1)*FDir[np.newaxis, :])
                      for n in offsets]
        res = np.zeros((ax0, L_sig+L_F))

    # overlap and add
    for i, n in enumerate(offsets):
        res[:, n:n+L_F] += tempresult[i]

    if zi is not None:
        res[:, :zi.shape[0]] = res[:, :zi.shape[0]] + zi
        return res[:, :L_sig], res[:, L_sig:]
    else:
        return res[:, :L_sig]


if __name__ == '__main__':

    fn = "/Users/dlu/Developer/dbs_projects/data_collected/experiment_br_20170419/20170419-153633-001/20170419-153633-001"
    dta = DBSTrackAnalysis(base_fn=fn)
    dta.process(version=1)
