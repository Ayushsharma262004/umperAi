"""
Property-based tests for PerformanceMonitor.

Tests universal correctness properties for performance monitoring,
metric display, alert triggering, and resource usage logging.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
import time
from umpirai.monitoring.performance_monitor import (
    PerformanceMonitor,
    PerformanceMetrics,
    ResourceUsage,
    AlertType
)


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def resource_usage_strategy(draw):
    """Generate valid ResourceUsage instances."""
    cpu_percent = draw(st.floats(min_value=0.0, max_value=100.0))
    memory_mb = draw(st.floats(min_value=0.0, max_value=32768.0))
    memory_percent = draw(st.floats(min_value=0.0, max_value=100.0))
    
    # Optionally include GPU metrics
    include_gpu = draw(st.booleans())
    gpu_percent = draw(st.floats(min_value=0.0, max_value=100.0)) if include_gpu else None
    gpu_memory_mb = draw(st.floats(min_value=0.0, max_value=16384.0)) if include_gpu else None
    
    return ResourceUsage(
        cpu_percent=cpu_percent,
        memory_mb=memory_mb,
        memory_percent=memory_percent,
        gpu_percent=gpu_percent,
        gpu_memory_mb=gpu_memory_mb
    )


@st.composite
def performance_metrics_strategy(draw):
    """Generate valid PerformanceMetrics instances."""
    timestamp = draw(st.floats(min_value=0.0, max_value=1e10))
    fps = draw(st.floats(min_value=0.0, max_value=120.0))
    processing_latency_ms = draw(st.floats(min_value=0.0, max_value=5000.0))
    
    # Optionally include detection accuracy
    include_accuracy = draw(st.booleans())
    detection_accuracy = draw(st.floats(min_value=0.0, max_value=1.0)) if include_accuracy else None
    
    # Optionally include resource usage
    include_resources = draw(st.booleans())
    resource_usage = draw(resource_usage_strategy()) if include_resources else None
    
    return PerformanceMetrics(
        timestamp=timestamp,
        fps=fps,
        processing_latency_ms=processing_latency_ms,
        detection_accuracy=detection_accuracy,
        resource_usage=resource_usage
    )


# ============================================================================
# Property 30: Performance Metric Display
# ============================================================================

@given(st.lists(performance_metrics_strategy(), min_size=1, max_size=50))
def test_property_30_performance_metric_display(metrics_list):
    """
    Property 30: Performance Metric Display
    
    For any system operational state, the Performance Monitor SHALL display
    current frame rate and processing latency.
    
    Validates: Requirements 16.1, 16.2
    """
    monitor = PerformanceMonitor(history_size=100)
    
    # Update monitor with metrics
    for metrics in metrics_list:
        monitor.update_metrics(metrics)
    
    # Get display metrics
    display = monitor.display_metrics()
    
    # Property: Display must include FPS
    assert "fps" in display, "Display must include FPS metric"
    assert isinstance(display["fps"], (int, float)), "FPS must be numeric"
    assert display["fps"] >= 0, "FPS must be non-negative"
    
    # Property: Display must include processing latency
    assert "processing_latency_ms" in display, "Display must include processing latency"
    assert isinstance(display["processing_latency_ms"], (int, float)), "Latency must be numeric"
    assert display["processing_latency_ms"] >= 0, "Latency must be non-negative"
    
    # Property: Display must include resource usage metrics
    assert "cpu_percent" in display, "Display must include CPU usage"
    assert "memory_mb" in display, "Display must include memory usage"
    assert "memory_percent" in display, "Display must include memory percentage"
    
    # Property: get_current_fps() must return valid FPS
    current_fps = monitor.get_current_fps()
    assert isinstance(current_fps, (int, float)), "get_current_fps() must return numeric value"
    assert current_fps >= 0, "get_current_fps() must return non-negative value"
    
    # Property: get_processing_latency() must return valid latency
    current_latency = monitor.get_processing_latency()
    assert isinstance(current_latency, (int, float)), "get_processing_latency() must return numeric value"
    assert current_latency >= 0, "get_processing_latency() must return non-negative value"


# ============================================================================
# Property 31: Performance Alert Triggering
# ============================================================================

@given(
    fps=st.floats(min_value=0.0, max_value=120.0),
    latency_ms=st.floats(min_value=0.0, max_value=5000.0),
    detection_accuracy=st.floats(min_value=0.0, max_value=1.0),
    memory_percent=st.floats(min_value=0.0, max_value=100.0)
)
def test_property_31_performance_alert_triggering(fps, latency_ms, detection_accuracy, memory_percent):
    """
    Property 31: Performance Alert Triggering
    
    For any system state where frame rate drops below 25 FPS or processing
    latency exceeds 2 seconds, the system SHALL generate an operator alert.
    
    Validates: Requirements 16.3, 16.4
    """
    monitor = PerformanceMonitor(history_size=100)
    
    # Create resource usage with specified memory
    resource_usage = ResourceUsage(
        cpu_percent=50.0,
        memory_mb=1024.0,
        memory_percent=memory_percent
    )
    
    # Create metrics with specified values
    # Need to add multiple metrics to calculate FPS accurately
    base_timestamp = time.time()
    
    # Add 30 frames to establish FPS
    if fps > 0:
        frame_interval = 1.0 / fps
        for i in range(30):
            metrics = PerformanceMetrics(
                timestamp=base_timestamp + i * frame_interval,
                fps=fps,
                processing_latency_ms=latency_ms,
                detection_accuracy=detection_accuracy,
                resource_usage=resource_usage
            )
            monitor.update_metrics(metrics)
    else:
        # For zero FPS, just add one metric
        metrics = PerformanceMetrics(
            timestamp=base_timestamp,
            fps=fps,
            processing_latency_ms=latency_ms,
            detection_accuracy=detection_accuracy,
            resource_usage=resource_usage
        )
        monitor.update_metrics(metrics)
    
    # Check alerts
    alerts = monitor.check_alerts()
    alert_types = [alert.alert_type for alert in alerts]
    
    # Property: Low FPS triggers alert
    calculated_fps = monitor.get_current_fps()
    if calculated_fps > 0 and calculated_fps < PerformanceMonitor.FPS_THRESHOLD:
        assert AlertType.LOW_FPS in alert_types, \
            f"Low FPS ({calculated_fps:.1f}) must trigger alert (threshold: {PerformanceMonitor.FPS_THRESHOLD})"
    
    # Property: High latency triggers alert
    if latency_ms > PerformanceMonitor.LATENCY_THRESHOLD_MS:
        assert AlertType.HIGH_LATENCY in alert_types, \
            f"High latency ({latency_ms:.0f} ms) must trigger alert (threshold: {PerformanceMonitor.LATENCY_THRESHOLD_MS} ms)"
    
    # Property: Low detection accuracy triggers alert
    if detection_accuracy < PerformanceMonitor.DETECTION_ACCURACY_THRESHOLD:
        assert AlertType.LOW_DETECTION_ACCURACY in alert_types, \
            f"Low detection accuracy ({detection_accuracy*100:.1f}%) must trigger alert (threshold: {PerformanceMonitor.DETECTION_ACCURACY_THRESHOLD*100}%)"
    
    # Property: High memory usage triggers alert
    if memory_percent > PerformanceMonitor.MEMORY_THRESHOLD_PERCENT:
        assert AlertType.HIGH_MEMORY_USAGE in alert_types, \
            f"High memory usage ({memory_percent:.1f}%) must trigger alert (threshold: {PerformanceMonitor.MEMORY_THRESHOLD_PERCENT}%)"
    
    # Property: All alerts must have valid structure
    for alert in alerts:
        assert alert.message, "Alert must have non-empty message"
        assert alert.timestamp >= 0, "Alert timestamp must be non-negative"
        assert alert.severity in ["info", "warning", "critical"], "Alert must have valid severity"


@given(
    fps=st.floats(min_value=25.01, max_value=120.0),  # Strictly above threshold
    latency_ms=st.floats(min_value=0.0, max_value=2000.0),
    detection_accuracy=st.floats(min_value=0.80, max_value=1.0),
    memory_percent=st.floats(min_value=0.0, max_value=90.0)
)
def test_property_31_no_alerts_when_within_thresholds(fps, latency_ms, detection_accuracy, memory_percent):
    """
    Property 31 (Inverse): No alerts when metrics are within thresholds.
    
    For any system state where all metrics are within acceptable thresholds,
    the system SHALL NOT generate alerts.
    """
    monitor = PerformanceMonitor(history_size=100)
    
    # Create resource usage with specified memory
    resource_usage = ResourceUsage(
        cpu_percent=50.0,
        memory_mb=1024.0,
        memory_percent=memory_percent
    )
    
    # Add multiple frames to establish FPS
    base_timestamp = time.time()
    frame_interval = 1.0 / fps
    
    for i in range(30):
        metrics = PerformanceMetrics(
            timestamp=base_timestamp + i * frame_interval,
            fps=fps,
            processing_latency_ms=latency_ms,
            detection_accuracy=detection_accuracy,
            resource_usage=resource_usage
        )
        monitor.update_metrics(metrics)
    
    # Check alerts
    alerts = monitor.check_alerts()
    
    # Property: No alerts should be triggered when all metrics are within thresholds
    assert len(alerts) == 0, \
        f"No alerts should be triggered when metrics are within thresholds. Got: {[a.alert_type for a in alerts]}"


# ============================================================================
# Property 32: Resource Usage Logging
# ============================================================================

@given(st.lists(performance_metrics_strategy(), min_size=1, max_size=50))
def test_property_32_resource_usage_logging(metrics_list):
    """
    Property 32: Resource Usage Logging
    
    For any system operational state, the system SHALL log CPU and memory
    consumption metrics.
    
    Validates: Requirements 16.5
    """
    monitor = PerformanceMonitor(history_size=100)
    
    # Update monitor with metrics
    for metrics in metrics_list:
        monitor.update_metrics(metrics)
    
    # Property: get_resource_usage() must return valid ResourceUsage
    resource_usage = monitor.get_resource_usage()
    assert isinstance(resource_usage, ResourceUsage), "Must return ResourceUsage instance"
    
    # Property: CPU usage must be logged
    assert isinstance(resource_usage.cpu_percent, (int, float)), "CPU usage must be numeric"
    assert 0 <= resource_usage.cpu_percent <= 100, "CPU usage must be in range [0, 100]"
    
    # Property: Memory usage must be logged
    assert isinstance(resource_usage.memory_mb, (int, float)), "Memory usage must be numeric"
    assert resource_usage.memory_mb >= 0, "Memory usage must be non-negative"
    assert isinstance(resource_usage.memory_percent, (int, float)), "Memory percent must be numeric"
    assert 0 <= resource_usage.memory_percent <= 100, "Memory percent must be in range [0, 100]"
    
    # Property: GPU metrics are optional but must be valid if present
    if resource_usage.gpu_percent is not None:
        assert isinstance(resource_usage.gpu_percent, (int, float)), "GPU usage must be numeric"
        assert 0 <= resource_usage.gpu_percent <= 100, "GPU usage must be in range [0, 100]"
    
    if resource_usage.gpu_memory_mb is not None:
        assert isinstance(resource_usage.gpu_memory_mb, (int, float)), "GPU memory must be numeric"
        assert resource_usage.gpu_memory_mb >= 0, "GPU memory must be non-negative"
    
    # Property: Metrics history must contain resource usage data
    history = monitor.get_metrics_history()
    assert len(history) == len(metrics_list), "History must contain all added metrics"
    
    # Property: Display must include resource usage
    display = monitor.display_metrics()
    assert "cpu_percent" in display, "Display must include CPU usage"
    assert "memory_mb" in display, "Display must include memory usage in MB"
    assert "memory_percent" in display, "Display must include memory usage percentage"


@given(st.integers(min_value=1, max_value=100))
@settings(deadline=None)  # Disable deadline - resource monitoring takes time
def test_property_32_resource_usage_always_available(num_updates):
    """
    Property 32 (Availability): Resource usage must always be available.
    
    For any number of metric updates, the system SHALL always be able to
    provide current resource usage information.
    """
    monitor = PerformanceMonitor(history_size=100)
    
    base_timestamp = time.time()
    
    # Add multiple metric updates
    for i in range(num_updates):
        metrics = PerformanceMetrics(
            timestamp=base_timestamp + i * 0.033,  # ~30 FPS
            fps=30.0,
            processing_latency_ms=100.0
        )
        monitor.update_metrics(metrics)
        
        # Property: Resource usage must be available after each update
        resource_usage = monitor.get_resource_usage()
        assert isinstance(resource_usage, ResourceUsage), \
            f"Resource usage must be available after update {i+1}"
        assert resource_usage.cpu_percent >= 0, "CPU usage must be valid"
        assert resource_usage.memory_mb >= 0, "Memory usage must be valid"
