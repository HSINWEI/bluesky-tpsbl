from ophyd import Device
from ophyd import Component as Cpt
from types import SimpleNamespace

class MotorManager(Device):
    motors = []
    def __init__(self, *args, fstr_width=10, fstr_prec=5, connection_timeout=0.1, **kwargs):
        Device.__init__(self, *args, **kwargs)
        self.fstr_width = fstr_width
        self.fstr_prec = fstr_prec
        self.connection_timeout = connection_timeout

    def add_motor(self, motor):
        self.motors.append(motor)

    #deprecated
    def get_object_ref_name(self, obj):
        '''
            used when device is created outside of MotorManager
        '''
        if obj.dotted_name == '':
            ''' find obj ref name in parent or globals()  '''
            index = list(globals().values()).index(obj)
            ref_name = list(globals().keys())[index]
        else:
            ''' find obj parent's name '''
            last_dotted_name = obj.dotted_name.split('.')[-1]
            ref_name = f"{self.get_object_ref_name(obj.parent)}.{last_dotted_name}"
        return ref_name

    @property
    def motors_val(self):
        motors_val = {}
        for motor in self.motors:
            try:
                # motor_ref_name = self.get_object_ref_name(motor)
                motor_ref_name = motor.dotted_name
                motors_val[f'{motor_ref_name}'] = motor.user_setpoint.get(connection_timeout=self.connection_timeout)

            except Exception as e:
                print(e)
        return motors_val

    def show_all(self):
        import cmd
        import os
        from more_itertools import grouper
        motors_val = self.motors_val
        rows, columns = os.popen('stty size', 'r').read().split()
        field_len = max(max([len(name) for name in motors_val.keys()])+1,self.fstr_width)
        fields_per_line = int(int(columns)/field_len)
        data_group = grouper(motors_val, fields_per_line)
        for dg in data_group:
            for data_key in dg:
                if data_key:
                    print(f"{data_key:>{field_len}s}", end='')
            print('')
            for data_key in dg:
                if data_key:
                    print(f"{motors_val[data_key]:{field_len}.{self.fstr_prec}f}", end='')
            print('')
            print('')

    def __call__(self):
        self.show_all()

    def __repr__(self):
        from contextlib import redirect_stdout
        import io
        sio = io.StringIO()
        with redirect_stdout(sio):
            self.show_all()
        return sio.getvalue()

    def ns(self):
        ns_dict = {}
        for name in self.component_names:
            ns_dict[name] = getattr(self, name)

        return SimpleNamespace(**ns_dict)

from ophyd import EpicsMotor
class EpicsMotorMM(EpicsMotor):
    def __init__(self, *args, **wkargs):
        EpicsMotor.__init__(self, *args, **wkargs)

        mm_candicate = self.parent
        while mm_candicate.parent:
            mm_candicate = mm_candicate.parent
        mm_candicate.add_motor(self)


''' example
from ophyd import Device
from from tpsbl.ophyd.motor_manager import EpicsMotorMM as EpicsMotor
class Slits(Device):
    t = Cpt(EpicsMotor,     'ZPlus')
    b = Cpt(EpicsMotor,    'ZMinus')
    r = Cpt(EpicsMotor,     'XPlus')
    l = Cpt(EpicsMotor,    'XMinus')
    ho = Cpt(EpicsMotor, 'XOpening')
    hc = Cpt(EpicsMotor,  'XCenter')
    vo = Cpt(EpicsMotor, 'ZOpening')
    vc = Cpt(EpicsMotor,  'ZCenter')

from tpsbl.ophyd.motor_manager import MotorManager
class MotorManager19a(MotorManager):
    s1 = Cpt(Slits, "Slits1:")
    s2 = Cpt(Slits, "Slits2:")

wa = MotorManager19a("19a:", name='')
globals().update(wa.ns().__dict__)

'''
