"""
UmpirAI System - Main Integration Module

This module provides the UmpirAISystem class which integrates all components
of the AI Auto-Umpiring System into a unified processing pipeline.
"""

import time
import logging
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np

from umpirai.video.video_processor import VideoProcessor, CameraSource, VideoInputError
from umpirai.video.multi_camera_synchronizer import MultiCameraSynchronizer, CameraIntrinsics, SynchronizedFrameSet
from umpirai.detection.object_detector import ObjectDetector, DetectionError
from umpirai.tracking.ball_tracker import BallTracker, BallDetection
from umpirai.decision.decision_engine import DecisionEngine, DecisionEngineConfig, ProcessingError
from umpirai.output.decision_output import DecisionOutput, OutputConfig, OutputFormat
from umpirai.logging.event_logger import EventLogger, PerformanceMetrics
from umpirai.monitoring.performance_monitor import PerformanceMonitor, ResourceUsage
from umpirai.calibration.calibration_manager import CalibrationManager, CalibrationData
from umpirai.models.data_models import (
    Frame,
    Detection,
    DetectionResult,
    TrackState,
    Trajectory,
    Decision,
    EventType,
    Position3D,
)

# Configure logging
logger = logging.getLogger(__name__)


class SystemMode(Enum):
    """System operational modes with graceful degradation."""
    FULL = "full"  # All cameras, full processing, all features enabled
    REDUCED = "reduced"  # Fewer cameras, reduced frame rate, core features only
    MINIMAL = "minimal"  # Single camera, 20 FPS, basic decisions only
    SAFE = "safe"  # No decisions, logging only, operator alerts


@dataclass
class SystemConfig:
    """Configuration for UmpirAI System."""
    # Video processing
    target_fps: float = 30.0
    buffer_seconds: float = 2.0
    
    # Detection
    detection_device: str = "cpu"  # "cpu", "cuda", "mps"
    model_path: Optional[str] = None
    
    # Decision engine
    decision_config: Optional[DecisionEngineConfig] = None
    
    # Output
    output_config: Optional[OutputConfig] = None
    output_format: OutputFormat = OutputFormat.ALL
    
    # Logging
    log_directory: str = "logs"
    log_retention_days: int = 30
    
    # Performance monitoring
    enable_performance_monitoring: bool = True
    performance_history_size: int = 100
    
    # System modes
    initial_mode: SystemMode = SystemMode.FULL
    auto_degradation: bool = True  # Automatically switch modes on errors
    
    # Continuous operation
    max_runtime_minutes: int = 120  # Maximum continuous operation time
    
    def __post_init__(self):
        """Validate configuration."""
        if not isinstance(self.target_fps, (int, float)) or self.target_fps <= 0:
            raise ValueError("target_fps must be positive")
        if not isinstance(self.buffer_seconds, (int, float)) or self.buffer_seconds <= 0:
            raise ValueError("buffer_seconds must be positive")
        if not isinstance(self.detection_device, str):
            raise TypeError("detection_device must be a string")
        if not isinstance(self.log_directory, str):
            raise TypeError("log_directory must be a string")
        if not isinstance(self.log_retention_days, int) or self.log_retention_days < 1:
            raise ValueError("log_retention_days must be at least 1")
        if not isinstance(self.max_runtime_minutes, int) or self.max_runtime_minutes <= 0:
            raise ValueError("max_runtime_minutes must be positive")


@dataclass
class SystemStatus:
    """Current system status."""
    mode: SystemMode
    is_running: bool
    uptime_seconds: float
    frames_processed: int
    decisions_made: int
    current_fps: float
    processing_latency_ms: float
    active_cameras: List[str]
    failed_cameras: List[str]
    active_alerts: int
    last_error: Optional[str] = None


