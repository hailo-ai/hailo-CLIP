import os
import argparse
import logging
import sys
import signal
import importlib.util
from functools import partial
import gi
import threading
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst, GLib
from clip_app.logger_setup import setup_logger, set_log_level
from clip_app.clip_pipeline import get_pipeline
from clip_app.text_image_matcher import text_image_matcher
from clip_app import gui
from hailo_apps_infra.gstreamer_app import picamera_thread
from hailo_apps_infra.gstreamer_helper_pipelines import get_source_type

# add logging
logger = setup_logger()
set_log_level(logger, logging.INFO)


class ClipApp():
    def __init__(self, user_data, app_callback):
        self.args = self.parse_arguments().parse_args()
        
        self.app_callback = app_callback
        set_log_level(logger, logging.INFO)

        self.user_data = user_data
        self.win = AppWindow(self.args, self.user_data, self.app_callback)
    def run(self):
        self.win.connect("destroy", self.on_destroy)
        self.win.show_all()
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        Gtk.main()
        
    def on_destroy(self, window):
        logger.info("Destroying window...")
        window.quit_button_clicked(None)
        
    def parse_arguments(self):
        parser = argparse.ArgumentParser(description="Hailo online CLIP app")
        parser.add_argument("--input", "-i", type=str, default="/dev/video0", help="Input source. Can be a file, USB (webcam), RPi camera (CSI camera module). \
        For RPi camera use '-i rpi' \
        For demo video use '--input demo'. \
        Default is /dev/video0.")
        parser.add_argument("--detector", "-d", type=str, choices=["person", "face", "none"], default="none", help="Which detection pipeline to use.")
        parser.add_argument("--json-path", type=str, default=None, help="Path to JSON file to load and save embeddings. If not set, embeddings.json will be used.")
        parser.add_argument("--disable-sync", action="store_true",help="Disables display sink sync, will run as fast as possible. Relevant when using file source.")
        parser.add_argument("--dump-dot", action="store_true", help="Dump the pipeline graph to a dot file.")
        parser.add_argument("--detection-threshold", type=float, default=0.5, help="Detection threshold.")
        parser.add_argument("--show-fps", "-f", action="store_true", help="Print FPS on sink.")
        parser.add_argument("--disable-runtime-prompts", action="store_true", help="When set, app will not support runtime prompts. Default is False.")

        return parser

