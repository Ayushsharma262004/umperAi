"""
Configuration management for the UmpirAI system.

This module handles loading, validation, and access to system configuration parameters.
"""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class VideoConfig:
    """Video processing configuration."""
    target_fps: int = 30
    frame_width: int = 1280
    frame_height: int = 720
    buffer_duration_seconds: float = 2.0
    exposure_adjustment_threshold: float = 0.30
    reconnection_attempts: int = 3
    reconnection_backoff_base: float = 1.0  # seconds
    
    def __post_init__(self):
        """Validate video configuration."""
        if self.target_fps <= 0:
            raise ValueError("target_fps must be positive")
        if self.frame_width <= 0 or self.frame_height <= 0:
            raise ValueError("frame dimensions must be positive")
        if self.buffer_duration_seconds <= 0:
            raise ValueError("buffer_duration_seconds must be positive")
        if not (0.0 < self.exposure_adjustment_threshold <= 1.0):
            raise ValueError("exposure_adjustment_threshold must be in (0, 1]")
        if self.reconnection_attempts < 0:
            raise ValueError("reconnection_attempts must be non-negative")


@dataclass
class DetectionConfig:
    """Object detection configuration."""
    model_name: str = "yolov8m"
    confidence_threshold_high: float = 0.90
    confidence_threshold_medium: float = 0.70
    confidence_threshold_low: float = 0.70
    target_accuracy_ball: float = 0.90
    target_accuracy_stumps: float = 0.95
    target_accuracy_players: float = 0.85
    use_gpu: bool = True
    fallback_to_cpu: bool = True
    
    def __post_init__(self):
        """Validate detection configuration."""
        if not (0.0 <= self.confidence_threshold_high <= 1.0):
            raise ValueError("confidence_threshold_high must be in [0, 1]")
        if not (0.0 <= self.confidence_threshold_medium <= 1.0):
            raise ValueError("confidence_threshold_medium must be in [0, 1]")
        if not (0.0 <= self.confidence_threshold_low <= 1.0):
            raise ValueError("confidence_threshold_low must be in [0, 1]")


@dataclass
class TrackingConfig:
    """Ball tracking configuration."""
    max_occlusion_frames: int = 10
    trajectory_history_frames: int = 30
    measurement_noise_sigma: float = 5.0  # pixels
    process_noise_sigma: float = 0.1
    gravity: float = 9.81  # m/s²
    drag_coefficient: float = 0.95
    
    def __post_init__(self):
        """Validate tracking configuration."""
        if self.max_occlusion_frames < 0:
            raise ValueError("max_occlusion_frames must be non-negative")
        if self.trajectory_history_frames <= 0:
            raise ValueError("trajectory_history_frames must be positive")
        if self.measurement_noise_sigma <= 0:
            raise ValueError("measurement_noise_sigma must be positive")
        if self.gravity <= 0:
            raise ValueError("gravity must be positive")


@dataclass
class DecisionConfig:
    """Decision engine configuration."""
    wide_guideline_offset: float = 1.0  # meters from batsman center
    batsman_movement_threshold: float = 0.5  # meters
    confidence_review_threshold: float = 0.80
    decision_latency_target_ms: float = 500.0
    decision_latency_max_ms: float = 1000.0
    fielder_control_frames: int = 3
    ground_contact_height_threshold: float = 0.1  # meters
    
    def __post_init__(self):
        """Validate decision configuration."""
        if self.wide_guideline_offset <= 0:
            raise ValueError("wide_guideline_offset must be positive")
        if self.batsman_movement_threshold < 0:
            raise ValueError("batsman_movement_threshold must be non-negative")
        if not (0.0 <= self.confidence_review_threshold <= 1.0):
            raise ValueError("confidence_review_threshold must be in [0, 1]")


@dataclass
class SynchronizationConfig:
    """Multi-camera synchronization configuration."""
    max_temporal_offset_ms: float = 50.0
    sync_quality_threshold: float = 0.8
    enable_frame_interpolation: bool = True
    
    def __post_init__(self):
        """Validate synchronization configuration."""
        if self.max_temporal_offset_ms <= 0:
            raise ValueError("max_temporal_offset_ms must be positive")
        if not (0.0 <= self.sync_quality_threshold <= 1.0):
            raise ValueError("sync_quality_threshold must be in [0, 1]")


@dataclass
class PerformanceConfig:
    """Performance monitoring configuration."""
    min_fps_threshold: int = 25
    max_latency_threshold_ms: float = 2000.0
    min_detection_accuracy: float = 0.80
    max_memory_usage_percent: float = 90.0
    max_cpu_usage_percent: float = 90.0
    resource_check_interval_seconds: float = 1.0
    
    def __post_init__(self):
        """Validate performance configuration."""
        if self.min_fps_threshold <= 0:
            raise ValueError("min_fps_threshold must be positive")
        if self.max_latency_threshold_ms <= 0:
            raise ValueError("max_latency_threshold_ms must be positive")


