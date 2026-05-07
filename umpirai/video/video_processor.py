"""
Video processing component for capturing and preprocessing video frames.

This module provides the VideoProcessor class which handles multi-camera video capture,
frame buffering, preprocessing, and automatic exposure adjustment.
"""

import threading
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Deque
import cv2
import numpy as np

from umpirai.models.data_models import Frame


class CameraSourceType(Enum):
    """Types of camera sources supported."""
    RTSP = "rtsp"  # RTSP streaming (e.g., smartphone cameras)
    HTTP = "http"  # HTTP streaming
    USB = "usb"    # USB camera
    HDMI = "hdmi"  # HDMI capture device
    FILE = "file"  # Video file (for testing)


@dataclass
class CameraSource:
    """Configuration for a camera source."""
    source_type: CameraSourceType
    source_path: str  # URL for streaming, device index for USB/HDMI, file path for FILE
    
    def __post_init__(self):
        """Validate camera source configuration."""
        if not isinstance(self.source_type, CameraSourceType):
            raise TypeError("source_type must be a CameraSourceType enum")
        if not isinstance(self.source_path, (str, int)):
            raise TypeError("source_path must be a string or integer")


class CameraThread:
    """Thread for capturing frames from a single camera source."""
    
    def __init__(self, camera_id: str, source: CameraSource, buffer_size: int = 60):
        """
        Initialize camera capture thread.
        
        Args:
            camera_id: Unique identifier for this camera
            source: Camera source configuration
            buffer_size: Maximum number of frames to buffer (default: 60 frames = 2 seconds at 30 FPS)
        """
        self.camera_id = camera_id
        self.source = source
        self.buffer_size = buffer_size
        
        # Frame buffer (circular buffer using deque)
        self.frame_buffer: Deque[Frame] = deque(maxlen=buffer_size)
        
        # Thread control
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.lock = threading.Lock()
        
        # Video capture
        self.capture: Optional[cv2.VideoCapture] = None
        
        # Frame rate tracking
        self.frame_count = 0
        self.start_time = 0.0
        self.last_frame_time = 0.0
        
        # Exposure tracking
        self.last_exposure = None
        self.reference_brightness = None
        
    def start(self) -> None:
        """Start the camera capture thread."""
        if self.running:
            return
            
        # Initialize video capture
        if self.source.source_type in [CameraSourceType.USB, CameraSourceType.HDMI]:
            # For USB/HDMI, source_path should be an integer device index
            device_index = int(self.source.source_path) if isinstance(self.source.source_path, str) else self.source.source_path
            self.capture = cv2.VideoCapture(device_index)
        else:
            # For RTSP, HTTP, FILE, source_path is a string URL/path
            self.capture = cv2.VideoCapture(self.source.source_path)
        
        if not self.capture.isOpened():
            raise RuntimeError(f"Failed to open camera source: {self.source.source_path}")
        
        # Start capture thread
        self.running = True
        self.start_time = time.monotonic()
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
    
    def stop(self) -> None:
        """Stop the camera capture thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.capture:
            self.capture.release()
            self.capture = None
    
    def _capture_loop(self) -> None:
        """Main capture loop running in separate thread."""
        reconnect_attempts = 0
        max_reconnect_attempts = 3
        
        while self.running:
            if not self.capture or not self.capture.isOpened():
                # Attempt reconnection
                if reconnect_attempts < max_reconnect_attempts:
                    reconnect_attempts += 1
                    backoff_time = 2 ** (reconnect_attempts - 1)  # Exponential backoff: 1s, 2s, 4s
                    time.sleep(backoff_time)
                    
                    try:
                        if self.source.source_type in [CameraSourceType.USB, CameraSourceType.HDMI]:
                            device_index = int(self.source.source_path) if isinstance(self.source.source_path, str) else self.source.source_path
                            self.capture = cv2.VideoCapture(device_index)
                        else:
                            self.capture = cv2.VideoCapture(self.source.source_path)
                        
                        if self.capture.isOpened():
                            reconnect_attempts = 0  # Reset on successful reconnection
                    except Exception:
                        continue
                else:
                    # Max reconnection attempts reached
                    break
                continue
            
            ret, frame = self.capture.read()
            if not ret:
                # Frame read failed, will attempt reconnection on next iteration
                continue
            
            # Capture timestamp using monotonic clock
            timestamp = time.monotonic()
            
            # Preprocess frame
            processed_frame = self._preprocess_frame(frame)
            
            # Create Frame object
            frame_obj = Frame(
                camera_id=self.camera_id,
                frame_number=self.frame_count,
                timestamp=timestamp,
                image=processed_frame,
                metadata={
                    "raw_shape": frame.shape,
                    "capture_time": timestamp
                }
            )
            
            # Add to buffer (thread-safe)
            with self.lock:
                self.frame_buffer.append(frame_obj)
                self.frame_count += 1
                self.last_frame_time = timestamp
    
    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess video frame.
        
        Steps:
        1. Resize to 1280x720
        2. Convert BGR to RGB
        3. Normalize pixel values to [0, 1]
        4. Apply gamma correction if needed
        
        Args:
            frame: Raw frame from camera (BGR format)
            
        Returns:
            Preprocessed frame (RGB format, normalized)
        """
        # Resize to 1280x720
        resized = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_LINEAR)
        
        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Calculate brightness for exposure adjustment
        brightness = np.mean(rgb)
        
        # Initialize reference brightness on first frame
        if self.reference_brightness is None:
            self.reference_brightness = brightness
        
        # Check if lighting has changed significantly (±30% threshold)
        brightness_change = abs(brightness - self.reference_brightness) / self.reference_brightness
        if brightness_change > 0.30:
            # Apply gamma correction to compensate
            if brightness < self.reference_brightness:
                # Image is darker, increase gamma
                gamma = 1.2
            else:
                # Image is brighter, decrease gamma
                gamma = 0.8
            
            # Apply gamma correction
            inv_gamma = 1.0 / gamma
            table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
            rgb = cv2.LUT(rgb, table)
            
            # Update reference brightness
            self.reference_brightness = brightness
        
        # Normalize pixel values to [0, 1] - but keep as uint8 for efficiency
        # The normalization to [0, 1] will be done by the detection model if needed
        # For now, keep as uint8 [0, 255] to save memory
        
        return rgb
    
    def get_latest_frame(self) -> Optional[Frame]:
        """
        Get the most recent frame from the buffer.
        
        Returns:
            Latest frame, or None if buffer is empty
        """
        with self.lock:
            if len(self.frame_buffer) == 0:
                return None
            return self.frame_buffer[-1]
    
    def get_frame_rate(self) -> float:
        """
        Calculate current frame rate.
        
        Returns:
            Frames per second
        """
        if self.frame_count == 0:
            return 0.0
        
        elapsed = time.monotonic() - self.start_time
        if elapsed == 0:
            return 0.0
        
        return self.frame_count / elapsed


