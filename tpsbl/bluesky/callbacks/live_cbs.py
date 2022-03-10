from bluesky.callbacks.core import LiveTable
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.callbacks.fitting import LiveFit
from lmfit.models import GaussianModel
from types import MethodType
import pandas as pd
import lmfit
import numpy as np

class LiveEdgeFit(LiveFit):
    def start(self, doc):
        super().start(doc)
        self.yv_prev = None

    def event(self, doc):
        if self.y not in doc['data']:
            return

        if self.yv_prev is None:
            self.yv_prev = doc['data'][self.y]
            return

        yv_diff = doc['data'][self.y] - self.yv_prev
        self.yv_prev = doc['data'][self.y]

        doc_new = dict(doc)
        doc_new['data'] = dict(doc['data'])
        doc_new['data'][self.y] = yv_diff

        super().event(doc_new)

class LiveCbsFactory:
    def __init__(self, positioner=None, detector=None, choice=None,
                 x_data_name=None, y_data_name=None, update_every=None,
                 live_table_enabled=False, fit_plots_enabled=True, verbose=False):  # @UnusedVariable
        '''
        a monkey patch for one dimensional scan
        to compute and move to desired position after scan
        :param positioner: move to desired position after scan
                           positioner.name is the default value of x_data_name if not None
        :param detector: detector.name is the default value of y_data_name if not None
        :param choice: choose method to find top position
        :param x_data_name: override positioner.name if not None
        :param y_data_name: override detector.name if not None
        :param update_every: see LiveFit
        :param live_table_enabled: set False if outside bec table is enabled
        :param fit_plots_enabled: option to disable fit plots

        :example:
            rr = RunRouter([LiveCbsFactory(motor, noisy_det, 'peak', update_every=101)])
        :example:
            RunEngine()(scan([noisy_det], motor, -5,5,101),
               RunRouter([LiveCbsFactory(motor, noisy_det, 'peak', update_every=101)]))
        '''
        self.positioner = positioner
        self.detector = detector
        self.choice = choice
        self.x_data_name = x_data_name or (None if positioner is None else positioner.name)
        self.y_data_name = y_data_name or (None if detector is None else detector.name)
        self.update_every = update_every
        self.live_table_enabled = live_table_enabled
        self.fit_plots_enabled = fit_plots_enabled
        self.verbose = verbose

    def __call__(self, name, doc):
        scan_id = doc['scan_id']
        uid = doc['uid']
        plan_name = doc['plan_name']

        x = self.x_data_name or doc.get('x_data_name')
        y = self.y_data_name or doc.get('y_data_name')

        if self.live_table_enabled:
            lt = LiveTable([y,x])
        bec = BestEffortCallback(table_enabled=True)
        lf = LiveFit(GaussianModel(), y, {'x':x}, update_every=self.update_every or int(doc['num_points']/10))
        lef = LiveEdgeFit(GaussianModel(), y, {'x':x}, update_every=self.update_every or int(doc['num_points']/10))

        choice = self.choice or doc.get('choice','peak')
        positioner = self.positioner

        def descriptor_decorator(cb):
            orig_descriptor = cb.descriptor
            def inner(self, doc):
                orig_descriptor(doc)
                if doc['name'] == 'primary':
                    fig = list(bec._live_plots.values())[0][y].ax.figure
                    fig.canvas.manager.window.setGeometry(0,30,640,601)
            return MethodType(inner, cb)
        bec.descriptor = descriptor_decorator(bec)

        def stop_decorator(cb):
            orig_stop = cb.stop
            fit_plots_enabled = self.fit_plots_enabled
            verbose = self.verbose
            def inner(self, doc):
                orig_stop(doc)

                if verbose:
                    print(f'== Gaussian fit ==\n {lf.result.fit_report()}\n')
                    print(f'== Edge fit ==\n {lef.result.fit_report()}\n')
                    print(f'== bec peaks ==\n {bec.peaks}\n')
                '''
                    collect top result of all methods
                '''
                top_res = dict(
                    max = dict(pos=bec.peaks['max'][y][0], height=bec.peaks['max'][y][1], fwhm='-'),
                    min = dict(pos=bec.peaks['min'][y][0], height=bec.peaks['min'][y][1], fwhm='-'),
                    com = dict(pos=bec.peaks['com'][y], height='-', fwhm='-'),
                    cen = dict(pos=bec.peaks['cen'][y], height='-', fwhm='-'),
                    fit = dict(pos=lf.result.params['center'].value, height=lf.result.params['height'].value,
                               fwhm=lf.result.params['fwhm'].value),
                    edgefit = dict(pos=lef.result.params['center'].value, height=lef.result.params['height'].value,
                                   fwhm=lef.result.params['fwhm'].value),
                    )
                with pd.option_context('display.float_format', '{:0.6f}'.format):
                    df = pd.DataFrame().from_dict(top_res, orient='index')
                    df.index.name = 'method'
                    print(df, end='\n\n')
                '''
                    move positioner
                '''
                top = top_res.get(choice, {}).get('pos',None)

                if (positioner is not None
                    and x in positioner.describe()
                    and top is not None):
                    print(f"{plan_name}: UID = {uid}, Scan ID:{scan_id}")
                    positioner.move(top)
                    print(f"Found and moved to top at {top:.3} via method {choice}\n", flush=True)

                if fit_plots_enabled:
                    fig = lf.result.plot()
                    fig.canvas.manager.window.setGeometry(640,30,640,601)
                    fig.canvas.manager.set_window_title(f"Scan ID: {scan_id}, {lf.__class__.__name__}")

                    fig = lef.result.plot()
                    fig.canvas.manager.window.setGeometry(640,805,640,601)
                    fig.canvas.manager.set_window_title(f"Scan ID: {scan_id} {lef.__class__.__name__}")

            return MethodType(inner, cb)
        bec.stop = stop_decorator(bec)

        if self.live_table_enabled:
            cbs = [lt, lf, lef, bec], []
        else:
            cbs = [lf, lef, bec], []
        return cbs

