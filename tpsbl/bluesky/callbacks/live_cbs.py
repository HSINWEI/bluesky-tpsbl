from bluesky.callbacks.core import LiveTable
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.callbacks.fitting import LiveFit
from lmfit.models import GaussianModel
from types import MethodType

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
                 x_data_name=None, y_data_name=None, update_every=None):
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

        :example:
            rr = RunRouter([LiveCbsFactory(motor, noisy_det, 'peak', update_every=101)])
        :example:
            RE(scan([noisy_det], motor, -5,5,101),
               RunRouter([LiveCbsFactory(motor, noisy_det, 'peak', update_every=101)]))
        '''
        self.positioner = positioner
        self.detector = detector
        self.choice = choice
        self.x_data_name = x_data_name or (None if positioner is None else positioner.name)
        self.y_data_name = y_data_name or (None if detector is None else detector.name)
        self.update_every = update_every

    def __call__(self, name, doc):
        scan_id = doc['scan_id']
        uid = doc['uid']
        plan_name = doc['plan_name']

        x = self.x_data_name or doc.get('x_data_name')
        y = self.y_data_name or doc.get('y_data_name')

        lt = LiveTable([y,x])
        bec = BestEffortCallback(table_enabled=False)
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
            def inner(self, doc):
                orig_stop(doc)
                fig = lf.result.plot()
                fig.canvas.manager.window.setGeometry(640,30,640,601)
                fig.canvas.set_window_title(f"Scan ID: {scan_id}, {lf.__class__.__name__}")
                print(lf.result.fit_report())
                fig = lef.result.plot()
                fig.canvas.manager.window.setGeometry(640,805,640,601)
                fig.canvas.set_window_title(f"Scan ID: {scan_id} {lef.__class__.__name__}")
                print(bec.peaks)
                '''
                    move positioner
                '''
                if (positioner is not None
                    and x in positioner.describe()):
                    if choice == 'peak':
                        top = bec.peaks['max'][y][0]
                    elif choice == 'valley':
                        top = bec.peaks['min'][y][0]
                    elif choice == 'com':
                        top = bec.peaks['com'][y]
                    elif choice == 'cen':
                        top = bec.peaks['cen'][y]
                    elif choice == 'fit':
                        top = lf.result.params['center'].value
                    elif choice == 'edgefit':
                        top = lef.result.params['center'].value
                    print(f"{plan_name}: UID = {uid}, Scan ID:{scan_id}")
                    positioner.move(top)
                    print(f"Found and moved to top at {top:.3} via method {choice}\n")
            return MethodType(inner, cb)
        bec.stop = stop_decorator(bec)

        return [lt, lf, lef, bec], []

