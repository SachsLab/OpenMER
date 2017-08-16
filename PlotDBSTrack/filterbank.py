import numpy as np
from scipy.signal import firwin
import pyfftw.interfaces.numpy_fft as fft

from parallel import Parallel

class FastFilterBank(object):
    def __init__(self, **kwargs):
        self.update(**kwargs)

    def __del__(self):
        if self.n_processes > 1:
            self.kill()

    def kill(self, opt=None): # kill the multiprocess
        self.pfunc.kill(opt=opt)

    def update(self, nprocs     = 1,
                     factor     = None,
                     bw_hz      = None,
                     foi_hz     = None,
                     fs_hz      = None,
                     f_ord      = None,
                     ftype      = None,
                     n_freqs    = None,
                     n_samples  = None,
                     n_channels = None):

        self.n_channels  = n_channels if n_channels is not None else self.n_channels
        self.n_freqs     = n_freqs if n_freqs is not None else self.n_freqs
        self.n_processes = min(Parallel.check_nprocs()-1, self.n_freqs) if nprocs != 1 else 1

        # Signal process properties
        self.decimate_by = factor
        self.n_samples   = int(n_samples / self.decimate_by)
        self.sample_rate = fs_hz / self.decimate_by if fs_hz is not None else self.sample_rate

        self.bandwidth = bw_hz if bw_hz is not None else self.bandwidth

        self.w_, self.H_ = self.create_filter(f_ord, self.bandwidth / 2.0, self.sample_rate/2.0, self.n_samples, ftype='fir', output='freq')
        self.Hwin = self.H_[np.logical_and(self.w_>=-self.bandwidth / 2.0, self.w_<self.bandwidth / 2.0)]

        self.n_samples_procs = self.Hwin.size

        # Setup center frequencies
        if len(foi_hz) > 1:
            cf = np.arange(*foi_hz, np.diff(foi_hz)/self.n_freqs, dtype=int)
            diff = cf.shape[0] - self.n_freqs
            if diff > 0:
                cf = cf[:-diff]
        else:
            cf = foi_hz

        self.freqs = np.asarray([(f-self.bandwidth/2, f+self.bandwidth/2) for f in cf])
        print(self.freqs)
        print(self.freqs.shape)
        # Create rules for how to handle the data
        self._encoder_rule()
        self._decoder_rule()

        if self.n_processes > 1:
            self.pfunc = Parallel(self.multiply,
                            nprocs=self.n_processes, axis=0, flag=0,
                            ins_shape=[(self.n_channels, self.n_freqs, self.n_samples_procs), (1, self.n_samples_procs)], ins_dtype=[np.complex64, np.complex64],
                            out_shape= (self.n_channels, self.n_freqs, self.n_samples_procs), out_dtype=np.complex64)

    def process(self, signal, encode_type='full', axis=-1, planner_effort='FFTW_ESTIMATE'):

        tmp = self._encoder(signal, self.decimate_by)
        return self._decoder(tmp, result=encode_type)

    def _encoder(self, x, decimate, axis=-1, planner_effort='FFTW_ESTIMATE'):
        """
        Transform the time series data into a multiple sub-banded demodulated signal in frequency domain.
        """
        Nch, Nsamp = x.shape
        Nsamp_dec  = int(Nsamp / decimate)

        X = fft.fft(x, axis=axis, planner_effort=planner_effort)

        if Nsamp % 2 == 0:
            X[:,1:Nsamp//2] *= 2
            X[:,Nsamp//2:]   = 0
        else:
            X[:,1:(Nsamp + 1)//2] *= 2
            X[:,(Nsamp + 1)//2]    = 0

        X_ = fft.fftshift(X, axes=-1)[:,int((Nsamp-Nsamp_dec)//2):int((Nsamp+Nsamp_dec)//2)] / decimate

        if self.n_processes > 1:
            func = self.pfunc.result
        else:
            func = self.multiply

        return func(X_[:,self.encoder_rule], np.atleast_2d(self.Hwin))

    def _decoder(self, x_encoded, result='full', axis=-1, planner_effort='FFTW_ESTIMATE'):
        """
        Transform the encoded data back to time series.
        result = 'full': return to original modulating frequencies for each sub-band.
        result = 'auto': return to the lowest modulating frequencies for each sub-band.
        """
        Nch, Nf, Nsamp = x_encoded.shape
        if result == 'full':
            out = np.zeros((Nch, self.n_freqs, self.n_samples), dtype=np.complex64)
            out[:, self.decoder_rule, self.encoder_rule] = x_encoded
            out = fft.fftshift(out, axes=axis)
            return fft.ifft(out, axis=axis, planner_effort=planner_effort)
        elif result == 'auto':
            out = x_encoded
            out = fft.fftshift(out, axes=axis)
            out = np.roll(out, int(self.bandwidth//2 * (self.n_samples//self.sample_rate)))

            return fft.ifft(out, n=self.n_samples, axis=axis, planner_effort=planner_effort)

    def _encoder_rule(self):
        """
        Looking only at frequency domain.
        Shifts all sub-banded signals to center at 0 Hz.
        """
        # Shifting indices in frequency domain
        idx0     = np.logical_and(self.w_[:,np.newaxis]>=self.freqs[:,0][np.newaxis,:], self.w_[:,np.newaxis]<self.freqs[:,-1][np.newaxis,:]).T
        win_idx0 = np.ones((self.n_freqs,1)) * np.arange(self.n_samples)

        diff = int(self.n_freqs * self.n_samples_procs - win_idx0[idx0].size)
        if diff < 0:
            tmp =  win_idx0[idx0][:diff]
        elif diff > 0:
            tmp = np.hstack([win_idx0[idx0], np.arange(diff)])
        else:
            tmp = win_idx0[idx0]

        self.encoder_rule  = np.array(tmp.reshape(self.n_freqs, self.n_samples_procs), dtype=np.int64)

    def _decoder_rule(self):
        if not hasattr(self, 'encoder_rule'):
            self._encoder_rule()

        self.decoder_rule = np.array(np.arange(self.n_freqs)[:, np.newaxis] + np.zeros((1, self.Hwin.size)), dtype=np.int64)

    @staticmethod
    def multiply(x1, x2, axis=-1):
        return x1 * x2

    @staticmethod
    def create_filter(order, cutoff, nyquist, N, ftype='fir', output='freq', shift=True):
        """
        Create a prototype filter.
        """
        h = firwin(order, cutoff, nyq=nyquist)

        if output == 'freq':
            w = fft.fftfreq(N)
            w *= (nyquist*2)

            H    = fft.fft(h, n=N, axis=-1, planner_effort='FFTW_ESTIMATE')

            if shift:
                return fft.fftshift(w), fft.fftshift(H)
            else:
                return w, H

        else:
            return h

class FilterProcess(object):

    def __init__(self, filter_obj, method='ola', block_size=8000):

        self.block_size = block_size
        self.proc_size  = 2 << (self.block_size-1).bit_length()
        self.padded_len = self.proc_size - self.block_size + 1

        self.ffb = filter_obj

    def process(self, signal):

        offsets = range(0, self.ffb.n_samples, self.padded_len)

        out = np.zeros((signal.shape[0], self.ffb.n_freqs, self.ffb.n_samples+self.proc_size), dtype=np.complex64)
        for i, n in enumerate(offsets):
            tmpx = np.hstack([signal[:, n:n+self.padded_len], np.zeros((x1.shape[0], self.proc_size-signal[:, n:n+self.padded_len].shape[axis]))])
            tmp_res = self.ffb.process(tmpx)
            out[:,:,n:n+self.proc_size] += tmp_res

        return out[:,:,:self.ffb.n_samples]
