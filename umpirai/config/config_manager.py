"""
Configuration management for UmpirAI system.

This module provides configuration loading, validation, and management
for the UmpirAI cricket umpiring system.
"""

import os
import json
import yaml
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from pathlib import Path


@dataclass
class VideoConfig:
    """Video processing configuration."""
    target_fps: int = 30
    resolution_width: int = 1280
    resolution_height: int = 720
    buffer_size_seconds: float = 2.0
    exposure_adjustment_threshold: float = 0.3
    gamma_correction: bool = True
    
    def validate(self) -> None:
        """Validate video configuration."""
        if self.target_fps <= 0:
            raise ValueError("target_fps must be positive")
        if self.resolution_width <= 0 or self.resolution_height <= 0:
            raise ValueError("Resolution dimensions must be positive")
        if self.buffer_size_seconds <= 0:
            raise ValueError("buffer_size_seconds must be positive")
        if not 0 <= self.exposure_adjustment_threshold <= 1:
            raise ValueError("exposure_adjustment_threshold must be between 0 and 1")


@dataclass
class DetectionConfig:
    """Object detection configuration."""
    model_path: str = "yolov8m.pt"
    confidence_threshold_high: float = 0.9
    confidence_threshold_medium: float = 0.7
    confidence_threshold_low: float = 0.5
    enable_multi_view_fusion: bool = True
    max_cameras: int = 4
    
    def validate(self) -> None:
        """Validate detection configuration."""
        if not 0 <= self.confidence_threshold_low <= self.confidence_threshold_medium <= self.confidence_threshold_high <= 1:
            raise ValueError("Confidence thresholds must be in ascending order and between 0 and 1")
        if self.max_cameras < 1 or self.max_cameras > 4:
            raise ValueError("max_cameras must be between 1 and 4")


@dataclass
class TrackingConfig:
    """Ball tracking configuration."""
    max_occlusion_frames: int = 10
    trajectory_history_size: int = 30
    process_noise: float = 0.1
    measurement_noise: float = 5.0
    gravity: float = 9.81
    air_resistance_coefficient: float = 0.47
    
    def validate(self) -> None:
        """Validate tracking configuration."""
        if self.max_occlusion_frames < 1:
            raise ValueError("max_occlusion_frames must be at least 1")
        if self.trajectory_history_size < 1:
            raise ValueError("trajectory_history_size must be at least 1")
        if self.process_noise <= 0 or self.measurement_noise <= 0:
            raise ValueError("Noise parameters must be positive")
        if self.gravity <= 0:
            raise ValueError("gravity must be positive")


@dataclass
class DecisionConfig:
    """Decision engine configuration."""
    confidence_review_threshold: float = 0.8
    wide_guideline_offset: float = 1.0
    batsman_movement_threshold: float = 0.5
    fielder_control_frames: int = 3
    ground_contact_height_threshold: float = 0.1
    enable_wide_detector: bool = True
    enable_no_ball_detector: bool = True
    enable_bowled_detector: bool = True
    enable_caught_detector: bool = True
    enable_lbw_detector: bool = True
    
    def validate(self) -> None:
        """Validate decision configuration."""
        if not 0 <= self.confidence_review_threshold <= 1:
            raise ValueError("confidence_review_threshold must be between 0 and 1")
        if self.wide_guideline_offset <= 0:
            raise ValueError("wide_guideline_offset must be positive")
        if self.batsman_movement_threshold <= 0:
            raise ValueError("batsman_movement_threshold must be positive")
        if self.fielder_control_frames < 1:
            raise ValueError("fielder_control_frames must be at least 1")
        if self.ground_contact_height_threshold < 0:
            raise ValueError("ground_contact_height_threshold must be non-negative")


