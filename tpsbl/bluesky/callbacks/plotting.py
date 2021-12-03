from bluesky.callbacks.mpl_plotting import LivePlot, QtAwareCallback, LiveGrid
import numpy as np

class PXRDPlot(LivePlot):
    def start(self, doc):
        super().start(doc)
        self.ax.figure.canvas.manager.window.setGeometry(0,0,1275,700)
        self.ax.figure.show()

    def update_caches(self, x, y):
        self.y_data = y
        self.x_data = x
    # def update_plot(self):
        # self.ax.figure.canvas.draw_idle()

    def stop(self, doc):
        QtAwareCallback.stop(self, doc)

class LiveGridImage(LiveGrid):

    def __init__(self,*args, interpolation='nearest', percentile=(5,95), **wkargs):
        super().__init__(*args, **wkargs)

        self.percentile = percentile

        def setup():
            nonlocal interpolation
            self.interpolation = interpolation

        def post_setup():
            self.im.set_interpolation(self.interpolation)

        self.__setup = setup
        self.__post_setup = post_setup

    def start(self, doc):
        if not hasattr(self, 'im'):
            self.__setup()
            super().start(doc)
            self.__post_setup()
            self.ax.figure.canvas.manager.window.setGeometry(0,0,1275,700)
        else:
            self.ax.set_title('scan {uid} [{sid}]'.format(sid=doc['scan_id'],
                              uid=doc['uid'][:6]))

    def event(self, doc):
        if self.I not in doc['data']:
            return

        self.im.colorbar.set_label(f"seq#:{doc['seq_num']}")
        I = doc['data'][self.I]
        self.update(I)

    def update(self, I):
        self._Idata = I
        if self.clim is None:
            percentile_low, percentile_high = self.percentile
            lim_low = np.percentile(self._Idata, percentile_low)
            lim_high = np.percentile(self._Idata, percentile_high)
            self.im.set_clim(lim_low, lim_high)

        self.im.set_array(self._Idata)
        self.ax.figure.canvas.draw_idle()

'''
    plotting sqeuence of signal,tth data
'''
import threading
from bluesky.callbacks.core import make_class_safe
import logging

logger = logging.getLogger(__name__)

@make_class_safe(logger=logger)
class ResultPlot(QtAwareCallback):
    def __init__(self, y_data_name, x_data_name, ax=None, fig=None, max_line_num=10, vis_line_num=3, show_legend=True, **kwargs):
        self.y_data_name = y_data_name
        self.x_data_name = x_data_name

        super().__init__(use_teleporter=kwargs.pop('use_teleporter', None))
        self.__setup_lock = threading.Lock()
        self.__setup_event = threading.Event()
        def setup():
            nonlocal ax, kwargs
            import matplotlib.pyplot as plt
            with self.__setup_lock:
                if self.__setup_event.is_set():
                    return
                self.__setup_event.set()
            if ax is None:
                fig = plt.figure()
                ax = fig.add_axes([0.1, 0.1, 0.6, 0.75])
                fig.show()
            self.ax = ax
            self.fig = fig
            fig.canvas.manager.window.setGeometry(0,802,1275,600)

            self.ax.set_xlabel('2' + r'$\theta$' +'(\u00b0)')
            self.ax.set_ylabel('Intensity')
            self.kwargs = kwargs
            fig.canvas.mpl_connect('pick_event', self.__on_pick)

        def on_pick(event):
            # On the pick event, find the original line corresponding to the legend
            # proxy line, and toggle its visibility.
            legline = event.artist
            origline = self.lined[legline]
            visible = not origline.get_visible()
            origline.set_visible(visible)
            # Change the alpha on the line in the legend so we can see what lines
            # have been toggled.
            legline.set_alpha(1.0 if visible else 0.2)
            self.ax.figure.canvas.draw_idle()

        self.__on_pick = on_pick
        self.__setup = setup
        self.max_line_num = max_line_num
        self.vis_line_num = vis_line_num
        self.show_legend = show_legend

    def start(self, doc):
        self.__setup()
        self.ax.set_title("scan id = %d" % (doc["scan_id"]))
        self.lined = {}
        self.lines = []

    def event(self, doc):
        tth = doc['data'].get(self.x_data_name,[])
        signal = doc['data'].get(self.y_data_name,[])
        if len(tth) and len(signal):
            line = self.ax.plot(tth,signal,label=f"seq#:{doc['seq_num']}", **self.kwargs)
            self.lines += line
            if self.max_line_num != None and len(self.lines) > self.max_line_num:
                self.lines[0].remove()
                del self.lines[0]
            for line in self.lines:
                line.set_visible(True)

            if self.show_legend:
                self.legend = self.ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)

                if self.vis_line_num != None and len(self.lines) > self.vis_line_num:
                    vis_line_start_index = len(self.lines) - self.vis_line_num
                else:
                    vis_line_start_index = 0

                for (index, legline), origline in zip(enumerate(self.legend.get_lines()), self.lines):
                    legline.set_picker(True)  # Enable picking on the legend line.
                    self.lined[legline] = origline
                    if index < vis_line_start_index:
                        legline.set_alpha(0.2)
                        origline.set_visible(False)
        #                 print(f"legline, origline={legline},{origline}")
            self.ax.figure.canvas.draw_idle()