class UmpirAISystem:
    """
    Main UmpirAI System integrating all components.
    
    This class provides the complete AI Auto-Umpiring System with:
    - Multi-camera video capture and synchronization
    - Object detection using YOLOv8
    - Ball tracking with Extended Kalman Filter
    - Decision making based on cricket rules
    - Real-time output (text, audio, visual)
    - Event logging and performance monitoring
    - Graceful degradation and error handling
    - 120-minute continuous operation support
    
    Processing Pipeline:
    1. Video Capture: Cameras capture frames → Video Processor buffers and preprocesses
    2. Synchronization: Multi-camera frames aligned by timestamp within 50ms
    3. Detection: YOLOv8 identifies ball, stumps, players, crease lines in each frame
    4. Confidence Evaluation: Detection confidence scores evaluated; low confidence flagged
    5. Tracking: EKF tracks ball position across frames, predicts during occlusion
    6. Decision Making: Rule engine analyzes trajectory and positions to classify events
    7. Output Generation: Decisions formatted as text/audio and logged with video references
    
    System Modes (Graceful Degradation):
    - Full Mode: All cameras, full processing, all features enabled
    - Reduced Mode: Fewer cameras, reduced frame rate, core features only
    - Minimal Mode: Single camera, 20 FPS, basic decisions only
    - Safe Mode: No decisions, logging only, operator alerts
    """
    
    def __init__(self, config: Optional[SystemConfig] = None):
        """
        Initialize UmpirAI System.
        
        Args:
            config: System configuration
        """
        self.config = config or SystemConfig()
        
        # System state
        self.mode = self.config.initial_mode
        self.is_running = False
        self.start_time: Optional[float] = None
        self.frames_processed = 0
        self.decisions_made = 0
        
        # Initialize components
        self._initialize_components()
        
        # Error tracking
        self.errors: List[Dict[str, Any]] = []
        self.last_error: Optional[str] = None
        
        # Runtime tracking
        self.max_runtime_seconds = self.config.max_runtime_minutes * 60
        
        logger.info(f"UmpirAI System initialized in {self.mode.value} mode")
    
    def _initialize_components(self) -> None:
        """Initialize all system components."""
        # Video Processor
        self.video_processor = VideoProcessor(
            buffer_seconds=self.config.buffer_seconds,
            target_fps=self.config.target_fps,
            error_callback=self._handle_video_error
        )
        
        # Multi-Camera Synchronizer
        self.synchronizer = MultiCameraSynchronizer(
            max_cameras=4,
            target_sync_ms=50.0
        )
        
        # Object Detector
        try:
            self.object_detector = ObjectDetector(
                model_path=self.config.model_path,
                device=self.config.detection_device
            )
        except Exception as e:
            logger.error(f"Failed to initialize object detector: {e}")
            # Try CPU fallback
            if self.config.detection_device != "cpu":
                logger.info("Attempting CPU fallback for object detector")
                self.object_detector = ObjectDetector(
                    model_path=self.config.model_path,
                    device="cpu"
                )
            else:
                raise
        
        # Ball Tracker
        self.ball_tracker = BallTracker(
            dt=1.0 / self.config.target_fps,
            measurement_noise=5.0,
            process_noise=0.1
        )
        
        # Decision Engine
        decision_config = self.config.decision_config or DecisionEngineConfig()
        self.decision_engine = DecisionEngine(
            calibration=None,  # Will be set during startup
            config=decision_config
        )
        
        # Decision Output
        output_config = self.config.output_config or OutputConfig()
        self.decision_output = DecisionOutput(config=output_config)
        self.decision_output.set_output_format(self.config.output_format)
        
        # Event Logger
        self.event_logger = EventLogger(
            log_directory=self.config.log_directory,
            retention_days=self.config.log_retention_days
        )
        
        # Performance Monitor
        if self.config.enable_performance_monitoring:
            self.performance_monitor = PerformanceMonitor(
                history_size=self.config.performance_history_size
            )
        else:
            self.performance_monitor = None
        
        # Calibration Manager
        self.calibration_manager = CalibrationManager()
    
    def add_camera(
        self,
        camera_id: str,
        source: CameraSource,
        intrinsics: Optional[CameraIntrinsics] = None
    ) -> None:
        """
        Add a camera to the system.
        
        Args:
            camera_id: Unique identifier for the camera
            source: Camera source configuration
            intrinsics: Optional camera intrinsic parameters for synchronization
        """
        # Add to video processor
        self.video_processor.add_camera_source(camera_id, source)
        
        # Add to synchronizer if intrinsics provided
        if intrinsics:
            self.synchronizer.add_camera(camera_id, intrinsics)
        
        logger.info(f"Camera {camera_id} added to system")
    
    def load_calibration(self, calibration_path: Path) -> None:
        """
        Load pitch calibration from file.
        
        Args:
            calibration_path: Path to calibration JSON file
        """
        calibration = self.calibration_manager.load_calibration(calibration_path)
        self.decision_engine.update_calibration(calibration)
        logger.info(f"Calibration loaded from {calibration_path}")
    
    def set_calibration(self, calibration: CalibrationData) -> None:
        """
        Set pitch calibration directly.
        
        Args:
            calibration: Calibration data object
        """
        self.decision_engine.update_calibration(calibration)
        logger.info(f"Calibration set: {calibration.calibration_name}")
    
    def start(self) -> None:
        """
        Start the UmpirAI System.
        
        Initializes all components and begins video capture and processing.
        
        Raises:
            RuntimeError: If system is already running or startup fails
        """
        if self.is_running:
            raise RuntimeError("System is already running")
        
        # Validate calibration
        if self.decision_engine.calibration is None:
            logger.warning("No calibration loaded. Decisions may be inaccurate.")
        
        # Start video capture
        try:
            self.video_processor.start_capture()
        except Exception as e:
            logger.error(f"Failed to start video capture: {e}")
            raise RuntimeError(f"Video capture startup failed: {e}")
        
        # Reset tracking and monitoring
        self.ball_tracker.reset()
        if self.performance_monitor:
            self.performance_monitor.reset()
        
        # Update state
        self.is_running = True
        self.start_time = time.time()
        self.frames_processed = 0
        self.decisions_made = 0
        
        logger.info("UmpirAI System started successfully")
    
    def stop(self) -> None:
        """
        Stop the UmpirAI System.
        
        Gracefully shuts down all components and saves any pending data.
        """
        if not self.is_running:
            return
        
        logger.info("Stopping UmpirAI System...")
        
        # Stop video capture
        self.video_processor.stop_capture()
        
        # Save match data if critical errors occurred
        if self.decision_engine.has_critical_error():
            logger.warning("Critical errors detected. Saving match data...")
            save_path = Path(self.config.log_directory) / f"match_data_{int(time.time())}.json"
            self.decision_engine.save_match_data(str(save_path))
        
        # Update state
        self.is_running = False
        
        # Log final statistics
        uptime = time.time() - self.start_time if self.start_time else 0
        logger.info(
            f"UmpirAI System stopped. "
            f"Uptime: {uptime:.1f}s, "
            f"Frames: {self.frames_processed}, "
            f"Decisions: {self.decisions_made}"
        )
    
    def process_frame(self) -> Optional[Decision]:
        """
        Process a single frame through the complete pipeline.
        
        Pipeline stages:
        1. Capture: Get synchronized frames from all cameras
        2. Detect: Run object detection on frames
        3. Track: Update ball tracker with detections
        4. Decide: Generate umpiring decision
        5. Output: Display/announce decision
        6. Log: Record event and performance metrics
        
        Returns:
            Decision object if an event was detected, None otherwise
        """
        if not self.is_running:
            raise RuntimeError("System is not running. Call start() first.")
        
        # Check runtime limit
        if self.start_time and (time.time() - self.start_time) > self.max_runtime_seconds:
            logger.warning(f"Maximum runtime of {self.config.max_runtime_minutes} minutes reached")
            self.stop()
            return None
        
        frame_start_time = time.time()
        
        try:
            # Stage 1: Capture synchronized frames
            frames = self.video_processor.get_synchronized_frames()
            
            if not frames:
                logger.warning("No frames available from cameras")
                return None
            
            # Synchronize frames if multiple cameras
            if len(frames) > 1:
                synchronized_frames = self.synchronizer.synchronize_frames(frames)
                frames = synchronized_frames.frames
            
            # Use primary camera frame for processing
            primary_camera_id = list(frames.keys())[0]
            primary_frame = frames[primary_camera_id]
            
            # Stage 2: Object Detection
            if len(frames) == 1:
                # Single camera detection
                detection_result = self.object_detector.detect(primary_frame)
            else:
                # Multi-camera detection with fusion
                multi_view_result = self.object_detector.detect_multi_view(frames)
                # Convert to DetectionResult format
                detection_result = DetectionResult(
                    frame=primary_frame,
                    detections=multi_view_result.detections,
                    processing_time_ms=multi_view_result.processing_time_ms
                )
            
            # Stage 3: Ball Tracking
            ball_detections = [d for d in detection_result.detections if d.class_name == "ball"]
            
            if ball_detections:
                # Use highest confidence ball detection
                ball_detection = max(ball_detections, key=lambda d: d.confidence)
                
                # Create BallDetection object
                ball_det = BallDetection(
                    detection=ball_detection,
                    timestamp=primary_frame.timestamp,
                    pixel_coords=ball_detection.bounding_box.center(),
                    position_3d=ball_detection.position_3d
                )
                
                # Update tracker
                track_state = self.ball_tracker.update(ball_det, primary_frame.timestamp)
            else:
                # No ball detected - predict position during occlusion
                if self.ball_tracker.is_initialized:
                    predicted_position = self.ball_tracker.predict(primary_frame.timestamp)
                    track_state = self.ball_tracker._get_track_state()
                else:
                    # Cannot track without initialization
                    track_state = None
            
            # Get trajectory
            trajectory = self.ball_tracker.get_trajectory_object()
            
            # Stage 4: Decision Making
            decision = None
            if track_state and len(trajectory.positions) > 0:
                decision = self.decision_engine.process_frame(
                    detection_result=detection_result,
                    track_state=track_state,
                    trajectory=trajectory,
                    calibration=self.decision_engine.calibration,
                    frame_image=primary_frame.image
                )
            
            # Stage 5: Output Decision
            if decision:
                self.decision_output.output_decision(
                    decision,
                    frame=primary_frame.image,
                    output_format=self.config.output_format
                )
                self.decisions_made += 1
            
            # Stage 6: Logging and Monitoring
            frame_end_time = time.time()
            processing_latency_ms = (frame_end_time - frame_start_time) * 1000
            
            # Log decision
            if decision:
                self.event_logger.log_decision(decision)
            
            # Update performance metrics
            if self.performance_monitor:
                resource_usage = self.performance_monitor.get_resource_usage()
                # Use PerformanceMetrics from monitoring module
                from umpirai.monitoring.performance_monitor import PerformanceMetrics as MonitorMetrics
                monitor_metrics = MonitorMetrics(
                    timestamp=primary_frame.timestamp,
                    fps=self.video_processor.get_frame_rate(),
                    processing_latency_ms=processing_latency_ms,
                    detection_accuracy=None,  # Would need ground truth for this
                    resource_usage=resource_usage
                )
                self.performance_monitor.update_metrics(monitor_metrics)
                
                # Use PerformanceMetrics from logging module for event logger
                from umpirai.logging.event_logger import PerformanceMetrics as LoggerMetrics
                logger_metrics = LoggerMetrics(
                    timestamp=primary_frame.timestamp,
                    fps=self.video_processor.get_frame_rate(),
                    processing_latency_ms=processing_latency_ms,
                    cpu_usage_percent=resource_usage.cpu_percent,
                    memory_usage_mb=resource_usage.memory_mb,
                    gpu_usage_percent=resource_usage.gpu_percent
                )
                self.event_logger.log_performance(logger_metrics)
                
                # Check for alerts and handle degradation
                alerts = self.performance_monitor.check_alerts()
                if alerts and self.config.auto_degradation:
                    self._handle_performance_alerts(alerts)
            
            # Update frame counter
            self.frames_processed += 1
            
            return decision
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}", exc_info=True)
            self.last_error = str(e)
            self.errors.append({
                "timestamp": time.time(),
                "error": str(e),
                "type": type(e).__name__
            })
            
            # Handle error with graceful degradation
            if self.config.auto_degradation:
                self._handle_processing_error(e)
            
            return None
    
    def run_continuous(self, duration_seconds: Optional[float] = None) -> None:
        """
        Run continuous processing loop.
        
        Processes frames continuously until stopped or duration expires.
        
        Args:
            duration_seconds: Optional duration to run (None = run until stopped)
        """
        if not self.is_running:
            self.start()
        
        end_time = None
        if duration_seconds:
            end_time = time.time() + duration_seconds
        
        logger.info(f"Starting continuous processing loop (duration: {duration_seconds or 'unlimited'}s)")
        
        try:
            while self.is_running:
                # Check duration limit
                if end_time and time.time() >= end_time:
                    logger.info("Duration limit reached")
                    break
                
                # Process frame
                self.process_frame()
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.001)
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.stop()
    
    def get_status(self) -> SystemStatus:
        """
        Get current system status.
        
        Returns:
            SystemStatus object with current state
        """
        uptime = time.time() - self.start_time if self.start_time and self.is_running else 0.0
        
        active_cameras = self.video_processor.get_healthy_cameras()
        failed_cameras = self.video_processor.get_failed_cameras()
        
        current_fps = self.video_processor.get_frame_rate() if self.is_running else 0.0
        
        processing_latency = 0.0
        active_alerts = 0
        if self.performance_monitor:
            processing_latency = self.performance_monitor.get_processing_latency()
            active_alerts = len(self.performance_monitor.check_alerts())
        
        return SystemStatus(
            mode=self.mode,
            is_running=self.is_running,
            uptime_seconds=uptime,
            frames_processed=self.frames_processed,
            decisions_made=self.decisions_made,
            current_fps=current_fps,
            processing_latency_ms=processing_latency,
            active_cameras=active_cameras,
            failed_cameras=failed_cameras,
            active_alerts=active_alerts,
            last_error=self.last_error
        )
    
    def switch_mode(self, new_mode: SystemMode) -> None:
        """
        Switch system operational mode.
        
        Args:
            new_mode: Target system mode
        """
        if new_mode == self.mode:
            return
        
        logger.info(f"Switching system mode: {self.mode.value} → {new_mode.value}")
        
        old_mode = self.mode
        self.mode = new_mode
        
        # Apply mode-specific configuration
        if new_mode == SystemMode.FULL:
            # Full mode: all features enabled
            self.config.target_fps = 30.0
            self.decision_engine.config.enable_wide_detection = True
            self.decision_engine.config.enable_no_ball_detection = True
            self.decision_engine.config.enable_bowled_detection = True
            self.decision_engine.config.enable_caught_detection = True
            self.decision_engine.config.enable_lbw_detection = True
            
        elif new_mode == SystemMode.REDUCED:
            # Reduced mode: core features, reduced frame rate
            self.config.target_fps = 25.0
            self.decision_engine.config.enable_wide_detection = True
            self.decision_engine.config.enable_no_ball_detection = True
            self.decision_engine.config.enable_bowled_detection = True
            self.decision_engine.config.enable_caught_detection = True
            self.decision_engine.config.enable_lbw_detection = False  # Disable complex LBW
            
        elif new_mode == SystemMode.MINIMAL:
            # Minimal mode: basic decisions only
            self.config.target_fps = 20.0
            self.decision_engine.config.enable_wide_detection = True
            self.decision_engine.config.enable_no_ball_detection = True
            self.decision_engine.config.enable_bowled_detection = True
            self.decision_engine.config.enable_caught_detection = False
            self.decision_engine.config.enable_lbw_detection = False
            
        elif new_mode == SystemMode.SAFE:
            # Safe mode: no decisions, logging only
            self.decision_engine.config.enable_wide_detection = False
            self.decision_engine.config.enable_no_ball_detection = False
            self.decision_engine.config.enable_bowled_detection = False
            self.decision_engine.config.enable_caught_detection = False
            self.decision_engine.config.enable_lbw_detection = False
        
        logger.info(f"System mode switched to {new_mode.value}")
    
    def _handle_video_error(self, error: VideoInputError) -> None:
        """
        Handle video input errors.
        
        Args:
            error: Video input error information
        """
        logger.error(f"Video error: {error.error_type} - {error.message}")
        self.last_error = error.message
        self.errors.append({
            "timestamp": error.timestamp,
            "error": error.message,
            "type": error.error_type,
            "component": "VideoProcessor"
        })
        
        # Check if we should degrade
        if self.config.auto_degradation:
            failed_cameras = self.video_processor.get_failed_cameras()
            healthy_cameras = self.video_processor.get_healthy_cameras()
            
            if len(failed_cameras) > 0 and len(healthy_cameras) == 0:
                # All cameras failed - switch to safe mode
                logger.critical("All cameras failed. Switching to safe mode.")
                self.switch_mode(SystemMode.SAFE)
            elif len(failed_cameras) > 0:
                # Some cameras failed - degrade based on remaining cameras
                if len(healthy_cameras) == 1 and self.mode != SystemMode.MINIMAL:
                    logger.warning("Only one camera remaining. Switching to minimal mode.")
                    self.switch_mode(SystemMode.MINIMAL)
                elif len(healthy_cameras) <= 2 and self.mode == SystemMode.FULL:
                    logger.warning("Reduced camera count. Switching to reduced mode.")
                    self.switch_mode(SystemMode.REDUCED)
    
    def _handle_performance_alerts(self, alerts: List) -> None:
        """
        Handle performance alerts with graceful degradation.
        
        Args:
            alerts: List of performance alerts
        """
        for alert in alerts:
            logger.warning(f"Performance alert: {alert.message}")
            
            # Degrade mode based on alert type
            if alert.severity == "critical":
                if self.mode == SystemMode.FULL:
                    self.switch_mode(SystemMode.REDUCED)
                elif self.mode == SystemMode.REDUCED:
                    self.switch_mode(SystemMode.MINIMAL)
                elif self.mode == SystemMode.MINIMAL:
                    self.switch_mode(SystemMode.SAFE)
    
    def _handle_processing_error(self, error: Exception) -> None:
        """
        Handle processing errors with graceful degradation.
        
        Args:
            error: Exception that occurred
        """
        logger.error(f"Processing error: {error}")
        
        # For now, just log the error
        # In production, could implement more sophisticated error handling
        # and degradation logic based on error type
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
