import numpy as np

# use the same GUI format as the other ones
from qtpy.QtWidgets import QLabel, QGridLayout, QWidget, QVBoxLayout

from qtpy.QtGui import QColor, QFont

import pyqtgraph as pg
from dbsgui.my_widgets.custom import THEMES

pen_colors = THEMES['dark']['pencolors']

# Plot settings dictionaries
DEFAULTPLOT = {
    'title': None,
    'x_label': None,
    'y_label': None,
    'x_ticks': False,
    'y_ticks': False,
    'x_axis': True,  # Is Visible
    'y_axis': True,
    'x_range': None,  # None for auto-scale, list otherwise
    'y_range': [0, 1],
    'auto_scale': False,
    'interactive': True,
    'marker_line': 0.0,
    'error_bars': False,
    'pen_color': QColor(255, 255, 255),
    'text_anchor': (2, 0.5),
    # to get data
    'x_name': None,
    'y_name': None,
    'post_processing': None,
    'swap_xy': False
}
FEAT_VS_DEPTH = {**DEFAULTPLOT,
                 'x_range': [-20, 5],
                 'y_ticks': True,
                 'interactive': True,
                 'auto_scale': True,
                 'x_name': 'depth'}
DEPTH = {**DEFAULTPLOT,
         'x_range': [-5, 5],
         'x_axis': False,
         'y_range': [-20, 5],
         'y_name': 'depth',
         'y_ticks': True,
         'interactive': True,
         'swap_xy': True,
         'text_anchor': (0.5, 2)}


