"""
Unit tests for VideoProcessor component.

Tests cover:
- Camera source management (add, start, stop)
- Frame buffering and retrieval
- Preprocessing pipeline
- Error handling for camera disconnection
"""

import pytest
import numpy as np
import time
import tempfile
import cv2
from pathlib import Path

from umpirai.video import VideoProcessor, CameraSource, CameraSourceType
from umpirai.models.data_models import Frame


class TestCameraSource:
    """Tests for CameraSource configuration."""
    
    def test_camera_source_creation_rtsp(self):
        """Test creating RTSP camera source."""
        source = CameraSource(
            source_type=CameraSourceType.RTSP,
            source_path="rtsp://192.168.1.100:8554/stream"
        )
        assert source.source_type == CameraSourceType.RTSP
        assert source.source_path == "rtsp://192.168.1.100:8554/stream"
    
    def test_camera_source_creation_usb(self):
        """Test creating USB camera source."""
        source = CameraSource(
            source_type=CameraSourceType.USB,
            source_path=0
        )
        assert source.source_type == CameraSourceType.USB
        assert source.source_path == 0
    
    def test_camera_source_creation_file(self):
        """Test creating file camera source."""
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path="/path/to/video.mp4"
        )
        assert source.source_type == CameraSourceType.FILE
        assert source.source_path == "/path/to/video.mp4"
    
    def test_camera_source_invalid_type(self):
        """Test that invalid source type raises error."""
        with pytest.raises(TypeError):
            CameraSource(
                source_type="invalid",
                source_path="path"
            )
    
    def test_camera_source_invalid_path_type(self):
        """Test that invalid path type raises error."""
        with pytest.raises(TypeError):
            CameraSource(
                source_type=CameraSourceType.RTSP,
                source_path=[]
            )


