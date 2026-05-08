"""
Unit tests for configuration management system.
"""

import pytest
import os
import tempfile
import json
import yaml
from pathlib import Path

from umpirai.config.config_manager import (
    SystemConfig,
    VideoConfig,
    DetectionConfig,
    TrackingConfig,
    DecisionConfig,
    OutputConfig,
    LoggingConfig,
    PerformanceConfig,
    CalibrationConfig,
    ConfigManager,
    load_config,
    save_config,
    create_default_config
)


class TestVideoConfig:
    """Test VideoConfig validation."""
    
    def test_valid_video_config(self):
        """Test valid video configuration."""
        config = VideoConfig()
        config.validate()  # Should not raise
    
    def test_invalid_fps(self):
        """Test invalid FPS value."""
        config = VideoConfig(target_fps=-1)
        with pytest.raises(ValueError, match="target_fps must be positive"):
            config.validate()
    
    def test_invalid_resolution(self):
        """Test invalid resolution."""
        config = VideoConfig(resolution_width=-1)
        with pytest.raises(ValueError, match="Resolution dimensions must be positive"):
            config.validate()
    
    def test_invalid_buffer_size(self):
        """Test invalid buffer size."""
        config = VideoConfig(buffer_size_seconds=-1.0)
        with pytest.raises(ValueError, match="buffer_size_seconds must be positive"):
            config.validate()
    
    def test_invalid_exposure_threshold(self):
        """Test invalid exposure threshold."""
        config = VideoConfig(exposure_adjustment_threshold=1.5)
        with pytest.raises(ValueError, match="exposure_adjustment_threshold must be between 0 and 1"):
            config.validate()


class TestDetectionConfig:
    """Test DetectionConfig validation."""
    
    def test_valid_detection_config(self):
        """Test valid detection configuration."""
        config = DetectionConfig()
        config.validate()  # Should not raise
    
    def test_invalid_confidence_order(self):
        """Test invalid confidence threshold ordering."""
        config = DetectionConfig(
            confidence_threshold_high=0.5,
            confidence_threshold_low=0.9
        )
        with pytest.raises(ValueError, match="Confidence thresholds must be in ascending order"):
            config.validate()
    
    def test_invalid_max_cameras(self):
        """Test invalid max cameras."""
        config = DetectionConfig(max_cameras=5)
        with pytest.raises(ValueError, match="max_cameras must be between 1 and 4"):
            config.validate()


class TestTrackingConfig:
    """Test TrackingConfig validation."""
    
    def test_valid_tracking_config(self):
        """Test valid tracking configuration."""
        config = TrackingConfig()
        config.validate()  # Should not raise
    
    def test_invalid_occlusion_frames(self):
        """Test invalid occlusion frames."""
        config = TrackingConfig(max_occlusion_frames=0)
        with pytest.raises(ValueError, match="max_occlusion_frames must be at least 1"):
            config.validate()
    
    def test_invalid_noise(self):
        """Test invalid noise parameters."""
        config = TrackingConfig(process_noise=-0.1)
        with pytest.raises(ValueError, match="Noise parameters must be positive"):
            config.validate()


class TestDecisionConfig:
    """Test DecisionConfig validation."""
    
    def test_valid_decision_config(self):
        """Test valid decision configuration."""
        config = DecisionConfig()
        config.validate()  # Should not raise
    
    def test_invalid_confidence_threshold(self):
        """Test invalid confidence threshold."""
        config = DecisionConfig(confidence_review_threshold=1.5)
        with pytest.raises(ValueError, match="confidence_review_threshold must be between 0 and 1"):
            config.validate()
    
    def test_invalid_wide_guideline(self):
        """Test invalid wide guideline offset."""
        config = DecisionConfig(wide_guideline_offset=-1.0)
        with pytest.raises(ValueError, match="wide_guideline_offset must be positive"):
            config.validate()


class TestOutputConfig:
    """Test OutputConfig validation."""
    
    def test_valid_output_config(self):
        """Test valid output configuration."""
        config = OutputConfig()
        config.validate()  # Should not raise
    
    def test_invalid_latency(self):
        """Test invalid latency values."""
        config = OutputConfig(
            decision_latency_target_ms=1000.0,
            decision_latency_max_ms=500.0
        )
        with pytest.raises(ValueError, match="decision_latency_max_ms must be >= decision_latency_target_ms"):
            config.validate()


