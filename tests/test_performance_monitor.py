"""
Unit tests for PerformanceMonitor.

Tests specific examples and edge cases for performance monitoring,
alert threshold logic, metric aggregation, and resource monitoring.
"""

import pytest
import time
from umpirai.monitoring.performance_monitor import (
    PerformanceMonitor,
    PerformanceMetrics,
    ResourceUsage,
    Alert,
    AlertType
)


class TestPerformanceMonitorInitialization:
    """Test PerformanceMonitor initialization."""
    
    def test_initialization_default(self):
        """Test default initialization."""
        monitor = PerformanceMonitor()
        assert monitor._history_size == 100
        assert len(monitor._metrics_history) == 0
        assert len(monitor._active_alerts) == 0
        assert monitor._frame_count == 0
    
    def test_initialization_custom_history_size(self):
        """Test initialization with custom history size."""
        monitor = PerformanceMonitor(history_size=50)
        assert monitor._history_size == 50
    
    def test_initialization_invalid_history_size(self):
        """Test initialization with invalid history size."""
        with pytest.raises(ValueError):
            PerformanceMonitor(history_size=0)
        
        with pytest.raises(ValueError):
            PerformanceMonitor(history_size=-10)


class TestResourceUsage:
    """Test ResourceUsage data class."""
    
    def test_resource_usage_valid(self):
        """Test valid ResourceUsage creation."""
        usage = ResourceUsage(
            cpu_percent=45.5,
            memory_mb=1024.0,
            memory_percent=50.0
        )
        assert usage.cpu_percent == 45.5
        assert usage.memory_mb == 1024.0
        assert usage.memory_percent == 50.0
        assert usage.gpu_percent is None
        assert usage.gpu_memory_mb is None
    
    def test_resource_usage_with_gpu(self):
        """Test ResourceUsage with GPU metrics."""
        usage = ResourceUsage(
            cpu_percent=45.5,
            memory_mb=1024.0,
            memory_percent=50.0,
            gpu_percent=75.0,
            gpu_memory_mb=2048.0
        )
        assert usage.gpu_percent == 75.0
        assert usage.gpu_memory_mb == 2048.0
    
    def test_resource_usage_invalid_cpu(self):
        """Test ResourceUsage with invalid CPU percentage."""
        with pytest.raises(ValueError):
            ResourceUsage(
                cpu_percent=150.0,  # Invalid: >100
                memory_mb=1024.0,
                memory_percent=50.0
            )
        
        with pytest.raises(ValueError):
            ResourceUsage(
                cpu_percent=-10.0,  # Invalid: <0
                memory_mb=1024.0,
                memory_percent=50.0
            )
    
    def test_resource_usage_invalid_memory(self):
        """Test ResourceUsage with invalid memory values."""
        with pytest.raises(ValueError):
            ResourceUsage(
                cpu_percent=50.0,
                memory_mb=-100.0,  # Invalid: negative
                memory_percent=50.0
            )
        
        with pytest.raises(ValueError):
            ResourceUsage(
                cpu_percent=50.0,
                memory_mb=1024.0,
                memory_percent=150.0  # Invalid: >100
            )


class TestPerformanceMetrics:
    """Test PerformanceMetrics data class."""
    
    def test_performance_metrics_valid(self):
        """Test valid PerformanceMetrics creation."""
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            fps=30.0,
            processing_latency_ms=100.0
        )
        assert metrics.fps == 30.0
        assert metrics.processing_latency_ms == 100.0
        assert metrics.detection_accuracy is None
        assert metrics.resource_usage is None
    
    def test_performance_metrics_with_all_fields(self):
        """Test PerformanceMetrics with all optional fields."""
        resource_usage = ResourceUsage(
            cpu_percent=50.0,
            memory_mb=1024.0,
            memory_percent=50.0
        )
        
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            fps=30.0,
            processing_latency_ms=100.0,
            detection_accuracy=0.95,
            resource_usage=resource_usage
        )
        assert metrics.detection_accuracy == 0.95
        assert metrics.resource_usage == resource_usage
    
    def test_performance_metrics_invalid_fps(self):
        """Test PerformanceMetrics with invalid FPS."""
        with pytest.raises(ValueError):
            PerformanceMetrics(
                timestamp=time.time(),
                fps=-10.0,  # Invalid: negative
                processing_latency_ms=100.0
            )
    
    def test_performance_metrics_invalid_latency(self):
        """Test PerformanceMetrics with invalid latency."""
        with pytest.raises(ValueError):
            PerformanceMetrics(
                timestamp=time.time(),
                fps=30.0,
                processing_latency_ms=-50.0  # Invalid: negative
            )
    
    def test_performance_metrics_invalid_accuracy(self):
        """Test PerformanceMetrics with invalid detection accuracy."""
        with pytest.raises(ValueError):
            PerformanceMetrics(
                timestamp=time.time(),
                fps=30.0,
                processing_latency_ms=100.0,
                detection_accuracy=1.5  # Invalid: >1.0
            )


