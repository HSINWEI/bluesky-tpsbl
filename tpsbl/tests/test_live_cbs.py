from tpsbl.bluesky.callbacks.live_cbs import LiveEdgeFit, LiveCbsFactory
from ophyd.sim import SynGauss, motor, noisy_det
from scipy import special
import numpy as np
from lmfit.models import GaussianModel
from bluesky.plans import scan
from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback
from event_model import RunRouter

class SynError(SynGauss):
    def _compute(self):
        m = self._motor.read()[self._motor_field]['value']
        # we need to do this one at a time because
        #   - self.read() may be screwed with by the user
        #   - self.get() would cause infinite recursion
        Imax = self.Imax.get()
        center = self.center.get()
        sigma = self.sigma.get()
        noise = self.noise.get()
        noise_multiplier = self.noise_multiplier.get()
        v = Imax * (special.erf(m)+1)
        if noise == 'poisson':
            v = int(self.random_state.poisson(np.round(v), 1))
        elif noise == 'uniform':
            v += self.random_state.uniform(-1, 1) * noise_multiplier
        return v

cum_det = SynError('cum_det', motor, 'motor', center=0, Imax=10,
                     noise='uniform', sigma=1, noise_multiplier=0.1,
                     labels={'detectors'})

def test_live_edge_fit():
    lef = LiveEdgeFit(GaussianModel(), 'cum_det', {'x':'motor'})
    RE = RunEngine({})
    bec = BestEffortCallback()
    RE(scan([cum_det], motor, -5,5,101), [bec, lef])
    lef.result.plot()

def test_live_cbs_factory():
    motor.move = motor.set
    RE = RunEngine({})
    RE(scan([noisy_det], motor, -5,5,101),
       RunRouter([LiveCbsFactory(motor, noisy_det, 'fit', update_every=101)]))

    RE(scan([cum_det], motor, -5,5,101),
       RunRouter([LiveCbsFactory(motor, cum_det, 'edgefit', update_every=101)]))