class BasePlotWidget(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(BasePlotWidget, self).__init__(*args, **kwargs)
        self.plot_config = plot_config
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.glw = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.glw)
        self.plot = self.glw.addPlot(enableMenu=False)
        self.line = None
        self.text = None

        self.data = {}

        self.configure_plot()

    def leaveEvent(self, QEvent):
        self.clear_text_line()
        super().leaveEvent(QEvent)

    def clear_text_line(self):
        if self.line:
            self.line.setValue(-999999)
        if self.text:
            self.text.setText('')
            self.text.fill.setColor(QColor(0, 0, 0, 0))
        [x.setSymbolSize(6) for x in self.plot.curves]

    def configure_plot(self):
        self.plot.setTitle(title=self.plot_config['title'], **{'color': 'w', 'size': '16pt'})
        if self.plot_config['marker_line'] is not None:
            self.plot.addItem(pg.InfiniteLine(angle=90,
                                              pos=self.plot_config['marker_line'],
                                              movable=False,
                                              pen='y'))
        self.plot.setMouseEnabled(x=False, y=False)
        if self.plot_config['x_range']:
            self.plot.setXRange(self.plot_config['x_range'][0], self.plot_config['x_range'][1], padding=0)
        if self.plot_config['y_range']:
            self.plot.setYRange(self.plot_config['y_range'][0], self.plot_config['y_range'][1], padding=0)
        self.plot.setLabel('bottom', self.plot_config['x_label'])
        self.plot.setLabel('left', self.plot_config['y_label'])
        if not self.plot_config['x_axis']:
            self.plot.hideAxis('bottom')
        if not self.plot_config['y_axis']:
            self.plot.hideAxis('left')
        font = QFont()
        font.setPixelSize(20)
        font.setBold(True)

        self.plot.getAxis('bottom').setStyle(showValues=self.plot_config['x_ticks'])
        self.plot.getAxis('bottom').tickFont = font
        self.plot.getAxis('bottom').setPen((255, 255, 255, 255))
        self.plot.getAxis('bottom').setStyle(tickTextOffset=10)

        self.plot.getAxis('left').setStyle(showValues=self.plot_config['y_ticks'])
        self.plot.getAxis('left').tickFont = font
        self.plot.getAxis('left').setPen((255, 255, 255, 255))

        if self.plot_config['interactive']:
            self.plot.scene().sigMouseMoved.connect(self.mouse_moved)
            if self.plot_config['swap_xy']:
                self.line = pg.InfiniteLine(angle=0,
                                            pos=-9999,
                                            movable=False,
                                            pen='w')
            else:
                self.line = pg.InfiniteLine(angle=90,
                                            pos=-9999,
                                            movable=False,
                                            pen='w')
            self.line.setZValue(5)
            self.plot.addItem(self.line)

            self.text = pg.TextItem(text='', color='w', fill=(0, 0, 0, 0))
            self.text.setAnchor(self.plot_config['text_anchor'])
            self.text.setX(0)
            self.text.setY(0.5)
            self.plot.addItem(self.text)
            self.text.setZValue(6)

    def mouse_moved(self, evt):
        plot_coord = self.plot.vb.mapSceneToView(evt)
        closest = -99999
        value = None
        curves = [x for x in self.plot.curves if x.opts['symbol']]
        if self.plot_config['swap_xy']:
            y_ = [(x.yData[0], x.setSymbolSize(6))[0] for x in curves]

            if y_:
                closest = min(y_, key=lambda x: abs(x - plot_coord.y()))
                idx = y_.index(closest)
                value = curves[idx].xData[0]
                curves[idx].setSymbolSize(12)

                self.text.setY(closest)
                self.text.setX(0)
        else:
            x_ = [(x.xData, x.setSymbolSize(6))[0] for x in curves]
            if x_:
                closest = min(x_, key=lambda x: abs(x - plot_coord.x()))[0]
                idx = x_.index(closest)
                value = curves[idx].yData[0]
                curves[idx].setSymbolSize(12)

                self.text.setX(closest)
                self.text.setY(0)
                # self.text.setY(value)

        self.line.setValue(closest)

        if value is not None:
            self.text.setText('x: ' + "{0:.3f}".format(closest) + '\n' + 'y: ' +
                              "{0:.3f}".format(value))
            self.text.fill.setColor(QColor(0, 0, 0, 175))

    def update_plot(self, all_data):
        if all_data is not None:
            # all_data is a dict {datum_id: [depth, np array of data]}
            for idx, data in all_data.items():
                # append data
                x = data[self.plot_config['x_name']] if self.plot_config['x_name'] in data else None

                if x not in [None, ''] and self.plot_config['y_name'] in data:
                    y = data[self.plot_config['y_name']]
                    self.data[x] = y

                    if y[2]:
                        symbol_brush = self.plot_config['pen_color']
                    else:
                        symbol_brush = None

                    # post_processing receives the entire feature value array, typically:
                    # [x, y, valid].
                    # should return an array with values to plot
                    if self.plot_config['post_processing'] and not self.plot_config['error_bars']:
                        y = self.plot_config['post_processing'](y)
                    elif self.plot_config['post_processing'] and self.plot_config['error_bars']:
                        y, eb = self.plot_config['post_processing'](y)
                        self.plot.addItem(pg.ErrorBarItem(x=[x], y=y, height=eb, pen=self.plot_config['pen_color']))
                    else:
                        y = y[1]

                    self.plot.plot(x=[x], y=y, symbol='o', symbolSize=6,
                                   symbolBrush=symbol_brush, symbolPen=self.plot_config['pen_color'])
                    if self.plot_config['auto_scale']:
                        self.plot.enableAutoRange(axis=pg.ViewBox.YAxis)

    def clear_plot(self):
        # rms settings
        self.plot.clear()
        self.configure_plot()
        self.data = {}


