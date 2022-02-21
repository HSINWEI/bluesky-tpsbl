# Set up a RunRouter suitable for exporting from many runs.
import copy
import pandas as pd
from suitcase.csv import Serializer as CSVSerializer
class XYESerializer(CSVSerializer):
    '''
        Method 1: override superior function
            This is method 1.

        Method 2: Run-time method patching
            instantiate csv_serializer
            csv_serializer.event_page  = types.MethodType(to_xye, csv_serializer)

        Parameters
        ----------
        xye_prefix : str, optional
            The second part of the filename of the generated xye files. This
        string may include templates as in
        ``{motor1-{event[data][motor1_setpoint]}-motor2-{event[data][motor2_setpoint]}``,
        The default value is extracted all motors except the innermost motor from RunStart document
    '''
    def __init__(self, y_data_name, x_data_name, *args, xye_prefix=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._xye_prefix = xye_prefix
        self.y_data_name = y_data_name
        self.x_data_name = x_data_name

    def start(self,doc):
        super().start(doc)

        # hint: md_args.extend([repr(motor), pos_list])
        if self._xye_prefix == None:
            mtr_sp_list = [f'seq_num-{{event[seq_num][0]:04d}}']
            if 'args' in doc['plan_args'].keys():
                for motorname in (doc['motors'][:-1] or doc['motors']):
                    mtr_sp_list.append(f"{motorname}-{{event[data][{motorname}_user_setpoint][0]:.2f}}")
            self._xye_prefix = '-'.join(mtr_sp_list)

    def to_xye(self, doc):
        df = pd.DataFrame({self.x_data_name:doc['data'][self.x_data_name][0].round(3),
                           self.y_data_name:doc['data'][self.y_data_name][0].round(1)})
        df=df.set_index(self.x_data_name)
        df.index.name = self.x_data_name
        _templated_xye_prefix = self._xye_prefix.format(event=doc)
        filename = (f'{self._templated_file_prefix}'
                    f"{_templated_xye_prefix}.xye")
        f = self._manager.open('stream_data', filename, 'xt')
        df.to_csv(f, **self._kwargs)

    def event_page(self, doc):
        if (len(doc['data'].get(self.x_data_name,[])) and
            len(doc['data'].get(self.y_data_name,[]))):
            ''' filter out unfilled data '''
            doc_new = copy.deepcopy(doc)
            if not all(map(all, doc['filled'].values())):
                # check that all event_page data is filled.
                unfilled_data = []
                for field, filled in doc['filled'].items():
                    if not all(filled):
                        unfilled_data.append(field)
                        del doc_new['data'][field]
                        del doc_new['filled'][field]
            self.to_xye(doc_new)

    def stop(self, doc):
        super().stop(doc)