class TestLoggingConfig:
    """Test LoggingConfig validation."""
    
    def test_valid_logging_config(self):
        """Test valid logging configuration."""
        config = LoggingConfig()
        config.validate()  # Should not raise
    
    def test_invalid_log_level(self):
        """Test invalid log level."""
        config = LoggingConfig(log_level="INVALID")
        with pytest.raises(ValueError, match="log_level must be one of"):
            config.validate()
    
    def test_invalid_retention(self):
        """Test invalid retention days."""
        config = LoggingConfig(retention_days=0)
        with pytest.raises(ValueError, match="retention_days must be at least 1"):
            config.validate()
    
    def test_invalid_log_format(self):
        """Test invalid log format."""
        config = LoggingConfig(log_format="invalid")
        with pytest.raises(ValueError, match="log_format must be"):
            config.validate()


class TestPerformanceConfig:
    """Test PerformanceConfig validation."""
    
    def test_valid_performance_config(self):
        """Test valid performance configuration."""
        config = PerformanceConfig()
        config.validate()  # Should not raise
    
    def test_invalid_fps_threshold(self):
        """Test invalid FPS threshold."""
        config = PerformanceConfig(fps_alert_threshold=-1.0)
        with pytest.raises(ValueError, match="fps_alert_threshold must be positive"):
            config.validate()
    
    def test_invalid_memory_threshold(self):
        """Test invalid memory threshold."""
        config = PerformanceConfig(memory_alert_threshold_percent=150.0)
        with pytest.raises(ValueError, match="memory_alert_threshold_percent must be between 0 and 100"):
            config.validate()


class TestSystemConfig:
    """Test SystemConfig."""
    
    def test_default_system_config(self):
        """Test default system configuration."""
        config = SystemConfig()
        config.validate()  # Should not raise
    
    def test_system_config_to_dict(self):
        """Test converting system config to dictionary."""
        config = SystemConfig()
        data = config.to_dict()
        
        assert isinstance(data, dict)
        assert 'video' in data
        assert 'detection' in data
        assert 'tracking' in data
        assert 'decision' in data
        assert 'output' in data
        assert 'logging' in data
        assert 'performance' in data
        assert 'calibration' in data
    
    def test_system_config_from_dict(self):
        """Test creating system config from dictionary."""
        data = {
            'video': {'target_fps': 60},
            'detection': {'max_cameras': 2},
            'max_runtime_minutes': 180
        }
        
        config = SystemConfig.from_dict(data)
        
        assert config.video.target_fps == 60
        assert config.detection.max_cameras == 2
        assert config.max_runtime_minutes == 180
    
    def test_invalid_max_runtime(self):
        """Test invalid max runtime."""
        config = SystemConfig(max_runtime_minutes=0)
        with pytest.raises(ValueError, match="max_runtime_minutes must be at least 1"):
            config.validate()


