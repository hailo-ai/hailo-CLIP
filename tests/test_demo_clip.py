import pytest
import subprocess
import os
import sys
import time
import signal
import glob
import logging
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Add path for clip app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from picamera2 import Picamera2
    rpi_camera_available = True
except ImportError:
    rpi_camera_available = False

# Constants
TEST_RUN_TIME = 5  # Same as Hailo RPi examples
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def get_usb_video_devices():
    """Get a list of video devices that are connected via USB and have video capture capability."""
    video_devices = [f'/dev/{device}' for device in os.listdir('/dev') if device.startswith('video')]
    usb_video_devices = []

    for device in video_devices:
        try:
            udevadm_cmd = ["udevadm", "info", "--query=all", "--name=" + device]
            result = subprocess.run(udevadm_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode('utf-8')

            if "ID_BUS=usb" in output and ":capture:" in output:
                usb_video_devices.append(device)
        except Exception as e:
            print(f"Error checking device {device}: {e}")

    return usb_video_devices

def check_rpi_camera_available():
    """Check if RPi camera is available."""
    try:
        result = subprocess.run(
            ['rpicam-hello', '-t', '1'],
            capture_output=True,
            text=True,
            timeout=2
        )
        return "no cameras available" not in result.stderr.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def test_rpi_camera_connection():
    """Test if RPI camera is connected by running rpicam-hello."""
    log_file_path = os.path.join(LOG_DIR, "rpi_camera_test.log")

    with open(log_file_path, "w") as log_file:
        process = subprocess.Popen(
            ['rpicam-hello', '-t', '0', '--post-process-file', '/usr/share/rpi-camera-assets/hailo_yolov6_inference.json'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            time.sleep(TEST_RUN_TIME)
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail(f"RPI camera connection test could not be terminated")

        stdout, stderr = process.communicate()
        log_file.write(f"rpi_camera stdout:\n{stdout.decode()}\n")
        log_file.write(f"rpi_camera stderr:\n{stderr.decode()}\n")

        if "ERROR: *** no cameras available ***" in stderr.decode():
            pytest.skip("RPI camera is not connected")
        else:
            log_file.write("RPI camera is connected and working.\n")

def test_demo_clip():
    """Test CLIP application with demo video."""
    log_file_path = os.path.join(LOG_DIR, "clip_demo_test.log")

    with open(log_file_path, "w") as log_file:
        process = subprocess.Popen(
            ['python', 'clip_application.py', '--input', 'demo', '--disable-runtime-prompts'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            time.sleep(TEST_RUN_TIME)
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail(f"Demo clip test could not be terminated")

        stdout, stderr = process.communicate()
        log_file.write(f"Demo clip stdout:\n{stdout.decode()}\n")
        log_file.write(f"Demo clip stderr:\n{stderr.decode()}\n")

        assert "Traceback" not in stderr.decode(), f"Exception occurred in demo test: {stderr.decode()}"
        assert "Error" not in stderr.decode(), f"Error occurred in demo test: {stderr.decode()}"
        log_file.write("Demo clip test completed successfully.\n")

def test_all_detectors():
    """Test CLIP application with different detectors."""
    detectors = ['none', 'person', 'face']
    
    for detector in detectors:
        log_file_path = os.path.join(LOG_DIR, f"clip_{detector}_test.log")
        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(
                ['python', 'clip_application.py', '--input', 'demo', '--detector', detector, '--disable-runtime-prompts'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            try:
                time.sleep(TEST_RUN_TIME)
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail(f"{detector} detector test could not be terminated")

            stdout, stderr = process.communicate()
            log_file.write(f"{detector} detector stdout:\n{stdout.decode()}\n")
            log_file.write(f"{detector} detector stderr:\n{stderr.decode()}\n")

            assert "Traceback" not in stderr.decode(), f"Exception occurred with detector {detector}: {stderr.decode()}"
            assert "Error" not in stderr.decode(), f"Error occurred with detector {detector}: {stderr.decode()}"
            log_file.write(f"{detector} detector test completed successfully.\n")

@pytest.mark.camera
def test_usb_camera():
    """Test CLIP application with USB camera."""
    usb_cameras = get_usb_video_devices()
    if not usb_cameras:
        pytest.skip("No USB cameras found")

    for camera in usb_cameras:
        device_name = os.path.basename(camera)
        log_file_path = os.path.join(LOG_DIR, f"clip_usb_camera_{device_name}_test.log")

        with open(log_file_path, "w") as log_file:
            process = subprocess.Popen(
                ['python', 'clip_application.py', '--input', camera, '--disable-runtime-prompts'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            try:
                time.sleep(TEST_RUN_TIME)
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail(f"USB camera test for {camera} could not be terminated")

            stdout, stderr = process.communicate()
            log_file.write(f"USB camera stdout:\n{stdout.decode()}\n")
            log_file.write(f"USB camera stderr:\n{stderr.decode()}\n")

            assert "Traceback" not in stderr.decode(), f"Exception occurred with USB camera: {stderr.decode()}"
            assert "Error" not in stderr.decode(), f"Error occurred with USB camera: {stderr.decode()}"
            log_file.write("USB camera test completed successfully.\n")

#### this is the original code for the run of clip with rpi camera , need to fix rpi input 
# @pytest.mark.camera
# def test_rpi_camera():
#     """Test CLIP application with RPi camera."""
#     if not check_rpi_camera_available():
#         pytest.skip("RPi camera not available")

#     log_file_path = os.path.join(LOG_DIR, "clip_rpi_camera_test.log")

#     with open(log_file_path, "w") as log_file:
#         process = subprocess.Popen(
#             ['python3', '-m', 'clip_app.clip_app', '--input', 'rpi', '--disable-runtime-prompts'],
#             stdout=subprocess.PIPE, stderr=subprocess.PIPE)

#         try:
#             time.sleep(TEST_RUN_TIME)
#             process.send_signal(signal.SIGTERM)
#             process.wait(timeout=5)
#         except subprocess.TimeoutExpired:
#             process.kill()
#             pytest.fail("RPi camera test could not be terminated")

#         stdout, stderr = process.communicate()
#         log_file.write(f"RPi camera stdout:\n{stdout.decode()}\n")
#         log_file.write(f"RPi camera stderr:\n{stderr.decode()}\n")

#         assert "Traceback" not in stderr.decode(), f"Exception occurred with RPi camera: {stderr.decode()}"
#         assert "Error" not in stderr.decode(), f"Error occurred with RPi camera: {stderr.decode()}"
#         log_file.write("RPi camera test completed successfully.\n")

if __name__ == "__main__":
    pytest.main(["-v", __file__])