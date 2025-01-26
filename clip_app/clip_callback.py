import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

class app_callback_class:
    def __init__(self):
        self.frame_count = 0
        self.use_frame = False
        self.running = True

    def increment(self):
        self.frame_count += 1

    def get_count(self):
        return self.frame_count

def dummy_callback(self, pad, info, user_data):
    """
    A minimal dummy callback function that returns immediately.

    Args:
        pad: The GStreamer pad
        info: The probe info
        user_data: User-defined data passed to the callback

    Returns:
        Gst.PadProbeReturn.OK
    """
    return Gst.PadProbeReturn.OK

