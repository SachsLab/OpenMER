# import numpy as np
#
# FS = 30000
# BETABAND = [13, 30]
# GAMMABAND = [60, 200]
#
#
# class PAC:
#
#     name = "PAC"
#     desc = """ Using MSPACMAN algorithm to compute Beta to high-gamma PAC. """
#     category = "DBS"
#
#     def __init__(self, db_id):
#         self.db_id = db_id
#
#         from pytf import FilterBank
#
#         # Create the filter banks
#         decimate_by = 20
#         fpsize = BETABAND[1] - BETABAND[0] + 1  # number of frequencies for phase
#         fasize = np.int(np.round((GAMMABAND[1] - GAMMABAND[0]) / 10) + 1)   # number of frequencies for amp
#
#         # from Dvorak and Fenton, JNeurosciMeth, 2014:
#         #     For accurate PAC estimation, standard PAC algorithms require amplitude filters with a bandwidth
#         #     at least twice the modulatory frequency. The phase filters must be moderately narrow-band, especially
#         #     when the modulatory rhythm is non-sinusoidal. The minimally appropriate analysis window is ∼10 s.
#         # As our highest beta band frequency is 30 Hz we set the gamma bandwidth to be 60Hz.
#         bw_p = 2  # band width phase
#         bw_a = 60  # band width amplitude
#
#         # Get the phase-giving and amplitude-enveloping signals for comodulogram
#         fp = np.linspace(BETABAND[0], BETABAND[1], fpsize)  # 13 - 30 Hz, 18 freqs; 1 Hz steps
#         fa = np.linspace(GAMMABAND[0], GAMMABAND[1], fasize)  # 60 - 200 Hz, 15 steps; 10Hz steps
#
#         fois_lo = np.asarray([(f - bw_p, f + bw_p) for f in fp])
#         fois_hi = np.asarray([(f - bw_a, f + bw_a) for f in fa])
#
#         self.los = FilterBank(binsize=2 ** 14,
#                               freq_bands=fois_lo,
#                               order=2 ** 12,
#                               sample_rate=FS,
#                               decimate_by=decimate_by,
#                               hilbert=True)
#
#         self.his = FilterBank(binsize=2 ** 14,
#                               freq_bands=fois_hi,
#                               order=2 ** 12,
#                               sample_rate=FS,
#                               decimate_by=decimate_by,
#                               hilbert=True)
#
#     def run(self, data):
#         from mspacman.algorithm.pac_ import (pad, pac_mi)
#         """
#         input datum store erp field and returns mean and peak MI value for Beta-high-gamma PAC.
#
#         :param data:
#             n_channel x n_samples numpy array
#         :return:
#             n_channel x 2 MI value [peak, average]
#         """
#         data = data * .25
#
#         x_los = self.los.analysis(data, window='hanning')
#         x_his = self.his.analysis(data, window='hanning')
#
#         angs, amps = np.angle(x_los), np.abs(x_his)
#
#         # Compute PAC
#         # phase-amplitude distribution (pad)
#         pds = pad(angs, amps, nbins=10)
#         # modulation indices: chan x los x his
#         mis = pac_mi(pds)
#
#         out_data = np.concatenate((np.atleast_2d(mis.max(axis=2).max(axis=1)).T,
#                                    np.atleast_2d(mis.mean(axis=2).mean(axis=1)).T), axis=1)
#
#         return out_data, np.zeros((out_data.shape[1],))
#
#
# if __name__ == '__main__':
#
#     fname = 'C:\\Users\\Doug\\Desktop\\data.npy'
#     data = np.fromfile(fname, dtype=np.int16)
#     data = data * 0.25
#     data = np.reshape(data, (3, 120000))
#     data = np.atleast_2d(data)
#     pac = PAC(1)
#
#     output = pac.run(data)
#
#     print(output)
#
#
#