from bluesky.callbacks.mpl_plotting import QtAwareCallback
import matplotlib.pyplot as plt
import matplotlib.lines as lines
from matplotlib.widgets import CheckButtons
class ProcPlot(QtAwareCallback):
    def __init__(self, *args, xy_lim=None, autoscale=True, **kwargs):
        super().__init__(*args, **kwargs)
        # internal state
        self._start_doc = None
        self._descriptors = {}
        self._delta_mot_name = None
        self._delta_mot_poslist = []
        self._colors = plt.rcParams['axes.prop_cycle']()
        self._lines = {}
        self.xy_lim = xy_lim
        self.autoscale = autoscale

    def setup(self):
        fig = plt.figure('fig_name')
        if not fig.axes:
            fig_cols = 10
            ax_leg = plt.subplot2grid((1,fig_cols), (0,0), colspan=2, fig=fig)
            ax_leg.set_aspect('equal', anchor='N')
            ax = plt.subplot2grid((1,fig_cols), (0,3), colspan=fig_cols-2, fig=fig)
            ax.set_position([0.3, 0.1, 0.5, 0.75])
            fig_win = ax.figure.canvas.manager.window
            fig_win.setGeometry(0,0,1275,700)
            fig.canvas.set_window_title('---  TPS HRPXRD ---')
            fig.show()
            self._lines.clear()

        self.fig =fig
        axes = fig.axes
        self.ax_leg = axes[0]
        self.ax = axes[1]

        if self.xy_lim is not None:
            self.ax.set_xlim(self.xy_lim[0])
            self.ax.set_ylim(self.xy_lim[1])

        for line in self.ax.lines:
            self._lines[line.get_label()] = line

    def start(self, doc):
        self._start_doc = doc
        '''
        according to the design of mythen_grid_scan,
        expected that the last motor is delta for mythen
        '''
        self._delta_mot_name = doc['motors'][-1]
        self._delta_mot_poslist = doc['plan_args']['args'][-1]

    def descriptor(self, doc):
        self._descriptors[doc['uid']] = doc
        self.setup()

    def update_check_buttons(self):
        LABEL_ALL = "All"
        label_all_vis = True
        self.ax_leg.clear()
        self.check_labels = [label for label in self._lines.keys()] + [LABEL_ALL]
        check_labels_vis = [line.get_visible() for line in self._lines.values()] + [label_all_vis]

        check_buttons = CheckButtons(self.ax_leg, self.check_labels, check_labels_vis)
        self.check_buttons = check_buttons
        # scale symbols according to live_ax_leg.set_ylim(top=
        live_ax_leg_yscale=2
        w=check_buttons.rectangles[0].get_width()
        [rect.set_width(w*live_ax_leg_yscale) for rect in check_buttons.rectangles]
        xd = check_buttons.lines[0][0].get_xdata()
        xd = [xd[0],live_ax_leg_yscale*xd[1]-xd[0]]
        [[line.set_xdata(xd) for line in cross] for cross in check_buttons.lines]
        self.ax_leg.set_ylim(top=live_ax_leg_yscale)
        self.ax_leg.axis('off')

        def on_check_func(label):
            index = self.check_labels.index(label)
            vis = self.check_buttons.get_status()[index]
            #! print(f"on_clicked {label}, index:{index}")
            #live_lines[index].set_visible(not live_lines[index].get_visible())
            if index == self.check_labels.index(LABEL_ALL):
                for line, chk_btn  in zip(self._lines.values(), self.check_buttons.lines):
                    line.set_visible(vis)
                    chk_btn[0].set_visible(vis)
                    chk_btn[1].set_visible(vis)
            else:
                self._lines[label].set_visible(vis)
            self.fig.canvas.draw()
        check_buttons_cid = check_buttons.on_clicked(on_check_func)

    def event(self, doc):
        '''
        doc example:
        doc_plot = {
            'data': {'x': tth_plot_sign*tth_temp, 'y':signal_temp},
            'line_params': {'label':f'{self._raw["label"]}{delta_mythen}', 'marker':'x', 'linestyle':'', 'markersize':5}
            }
        '''
        line_params = doc.get('line_params',{})
        line_label = line_params.get('label')
        if line_label:
            if line_label == 'all_lines':
                x = doc.get('data',{}).get('x',[])
                y = doc.get('data',{}).get('y',[])
                for line in self._lines.values():
                    line.set_xdata(x)
                    line.set_ydata(y)
            else:
                x = doc.get('data',{}).get('x',[])
                y = doc.get('data',{}).get('y',[])
                line = self._lines.get(line_label)
                if line:
                    line.set_xdata(x)
                    line.set_ydata(y)
                else:
                    ''' new line '''
                    line = lines.Line2D(x, y,
                                        **line_params,
                                        **next(self._colors))
                    self.ax.add_line(line)
                    self._lines[line_label] = line
                    self.ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
                    if self.autoscale: self.ax.autoscale()
                    self.update_check_buttons()
            self.fig.canvas.draw_idle()
'''
proc_plot = ProcPlot()

doc_descriptor = {'uid': 'uid-xxx-xxx-xxx'}
proc_plot('descriptor', doc_descriptor)

import numpy as np
tth_temp = 0.005*np.array(range(23040))
tth_plot_sign=1.0
delta_mythen=12.3
data_angoft = {'raw':1, 'bci':3, 'ff':5, 'valid':7, 'dvdl':11}
# data_angoft = {'raw':0, 'bci':0, 'ff':0, 'valid':0, 'dvdl':0}
for i in range(101):
    for label, angoft in data_angoft.items():
        signal_temp = np.sin(np.pi/100*(tth_temp+angoft+i*angoft)*5)
        doc = {'data':{'x': tth_temp, 'y':signal_temp},
               'line_params': {'label':f'{label}{delta_mythen}', 'marker':'x', 'linestyle':'', 'markersize':5}
               }
        proc_plot('event', doc)
    plt.pause(0.05)
'''