class TestConfigManager:
    """Test ConfigManager."""
    
    def test_create_default_config(self):
        """Test creating default configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'config.yaml')
            manager = ConfigManager()
            config = manager.create_default_config(output_path)
            
            assert isinstance(config, SystemConfig)
            assert os.path.exists(output_path)
    
    def test_save_and_load_yaml(self):
        """Test saving and loading YAML configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'test_config.yaml')
            
            # Create and save config
            config = SystemConfig()
            config.video.target_fps = 60
            config.detection.max_cameras = 2
            
            manager = ConfigManager()
            manager.save(config, config_path)
            
            # Load config
            loaded_config = manager.load(config_path)
            
            assert loaded_config.video.target_fps == 60
            assert loaded_config.detection.max_cameras == 2
    
    def test_save_and_load_json(self):
        """Test saving and loading JSON configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'test_config.json')
            
            # Create and save config
            config = SystemConfig()
            config.video.target_fps = 60
            
            manager = ConfigManager()
            manager.save(config, config_path)
            
            # Load config
            loaded_config = manager.load(config_path)
            
            assert loaded_config.video.target_fps == 60
    
    def test_load_nonexistent_file(self):
        """Test loading nonexistent configuration file."""
        manager = ConfigManager()
        with pytest.raises(FileNotFoundError):
            manager.load('nonexistent_config.yaml')
    
    def test_save_without_path(self):
        """Test saving without specifying path."""
        manager = ConfigManager()
        config = SystemConfig()
        
        with pytest.raises(ValueError, match="No output path specified"):
            manager.save(config)
    
    def test_get_config_before_load(self):
        """Test getting config before loading."""
        manager = ConfigManager()
        with pytest.raises(RuntimeError, match="No configuration loaded"):
            manager.get_config()
    
    def test_unsupported_file_format(self):
        """Test unsupported file format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.txt')
            
            manager = ConfigManager()
            config = SystemConfig()
            
            with pytest.raises(ValueError, match="Unsupported configuration file format"):
                manager.save(config, config_path)


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_load_config_function(self):
        """Test load_config convenience function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.yaml')
            
            # Create config file
            config = SystemConfig()
            save_config(config, config_path)
            
            # Load using convenience function
            loaded_config = load_config(config_path)
            
            assert isinstance(loaded_config, SystemConfig)
    
    def test_save_config_function(self):
        """Test save_config convenience function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.yaml')
            
            config = SystemConfig()
            config.video.target_fps = 60
            
            save_config(config, config_path)
            
            assert os.path.exists(config_path)
            
            # Verify saved content
            loaded_config = load_config(config_path)
            assert loaded_config.video.target_fps == 60
    
    def test_create_default_config_function(self):
        """Test create_default_config convenience function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.yaml')
            
            config = create_default_config(config_path)
            
            assert isinstance(config, SystemConfig)
            assert os.path.exists(config_path)


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_validate_on_load(self):
        """Test that configuration is validated on load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'invalid_config.yaml')
            
            # Create invalid config manually
            invalid_data = {
                'video': {'target_fps': -1}  # Invalid
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(invalid_data, f)
            
            manager = ConfigManager()
            with pytest.raises(ValueError):
                manager.load(config_path)
    
    def test_validate_on_save(self):
        """Test that configuration is validated on save."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.yaml')
            
            config = SystemConfig()
            config.video.target_fps = -1  # Invalid
            
            manager = ConfigManager()
            with pytest.raises(ValueError):
                manager.save(config, config_path)


class TestConfigRoundTrip:
    """Test configuration round-trip (save and load)."""
    
    def test_yaml_round_trip(self):
        """Test YAML round-trip preserves all values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.yaml')
            
            # Create config with custom values
            config = SystemConfig()
            config.video.target_fps = 60
            config.video.resolution_width = 1920
            config.detection.max_cameras = 3
            config.tracking.max_occlusion_frames = 15
            config.decision.confidence_review_threshold = 0.85
            config.output.enable_audio_announcement = True
            config.logging.log_level = "DEBUG"
            config.performance.fps_alert_threshold = 20.0
            config.max_runtime_minutes = 180
            
            # Save and load
            save_config(config, config_path)
            loaded_config = load_config(config_path)
            
            # Verify all values preserved
            assert loaded_config.video.target_fps == 60
            assert loaded_config.video.resolution_width == 1920
            assert loaded_config.detection.max_cameras == 3
            assert loaded_config.tracking.max_occlusion_frames == 15
            assert loaded_config.decision.confidence_review_threshold == 0.85
            assert loaded_config.output.enable_audio_announcement == True
            assert loaded_config.logging.log_level == "DEBUG"
            assert loaded_config.performance.fps_alert_threshold == 20.0
            assert loaded_config.max_runtime_minutes == 180
    
    def test_json_round_trip(self):
        """Test JSON round-trip preserves all values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.json')
            
            config = SystemConfig()
            config.video.target_fps = 60
            config.detection.max_cameras = 2
            
            save_config(config, config_path)
            loaded_config = load_config(config_path)
            
            assert loaded_config.video.target_fps == 60
            assert loaded_config.detection.max_cameras == 2
