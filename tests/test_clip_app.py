import os
import pytest
import subprocess
import time
import signal
import json
import cv2
import numpy as np
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Import clip app modules
from clip_app.text_image_matcher import TextImageMatcher, text_image_matcher
import clip_application as callback_module

class TestSanityCheck:
    """Basic sanity checks for the CLIP application."""
    
    def test_hailo_runtime(self):
        """Test if Hailo runtime is installed and accessible."""
        try:
            result = subprocess.run(['hailortcli', '--version'], 
                                  check=True, capture_output=True, text=True)
            assert result.returncode == 0, "Hailo runtime check failed"
            print(f"Hailo runtime version: {result.stdout.strip()}")
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Hailo runtime is not properly installed: {str(e)}")

    def test_required_files(self):
        """Test if all required files exist."""
        required_files = [
            'setup_env.sh',
            'download_resources.sh',
            'compile_postprocess.sh',
            'requirements.txt',
            'resources/libclip_post.so',
            'resources/libclip_matcher.so',
            'resources/libclip_croppers.so'
        ]
        for file in required_files:
            assert os.path.exists(file), f"Required file missing: {file}"

    def test_environment_variables(self):
        """Test if required environment variables are set."""
        required_vars = ['TAPPAS_POST_PROC_DIR', 'DEVICE_ARCHITECTURE']
        for var in required_vars:
            assert os.environ.get(var) is not None, f"Environment variable {var} is not set"
            print(f"{var} is set to: {os.environ.get(var)}")

    def test_verify_device_architecture(self):
        """Verify device architecture is properly detected."""
        device_arch = os.environ.get('DEVICE_ARCHITECTURE')
        assert device_arch in ['HAILO8', 'HAILO8L'], f"Invalid device architecture: {device_arch}"

class TestTextImageMatcher:
    """Tests for the TextImageMatcher functionality."""

    @pytest.fixture(scope="class")
    def matcher(self):
        """Fixture providing a TextImageMatcher instance."""
        return text_image_matcher

    def test_singleton_pattern(self, matcher):
        """Verify TextImageMatcher implements singleton pattern correctly."""
        matcher2 = TextImageMatcher()
        assert matcher is matcher2, "TextImageMatcher singleton pattern failed"

    def test_threshold_setting(self, matcher):
        """Test setting and getting threshold values."""
        test_threshold = 0.75
        matcher.set_threshold(test_threshold)
        assert matcher.threshold == test_threshold
        
        # Test bounds
        matcher.set_threshold(0.0)
        assert matcher.threshold == 0.0
        matcher.set_threshold(1.0)
        assert matcher.threshold == 1.0

    def test_text_prefix(self, matcher):
        """Test setting and getting text prefix."""
        test_prefix = "Testing: "
        original_prefix = matcher.text_prefix
        matcher.set_text_prefix(test_prefix)
        assert matcher.text_prefix == test_prefix
        # Restore original prefix
        matcher.set_text_prefix(original_prefix)

    def test_embeddings_save_load(self, matcher, tmp_path):
        """Test saving and loading embeddings."""
        test_file = tmp_path / "test_embeddings.json"
        
        # Set test values
        test_threshold = 0.85
        test_prefix = "Test prefix: "
        matcher.threshold = test_threshold
        matcher.text_prefix = test_prefix
        
        # Save embeddings
        matcher.save_embeddings(str(test_file))
        
        # Modify values
        matcher.threshold = 0.5
        matcher.text_prefix = "Changed: "
        
        # Load embeddings
        matcher.load_embeddings(str(test_file))
        
        # Verify values were restored
        assert matcher.threshold == test_threshold
        assert matcher.text_prefix == test_prefix

class TestGStreamerPipeline:
    """Tests for GStreamer pipeline functionality."""

    @classmethod
    def setup_class(cls):
        """Initialize GStreamer for pipeline tests."""
        Gst.init(None)

    def test_basic_pipeline(self):
        """Test basic GStreamer pipeline creation and state changes."""
        pipeline_str = (
            'videotestsrc num-buffers=10 ! '
            'video/x-raw,format=RGB,width=640,height=480 ! '
            'fakesink'
        )
        
        try:
            pipeline = Gst.parse_launch(pipeline_str)
            assert pipeline is not None
            
            # Test state changes
            ret = pipeline.set_state(Gst.State.PLAYING)
            assert ret != Gst.StateChangeReturn.FAILURE
            
            time.sleep(1)  # Let it run briefly
            
            ret = pipeline.set_state(Gst.State.NULL)
            assert ret != Gst.StateChangeReturn.FAILURE
            
        except GLib.Error as e:
            pytest.fail(f"Pipeline creation failed: {e}")

    def test_plugin_availability(self):
        """Test if required GStreamer plugins are available."""
        required_plugins = ['hailo', 'hailotools']
        for plugin in required_plugins:
            registry = Gst.Registry.get()
            plugin_obj = registry.find_plugin(plugin)
            assert plugin_obj is not None, f"Required GStreamer plugin '{plugin}' not found"

class TestCallbackFunctionality:
    """Tests for callback functionality."""

    def test_callback_class(self):
        """Test the callback class functionality."""
        callback_instance = callback_module.app_callback_class()
        
        # Test initial state
        assert callback_instance.frame_count == 0
        assert callback_instance.use_frame is False
        assert callback_instance.running is True
        
        # Test frame counter
        callback_instance.increment()
        assert callback_instance.frame_count == 1
        assert callback_instance.get_count() == 1

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_embeddings_file(self, tmp_path):
        """Test handling of invalid embeddings file."""
        matcher = text_image_matcher
        invalid_file = tmp_path / "nonexistent.json"
        
        # Should handle non-existent file
        matcher.load_embeddings(str(invalid_file))
        assert os.path.exists(invalid_file)
        
        # Should handle malformed JSON
        with open(invalid_file, 'w') as f:
            f.write("invalid json content")
        
        try:
            matcher.load_embeddings(str(invalid_file))  # Should not raise exception
        except Exception as e:
            pytest.fail(f"Loading malformed JSON raised an exception: {e}")
    
    def test_empty_embeddings(self):
        """Test matcher behavior with empty embeddings."""
        matcher = text_image_matcher
        empty_embeddings = matcher.get_embeddings()
        assert isinstance(empty_embeddings, list), "get_embeddings should return a list"
        
        # Match with empty embeddings should return empty list
        result = matcher.match(np.array([0.1, 0.2, 0.3]))
        assert isinstance(result, list), "match should return a list"
        assert len(result) == 0, "match with empty embeddings should return empty list"

def test_clean_shutdown():
    """Test clean shutdown of pipeline and resources."""
    Gst.init(None)
    pipeline_str = 'videotestsrc ! fakesink'
    pipeline = Gst.parse_launch(pipeline_str)
    
    # Start pipeline
    pipeline.set_state(Gst.State.PLAYING)
    
    # Simulate shutdown
    time.sleep(0.1)
    pipeline.send_event(Gst.Event.new_eos())
    pipeline.set_state(Gst.State.NULL)
    
    # Verify pipeline is properly cleaned up
    state = pipeline.get_state(0)[1]
    assert state == Gst.State.NULL, "Pipeline not properly cleaned up"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