class TestAlert:
    """Test Alert data class."""
    
    def test_alert_valid(self):
        """Test valid Alert creation."""
        alert = Alert(
            alert_type=AlertType.LOW_FPS,
            message="Frame rate degraded",
            timestamp=time.time()
        )
        assert alert.alert_type == AlertType.LOW_FPS
        assert alert.message == "Frame rate degraded"
        assert alert.severity == "warning"
    
    def test_alert_custom_severity(self):
        """Test Alert with custom severity."""
        alert = Alert(
            alert_type=AlertType.HIGH_MEMORY_USAGE,
            message="Memory pressure high",
            timestamp=time.time(),
            severity="critical"
        )
        assert alert.severity == "critical"
    
    def test_alert_invalid_severity(self):
        """Test Alert with invalid severity."""
        with pytest.raises(ValueError):
            Alert(
                alert_type=AlertType.LOW_FPS,
                message="Test",
                timestamp=time.time(),
                severity="invalid"
            )


class TestMetricUpdates:
    """Test metric update functionality."""
    
    def test_update_metrics_single(self):
        """Test updating with single metric."""
        monitor = PerformanceMonitor()
        
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            fps=30.0,
            processing_latency_ms=100.0
        )
        
        monitor.update_metrics(metrics)
        
        assert monitor._frame_count == 1
        assert len(monitor._metrics_history) == 1
        assert monitor._metrics_history[0] == metrics
    
    def test_update_metrics_multiple(self):
        """Test updating with multiple metrics."""
        monitor = PerformanceMonitor(history_size=10)
        
        base_timestamp = time.time()
        for i in range(15):
            metrics = PerformanceMetrics(
                timestamp=base_timestamp + i * 0.033,
                fps=30.0,
                processing_latency_ms=100.0
            )
            monitor.update_metrics(metrics)
        
        assert monitor._frame_count == 15
        # History should be limited to 10
        assert len(monitor._metrics_history) == 10
    
    def test_update_metrics_invalid_type(self):
        """Test updating with invalid metric type."""
        monitor = PerformanceMonitor()
        
        with pytest.raises(TypeError):
            monitor.update_metrics("invalid")


class TestFPSCalculation:
    """Test FPS calculation."""
    
    def test_get_current_fps_no_frames(self):
        """Test FPS calculation with no frames."""
        monitor = PerformanceMonitor()
        assert monitor.get_current_fps() == 0.0
    
    def test_get_current_fps_single_frame(self):
        """Test FPS calculation with single frame."""
        monitor = PerformanceMonitor()
        
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            fps=30.0,
            processing_latency_ms=100.0
        )
        monitor.update_metrics(metrics)
        
        # Single frame should return 0.0
        assert monitor.get_current_fps() == 0.0
    
    def test_get_current_fps_multiple_frames(self):
        """Test FPS calculation with multiple frames."""
        monitor = PerformanceMonitor()
        
        base_timestamp = time.time()
        target_fps = 30.0
        frame_interval = 1.0 / target_fps
        
        # Add 30 frames at 30 FPS
        for i in range(30):
            metrics = PerformanceMetrics(
                timestamp=base_timestamp + i * frame_interval,
                fps=target_fps,
                processing_latency_ms=100.0
            )
            monitor.update_metrics(metrics)
        
        calculated_fps = monitor.get_current_fps()
        # Should be close to 30 FPS
        assert 29.0 <= calculated_fps <= 31.0
    
    def test_get_current_fps_variable_rate(self):
        """Test FPS calculation with variable frame rate."""
        monitor = PerformanceMonitor()
        
        base_timestamp = time.time()
        
        # Add frames with varying intervals
        intervals = [0.033, 0.040, 0.030, 0.035, 0.033]  # Variable timing
        current_time = base_timestamp
        
        for interval in intervals:
            metrics = PerformanceMetrics(
                timestamp=current_time,
                fps=30.0,
                processing_latency_ms=100.0
            )
            monitor.update_metrics(metrics)
            current_time += interval
        
        calculated_fps = monitor.get_current_fps()
        assert calculated_fps > 0