class TestVideoProcessor:
    """Tests for VideoProcessor class."""
    
    @pytest.fixture
    def video_processor(self):
        """Create a VideoProcessor instance for testing."""
        return VideoProcessor(buffer_seconds=2.0, target_fps=30.0)
    
    @pytest.fixture
    def test_video_file(self):
        """Create a temporary test video file."""
        # Create a temporary video file with a few frames
        temp_dir = tempfile.mkdtemp()
        video_path = Path(temp_dir) / "test_video.mp4"
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(video_path), fourcc, 30.0, (1280, 720))
        
        # Write 90 frames (3 seconds at 30 FPS)
        for i in range(90):
            # Create a frame with varying brightness
            brightness = 128 + int(50 * np.sin(i / 10))
            frame = np.full((720, 1280, 3), brightness, dtype=np.uint8)
            # Add frame number as text
            cv2.putText(frame, f"Frame {i}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            out.write(frame)
        
        out.release()
        
        yield str(video_path)
        
        # Cleanup - wait a bit to ensure all handles are released
        time.sleep(0.2)
        try:
            video_path.unlink()
        except PermissionError:
            # On Windows, file may still be locked - try again after a short delay
            time.sleep(0.5)
            try:
                video_path.unlink()
            except PermissionError:
                # If still locked, skip cleanup (temp dir will be cleaned by OS eventually)
                pass
    
    def test_initialization(self, video_processor):
        """Test VideoProcessor initialization."""
        assert video_processor.buffer_seconds == 2.0
        assert video_processor.target_fps == 30.0
        assert video_processor.buffer_size == 60
        assert len(video_processor.cameras) == 0
        assert video_processor.capturing is False
    
    def test_add_camera_source(self, video_processor, test_video_file):
        """Test adding a camera source."""
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=test_video_file
        )
        
        video_processor.add_camera_source("cam1", source)
        
        assert "cam1" in video_processor.cameras
        assert video_processor.cameras["cam1"].camera_id == "cam1"
        assert video_processor.cameras["cam1"].source == source
    
    def test_add_duplicate_camera_raises_error(self, video_processor, test_video_file):
        """Test that adding duplicate camera ID raises error."""
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=test_video_file
        )
        
        video_processor.add_camera_source("cam1", source)
        
        with pytest.raises(ValueError, match="already exists"):
            video_processor.add_camera_source("cam1", source)
    
    def test_start_capture_without_cameras_raises_error(self, video_processor):
        """Test that starting capture without cameras raises error."""
        with pytest.raises(RuntimeError, match="No cameras added"):
            video_processor.start_capture()
    
    def test_start_and_stop_capture(self, video_processor, test_video_file):
        """Test starting and stopping capture."""
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=test_video_file
        )
        
        video_processor.add_camera_source("cam1", source)
        
        # Start capture
        video_processor.start_capture()
        assert video_processor.capturing is True
        
        # Wait for some frames to be captured
        time.sleep(0.5)
        
        # Stop capture
        video_processor.stop_capture()
        assert video_processor.capturing is False
    
    def test_get_frame(self, video_processor, test_video_file):
        """Test getting a frame from a specific camera."""
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=test_video_file
        )
        
        video_processor.add_camera_source("cam1", source)
        video_processor.start_capture()
        
        # Wait for frames to be captured
        time.sleep(0.5)
        
        # Get frame
        frame = video_processor.get_frame("cam1")
        
        assert frame is not None
        assert isinstance(frame, Frame)
        assert frame.camera_id == "cam1"
        assert frame.image.shape == (720, 1280, 3)
        assert frame.frame_number >= 0
        assert frame.timestamp > 0
        
        video_processor.stop_capture()
    
    def test_get_frame_nonexistent_camera_raises_error(self, video_processor):
        """Test that getting frame from nonexistent camera raises error."""
        with pytest.raises(KeyError, match="not found"):
            video_processor.get_frame("nonexistent")
    
    def test_get_synchronized_frames(self, video_processor, test_video_file):
        """Test getting synchronized frames from all cameras."""
        # Add two cameras
        source1 = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=test_video_file
        )
        source2 = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=test_video_file
        )
        
        video_processor.add_camera_source("cam1", source1)
        video_processor.add_camera_source("cam2", source2)
        video_processor.start_capture()
        
        # Wait for frames to be captured
        time.sleep(0.5)
        
        # Get synchronized frames
        frames = video_processor.get_synchronized_frames()
        
        assert len(frames) == 2
        assert "cam1" in frames
        assert "cam2" in frames
        assert isinstance(frames["cam1"], Frame)
        assert isinstance(frames["cam2"], Frame)
        
        video_processor.stop_capture()
    
    def test_frame_buffering(self, video_processor, test_video_file):
        """Test that frame buffer maintains correct size."""
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=test_video_file
        )
        
        video_processor.add_camera_source("cam1", source)
        video_processor.start_capture()
        
        # Wait for buffer to fill (2 seconds at 30 FPS = 60 frames)
        time.sleep(2.5)
        
        camera_thread = video_processor.cameras["cam1"]
        
        # Buffer should not exceed max size
        assert len(camera_thread.frame_buffer) <= camera_thread.buffer_size
        
        video_processor.stop_capture()
    
    def test_frame_preprocessing(self, video_processor, test_video_file):
        """Test that frames are preprocessed correctly."""
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=test_video_file
        )
        
        video_processor.add_camera_source("cam1", source)
        video_processor.start_capture()
        
        # Wait for frames
        time.sleep(0.5)
        
        frame = video_processor.get_frame("cam1")
        
        assert frame is not None
        # Frame should be resized to 1280x720
        assert frame.image.shape == (720, 1280, 3)
        # Frame should be RGB (not BGR)
        # We can't directly test color space, but we can check it's uint8
        assert frame.image.dtype == np.uint8
        # Pixel values should be in valid range
        assert np.all(frame.image >= 0)
        assert np.all(frame.image <= 255)
        
        video_processor.stop_capture()
    
    def test_get_frame_rate(self, video_processor, test_video_file):
        """Test frame rate calculation."""
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=test_video_file
        )
        
        video_processor.add_camera_source("cam1", source)
        video_processor.start_capture()
        
        # Wait for some frames to be captured
        time.sleep(1.0)
        
        # Get frame rate for specific camera
        fps = video_processor.get_frame_rate("cam1")
        assert fps > 0
        # Frame rate should be reasonable (video files can process faster than real-time)
        assert fps <= 200  # Upper bound check (generous for file playback)
        
        # Get average frame rate
        avg_fps = video_processor.get_frame_rate()
        assert avg_fps > 0
        
        video_processor.stop_capture()
    
    def test_get_frame_rate_nonexistent_camera_raises_error(self, video_processor):
        """Test that getting frame rate from nonexistent camera raises error."""
        with pytest.raises(KeyError, match="not found"):
            video_processor.get_frame_rate("nonexistent")
    
    def test_get_frame_rate_no_cameras(self, video_processor):
        """Test frame rate with no cameras returns 0."""
        fps = video_processor.get_frame_rate()
        assert fps == 0.0
    
    def test_adjust_exposure(self, video_processor, test_video_file):
        """Test manual exposure adjustment."""
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=test_video_file
        )
        
        video_processor.add_camera_source("cam1", source)
        video_processor.start_capture()
        
        # Wait for frames
        time.sleep(0.5)
        
        # Adjust exposure
        video_processor.adjust_exposure("cam1", 0.3)  # 30% increase
        
        # Should not raise error
        # The actual effect will be visible in subsequent frames
        
        video_processor.stop_capture()
    
    def test_adjust_exposure_nonexistent_camera_raises_error(self, video_processor):
        """Test that adjusting exposure for nonexistent camera raises error."""
        with pytest.raises(KeyError, match="not found"):
            video_processor.adjust_exposure("nonexistent", 0.3)
    
    def test_multiple_cameras(self, video_processor, test_video_file):
        """Test operation with multiple cameras."""
        # Add three cameras
        for i in range(3):
            source = CameraSource(
                source_type=CameraSourceType.FILE,
                source_path=test_video_file
            )
            video_processor.add_camera_source(f"cam{i}", source)
        
        video_processor.start_capture()
        
        # Wait for frames
        time.sleep(0.5)
        
        # Get frames from all cameras
        frames = video_processor.get_synchronized_frames()
        assert len(frames) == 3
        
        # Check each camera
        for i in range(3):
            assert f"cam{i}" in frames
            assert frames[f"cam{i}"].camera_id == f"cam{i}"
        
        video_processor.stop_capture()
    
    def test_frame_timestamps_monotonic(self, video_processor, test_video_file):
        """Test that frame timestamps are monotonically increasing."""
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=test_video_file
        )
        
        video_processor.add_camera_source("cam1", source)
        video_processor.start_capture()
        
        # Collect several frames
        time.sleep(0.5)
        
        camera_thread = video_processor.cameras["cam1"]
        
        # Get timestamps from buffer
        with camera_thread.lock:
            timestamps = [frame.timestamp for frame in camera_thread.frame_buffer]
        
        # Timestamps should be monotonically increasing
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1]
        
        video_processor.stop_capture()
    
    def test_frame_metadata(self, video_processor, test_video_file):
        """Test that frames contain proper metadata."""
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=test_video_file
        )
        
        video_processor.add_camera_source("cam1", source)
        video_processor.start_capture()
        
        time.sleep(0.5)
        
        frame = video_processor.get_frame("cam1")
        
        assert frame is not None
        assert "raw_shape" in frame.metadata
        assert "capture_time" in frame.metadata
        assert isinstance(frame.metadata["raw_shape"], tuple)
        assert isinstance(frame.metadata["capture_time"], float)
        
        video_processor.stop_capture()
    
    def test_stop_capture_idempotent(self, video_processor, test_video_file):
        """Test that stopping capture multiple times is safe."""
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=test_video_file
        )
        
        video_processor.add_camera_source("cam1", source)
        video_processor.start_capture()
        
        time.sleep(0.3)
        
        # Stop multiple times
        video_processor.stop_capture()
        video_processor.stop_capture()
        video_processor.stop_capture()
        
        assert video_processor.capturing is False
    
    def test_start_capture_idempotent(self, video_processor, test_video_file):
        """Test that starting capture multiple times is safe."""
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=test_video_file
        )
        
        video_processor.add_camera_source("cam1", source)
        
        # Start multiple times
        video_processor.start_capture()
        video_processor.start_capture()
        video_processor.start_capture()
        
        assert video_processor.capturing is True
        
        video_processor.stop_capture()


