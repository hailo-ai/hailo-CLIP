import os
import re
batch_size = 8
video_sink = "xvimagesink"
# Note: only 16:9 resolutions are supported
# RES_X = 1920
# RES_Y = 1080
RES_X = 1280
RES_Y = 720

# Check Hailo Device Type from the environment variable DEVICE_ARCHITECTURE
# If the environment variable is not set, default to HAILO8L
device_architecture = os.getenv("DEVICE_ARCHITECTURE")
if device_architecture is None or device_architecture == "HAILO8L":
    device_architecture = "HAILO8L"
    # HEF files for H8L
    YOLO5_HEF_NAME = "yolov5s_personface_h8l_pi.hef"
    CLIP_HEF_NAME = "clip_resnet_50x4_h8l.hef"
else:
    device_architecture = "HAILO8"
    # HEF files for H8
    YOLO5_HEF_NAME = "yolov5s_personface.hef"
    CLIP_HEF_NAME = "clip_resnet_50x4.hef"

from hailo_apps_infra.gstreamer_helper_pipelines import (
    SOURCE_PIPELINE,
    QUEUE,
    INFERENCE_PIPELINE,
    INFERENCE_PIPELINE_WRAPPER,
    TRACKER_PIPELINE,
    DISPLAY_PIPELINE,
    CROPPER_PIPELINE
)


###################################################################
# NEW helper function to add in your gstreamer_helper_pipelines.py
###################################################################


def get_pipeline(self):
    # Initialize directories and paths
    RESOURCES_DIR = os.path.join(self.current_path, "resources")
    POSTPROCESS_DIR = self.tappas_postprocess_dir
    hailopython_path = os.path.join(self.current_path, "clip_app/clip_hailopython.py")
    # personface
    YOLO5_POSTPROCESS_SO = os.path.join(POSTPROCESS_DIR, "libyolo_post.so")
    YOLO5_NETWORK_NAME = "yolov5_personface_letterbox"
    YOLO5_HEF_PATH = os.path.join(RESOURCES_DIR, YOLO5_HEF_NAME)
    YOLO5_CONFIG_PATH = os.path.join(RESOURCES_DIR, "configs/yolov5_personface.json")
    DETECTION_POST_PIPE = f'hailofilter so-path={YOLO5_POSTPROCESS_SO} qos=false function_name={YOLO5_NETWORK_NAME} config-path={YOLO5_CONFIG_PATH} '
    hef_path = YOLO5_HEF_PATH

    # CLIP
    clip_hef_path = os.path.join(RESOURCES_DIR, CLIP_HEF_NAME)
    clip_postprocess_so = os.path.join(RESOURCES_DIR, "libclip_post.so")
    DEFAULT_CROP_SO = os.path.join(RESOURCES_DIR, "libclip_croppers.so")
    clip_matcher_so = os.path.join(RESOURCES_DIR, "libclip_matcher.so")
    clip_matcher_config = os.path.join(self.current_path, "embeddings.json")

    source_pipeline = SOURCE_PIPELINE(
        video_source=self.input_uri,
        video_width=RES_X,
        video_height=RES_Y,
        video_format='RGB',
        name='source'
    )

    detection_pipeline = INFERENCE_PIPELINE(
            hef_path=hef_path,
            post_process_so=YOLO5_POSTPROCESS_SO,
            batch_size=batch_size,
            config_json=YOLO5_CONFIG_PATH,
            post_function_name=YOLO5_NETWORK_NAME,
            scheduler_priority=31,
            scheduler_timeout_ms=100,
            name='detection_inference'
        )

    if self.detector == "none":
        detection_pipeline_wrapper = ""
    else:
        detection_pipeline_wrapper = INFERENCE_PIPELINE_WRAPPER(detection_pipeline)


    clip_pipeline = INFERENCE_PIPELINE(
            hef_path=clip_hef_path,
            post_process_so=clip_postprocess_so,
            batch_size=batch_size,
            name='clip_inference',
            scheduler_timeout_ms=1000,
            scheduler_priority=16,
        )

    if self.detector == "person":
        class_id = 1
        crop_function_name = "person_cropper"
    elif self.detector == "face":
        class_id = 2
        crop_function_name = "face_cropper"
    else: # fast_sam
        class_id = 0
        crop_function_name = "object_cropper"

    tracker_pipeline = TRACKER_PIPELINE(class_id=class_id, keep_past_metadata=True)



    # Clip pipeline with cropper integration
    clip_cropper_pipeline = CROPPER_PIPELINE(
        inner_pipeline=clip_pipeline,
        so_path=DEFAULT_CROP_SO,
        function_name=crop_function_name,
        name='clip_cropper'
    )

    # Clip pipeline with muxer integration (no cropper)
    clip_pipeline_wrapper = " ! ".join([
        "tee name=clip_t hailomuxer name=clip_hmux clip_t.",
        str(QUEUE(name="clip_bypass_q", max_size_buffers=20)),
        "clip_hmux.sink_0 clip_t.",
        str(QUEUE(name="clip_muxer_queue")),
        "videoscale n-threads=4 qos=false",
        clip_pipeline,
        "clip_hmux.sink_1 clip_hmux.",
        str(QUEUE(name="clip_hmux_queue"))
    ])

    # TBD aggregator does not support ROI classification
    # clip_pipeline_wrapper = INFERENCE_PIPELINE_WRAPPER(clip_pipeline, name='clip')

    display_pipeline = DISPLAY_PIPELINE(video_sink=video_sink, sync=self.sync_req, show_fps=self.show_fps)

    # Text to image matcher
    CLIP_PYTHON_MATCHER = f'hailopython name=pyproc module={hailopython_path} qos=false '
    CLIP_CPP_MATCHER = f'hailofilter so-path={clip_matcher_so} qos=false config-path={clip_matcher_config} '

    clip_postprocess_pipeline = " ! ".join([
        CLIP_PYTHON_MATCHER,
        str(QUEUE(name="clip_postprocess_queue")),
        "identity name=identity_callback"
    ])

    # PIPELINE
    if self.detector == "none":
        PIPELINE = " ! ".join([
            source_pipeline,
            clip_pipeline_wrapper,
            clip_postprocess_pipeline,
            display_pipeline
        ])
    else:
        PIPELINE = " ! ".join([
            source_pipeline,
            detection_pipeline_wrapper,
            tracker_pipeline,
            clip_cropper_pipeline,
            clip_postprocess_pipeline,
            display_pipeline
        ])

    return PIPELINE