class TestLatencyTracking:
    """Test processing latency tracking."""
    
    def test_get_processing_latency_no_metrics(self):
        """Test latency retrieval with no metrics."""
        monitor = PerformanceMonitor()
        assert monitor.get_processing_latency() == 0.0
    
    def test_get_processing_latency_single_metric(self):
        """Test latency retrieval with single metric."""
        monitor = PerformanceMonitor()
        
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            fps=30.0,
            processing_latency_ms=150.0
        )
        monitor.update_metrics(metrics)
        
        assert monitor.get_processing_latency() == 150.0
    
    def test_get_processing_latency_multiple_metrics(self):
        """Test latency retrieval returns most recent value."""
        monitor = PerformanceMonitor()
        
        base_timestamp = time.time()
        
        # Add metrics with different latencies
        for i, latency in enumerate([100.0, 150.0, 200.0, 120.0]):
            metrics = PerformanceMetrics(
                timestamp=base_timestamp + i * 0.033,
                fps=30.0,
                processing_latency_ms=latency
            )
            monitor.update_metrics(metrics)
        
        # Should return most recent latency
        assert monitor.get_processing_latency() == 120.0


class TestAlertThresholds:
    """Test alert threshold logic."""
    
    def test_alert_low_fps(self):
        """Test alert generation for low FPS."""
        monitor = PerformanceMonitor()
        
        base_timestamp = time.time()
        low_fps = 20.0
        frame_interval = 1.0 / low_fps
        
        # Add frames at low FPS
        for i in range(30):
            metrics = PerformanceMetrics(
                timestamp=base_timestamp + i * frame_interval,
                fps=low_fps,
                processing_latency_ms=100.0
            )
            monitor.update_metrics(metrics)
        
        alerts = monitor.check_alerts()
        alert_types = [alert.alert_type for alert in alerts]
        
        assert AlertType.LOW_FPS in alert_types
    
    def test_alert_high_latency(self):
        """Test alert generation for high latency."""
        monitor = PerformanceMonitor()
        
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            fps=30.0,
            processing_latency_ms=2500.0  # Above threshold
        )
        monitor.update_metrics(metrics)
        
        alerts = monitor.check_alerts()
        alert_types = [alert.alert_type for alert in alerts]
        
        assert AlertType.HIGH_LATENCY in alert_types
    
    def test_alert_low_detection_accuracy(self):
        """Test alert generation for low detection accuracy."""
        monitor = PerformanceMonitor()
        
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            fps=30.0,
            processing_latency_ms=100.0,
            detection_accuracy=0.75  # Below threshold
        )
        monitor.update_metrics(metrics)
        
        alerts = monitor.check_alerts()
        alert_types = [alert.alert_type for alert in alerts]
        
        assert AlertType.LOW_DETECTION_ACCURACY in alert_types
    
    def test_alert_high_memory_usage(self):
        """Test alert generation for high memory usage."""
        monitor = PerformanceMonitor()
        
        resource_usage = ResourceUsage(
            cpu_percent=50.0,
            memory_mb=8192.0,
            memory_percent=95.0  # Above threshold
        )
        
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            fps=30.0,
            processing_latency_ms=100.0,
            resource_usage=resource_usage
        )
        monitor.update_metrics(metrics)
        
        alerts = monitor.check_alerts()
        alert_types = [alert.alert_type for alert in alerts]
        
        assert AlertType.HIGH_MEMORY_USAGE in alert_types
    
    def test_no_alerts_within_thresholds(self):
        """Test no alerts when all metrics are within thresholds."""
        monitor = PerformanceMonitor()
        
        base_timestamp = time.time()
        good_fps = 30.0
        frame_interval = 1.0 / good_fps
        
        resource_usage = ResourceUsage(
            cpu_percent=50.0,
            memory_mb=2048.0,
            memory_percent=50.0
        )
        
        # Add frames with good metrics
        for i in range(30):
            metrics = PerformanceMetrics(
                timestamp=base_timestamp + i * frame_interval,
                fps=good_fps,
                processing_latency_ms=500.0,  # Below threshold
                detection_accuracy=0.95,  # Above threshold
                resource_usage=resource_usage
            )
            monitor.update_metrics(metrics)
        
        alerts = monitor.check_alerts()
        assert len(alerts) == 0
    
    def test_multiple_alerts_simultaneously(self):
        """Test multiple alerts triggered simultaneously."""
        monitor = PerformanceMonitor()
        
        resource_usage = ResourceUsage(
            cpu_percent=50.0,
            memory_mb=8192.0,
            memory_percent=95.0  # Above threshold
        )
        
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            fps=30.0,
            processing_latency_ms=2500.0,  # Above threshold
            detection_accuracy=0.75,  # Below threshold
            resource_usage=resource_usage
        )
        monitor.update_metrics(metrics)
        
        alerts = monitor.check_alerts()
        alert_types = [alert.alert_type for alert in alerts]
        
        # Should have multiple alerts
        assert AlertType.HIGH_LATENCY in alert_types
        assert AlertType.LOW_DETECTION_ACCURACY in alert_types
        assert AlertType.HIGH_MEMORY_USAGE in alert_types