class AppWindow(Gtk.Window):
    # Add GUI functions to the AppWindow class
    build_ui = gui.build_ui
    add_text_boxes = gui.add_text_boxes
    update_text_boxes = gui.update_text_boxes
    update_text_prefix = gui.update_text_prefix
    quit_button_clicked = gui.quit_button_clicked
    on_text_box_updated = gui.on_text_box_updated
    on_slider_value_changed = gui.on_slider_value_changed
    on_negative_check_button_toggled = gui.on_negative_check_button_toggled
    on_ensemble_check_button_toggled = gui.on_ensemble_check_button_toggled
    on_load_button_clicked = gui.on_load_button_clicked
    on_save_button_clicked = gui.on_save_button_clicked
    update_progress_bars = gui.update_progress_bars
    on_track_id_update = gui.on_track_id_update
    disable_text_boxes = gui.disable_text_boxes

    # Add the get_pipeline function to the AppWindow class
    get_pipeline = get_pipeline


    def __init__(self, args, user_data, app_callback):
        Gtk.Window.__init__(self, title="Clip App")
        self.set_border_width(10)
        self.set_default_size(1, 1)
        self.fullscreen_mode = False

        self.current_path = os.path.dirname(os.path.realpath(__file__))
        # move self.current_path one directory up to get the path to the workspace
        self.current_path = os.path.dirname(self.current_path)
        os.environ["GST_DEBUG_DUMP_DOT_DIR"] = self.current_path

        self.tappas_postprocess_dir = os.environ.get('TAPPAS_POST_PROC_DIR', '')
        if self.tappas_postprocess_dir == '':
            logger.error("TAPPAS_POST_PROC_DIR environment variable is not set. Please set it by sourcing setup_env.sh")
            sys.exit(1)

        # Create options menu
        self.options_menu = args

        self.dump_dot = self.options_menu.dump_dot
        self.video_source = self.options_menu.input
        self.source_type = get_source_type(self.video_source)
        self.sync = "false" if (self.options_menu.disable_sync or self.source_type != "file") else "true"
        self.show_fps = self.options_menu.show_fps
        self.json_file = os.path.join(self.current_path, "embeddings.json") if self.options_menu.json_path is None else self.options_menu.json_path
        if self.options_menu.input == "demo":
            self.input = os.path.join(self.current_path, "resources", "clip_example.mp4")
            self.json_file = os.path.join(self.current_path, "example_embeddings.json") if self.options_menu.json_path is None else self.options_menu.json_path
        else:
            self.input = self.options_menu.input
        self.detector = self.options_menu.detector
        self.user_data = user_data
        self.app_callback = app_callback
        # get current path
        Gst.init(None)
        self.pipeline = self.create_pipeline()
        if self.input == "rpi":
            picam_thread = threading.Thread(target=picamera_thread, args=(self.pipeline, 1280, 720, 'RGB'))
            picam_thread.start()
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        # get text_image_matcher instance
        self.text_image_matcher = text_image_matcher
        self.text_image_matcher.set_threshold(self.options_menu.detection_threshold)

        # build UI
        self.max_entries = 6
        self.build_ui(self.options_menu)

        # set runtime
        if self.options_menu.disable_runtime_prompts:
            logger.info("No text embedding runtime selected, adding new text is disabled. Loading %s", self.json_file)
            self.disable_text_boxes()
            self.on_load_button_clicked(None)
        else:
            self.text_image_matcher.init_clip()

        if self.text_image_matcher.model_runtime is not None:
            logger.info("Using %s for text embedding", self.text_image_matcher.model_runtime)
            self.on_load_button_clicked(None)


        identity = self.pipeline.get_by_name("identity_callback")
        if identity is None:
            logger.warning("identity_callback element not found, add <identity name=identity_callback> in your pipeline where you want the callback to be called.")
        else:
            identity_pad = identity.get_static_pad("src")
            identity_pad.add_probe(Gst.PadProbeType.BUFFER, partial(self.app_callback, self), self.user_data)
        # start the pipeline
        self.pipeline.set_state(Gst.State.PLAYING)

        if self.dump_dot:
            GLib.timeout_add_seconds(5, self.dump_dot_file)

        self.update_text_boxes()

        # Define a timeout duration in nanoseconds (e.g., 5 seconds)
        timeout_ns = 5 * Gst.SECOND

        # Wait until state change is done or until the timeout occurs
        state_change_return, _state, _pending = self.pipeline.get_state(timeout_ns)

        if state_change_return == Gst.StateChangeReturn.SUCCESS:
            logger.info("Pipeline state changed to PLAYING successfully.")
        elif state_change_return == Gst.StateChangeReturn.ASYNC:
            logger.info("State change is ongoing asynchronously.")
        elif state_change_return == Gst.StateChangeReturn.FAILURE:
            logger.info("State change failed.")
        else:
            logger.warning("Unknown state change return value.")


    def dump_dot_file(self):
        logger.info("Dumping dot file...")
        Gst.debug_bin_to_dot_file(self.pipeline, Gst.DebugGraphDetails.ALL, "pipeline")
        return False


    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.on_eos()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error("Error: %s %s", err, debug)
            self.shutdown()
        # print QOS messages
        elif t == Gst.MessageType.QOS:
            # print which element is reporting QOS
            src = message.src.get_name()
            logger.info("QOS from %s", src)
        return True


    def on_eos(self):
        logger.info("EOS received, shutting down the pipeline.")
        self.pipeline.set_state(Gst.State.PAUSED)
        GLib.usleep(100000)  # 0.1 second delay

        self.pipeline.set_state(Gst.State.READY)
        GLib.usleep(100000)  # 0.1 second delay

        self.pipeline.set_state(Gst.State.NULL)
        GLib.idle_add(Gtk.main_quit)

    def shutdown(self):
        logger.info("Sending EOS event to the pipeline...")
        self.pipeline.send_event(Gst.Event.new_eos())

    def create_pipeline(self):
        pipeline_str = get_pipeline(self)
        logger.info('PIPELINE:\ngst-launch-1.0 %s', pipeline_str)
        try:
            pipeline = Gst.parse_launch(pipeline_str)
        except GLib.Error as e:
            logger.error("An error occurred while parsing the pipeline: %s", e)
        return pipeline

if __name__ == "__main__":
    run()