class VideoProcessor:
    """
    Video processor for multi-camera capture and preprocessing.
    
    Supports:
    - Multiple camera sources (RTSP/HTTP streaming, USB/HDMI capture)
    - Automatic exposure adjustment for lighting changes
    - Frame buffering with circular buffer (2-second capacity)
    - Frame rate monitoring
    - Separate thread per camera to prevent blocking
    """
    
    def __init__(self, buffer_seconds: float = 2.0, target_fps: float = 30.0):
        """
        Initialize video processor.
        
        Args:
            buffer_seconds: Buffer capacity in seconds (default: 2.0)
            target_fps: Target frame rate for buffer size calculation (default: 30.0)
        """
        self.buffer_seconds = buffer_seconds
        self.target_fps = target_fps
        self.buffer_size = int(buffer_seconds * target_fps)
        
        # Camera threads
        self.cameras: Dict[str, CameraThread] = {}
        
        # Capture state
        self.capturing = False
    
    def add_camera_source(self, camera_id: str, source: CameraSource) -> None:
        """
        Add a camera source to the processor.
        
        Args:
            camera_id: Unique identifier for this camera
            source: Camera source configuration
            
        Raises:
            ValueError: If camera_id already exists
        """
        if camera_id in self.cameras:
            raise ValueError(f"Camera with id '{camera_id}' already exists")
        
        camera_thread = CameraThread(camera_id, source, self.buffer_size)
        self.cameras[camera_id] = camera_thread
    
    def start_capture(self) -> None:
        """
        Start capturing from all camera sources.
        
        Raises:
            RuntimeError: If no cameras have been added
        """
        if len(self.cameras) == 0:
            raise RuntimeError("No cameras added. Use add_camera_source() first.")
        
        if self.capturing:
            return
        
        # Start all camera threads
        for camera_thread in self.cameras.values():
            camera_thread.start()
        
        self.capturing = True
    
    def stop_capture(self) -> None:
        """Stop capturing from all camera sources."""
        if not self.capturing:
            return
        
        # Stop all camera threads
        for camera_thread in self.cameras.values():
            camera_thread.stop()
        
        self.capturing = False
    
    def get_frame(self, camera_id: str) -> Optional[Frame]:
        """
        Get the latest frame from a specific camera.
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            Latest frame from the camera, or None if not available
            
        Raises:
            KeyError: If camera_id does not exist
        """
        if camera_id not in self.cameras:
            raise KeyError(f"Camera '{camera_id}' not found")
        
        return self.cameras[camera_id].get_latest_frame()
    
    def get_synchronized_frames(self) -> Dict[str, Frame]:
        """
        Get the latest frames from all cameras.
        
        Note: This returns the most recent frame from each camera.
        For precise temporal synchronization, use MultiCameraSynchronizer.
        
        Returns:
            Dictionary mapping camera_id to latest frame
        """
        frames = {}
        for camera_id, camera_thread in self.cameras.items():
            frame = camera_thread.get_latest_frame()
            if frame is not None:
                frames[camera_id] = frame
        return frames
    
    def adjust_exposure(self, camera_id: str, lighting_change: float) -> None:
        """
        Manually adjust exposure for a camera.
        
        Note: Automatic exposure adjustment is handled in preprocessing.
        This method is provided for manual control if needed.
        
        Args:
            camera_id: Camera identifier
            lighting_change: Lighting change factor (e.g., 0.3 for 30% increase)
            
        Raises:
            KeyError: If camera_id does not exist
        """
        if camera_id not in self.cameras:
            raise KeyError(f"Camera '{camera_id}' not found")
        
        camera_thread = self.cameras[camera_id]
        
        # Adjust reference brightness to trigger gamma correction
        if camera_thread.reference_brightness is not None:
            camera_thread.reference_brightness *= (1.0 + lighting_change)
    
    def get_frame_rate(self, camera_id: Optional[str] = None) -> float:
        """
        Get frame rate for a specific camera or average across all cameras.
        
        Args:
            camera_id: Camera identifier, or None for average across all cameras
            
        Returns:
            Frame rate in FPS
            
        Raises:
            KeyError: If camera_id does not exist
        """
        if camera_id is not None:
            if camera_id not in self.cameras:
                raise KeyError(f"Camera '{camera_id}' not found")
            return self.cameras[camera_id].get_frame_rate()
        else:
            # Return average frame rate across all cameras
            if len(self.cameras) == 0:
                return 0.0
            
            total_fps = sum(cam.get_frame_rate() for cam in self.cameras.values())
            return total_fps / len(self.cameras)