class RawPlots(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(RawPlots, self).__init__(*args, **kwargs)

        self.plot_config = plot_config
        self.pen_color = QColor(pen_colors[self.plot_config['color_iterator']])

        # Create and add GraphicsLayoutWidget
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create GLW for the depth plot
        depth_sett = {**DEPTH,
                      'pen_color': pen_colors[self.plot_config['color_iterator']]}
        self.depth_plot = BasePlotWidget(depth_sett)
        self.layout.addWidget(self.depth_plot, 0, 0, 8, 1)

        # extra depth_plot settings
        self.depth_plot.plot.invertY()
        self.fill_bar = self.depth_plot.plot.plot([-5, 5],
                                             [depth_sett['y_range'][0], depth_sett['y_range'][0]],
                                             fillLevel=depth_sett['y_range'][0], brush=(255, 255, 255, 100),
                                             movable=True)
        self.fill_bar_position = []
        self.depth_bar = pg.InfiniteLine(angle=0,
                                         bounds=[depth_sett['y_range'][0],
                                                 depth_sett['y_range'][1]],
                                         pos=depth_sett['y_range'][0],
                                         movable=True,
                                         pen='w')
        self.depth_bar.sigDragged.connect(self.depth_bar_drag)
        self.depth_plot.plot.addItem(self.depth_bar)
        self.depth_text = pg.TextItem(text='', color='w', fill=(0, 0, 0, 0))
        self.depth_text.setAnchor((.5, 1.5))
        self.depth_plot.plot.addItem(self.depth_text)
        self.depth_text.setZValue(1)

        # Prepare plot data
        self.data_layout = QVBoxLayout()
        self.layout.addLayout(self.data_layout, 0, 1, 8, 5)
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 5)

        self.data_figures = []
        self.current_pdi = [None] * 8  # currently plotted
        self.depth_pdi = {}  # all depth plot data items
        self.data_texts = []

        raw_sett = {**DEFAULTPLOT,
                    'x_axis': False,  # Is Visible
                    'y_axis': False,
                    'x_range': self.plot_config['x_range'],  # None for auto-scale, list otherwise
                    'y_range': [-self.plot_config['y_range'], self.plot_config['y_range']],
                    'auto_scale': False,
                    'interactive': False,
                    'marker_line': None,
                    'error_bars': False
                    }
        for i in range(8):
            tmp = BasePlotWidget(raw_sett)
            self.data_layout.addWidget(tmp)
            self.data_figures.append(tmp)
            tmp_txt = pg.TextItem(text="", angle=90, color='w')
            tmp_txt.setX(0)
            tmp_txt.setY(0)
            tmp_txt.setAnchor((0.5, 1))
            tmp_txt.setZValue(1)
            tmp.plot.addItem(tmp_txt)
            self.data_texts.append(tmp_txt)

    def fill_bar_update(self):
        # Set the current value depending on how the region is changed.
        # If dragged, will change to 4 values lower than the middle.
        # If top will change to 8 values below.
        # If bottom, will keep new value.

        all_depths = np.sort([x for x in self.depth_pdi.keys()])
        if len(all_depths) > 0:
            if self.fill_bar_position[0] != self.fill_bar.getRegion()[0] and \
               self.fill_bar_position[1] != self.fill_bar.getRegion()[1]:
                curr_value = np.mean(self.fill_bar.getRegion())
                offset = 3
            elif self.fill_bar_position[0] != self.fill_bar.getRegion()[0]:
                curr_value = self.fill_bar.getRegion()[0]
                offset = 7
            elif self.fill_bar_position[1] != self.fill_bar.getRegion()[1]:
                curr_value = self.fill_bar.getRegion()[1]
                offset = 0
            else:
                return

            diffs = abs(all_depths - curr_value)
            # lock to closest depth value
            idx, = np.where(diffs == min(diffs))[0]
            b_idx = min(len(all_depths)-1, idx + offset)
            t_idx = max(0, idx - 7)
            self.fill_bar_position = (all_depths[b_idx], all_depths[t_idx])
            self.fill_bar.setRegion((all_depths[b_idx], all_depths[t_idx]))

    def depth_bar_drag(self):
        # hide text field
        self.depth_plot.clear_text_line()

        # set fill area to be the first 8 depths found above the line
        all_depths = np.sort([x for x in self.depth_pdi.keys()])
        if len(all_depths) > 0:
            curr_value = self.depth_bar.value()
            diffs = abs(all_depths - curr_value)

            # lock to closest depth value
            idx, = np.where(diffs == min(diffs))[0]
            self.depth_bar.setValue(all_depths[idx])
            self.plot_depth_values()

    # Update plot is only for new datum
    def update_plot(self, all_data):
        new_depth = -20
        if all_data is not None:
            # all_data is a dict {datum_id: [depth, np array of data]}
            for _, depth_data in all_data.items():
                # append data
                if depth_data[0] not in self.depth_pdi.keys():
                    self.depth_pdi[depth_data[0]] = pg.PlotDataItem(depth_data[1],
                                                                    pen=self.pen_color,
                                                                    autoDownsample=True)

                # plot depth
                symbol_brush = self.pen_color if depth_data[2] else None
                self.depth_plot.plot.plot(x=[0], y=[depth_data[0]], symbol='o', symbolBrush=symbol_brush,
                                     symbolPen=self.pen_color, symbolSize=6)

                new_depth = max(depth_data[0], new_depth)

            # move draggable bar to new depth
            self.depth_bar.setValue(new_depth)
            self.plot_depth_values()

    def plot_depth_values(self):
        # get current index of selected depth
        all_depths = np.sort([x for x in self.depth_pdi.keys()])
        curr_value = self.depth_bar.value()

        # lock to closest depth value
        idx, = np.where(all_depths == curr_value)[0]

        # plot last 8 depth data
        # make fill bar around 8 depths above the currently selected one
        top_idx = max(0, idx - 7)
        self.fill_bar.setData(x=[-5, 5], y=[all_depths[idx], all_depths[idx]], fillLevel=all_depths[top_idx])

        plot_idx = 1
        while plot_idx <= 8:
            # remove any currently displayed line
            self.data_figures[-plot_idx].plot.removeItem(self.current_pdi[-plot_idx])

            if idx >= top_idx:
                to_plot = self.depth_pdi[all_depths[idx]]
                self.data_figures[-plot_idx].plot.addItem(to_plot)
                self.current_pdi[-plot_idx] = to_plot
                self.data_texts[-plot_idx].setText("{0:.3f}".format(all_depths[idx]))
            else:
                self.data_texts[-plot_idx].setText("")
                self.current_pdi[-plot_idx] = None

            self.data_figures[-plot_idx].plot.setYRange(-self.plot_config['y_range'], self.plot_config['y_range'])

            idx -= 1
            plot_idx += 1

    def clear_plot(self):
        self.depth_pdi = {}

        # clear depth plot
        self.depth_bar.setValue(-20)
        self.fill_bar.setData(x=[-5, 5],
                              y=[self.plot_config['depth_range'][0], self.plot_config['depth_range'][0]],
                              fillLevel=self.plot_config['depth_range'][0])

        for it in self.depth_plot.plot.listDataItems():
            if it.opts['symbol'] == 'o':
                self.depth_plot.plot.removeItem(it)

        # clear data plots
        for plt, data in zip(self.data_figures, self.current_pdi):
            plt.removeItem(data)

        for txt in self.data_texts:
            txt.setText("")


