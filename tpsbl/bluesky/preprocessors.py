from bluesky.preprocessors import msg_mutator, plan_mutator
from bluesky.utils import make_decorator
from collections import ChainMap
import bluesky_darkframes

def collect_stream_wrapper(plan):
    def patch_collect(msg):
        if msg.command == 'collect':
            msg = msg._replace(kwargs=ChainMap({'stream':True, 'return_payload':False}, msg.kwargs))
        return msg

    return (yield from msg_mutator(plan, patch_collect))
collect_stream_decorator = make_decorator(collect_stream_wrapper)

class SingleDarkFramePreprocessor(bluesky_darkframes.DarkFramePreprocessor):
    def __call__(self, plan):
        def clear_cache(msg):
            if msg.command == 'open_run':
                self.clear()
                return None, None
            else:
                return None, None
        plan = plan_mutator(plan, clear_cache)
        return super().__call__(plan)
