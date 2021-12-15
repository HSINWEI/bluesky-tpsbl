from ophyd.areadetector import (AreaDetector, ImagePlugin,
                                TIFFPlugin, StatsPlugin,
                                ProcessPlugin, ROIPlugin,
                                TransformPlugin)
from ophyd.areadetector.filestore_mixins import (FileStoreIterativeWrite,
                                                 FileStoreTIFFSquashing)
from ophyd.areadetector.trigger_mixins import SingleTrigger, MultiTrigger
from ophyd import (Component as Cpt, Signal)

'''
    common
'''
class XPDTIFFPlugin(TIFFPlugin, FileStoreTIFFSquashing,
                    FileStoreIterativeWrite):
    def __init__(self, *args, md={}, **kwargs):
        super().__init__(*args, **kwargs)
        self.md = md
        self.filename_desc = ""

    def make_filename(self):
        filename, read_path, write_path = super().make_filename()
        ''' overwrite short_uid filename '''
        if 'sample_name' in self.md:
            filename = f'{self.md["sample_name"]}'
            if len(self.filename_desc)>0:
                filename += f'_{self.filename_desc}'
        return filename, read_path, write_path

'''
    Eiger Detector
'''
class EigerDetector(AreaDetector):
    image = Cpt(ImagePlugin, 'image1:')
    _default_configuration_attrs = (
        AreaDetector._default_configuration_attrs +
        ('images_per_set', 'number_of_sets', 'pixel_size'))
    tiff = Cpt(XPDTIFFPlugin, 'TIFF1:',
               write_path_template='/a/b/c/',
               read_path_template=None,
               cam_name='cam',  # used to configure "tiff squashing"
               proc_name='proc',  # ditto
               read_attrs=[],
               root=None,
               path_semantics='posix',
               )

    proc = Cpt(ProcessPlugin, 'Proc1:')
    trans1 = Cpt(TransformPlugin, 'Trans1:')

    # These attributes together replace `num_images`. They control
    # summing images before they are stored by the detector (a.k.a. "tiff
    # squashing").
    images_per_set = Cpt(Signal, value=1, add_prefix=())
    number_of_sets = Cpt(Signal, value=1, add_prefix=())

    pixel_size = Cpt(Signal, value=.0001, kind='config')
    #testing DO
    detector_type = Cpt(Signal, value='Eiger', kind='config')
    stats1 = Cpt(StatsPlugin, 'Stats1:')
    stats2 = Cpt(StatsPlugin, 'Stats2:')
    stats3 = Cpt(StatsPlugin, 'Stats3:')
    stats4 = Cpt(StatsPlugin, 'Stats4:')
    stats5 = Cpt(StatsPlugin, 'Stats5:', kind = 'hinted')
    #stats5.total.kind = 'hinted'

    roi1 = Cpt(ROIPlugin, 'ROI1:')
    roi2 = Cpt(ROIPlugin, 'ROI2:')
    roi3 = Cpt(ROIPlugin, 'ROI3:')
    roi4 = Cpt(ROIPlugin, 'ROI4:')

    # dark_image = Cpt(SavedImageSignal, None)

    def __init__(self, *args, md={}, **kwargs):
        super().__init__(*args, **kwargs)
        self.md = md
        self.tiff.md = md
        self.stage_sigs.update([('cam.trigger_mode', 'Internal Series')])
        self.stage_sigs.update([('cam.acquire_time', 1)])
        self.tiff.stage_sigs.update([(self.proc.nd_array_port, self.trans1.port_name.get())])

        ''' ref. ophyd.areadetector.plugins.ImagePlugin '''
        self.image.shaped_image._shape = (self.image.array_size.height,
                                          self.image.array_size.width,
                                          self.image.array_size.depth)
        self.image.shaped_image.kind = 'normal'
        self.image.kind = 'normal'

    def stage(self):
        exp_time_sig_name = 'cam.acquire_time'
        acq_period_sig_name = 'cam.acquire_period'
        exp_time = self.md.get('ctrlprops',{}).get('exposure_time')
        if exp_time:
            self.stage_sigs.update([(exp_time_sig_name, exp_time)])
            self.stage_sigs.update([(acq_period_sig_name, exp_time)])
        else:
            if exp_time_sig_name in self.stage_sigs:
                del self.stage_sigs[exp_time_sig_name]
            if acq_period_sig_name in self.stage_sigs:
                del self.stage_sigs[acq_period_sig_name]

        return super().stage()

