import numpy as np

# use the same GUI format as the other ones
from qtpy.QtWidgets import QLabel, QGridLayout, QWidget, QVBoxLayout
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QFont

import pyqtgraph as pg

THEMES = {
    'dark': {
        'pencolors': ["cyan", QColor(0, 255, 0), "magenta", "red", "yellow", "white"],
        'bgcolor': Qt.black,
        'labelcolor': Qt.gray,
        'axiscolor': Qt.gray,
        'axiswidth': 1
    }
}


class RawPlotWidget(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(RawPlotWidget, self).__init__(*args, **kwargs)

        self.plot_config = plot_config
        self.pen_color = QColor(THEMES[self.plot_config['theme']]['pencolors'][self.plot_config['color_iterator']])

        # Create and add GraphicsLayoutWidget
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create GLW for the depth plot
        depth_glw = pg.GraphicsLayoutWidget(parent=self)

        self.layout.addWidget(depth_glw, 0, 0, 8, 1)

        # depth_GLW settings
        self.depth_plot = depth_glw.addPlot(enableMenu=False)
        self.depth_plot.invertY()
        self.depth_plot.setMouseEnabled(x=False, y=False)
        self.depth_plot.setYRange(self.plot_config['depth_range'][0], self.plot_config['depth_range'][1], padding=0)
        self.depth_plot.setXRange(-5, 5, padding=0)
        self.depth_plot.getAxis('bottom').setStyle(tickLength=0, showValues=False)
        self.depth_plot.getAxis('bottom').setPen((255, 255, 255, 255))
        font = QFont()
        font.setPixelSize(16)
        font.setBold(True)
        self.depth_plot.getAxis('left').tickFont = font
        self.depth_plot.getAxis('left').setPen((255, 255, 255, 255))

        self.depth_plot.scene().sigMouseMoved.connect(self.mouse_moved)

        # Plot vertical line and "target" (i.e. 0) line
        self.depth_plot.plot(np.zeros(100), np.arange(self.plot_config['depth_range'][0],
                                                      self.plot_config['depth_range'][1],
                                                      abs(self.plot_config['depth_range'][1] -
                                                          self.plot_config['depth_range'][0])/100))
        self.depth_plot.plot([-5, 5], [0, 0], pen='y')

        self.fill_bar = self.depth_plot.plot([-5, 5],
                                             [self.plot_config['depth_range'][0], self.plot_config['depth_range'][0]],
                                             fillLevel=self.plot_config['depth_range'][0], brush=(255, 255, 255, 100),
                                             movable=True)
        self.fill_bar_position = []

        self.depth_bar = pg.InfiniteLine(angle=0,
                                         bounds=[self.plot_config['depth_range'][0],
                                                 self.plot_config['depth_range'][1]],
                                         pos=self.plot_config['depth_range'][0],
                                         movable=True,
                                         pen='w')
        self.depth_bar.sigDragged.connect(self.depth_bar_drag)

        self.depth_plot.addItem(self.depth_bar)
        self.depth_text = pg.TextItem(text='', color='w', fill=(0, 0, 0, 0))
        self.depth_text.setAnchor((.5, 1.5))
        self.depth_plot.addItem(self.depth_text)
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
        for i in range(8):
            tmp = pg.GraphicsLayoutWidget()
            self.data_layout.addWidget(tmp)
            tmp = tmp.addPlot()
            tmp.hideAxis('bottom')
            tmp.hideAxis('left')
            tmp.setMouseEnabled(x=False, y=False)
            tmp.setXRange(plot_config['x_range'][0], self.plot_config['x_range'][1])
            tmp.setYRange(-self.plot_config['y_range'], self.plot_config['y_range'])
            self.data_figures.append(tmp)
            tmp_txt = pg.TextItem(text="", angle=90, color='w')
            tmp_txt.setX(0)
            tmp_txt.setY(0)
            tmp_txt.setAnchor((0.5, 1))
            tmp_txt.setZValue(1)
            tmp.addItem(tmp_txt)
            self.data_texts.append(tmp_txt)

    def mouse_moved(self, evt):
        # map y pixel position to nearest plot item position
        plot_coord = self.depth_plot.vb.mapSceneToView(evt)
        data_items = self.depth_plot.listDataItems()

        depths = list(self.depth_pdi.keys())
        if depths and abs(plot_coord.x()) < 4:
            diffs = [abs(x - plot_coord.y()) for x in depths]
            depth = depths[diffs.index(min(diffs))]

            for it in data_items:
                if it.yData[0] == depth and len(it.yData) == 1:
                    it.setSymbolSize(10)
                    self.depth_text.setText("{0:.3f}".format(depth))
                    self.depth_text.setX(0)
                    self.depth_text.setY(depth)
                    self.depth_text.fill.setColor(QColor(0, 0, 0, 175))
                else:
                    it.setSymbolSize(6)
        else:
            [x.setSymbolSize(6) for x in data_items]
            self.depth_text.setText("")
            self.depth_text.fill.setColor(QColor(0, 0, 0, 0))

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
                self.depth_plot.plot(x=[0], y=[depth_data[0]], symbol='o', symbolBrush=symbol_brush,
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
            self.data_figures[-plot_idx].removeItem(self.current_pdi[-plot_idx])

            if idx >= top_idx:
                to_plot = self.depth_pdi[all_depths[idx]]
                self.data_figures[-plot_idx].addItem(to_plot)
                self.current_pdi[-plot_idx] = to_plot
                self.data_texts[-plot_idx].setText("{0:.3f}".format(all_depths[idx]))
            else:
                self.data_texts[-plot_idx].setText("")
                self.current_pdi[-plot_idx] = None

            self.data_figures[-plot_idx].setYRange(-self.plot_config['y_range'], self.plot_config['y_range'])

            idx -= 1
            plot_idx += 1

    def clear_plot(self):
        self.depth_pdi = {}

        # clear depth plot
        self.depth_bar.setValue(-20)
        self.fill_bar.setData(x=[-5, 5],
                              y=[self.plot_config['depth_range'][0], self.plot_config['depth_range'][0]],
                              fillLevel=self.plot_config['depth_range'][0])

        for it in self.depth_plot.listDataItems():
            if it.opts['symbol'] == 'o':
                self.depth_plot.removeItem(it)

        # clear data plots
        for plt, data in zip(self.data_figures, self.current_pdi):
            plt.removeItem(data)

        for txt in self.data_texts:
            txt.setText("")


class DBSPlotWidget(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(DBSPlotWidget, self).__init__(*args, **kwargs)

        self.plot_config = plot_config
        self.pen_color = QColor(THEMES[self.plot_config['theme']]['pencolors'][self.plot_config['color_iterator']])

        # Create and add GraphicsLayoutWidget
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create GLW for the depth plot
        rms_glw = pg.GraphicsLayoutWidget(parent=self)
        self.layout.addWidget(rms_glw, 0, 0, 1, 1)

        beta_pwr_glw = pg.GraphicsLayoutWidget(parent=self)
        self.layout.addWidget(beta_pwr_glw, 1, 0, 1, 1)

        pac_glw = pg.GraphicsLayoutWidget(parent=self)
        self.layout.addWidget(pac_glw, 2, 0, 1, 1)

        # spacer
        # self.layout.addWidget(QLabel(), 3, 0, 1, 1)
        self.layout.setRowStretch(0, 1)
        self.layout.setRowStretch(1, 1)
        self.layout.setRowStretch(2, 1)

        # rms settings
        self.rms_plot = rms_glw.addPlot(enableMenu=False)
        self.rms_line, self.rms_text = self.configure_plot(self.rms_plot, 'Noise RMS (uV)', False)

        # beta pwr settings
        self.bp_plot = beta_pwr_glw.addPlot(enableMenu=False)
        self.bp_line, self.bp_text = self.configure_plot(self.bp_plot, 'Beta Power (dB)', False)

        # PAC settings
        self.pac_plot = pac_glw.addPlot(enableMenu=False)
        self.pac_line, self.pac_text = self.configure_plot(self.pac_plot, 'PAC', True)
        self.pac_plot.setYRange(-.1, 1, padding=0)
        self.depth_data = {}

    def configure_plot(self, plot, title, show_values):
        plot.setTitle(title=title, **{'color': 'w', 'size': '16pt'})
        plot.addItem(pg.InfiniteLine(angle=90,
                                     pos=0.0,
                                     movable=False,
                                     pen='y'))
        plot.setMouseEnabled(x=False, y=False)
        plot.setXRange(self.plot_config['depth_range'][0], self.plot_config['depth_range'][1], padding=0)
        plot.setYRange(0, 1, padding=0)

        font = QFont()
        font.setPixelSize(20)
        font.setBold(True)

        plot.getAxis('bottom').setStyle(showValues=show_values)
        plot.getAxis('bottom').tickFont = font
        plot.getAxis('bottom').setPen((255, 255, 255, 255))
        plot.getAxis('bottom').setStyle(tickTextOffset=10)

        plot.getAxis('left').tickFont = font
        plot.getAxis('left').setPen((255, 255, 255, 255))
        plot.scene().sigMouseMoved.connect(self.mouse_moved)

        line = pg.InfiniteLine(angle=90,
                               pos=self.plot_config['depth_range'][0],
                               movable=False,
                               pen='w')
        line.setZValue(50)
        plot.addItem(line)

        text = pg.TextItem(text='', color='w', fill=(0, 0, 0, 175))
        text.setAnchor((0, 1))
        text.setX(0)
        text.setY(0.5)
        plot.addItem(text)
        text.setZValue(6)

        return line, text

    def mouse_moved(self, evt):
        plot_coord = self.bp_plot.vb.mapSceneToView(evt)
        depths = list(self.depth_data.keys())
        if depths:
            diffs = [abs(x - plot_coord.x()) for x in depths]
            depth = depths[diffs.index(min(diffs))]

            self.rms_line.setValue(depth)
            if 'NoiseRMS' in self.depth_data[depth].keys():
                self.rms_text.setText('x: ' + "{0:.3f}".format(depth) + '\n' + 'y: ' +
                                      "{0:.3f}".format(self.depth_data[depth]['NoiseRMS'][1][0]))
                self.rms_text.setX(depth)
                self.rms_text.setY(0)

            self.bp_line.setValue(depth)
            if 'BetaPower' in self.depth_data[depth].keys():
                self.bp_text.setText('x: ' + "{0:.3f}".format(depth) + '\n' + 'y: ' +
                                     "{0:.3f}".format(10*np.log10(self.depth_data[depth]['BetaPower'][1][0])))
                self.bp_text.setX(depth)
                self.bp_text.setY(0)

            self.pac_line.setValue(depth)
            if 'PAC' in self.depth_data[depth].keys():
                # Peak value
                self.pac_text.setText('x: ' + "{0:.3f}".format(depth) + '\n' + 'y: ' +
                                      "{0:.3f}".format(self.depth_data[depth]['PAC'][1][0]))
                # Mean value
                # self.pac_text.setText('x: ' + "{0:.3f}".format(depth) + '\n' + 'y: ' +
                #                       "{0:.3f}".format(self.depth_data[depth]['PAC'][1][1]))
                self.pac_text.setX(depth)
                self.pac_text.setY(0)

    def update_plot(self, all_data):
        if all_data is not None:
            # all_data is a dict {datum_id: [depth, np array of data]}
            for idx, depth_data in all_data.items():
                # append data
                depth = depth_data.pop('depth', None)

                if depth:
                    self.depth_data[depth] = dict(depth_data)

                    # plot depth
                    if 'NoiseRMS' in depth_data.keys():
                        if depth_data['NoiseRMS'][2]:
                            symbol_brush = self.pen_color
                        else:
                            symbol_brush = None

                        self.rms_plot.plot(x=[depth], y=[depth_data['NoiseRMS'][1][0]], symbol='o',
                                           symbolBrush=symbol_brush, symbolPen=self.pen_color)
                        self.rms_plot.enableAutoRange(axis=pg.ViewBox.YAxis)

                    if 'BetaPower' in depth_data.keys():
                        if depth_data['BetaPower'][2]:
                            symbol_brush = self.pen_color
                        else:
                            symbol_brush = None

                        self.bp_plot.plot(x=[depth], y=10*np.log10([depth_data['BetaPower'][1][0]]),
                                          symbol='o', symbolBrush=symbol_brush, symbolPen=self.pen_color)
                        self.bp_plot.enableAutoRange(axis=pg.ViewBox.YAxis)

                    if 'PAC' in depth_data.keys():
                        if depth_data['PAC'][2]:
                            symbol_brush = self.pen_color
                        else:
                            symbol_brush = None
                        # Peak value
                        self.pac_plot.plot(x=[depth], y=[depth_data['PAC'][1][0]],
                                           symbol='t1', symbolBrush=symbol_brush, symbolPen=self.pen_color)
                        # mean value
                        # self.pac_plot.plot(x=[depth], y=[depth_data['PAC'][1][1]],
                        #                   symbol='o', symbolBrush=symbol_brush, symbolPen=self.pen_color)
                        self.pac_plot.enableAutoRange(axis=pg.ViewBox.YAxis)

    def clear_plot(self):
        # rms settings
        self.rms_plot.clear()
        self.rms_line, self.rms_text = self.configure_plot(self.rms_plot, 'Noise RMS (uV)', False)

        # beta pwr settings
        self.bp_plot.clear()
        self.bp_line, self.bp_text = self.configure_plot(self.bp_plot, 'Beta Power (dB)', False)

        # PAC settings
        self.pac_plot.clear()
        self.pac_line, self.pac_text = self.configure_plot(self.pac_plot, 'PAC', True)

        self.depth_data = {}


class LFPPlotWidget(QWidget):
    def __init__(self, plot_config, *args, **kwargs):
        super(LFPPlotWidget, self).__init__(*args, **kwargs)

        self.plot_config = plot_config
        self.pen_color = QColor(THEMES[self.plot_config['theme']]['pencolors'][self.plot_config['color_iterator']])

        # Create and add GraphicsLayoutWidget
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create GLW for the depth plot
        alpha_glw = pg.GraphicsLayoutWidget(parent=self)
        self.layout.addWidget(alpha_glw, 0, 0, 1, 1)

        self.layout.addWidget(QLabel(), 1, 0, 1, 1)
        self.layout.setRowStretch(0, 1)
        self.layout.setRowStretch(1, 1)

        # beta pwr settings
        self.alpha_plot = alpha_glw.addPlot(enableMenu=False)
        self.alpha_plot.setTitle(title='Spectrum slope (alpha)', **{'color': 'w', 'size': '16pt'})
        self.alpha_plot.plot([0, 0], [0, 10], pen='y')
        self.alpha_plot.setMouseEnabled(x=False, y=False)
        self.alpha_plot.setYRange(0, 10, padding=0)
        self.alpha_plot.setXRange(self.plot_config['depth_range'][0], self.plot_config['depth_range'][1], padding=0)

        font = QFont()
        font.setPixelSize(20)
        font.setBold(True)

        # X Axis
        self.alpha_plot.getAxis('bottom').setStyle(showValues=True)
        self.alpha_plot.getAxis('bottom').tickFont = font
        self.alpha_plot.getAxis('bottom').setStyle(tickTextOffset=10)
        self.alpha_plot.getAxis('bottom').setPen((255, 255, 255, 255))

        # Y Axis
        self.alpha_plot.getAxis('left').tickFont = font
        self.alpha_plot.getAxis('left').setPen((255, 255, 255, 255))

        self.depth_data = {}

    # Update plot is only for new datum
    def update_plot(self, all_data):
        if all_data is not None:
            # all_data is a dict {datum_id: [depth, [xvec, data]}
            for idx, depth_data in all_data.items():
                # append data
                for key in depth_data:
                    if key != 'depth':
                        self.depth_data[depth_data['depth']] = {key: depth_data[key]}

                # f_range = [1, 120]
                f_stops = [(-np.Inf, 1.0), (58, 62), (116, 124), (150, np.Inf)]

                freqs = self.depth_data[depth_data['depth']]['MultiTaperSpectrum'][0]
                b_freqs = np.ones(freqs.shape[0], dtype=bool)
                for f_s in f_stops:
                    b_freqs[np.logical_and(freqs >= f_s[0], freqs <= f_s[1])] = False

                pwr = self.depth_data[depth_data['depth']]['MultiTaperSpectrum'][1]

                a = np.vstack([-np.log(freqs[b_freqs].flatten()), np.ones(freqs[b_freqs].size)]).T
                alpha, b = np.linalg.lstsq(a,
                                           np.log(pwr[b_freqs].flatten()), rcond=None)[0]

                self.alpha_plot.plot(x=[depth_data['depth']], y=[alpha], symbol='o',
                                     symbolBrush=self.pen_color, pen=self.pen_color)

    def clear_plot(self):
        self.depth_data = {}
        for it in self.alpha_plot.listDataItems():
            if it.opts['symbol'] == 'o':
                self.alpha_plot.removeItem(it)