@dataclass
class LoggingConfig:
    """Logging configuration."""
    log_level: str = "INFO"
    log_retention_days: int = 30
    log_rotation_interval: str = "daily"
    enable_structured_logging: bool = True
    log_directory: str = "logs"
    
    def __post_init__(self):
        """Validate logging configuration."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        if self.log_retention_days <= 0:
            raise ValueError("log_retention_days must be positive")


@dataclass
class SystemConfig:
    """Complete system configuration."""
    video: VideoConfig = field(default_factory=VideoConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    decision: DecisionConfig = field(default_factory=DecisionConfig)
    synchronization: SynchronizationConfig = field(default_factory=SynchronizationConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)
    
    def to_json(self, filepath: Path) -> None:
        """Save configuration to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def to_yaml(self, filepath: Path) -> None:
        """Save configuration to YAML file."""
        with open(filepath, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)


class ConfigManager:
    """Manages system configuration loading and access."""
    
    def __init__(self, config: Optional[SystemConfig] = None):
        """
        Initialize configuration manager.
        
        Args:
            config: Optional SystemConfig instance. If None, uses defaults.
        """
        self._config = config if config is not None else SystemConfig()
    
    @classmethod
    def from_json(cls, filepath: Path) -> 'ConfigManager':
        """
        Load configuration from JSON file.
        
        Args:
            filepath: Path to JSON configuration file
            
        Returns:
            ConfigManager instance with loaded configuration
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        config = SystemConfig(
            video=VideoConfig(**data.get('video', {})),
            detection=DetectionConfig(**data.get('detection', {})),
            tracking=TrackingConfig(**data.get('tracking', {})),
            decision=DecisionConfig(**data.get('decision', {})),
            synchronization=SynchronizationConfig(**data.get('synchronization', {})),
            performance=PerformanceConfig(**data.get('performance', {})),
            logging=LoggingConfig(**data.get('logging', {}))
        )
        
        return cls(config)
    
    @classmethod
    def from_yaml(cls, filepath: Path) -> 'ConfigManager':
        """
        Load configuration from YAML file.
        
        Args:
            filepath: Path to YAML configuration file
            
        Returns:
            ConfigManager instance with loaded configuration
        """
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        config = SystemConfig(
            video=VideoConfig(**data.get('video', {})),
            detection=DetectionConfig(**data.get('detection', {})),
            tracking=TrackingConfig(**data.get('tracking', {})),
            decision=DecisionConfig(**data.get('decision', {})),
            synchronization=SynchronizationConfig(**data.get('synchronization', {})),
            performance=PerformanceConfig(**data.get('performance', {})),
            logging=LoggingConfig(**data.get('logging', {}))
        )
        
        return cls(config)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigManager':
        """
        Create configuration from dictionary.
        
        Args:
            data: Dictionary containing configuration data
            
        Returns:
            ConfigManager instance with loaded configuration
        """
        config = SystemConfig(
            video=VideoConfig(**data.get('video', {})),
            detection=DetectionConfig(**data.get('detection', {})),
            tracking=TrackingConfig(**data.get('tracking', {})),
            decision=DecisionConfig(**data.get('decision', {})),
            synchronization=SynchronizationConfig(**data.get('synchronization', {})),
            performance=PerformanceConfig(**data.get('performance', {})),
            logging=LoggingConfig(**data.get('logging', {}))
        )
        
        return cls(config)
    
    @property
    def config(self) -> SystemConfig:
        """Get the current system configuration."""
        return self._config
    
    def get_video_config(self) -> VideoConfig:
        """Get video processing configuration."""
        return self._config.video
    
    def get_detection_config(self) -> DetectionConfig:
        """Get object detection configuration."""
        return self._config.detection
    
    def get_tracking_config(self) -> TrackingConfig:
        """Get ball tracking configuration."""
        return self._config.tracking
    
    def get_decision_config(self) -> DecisionConfig:
        """Get decision engine configuration."""
        return self._config.decision
    
    def get_synchronization_config(self) -> SynchronizationConfig:
        """Get multi-camera synchronization configuration."""
        return self._config.synchronization
    
    def get_performance_config(self) -> PerformanceConfig:
        """Get performance monitoring configuration."""
        return self._config.performance
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration."""
        return self._config.logging
    
    def save(self, filepath: Path, format: str = 'json') -> None:
        """
        Save configuration to file.
        
        Args:
            filepath: Path to save configuration
            format: File format ('json' or 'yaml')
        """
        if format.lower() == 'json':
            self._config.to_json(filepath)
        elif format.lower() == 'yaml':
            self._config.to_yaml(filepath)
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'yaml'")
    
    def validate(self) -> bool:
        """
        Validate the current configuration.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        # Validation is performed in __post_init__ of each config dataclass
        # If we reach here, configuration is valid
        return True
