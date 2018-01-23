import numpy as np

def rms(x):
    """
    The root mean square of a signal.

    Parameters
    ----------
    x: array_like
        An array of input sequence.

    Returns
    -------
    out: float
        A root mean square of the signal.
    """
    return np.sqrt(np.mean(x**2))

def rmse(x1, x2):
    """
    The root mean square error between two signals.

    Parameters
    ----------
    x1: array_like
        An array of input sequence.

    x2: array_like
        Another array of input sequence.

    Returns
    -------
    out: float
        The root mean square error between the two input sequences.
    """
    return rms(x1-x2)

def nrmse(x1, x2):
    """
    The normalized root mean square error between two signals.

    Parameters
    ----------
    x1: array_like
        An array of input sequence.

    x2: array_like
        Another array of input sequence.

    Returns
    -------
    out: float
        The normalized root mean square error between the two input sequences.
    """
    return rms(x1-x2) / rms(x1)

def group_by(x, n=10):
    """
    Group a sequence by a number of iteration.
    """
    l = x.shape[0]
    remain = np.mod(l, n)
    if remain != 0:
        padding = np.zeros((n-remain))
        x = np.hstack([x, padding])

    w = x.shape[0] / n
    return [x[i*w:(i+1)*w] for i in xrange(n)]

# ====================================================
# ========== Pre-Process for Finding Artefact ========
# ====================================================
def segment_consecutive(data, stepsize=100):
    """
    Group data that has consecutive segments with increment < stepsize together.

    Parameters
    ----------
    signal: a single channel numpy array
    stepsize: the threshold specifying the difference between each increment

    Returns
    -------
    sub-arrays: list of ndarrays
        A list of sub-arrays grouped with consecutive signal, where the difference in the increment is specified by the stepsize.

    Examples
    --------
    >>> x = np.arange(100)
    >>> x[50:60] = np.arange(10) * 5
    >>> new_x = util.segment_consecutive(x, stepsize=10)
    >>> print new_x
    [array([ 0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15, 16,
            17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33,
            34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49]),
     array([ 0,  5, 10, 15, 20, 25, 30, 35, 40, 45]),
     array([60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76,
            77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93,
            94, 95, 96, 97, 98, 99])]
    """
    return np.split(data, np.where(np.abs(np.diff(data)) >= stepsize)[0]+1)

def artifact_flat(signal, replace_by_value=None, minGap=1, thres=1e-8):
    """
    Locate where the samples in the signal that are flat.

    Parameters
    ----------
    signal: Single channel numpy array
    replace_by_value: The value for replacing the flat samples
                      Default - None returns the labels only

    Returns
    -------
    signal: The new signal replacing the original one
      or
    label:  An array of boolean representing where the signal is flat
    """
    # label True for the flat samples
    #TODO: fix the minGap property such that it captures all the points.

    sig = signal.copy()
    label = (np.abs(sig - np.roll(sig, -minGap)) < thres) & (np.abs(signal - np.roll(signal, minGap)) < thres)
    labelTransition = np.roll(label, -minGap) & -np.roll(label, minGap) | np.roll(label, minGap) & -np.roll(label, -minGap)
    label[labelTransition] = True # mark all transitioning point as True

    if replace_by_value or replace_by_value == 0:
        sig[label] = replace_by_value
        return sig
    else:
        return label