class DBSPlots(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(DBSPlots, self).__init__(*args, **kwargs)
        self.plot_config = plot_config

        pen_color = QColor(pen_colors[plot_config['color_iterator']])

        # Create and add GraphicsLayoutWidget
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create GLW for the depth plot
        rms_sett = {**FEAT_VS_DEPTH,
                    'title': 'Noise RMS (' + u'\u03BC' + 'V)',
                    'y_name': 'NoiseRMS',
                    'pen_color': pen_color}
        self.rms_plot = BasePlotWidget(rms_sett)
        self.layout.addWidget(self.rms_plot, 0, 0, 1, 1)

        beta_sett = {**FEAT_VS_DEPTH,
                     'title': 'Beta power (dB)',
                     'y_name': 'BetaPower',
                     'post_processing': self.beta_process,
                     'pen_color': pen_color}
        self.bp_plot = BasePlotWidget(beta_sett)
        self.layout.addWidget(self.bp_plot, 1, 0, 1, 1)
        # https://gist.github.com/beniwohli/765262
        pac_sett = {**FEAT_VS_DEPTH,
                    'title': 'Peak ' + u'\u03B2' + '-' + u'\u03B3' + ' PAC (± var)',
                    'y_name': 'PAC',
                    'y_range': [-.1, 1],
                    'x_ticks': True,
                    'post_processing': self.pac_process,
                    'error_bars': True,
                    'pen_color': pen_color}
        self.pac_plot = BasePlotWidget(pac_sett)
        self.layout.addWidget(self.pac_plot, 2, 0, 1, 1)

        self.layout.setRowStretch(0, 1)
        self.layout.setRowStretch(1, 1)
        self.layout.setRowStretch(2, 1)

    @staticmethod
    def beta_process(data):
        return 10 * np.log10(data[1])

    @staticmethod
    def pac_process(data):
        # data contains peak, mean, variance
        return data[1][:1], data[1][-1:]

    def update_plot(self, all_data):
        self.rms_plot.update_plot(all_data)
        self.bp_plot.update_plot(all_data)
        self.pac_plot.update_plot(all_data)

    def clear_plot(self):
        self.rms_plot.clear_plot()
        self.bp_plot.clear_plot()
        self.pac_plot.clear_plot()


class LFPPlots(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(LFPPlots, self).__init__(*args, **kwargs)

        self.plot_config = plot_config
        self.pen_color = QColor(pen_colors[self.plot_config['color_iterator']])

        # Create and add GraphicsLayoutWidget
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create GLW for the depth plot
        alpha_sett = {**FEAT_VS_DEPTH,
                      'title': 'Spectrum slope (alpha)',
                      'x_ticks': True,
                      'x_name': 'depth',
                      'y_name': 'MultiTaperSpectrum',
                      'y_range': [0, 10],
                      'post_processing': self.alpha_process,
                      'pen_color': self.pen_color}
        self.alpha_plot = BasePlotWidget(alpha_sett)
        self.layout.addWidget(self.alpha_plot, 0, 0, 1, 1)

        self.layout.addWidget(QLabel(), 1, 0, 1, 1)
        self.layout.setRowStretch(0, 1)
        self.layout.setRowStretch(1, 1)

        self.depth_data = {}

    @staticmethod
    def alpha_process(data):
        f_stops = [(-np.Inf, 1.0), (58, 62), (116, 124), (150, np.Inf)]

        freqs = data[0]
        b_freqs = np.ones(freqs.shape[0], dtype=bool)
        for f_s in f_stops:
            b_freqs[np.logical_and(freqs >= f_s[0], freqs <= f_s[1])] = False

        pwr = data[1]

        a = np.vstack([-np.log(freqs[b_freqs].flatten()), np.ones(freqs[b_freqs].size)]).T
        alpha, b = np.linalg.lstsq(a,
                                   np.log(pwr[b_freqs].flatten()), rcond=None)[0]
        return [alpha]

    def update_plot(self, all_data):
        self.alpha_plot.update_plot(all_data)


class SpikePlots(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(SpikePlots, self).__init__(*args, **kwargs)

        self.plot_config = plot_config
        self.pen_color = QColor(pen_colors[self.plot_config['color_iterator']])

        # Create and add GraphicsLayoutWidget
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # rms settings
        rms_sett = {**FEAT_VS_DEPTH,
                    'title': 'Noise RMS (' + u'\u03BC' + 'V)',
                    'y_name': 'DBSSpikeFeatures',
                    'post_processing': lambda x: [x[1][0]],
                    'pen_color': self.pen_color}

        self.rms_plot = BasePlotWidget(rms_sett)
        self.layout.addWidget(self.rms_plot, 0, 0, 1, 1)

        # rate
        rate_sett = {**FEAT_VS_DEPTH,
                     'title': 'Rate (Hz)',
                     'y_name': 'DBSSpikeFeatures',
                     'post_processing': lambda x: [x[1][1]],
                     'pen_color': self.pen_color}

        self.rate_plot = BasePlotWidget(rate_sett)
        self.layout.addWidget(self.rate_plot, 1, 0, 1, 1)

        # rate
        burst_sett = {**FEAT_VS_DEPTH,
                      'title': 'Burst Index',
                      'y_name': 'DBSSpikeFeatures',
                      'post_processing': lambda x: [x[1][2]],
                      'pen_color': self.pen_color}

        self.burst_plot = BasePlotWidget(burst_sett)
        self.layout.addWidget(self.burst_plot, 2, 0, 1, 1)

        # FF
        ff_sett = {**FEAT_VS_DEPTH,
                   'title': 'Fano Factor',
                   'x_ticks': True,
                   'y_name': 'DBSSpikeFeatures',
                   'post_processing': lambda x: [x[1][3]],
                   'pen_color': self.pen_color}

        self.ff_plot = BasePlotWidget(ff_sett)
        self.layout.addWidget(self.ff_plot, 3, 0, 1, 1)

        self.layout.setRowStretch(0, 1)
        self.layout.setRowStretch(1, 1)
        self.layout.setRowStretch(2, 1)
        self.layout.setRowStretch(3, 1)

        self.depth_data = {}

    def update_plot(self, all_data):
        self.rms_plot.update_plot(all_data)
        self.rate_plot.update_plot(all_data)
        self.burst_plot.update_plot(all_data)
        self.ff_plot.update_plot(all_data)

    def clear_plot(self):
        # rms settings
        self.rms_plot.clear_plot()
        self.rate_plot.clear_plot()
        self.burst_plot.clear_plot()
        self.ff_plot.clear_plot()

        self.depth_data = {}


class NullPlotWidget(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(NullPlotWidget, self).__init__(*args, **kwargs)
        self.plot_config = plot_config

    def update_plot(self, all_data):
        pass

    def clear_plot(self):
        pass