class EigerStandard(SingleTrigger, EigerDetector):
    pass

'''
    PerkinElmer Detector
'''
from ophyd.areadetector import PerkinElmerDetector
class XPDPerkinElmer(PerkinElmerDetector):
    image = Cpt(ImagePlugin, 'image1:')
    _default_configuration_attrs = (
        PerkinElmerDetector._default_configuration_attrs +
        ('images_per_set', 'number_of_sets', 'pixel_size'))
    tiff = Cpt(XPDTIFFPlugin, 'TIFF1:',
               write_path_template='/a/b/c/',
               read_path_template=None,
               cam_name='cam',  # used to configure "tiff squashing"
               proc_name='proc',  # ditto
               read_attrs=[],
               root=f'/blsw/19a/data/commission/',
               path_semantics='windows',
               )

    # hdf5 = Cpt(XPDHDF5Plugin, 'HDF1:',
    #          write_path_template='G:/pe1_data/%Y/%m/%d/',
    #          read_path_template='/direct/XF28ID2/pe1_data/%Y/%m/%d/',
    #          root='/direct/XF28ID2/')

    proc = Cpt(ProcessPlugin, 'Proc1:')
    trans1 = Cpt(TransformPlugin, 'Trans1:')

    # These attributes together replace `num_images`. They control
    # summing images before they are stored by the detector (a.k.a. "tiff
    # squashing").
    images_per_set = Cpt(Signal, value=1, add_prefix=())
    number_of_sets = Cpt(Signal, value=1, add_prefix=())

    pixel_size = Cpt(Signal, value=.0001, kind='config')
    #testing DO
    detector_type = Cpt(Signal, value='Perkin', kind='config')
    stats1 = Cpt(StatsPlugin, 'Stats1:')
    stats2 = Cpt(StatsPlugin, 'Stats2:')
    stats3 = Cpt(StatsPlugin, 'Stats3:')
    stats4 = Cpt(StatsPlugin, 'Stats4:')
    stats5 = Cpt(StatsPlugin, 'Stats5:', kind = 'hinted')
    #stats5.total.kind = 'hinted'

    roi1 = Cpt(ROIPlugin, 'ROI1:')
    roi2 = Cpt(ROIPlugin, 'ROI2:')
    roi3 = Cpt(ROIPlugin, 'ROI3:')
    roi4 = Cpt(ROIPlugin, 'ROI4:')

    # dark_image = Cpt(SavedImageSignal, None)

    def __init__(self, *args, md={}, **kwargs):
        super().__init__(*args, **kwargs)
        self.md = md
        self.tiff.md = md
        self.stage_sigs.update([('cam.trigger_mode', 'Internal')])
        self.stage_sigs.update([('cam.acquire_time', 1)])
        self.tiff.stage_sigs.update([(self.proc.nd_array_port, self.trans1.port_name.get())])

    def stage(self):
        exp_time_sig_name = 'cam.acquire_time'
        exp_time = self.md.get('ctrlprops',{}).get('exposure_time')
        if exp_time:
            self.stage_sigs.update([(exp_time_sig_name, exp_time)])
        else:
            if exp_time_sig_name in self.stage_sigs:
                del self.stage_sigs[exp_time_sig_name]

        return super().stage()

class PerkinElmerTrigger:
    def trigger(self):
        ''' set exposure time again '''
        acq_time_key = 'cam.acquire_time'
        if acq_time_key in self.stage_sigs:
            self.cam.acquire_time._set_and_wait(self.stage_sigs[acq_time_key], 3.0)

class PerkinElmerStandard(SingleTrigger, XPDPerkinElmer, PerkinElmerTrigger):
    def trigger(self):
        PerkinElmerTrigger.trigger(self)
        return SingleTrigger.trigger(self)

class PerkinElmerMulti(MultiTrigger, XPDPerkinElmer):
    def trigger(self):
        PerkinElmerTrigger.trigger(self)
        return MultiTrigger.trigger(self)

