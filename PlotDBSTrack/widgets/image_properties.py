import numpy as np

def getRGBAFromCMap(x, c_inds, c_vals, mode='rgb'):
    """
    Args:
        x: value for which we want the colour float from 0 to 1
        c_inds: list of values at which the colormap is defined
        c_vals: list of PyQt4.QtGui.QColor for each of the above points
        mode: 'rgb' or 'hsv'
    Returns:
    """
    if x < np.min(c_inds):
        x = np.min(c_inds)

    ix_0 = (np.asarray(c_inds) <= x).nonzero()[0][0]
    x_0 = c_inds[ix_0]
    c_0 = c_vals[ix_0]

    if x >= np.max(c_inds):
        x = np.max(c_inds)
        ix_1 = c_inds.index(x)
    else:
        ix_1 = (np.asarray(c_inds) > x).nonzero()[0][0]
    x_1 = c_inds[ix_1]
    c_1 = c_vals[ix_1]
    dx = (x_1 - x_0)
    if dx == 0:
        f = 0.
    else:
        f = (x - x_0) / dx
    if mode == 'rgb':
        r = c_0.red() * (1. - f) + c_1.red() * f
        g = c_0.green() * (1. - f) + c_1.green() * f
        b = c_0.blue() * (1. - f) + c_1.blue() * f
        a = c_0.alpha() * (1. - f) + c_1.alpha() * f
        return r, g, b, a
    elif mode == 'hsv':
        h_0, s_0, v_0, _ = c_0.getHsv()
        h_1, s_1, v_1, _ = c_1.getHsv()
        h = h_0 * (1. - f) + h_1 * f
        s = s_0 * (1. - f) + s_1 * f
        v = v_0 * (1. - f) + v_1 * f
        c_out = QtGui.QColor()
        c_out.setHsv(h, s, v)
        return c_out.red(), c_out.green(), c_out.blue(), c_out.alpha()
    else:
        raise TypeError("mode must be 'rgb' or 'hsv'")


def getLUT(n_pts=512, cm_name='Spectral', cm_library='matplotlib', has_alpha=False):
    """

    :param n_pts:
    :param cm_name:
    :param cm_library:
    :param has_alpha:
    :return:
    """
    n_channels = 4 if has_alpha else 3
    lut = np.empty((n_pts, n_channels), dtype=np.ubyte)
    if cm_library == 'matplotlib':
        import matplotlib.cm as mplcm
        cmap = mplcm.get_cmap(cm_name)
        for i in range(n_pts):
            x = float(i) / (n_pts - 1)
            color = cmap(x)
            lut[i] = 255 * np.asarray(color[:n_channels])
    else:
        # pyqtgraph has its own colormap system but it is hidden deep inside its gradientEditor.
        # If we do not wish to invoke the gradientEditor then the code would look something like this.
        from pyqtgraph.Qt import QtGui
        from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
        grad_dict = Gradients[cm_name]
        c_inds = []
        c_vals = []
        for tick in grad_dict['ticks']:
            c_inds.append(tick[0])
            c_vals.append(QtGui.QColor(*tick[1]))
        c_inds, c_vals = zip(*sorted(zip(c_inds, c_vals)))  # Sort both accordings to c_inds
        for i in range(n_pts):
            x = float(i) / (n_pts - 1)
            lut[i] = getRGBAFromCMap(x, c_inds, c_vals, mode=grad_dict['mode'])[:n_channels]
    return lut