class TestResourceMonitoring:
    """Test resource usage monitoring."""
    
    def test_get_resource_usage(self):
        """Test resource usage retrieval."""
        monitor = PerformanceMonitor()
        
        usage = monitor.get_resource_usage()
        
        assert isinstance(usage, ResourceUsage)
        assert 0 <= usage.cpu_percent <= 100
        assert usage.memory_mb >= 0
        assert 0 <= usage.memory_percent <= 100
    
    def test_resource_usage_consistency(self):
        """Test resource usage returns consistent data."""
        monitor = PerformanceMonitor()
        
        usage1 = monitor.get_resource_usage()
        usage2 = monitor.get_resource_usage()
        
        # Values should be similar (within reasonable range)
        assert abs(usage1.cpu_percent - usage2.cpu_percent) < 50
        assert abs(usage1.memory_mb - usage2.memory_mb) < 1000


class TestMetricDisplay:
    """Test metric display functionality."""
    
    def test_display_metrics_structure(self):
        """Test display metrics returns correct structure."""
        monitor = PerformanceMonitor()
        
        metrics = PerformanceMetrics(
            timestamp=time.time(),
            fps=30.0,
            processing_latency_ms=100.0
        )
        monitor.update_metrics(metrics)
        
        display = monitor.display_metrics()
        
        assert "fps" in display
        assert "processing_latency_ms" in display
        assert "cpu_percent" in display
        assert "memory_mb" in display
        assert "memory_percent" in display
        assert "frame_count" in display
        assert "alerts" in display
    
    def test_display_metrics_values(self):
        """Test display metrics contains valid values."""
        monitor = PerformanceMonitor()
        
        base_timestamp = time.time()
        
        for i in range(10):
            metrics = PerformanceMetrics(
                timestamp=base_timestamp + i * 0.033,
                fps=30.0,
                processing_latency_ms=100.0
            )
            monitor.update_metrics(metrics)
        
        display = monitor.display_metrics()
        
        assert display["fps"] >= 0
        assert display["processing_latency_ms"] >= 0
        assert 0 <= display["cpu_percent"] <= 100
        assert display["memory_mb"] >= 0
        assert 0 <= display["memory_percent"] <= 100
        assert display["frame_count"] == 10
        assert display["alerts"] >= 0


class TestMetricAggregation:
    """Test metric aggregation and history."""
    
    def test_get_metrics_history(self):
        """Test metrics history retrieval."""
        monitor = PerformanceMonitor(history_size=10)
        
        base_timestamp = time.time()
        metrics_list = []
        
        for i in range(5):
            metrics = PerformanceMetrics(
                timestamp=base_timestamp + i * 0.033,
                fps=30.0,
                processing_latency_ms=100.0
            )
            metrics_list.append(metrics)
            monitor.update_metrics(metrics)
        
        history = monitor.get_metrics_history()
        
        assert len(history) == 5
        assert history == metrics_list
    
    def test_metrics_history_limit(self):
        """Test metrics history respects size limit."""
        monitor = PerformanceMonitor(history_size=5)
        
        base_timestamp = time.time()
        
        for i in range(10):
            metrics = PerformanceMetrics(
                timestamp=base_timestamp + i * 0.033,
                fps=30.0,
                processing_latency_ms=100.0
            )
            monitor.update_metrics(metrics)
        
        history = monitor.get_metrics_history()
        
        # Should only keep last 5
        assert len(history) == 5


class TestReset:
    """Test monitor reset functionality."""
    
    def test_reset(self):
        """Test reset clears all state."""
        monitor = PerformanceMonitor()
        
        # Add some metrics
        base_timestamp = time.time()
        for i in range(10):
            metrics = PerformanceMetrics(
                timestamp=base_timestamp + i * 0.033,
                fps=30.0,
                processing_latency_ms=100.0
            )
            monitor.update_metrics(metrics)
        
        # Reset
        monitor.reset()
        
        assert monitor._frame_count == 0
        assert len(monitor._metrics_history) == 0
        assert len(monitor._active_alerts) == 0
        assert len(monitor._frame_timestamps) == 0
