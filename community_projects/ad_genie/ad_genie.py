import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import os
import json
import random
import time
import multiprocessing
import hailo
from PIL import Image, ImageDraw
from hailo_apps_infra.gstreamer_app import app_callback_class
from clip_app.clip_app import ClipApp

class user_app_callback_class(app_callback_class):
    """
    User-defined callback class to process detections and manage display updates.
    """

    def __init__(self):
        """
        Initializes the user callback class, including loading resources,
        setting up the display, and starting the label processing process.
        """
        super().__init__()
        screen_width = 1080
        screen_height = 1920
        self.display = DisplayManager(screen_width, screen_height)
        self.display.show()
        CLOTHES_JSON_PATH = "resources/zara.json"
        CLOTHES_FOLDER = os.path.join("static", "clothes")
        # Load the clothes mapping from JSON
        with open(CLOTHES_JSON_PATH, "r", encoding="utf-8") as f:
            clothes_map = json.load(f)
        self.clothes_map = clothes_map
        self.MAX_QUEUE_SIZE = 3
        self.labels_queue = multiprocessing.Queue(maxsize=self.MAX_QUEUE_SIZE)
        client_process = multiprocessing.Process(target=self.label_to_css, args=(self.labels_queue,))
        client_process.start()

    def parse_lable(self,lable_str):
        """
        Parses a label string to determine the corresponding clothing item file.
        """

        if "Men" in lable_str:
            gender = "Men"
        elif "Women" in lable_str:
            gender = "Women"
            # We also assume the item is after "wearing".
        # For example, "a men wearing REFLECTIVE EFFECT JACKET"
        # -> item_str = "REFLECTIVE EFFECT JACKET"
        parts = lable_str.split("wearing a ")
        if len(parts) > 1:
            item_str = parts[1].strip().upper()  # "REFLECTIVE EFFECT JACKET"
        else:
            item_str = None
        # Attempt to look up the file
        matched_file = None
        if gender and item_str:
            if gender in self.clothes_map.keys() and item_str in self.clothes_map[gender].keys():
                matched_file = self.clothes_map[gender][item_str][0]
        return matched_file

    def update_image(self, file = None):
        """
        Updates the display with a new image.
        """
        if file is None:
            self.display.update_image(f"resources/images/{self.choose_random()}")
        else:
            self.display.update_image(f"resources/images/{file}")
        self.display.show()

    def choose_random(self):
        """
        Chooses a random clothing image from the loaded clothes map.
        """
        gender = random.choice(list(self.clothes_map.keys()))
        item_str = random.choice(list(self.clothes_map[gender].keys()))
        file = random.choice(list(self.clothes_map[gender][item_str]))
        return file

    def label_to_css(self, queue_in,) -> None:
        """
        Processes labels from the queue and updates the display accordingly.
        """
        start = time.time()
        while True:
            if not queue_in.empty():
                label = queue_in.get()
                label = queue_in.get()
                now_time = time.time()
                if now_time - start < 2:
                    continue
                start = time.time()
                matched_file = self.parse_lable(label)
                self.update_image(matched_file)

    def increment(self):
        """Increments the frame count (for potential future use)."""
        self.frame_count += 1

    def get_count(self):
        """
        Retrieves the current frame count.
        """
        return self.frame_count

def user_app_callback(self, pad, info, user_data):
    """
    This is the callback function that will be called when data is available
    from the pipeline.
    Processing time should be kept to a minimum in this function.
    If longer processing is needed, consider using a separate thread / process.
    """
    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    # Check if the buffer is valid
    if buffer is None:
        return Gst.PadProbeReturn.OK
    string_to_print = ""
    # Get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
    if len(detections) == 0:
        detections = [roi] # Use the ROI as the detection
    # Parse the detections
    for detection in detections:
        track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
        track_id = None
        label = None
        confidence = 0.0
        for track_id_obj in track:
            track_id = track_id_obj.get_id()
        if track_id is not None:
            string_to_print += f'Track ID: {track_id} '
        classifications = detection.get_objects_typed(hailo.HAILO_CLASSIFICATION)
        if len(classifications) > 0:
            string_to_print += ' CLIP Classifications:'
            for classification in classifications:
                label = classification.get_label()
                user_data.labels_queue.put(label)
                confidence = classification.get_confidence()
                string_to_print += f'Label: {label} Confidence: {confidence:.2f} '
            string_to_print += '\n'
        if isinstance(detection, hailo.HailoDetection):
            label = detection.get_label()
            bbox = detection.get_bbox()
            confidence = detection.get_confidence()
            string_to_print += f"Detection: {label} {confidence:.2f}\n"
    if string_to_print:
        print(string_to_print)
    return Gst.PadProbeReturn.OK

class DisplayManager:
    """
    Manages the display canvas for showing images and logos.
    """
    def __init__(self, screen_width, screen_height):
        """
        Initializes the display manager with screen dimensions.
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.canvas = Image.new('RGB', (screen_width, screen_height), color='white')  # white canvas
        self.image = None
        self.left_logo = None
        self.right_logo = None

    def update_image(self, image_path):
        """
        Updates the canvas with a new image.
        """
        new_image = Image.open(image_path)
        img_width, img_height = new_image.size
        left_margin = (self.screen_width - img_width) // 2
        top_margin = (self.screen_height - img_height) // 2
        self.canvas.paste(new_image, (left_margin, top_margin))
        self.image = new_image

    def update_logos(self, left_logo_path=None, right_logo_path=None):
        """
        Updates the canvas with logos at the bottom corners.
        """
        draw = ImageDraw.Draw(self.canvas)  # to draw white placeholders for logos

        # Handle the left logo
        if left_logo_path:
            left_logo = Image.open(left_logo_path).convert('RGBA')  # Ensure RGBA mode for transparency
            left_logo = left_logo.resize((100, 100))  # Resize logo if needed
            self.left_logo = left_logo
            logo_x = 0
            logo_y = self.screen_height - left_logo.height
            # Use the alpha channel of the logo as the mask for pasting
            self.canvas.paste(left_logo, (logo_x, logo_y), left_logo.split()[3])  # Alpha channel as mask

        # Handle the right logo
        if right_logo_path:
            right_logo = Image.open(right_logo_path).convert('RGBA')  # Ensure RGBA mode for transparency
            right_logo = right_logo.resize((100, 100))  # Resize logo if needed
            self.right_logo = right_logo
            logo_x = self.screen_width - right_logo.width
            logo_y = self.screen_height - right_logo.height
            # Use the alpha channel of the logo as the mask for pasting
            self.canvas.paste(right_logo, (logo_x, logo_y), right_logo.split()[3])  # Alpha channel as mask

    def show(self):
        """Displays the current canvas."""
        self.canvas.show()

    def save(self, save_path):
        """
        Saves the current canvas to a file.
        """
        self.canvas.save(save_path)
        
if __name__ == "__main__":
    user_data = user_app_callback_class()
    clip = ClipApp(user_data, user_app_callback)
    clip.run()