@dataclass
class OutputConfig:
    """Output configuration."""
    enable_text_display: bool = True
    enable_audio_announcement: bool = False
    enable_visual_indicators: bool = True
    decision_latency_target_ms: float = 500.0
    decision_latency_max_ms: float = 1000.0
    
    def validate(self) -> None:
        """Validate output configuration."""
        if self.decision_latency_target_ms <= 0:
            raise ValueError("decision_latency_target_ms must be positive")
        if self.decision_latency_max_ms < self.decision_latency_target_ms:
            raise ValueError("decision_latency_max_ms must be >= decision_latency_target_ms")


@dataclass
class LoggingConfig:
    """Logging configuration."""
    log_directory: str = "logs"
    log_level: str = "INFO"
    retention_days: int = 30
    enable_event_logging: bool = True
    enable_performance_logging: bool = True
    log_format: str = "jsonl"
    
    def validate(self) -> None:
        """Validate logging configuration."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        if self.retention_days < 1:
            raise ValueError("retention_days must be at least 1")
        if self.log_format not in ["jsonl", "json", "text"]:
            raise ValueError("log_format must be 'jsonl', 'json', or 'text'")


@dataclass
class PerformanceConfig:
    """Performance monitoring configuration."""
    fps_alert_threshold: float = 25.0
    latency_alert_threshold_ms: float = 2000.0
    detection_accuracy_alert_threshold: float = 0.8
    memory_alert_threshold_percent: float = 90.0
    enable_performance_monitoring: bool = True
    metrics_history_size: int = 100
    
    def validate(self) -> None:
        """Validate performance configuration."""
        if self.fps_alert_threshold <= 0:
            raise ValueError("fps_alert_threshold must be positive")
        if self.latency_alert_threshold_ms <= 0:
            raise ValueError("latency_alert_threshold_ms must be positive")
        if not 0 <= self.detection_accuracy_alert_threshold <= 1:
            raise ValueError("detection_accuracy_alert_threshold must be between 0 and 1")
        if not 0 <= self.memory_alert_threshold_percent <= 100:
            raise ValueError("memory_alert_threshold_percent must be between 0 and 100")
        if self.metrics_history_size < 1:
            raise ValueError("metrics_history_size must be at least 1")


@dataclass
class CalibrationConfig:
    """Calibration configuration."""
    calibration_directory: str = "calibrations"
    auto_load_last_calibration: bool = True
    require_calibration_validation: bool = True
    
    def validate(self) -> None:
        """Validate calibration configuration."""
        # No specific validation needed for current fields
        pass


@dataclass
class SystemConfig:
    """Complete system configuration."""
    video: VideoConfig = field(default_factory=VideoConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    decision: DecisionConfig = field(default_factory=DecisionConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    
    # System-level settings
    max_runtime_minutes: int = 120
    enable_graceful_degradation: bool = True
    
    def validate(self) -> None:
        """Validate entire system configuration."""
        self.video.validate()
        self.detection.validate()
        self.tracking.validate()
        self.decision.validate()
        self.output.validate()
        self.logging.validate()
        self.performance.validate()
        self.calibration.validate()
        
        if self.max_runtime_minutes < 1:
            raise ValueError("max_runtime_minutes must be at least 1")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemConfig':
        """Create configuration from dictionary."""
        # Extract nested configurations
        video_data = data.get('video', {})
        detection_data = data.get('detection', {})
        tracking_data = data.get('tracking', {})
        decision_data = data.get('decision', {})
        output_data = data.get('output', {})
        logging_data = data.get('logging', {})
        performance_data = data.get('performance', {})
        calibration_data = data.get('calibration', {})
        
        return cls(
            video=VideoConfig(**video_data),
            detection=DetectionConfig(**detection_data),
            tracking=TrackingConfig(**tracking_data),
            decision=DecisionConfig(**decision_data),
            output=OutputConfig(**output_data),
            logging=LoggingConfig(**logging_data),
            performance=PerformanceConfig(**performance_data),
            calibration=CalibrationConfig(**calibration_data),
            max_runtime_minutes=data.get('max_runtime_minutes', 120),
            enable_graceful_degradation=data.get('enable_graceful_degradation', True)
        )


class ConfigManager:
    """Manages system configuration loading, saving, and validation."""
    
    DEFAULT_CONFIG_PATHS = [
        'config.yaml',
        'config.yml',
        'config.json',
        'umpirai_config.yaml',
        'umpirai_config.yml',
        'umpirai_config.json'
    ]
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file. If None, searches default locations.
        """
        self.config_path = config_path
        self.config: Optional[SystemConfig] = None
    
    def load(self, config_path: Optional[str] = None) -> SystemConfig:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration file. If None, uses instance path or searches defaults.
        
        Returns:
            Loaded and validated SystemConfig
        
        Raises:
            FileNotFoundError: If configuration file not found
            ValueError: If configuration is invalid
        """
        path = config_path or self.config_path
        
        if path is None:
            # Search for default configuration files
            for default_path in self.DEFAULT_CONFIG_PATHS:
                if os.path.exists(default_path):
                    path = default_path
                    break
        
        if path is None:
            raise FileNotFoundError(
                f"No configuration file found. Searched: {self.DEFAULT_CONFIG_PATHS}"
            )
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        # Load based on file extension
        file_ext = Path(path).suffix.lower()
        
        with open(path, 'r') as f:
            if file_ext in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            elif file_ext == '.json':
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {file_ext}")
        
        # Create configuration from loaded data
        self.config = SystemConfig.from_dict(data)
        
        # Validate configuration
        self.config.validate()
        
        self.config_path = path
        return self.config
    
    def save(self, config: SystemConfig, output_path: Optional[str] = None) -> None:
        """
        Save configuration to file.
        
        Args:
            config: Configuration to save
            output_path: Path to save configuration. If None, uses instance path.
        
        Raises:
            ValueError: If no output path specified and no instance path set
        """
        path = output_path or self.config_path
        
        if path is None:
            raise ValueError("No output path specified")
        
        # Validate before saving
        config.validate()
        
        # Convert to dictionary
        data = config.to_dict()
        
        # Save based on file extension
        file_ext = Path(path).suffix.lower()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        
        with open(path, 'w') as f:
            if file_ext in ['.yaml', '.yml']:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            elif file_ext == '.json':
                json.dump(data, f, indent=2)
            else:
                raise ValueError(f"Unsupported configuration file format: {file_ext}")
        
        self.config = config
        self.config_path = path
    
    def get_config(self) -> SystemConfig:
        """
        Get current configuration.
        
        Returns:
            Current SystemConfig
        
        Raises:
            RuntimeError: If no configuration loaded
        """
        if self.config is None:
            raise RuntimeError("No configuration loaded. Call load() first.")
        return self.config
    
    def create_default_config(self, output_path: str = 'config.yaml') -> SystemConfig:
        """
        Create and save default configuration.
        
        Args:
            output_path: Path to save default configuration
        
        Returns:
            Default SystemConfig
        """
        config = SystemConfig()
        self.save(config, output_path)
        return config


# Convenience functions

def load_config(config_path: Optional[str] = None) -> SystemConfig:
    """
    Load configuration from file.
    
    Args:
        config_path: Path to configuration file. If None, searches default locations.
    
    Returns:
        Loaded and validated SystemConfig
    """
    manager = ConfigManager(config_path)
    return manager.load()


def save_config(config: SystemConfig, output_path: str) -> None:
    """
    Save configuration to file.
    
    Args:
        config: Configuration to save
        output_path: Path to save configuration
    """
    manager = ConfigManager()
    manager.save(config, output_path)


def create_default_config(output_path: str = 'config.yaml') -> SystemConfig:
    """
    Create and save default configuration.
    
    Args:
        output_path: Path to save default configuration
    
    Returns:
        Default SystemConfig
    """
    manager = ConfigManager()
    return manager.create_default_config(output_path)
