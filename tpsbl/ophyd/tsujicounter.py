from collections import OrderedDict
from ophyd import (EpicsSignalRO, EpicsSignal, Component as Cpt,
               DynamicDeviceComponent as DDCpt, Device)
from ophyd.device import DeviceStatus

def _chan_fields(attr_base, field_base, range_):
    defn = OrderedDict()
    for i in range_:
        attr = '{attr}{i}'.format(attr=attr_base, i=i)
        suffix = '{field}{i}'.format(field=field_base, i=i)
        defn[attr] = (EpicsSignalRO, suffix, {'kind':'omitted'})
    defn['cht'] = (EpicsSignalRO, 'RDAL:CHT',{'kind':'omitted'})
    return defn

class TsujiCounter(Device):
    clear_and_start = Cpt(EpicsSignal, 'CSTRT.PROC', kind='omitted')
    stop_counting = Cpt(EpicsSignal, 'STOP.PROC', kind='omitted')
    done = Cpt(EpicsSignalRO, 'CNTR_STA.A', kind='omitted')
    counting_time = Cpt(EpicsSignal, 'TPR', write_pv='STPR', kind='config')
    stop_mode = Cpt(EpicsSignalRO, 'MOD:STOPMODE', kind='config', string=True)
    rdal = Cpt(EpicsSignalRO, 'RDAL', kind='normal', auto_monitor=True)

    def __init__(self, *args, md={}, **kwargs):
        self.md = md
        Device.__init__(self, *args, **kwargs)

    def stage(self):
        if self.stop_mode.get() == 'N':
            ''' non-stop mode '''
            self.clear_and_start.set(1)
        else:
            ''' timer stop mode
            exp_time is in the unit second
            counting_time is in the unit microsecond
            '''
        exp_time_sig_name = 'counting_time'
        exp_time = self.md.get('ctrlprops',{}).get('exposure_time')
        if exp_time:
            self.stage_sigs.update([(exp_time_sig_name, int(exp_time*1000))])
        else:
            if exp_time_sig_name in self.stage_sigs:
                del self.stage_sigs[exp_time_sig_name]

        return super().stage()

    def unstage(self):
        if self.stop_mode.get() == 'N':
            self.stop_counting.set(1)

        return super().unstage()

    @property
    def exposure_time(self):
        '''
        :return: in the unit second
        '''
        return self.counting_time.get()/1000

    @exposure_time.setter
    def exposure_time(self,val):
        '''
        :param val: in the unit second
        '''
        st = self.counting_time.set(val*1000)
        st.wait()

    def set_exposure_time(self, val):
        st = self.counting_time.set(val)
        st.wait()

    def trigger(self):
        """
        Trigger the detector and return a Status object.
        """
        status = DeviceStatus(self)

        # Wire up a callback that will mark the status object as finished
        # when we see the state flip from "acquiring" to "not acquiring"---
        # that is, a negative edge.
        def callback(old_value, value, **kwargs):
            if old_value == 1 and value == 0:
                status._finished()
                self.done.clear_sub(callback)

        if self.stop_mode.get() == 'N':
            # doesn't need to set clear_and_start signal
            status._finished()
        else:
            self.done.subscribe(callback)
            # Now 'put' 1 to the clear_and_start signal.
            self.clear_and_start.set(1)


        # And return the Status object, which the caller can use to
        # tell when the action is complete.
        return status

    def select_channels(self, chan_indexs=None, kind='hinted', verbose=False):
        '''
        Select channels based on channel index (0-based)
        channel index includes: 0, 1, ... and 't' for cht
        '''
        if chan_indexs is None:
            for ch_dname in self.channels.component_names:
                if verbose: print('set {} {}'.format(ch_dname, kind))
                getattr(self.channels, ch_dname).kind = kind
        else:
            for chi in chan_indexs:
                ch_dname = 'ch'+str(chi)
                #print(ch_dname)
                if ch_dname in self.channels.component_names:
                    if verbose: print('set {} {}'.format(ch_dname, kind))
                    getattr(self.channels, ch_dname).kind = kind

    def deselect_channels(self, chan_indexs=None, verbose=False):
        self.select_channels(chan_indexs, 'omitted', verbose)

class TsujiCounter8Ch(TsujiCounter):
    channels = DDCpt(_chan_fields('ch','RDAL:CH', range(0, 8)))

class TsujiCounter16Ch(TsujiCounter):
    channels = DDCpt(_chan_fields('ch','RDAL:CH', range(0, 16)))

class TsujiCounter32Ch(TsujiCounter):
    channels = DDCpt(_chan_fields('ch','RDAL:CH', range(0, 32)))