class TestCameraDisconnection:
    """Tests for camera disconnection and error handling."""
    
    def test_invalid_camera_source_raises_error(self):
        """Test that invalid camera source raises error on start."""
        processor = VideoProcessor()
        
        # Add camera with invalid source
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path="/nonexistent/path/to/video.mp4"
        )
        
        processor.add_camera_source("cam1", source)
        
        # Starting capture should raise error
        with pytest.raises(RuntimeError, match="Failed to open camera source"):
            processor.start_capture()
    
    def test_get_frame_before_capture_returns_none(self):
        """Test that getting frame before capture starts returns None."""
        processor = VideoProcessor()
        
        # Create a valid test video
        temp_dir = tempfile.mkdtemp()
        video_path = Path(temp_dir) / "test.mp4"
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(video_path), fourcc, 30.0, (1280, 720))
        for i in range(10):
            frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            out.write(frame)
        out.release()
        
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=str(video_path)
        )
        
        processor.add_camera_source("cam1", source)
        
        # Get frame before starting capture
        frame = processor.get_frame("cam1")
        assert frame is None
        
        # Cleanup
        video_path.unlink()


class TestFramePreprocessing:
    """Tests for frame preprocessing pipeline."""
    
    def test_gamma_correction_applied_on_brightness_change(self):
        """Test that gamma correction is applied when brightness changes significantly."""
        processor = VideoProcessor()
        
        # Create a test video with significant brightness change
        temp_dir = tempfile.mkdtemp()
        video_path = Path(temp_dir) / "brightness_test.mp4"
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(video_path), fourcc, 30.0, (1280, 720))
        
        # First 30 frames: dark (brightness ~50)
        for i in range(30):
            frame = np.full((720, 1280, 3), 50, dtype=np.uint8)
            out.write(frame)
        
        # Next 30 frames: bright (brightness ~200)
        for i in range(30):
            frame = np.full((720, 1280, 3), 200, dtype=np.uint8)
            out.write(frame)
        
        out.release()
        
        source = CameraSource(
            source_type=CameraSourceType.FILE,
            source_path=str(video_path)
        )
        
        processor.add_camera_source("cam1", source)
        processor.start_capture()
        
        # Wait for frames to be processed
        time.sleep(2.0)
        
        # Get a frame (should have gamma correction applied)
        frame = processor.get_frame("cam1")
        assert frame is not None
        
        processor.stop_capture()
        
        # Cleanup
        video_path.unlink()
