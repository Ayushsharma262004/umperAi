"""
Performance monitoring for the UmpirAI system.

This module provides real-time performance monitoring including FPS tracking,
processing latency measurement, resource usage monitoring, and alert generation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import time
import psutil
from collections import deque


class AlertType(Enum):
    """Types of performance alerts."""
    LOW_FPS = "low_fps"
    HIGH_LATENCY = "high_latency"
    LOW_DETECTION_ACCURACY = "low_detection_accuracy"
    HIGH_MEMORY_USAGE = "high_memory_usage"


@dataclass
class Alert:
    """Performance alert."""
    alert_type: AlertType
    message: str
    timestamp: float
    severity: str = "warning"  # "info", "warning", "critical"
    
    def __post_init__(self):
        """Validate alert data."""
        if not isinstance(self.alert_type, AlertType):
            raise TypeError("alert_type must be an AlertType enum")
        if not isinstance(self.message, str) or not self.message:
            raise ValueError("message must be a non-empty string")
        if not isinstance(self.timestamp, (int, float)) or self.timestamp < 0:
            raise ValueError("timestamp must be a non-negative number")
        if self.severity not in ["info", "warning", "critical"]:
            raise ValueError("severity must be 'info', 'warning', or 'critical'")


@dataclass
class ResourceUsage:
    """System resource usage metrics."""
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    gpu_percent: Optional[float] = None
    gpu_memory_mb: Optional[float] = None
    
    def __post_init__(self):
        """Validate resource usage data."""
        if not isinstance(self.cpu_percent, (int, float)) or not (0 <= self.cpu_percent <= 100):
            raise ValueError("cpu_percent must be in range [0, 100]")
        if not isinstance(self.memory_mb, (int, float)) or self.memory_mb < 0:
            raise ValueError("memory_mb must be non-negative")
        if not isinstance(self.memory_percent, (int, float)) or not (0 <= self.memory_percent <= 100):
            raise ValueError("memory_percent must be in range [0, 100]")
        if self.gpu_percent is not None:
            if not isinstance(self.gpu_percent, (int, float)) or not (0 <= self.gpu_percent <= 100):
                raise ValueError("gpu_percent must be in range [0, 100] or None")
        if self.gpu_memory_mb is not None:
            if not isinstance(self.gpu_memory_mb, (int, float)) or self.gpu_memory_mb < 0:
                raise ValueError("gpu_memory_mb must be non-negative or None")


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot."""
    timestamp: float
    fps: float
    processing_latency_ms: float
    detection_accuracy: Optional[float] = None
    resource_usage: Optional[ResourceUsage] = None
    
    def __post_init__(self):
        """Validate performance metrics."""
        if not isinstance(self.timestamp, (int, float)) or self.timestamp < 0:
            raise ValueError("timestamp must be a non-negative number")
        if not isinstance(self.fps, (int, float)) or self.fps < 0:
            raise ValueError("fps must be non-negative")
        if not isinstance(self.processing_latency_ms, (int, float)) or self.processing_latency_ms < 0:
            raise ValueError("processing_latency_ms must be non-negative")
        if self.detection_accuracy is not None:
            if not isinstance(self.detection_accuracy, (int, float)) or not (0 <= self.detection_accuracy <= 1):
                raise ValueError("detection_accuracy must be in range [0, 1] or None")
        if self.resource_usage is not None and not isinstance(self.resource_usage, ResourceUsage):
            raise TypeError("resource_usage must be a ResourceUsage instance or None")


class PerformanceMonitor:
    """
    Monitor system performance and generate alerts.
    
    Tracks FPS, processing latency, resource usage, and detection accuracy.
    Generates alerts when metrics exceed defined thresholds.
    """
    
    # Alert thresholds
    FPS_THRESHOLD = 25.0
    LATENCY_THRESHOLD_MS = 2000.0
    DETECTION_ACCURACY_THRESHOLD = 0.80
    MEMORY_THRESHOLD_PERCENT = 90.0
    
    def __init__(self, history_size: int = 100):
        """
        Initialize the performance monitor.
        
        Args:
            history_size: Number of metric samples to keep in history
        """
        if not isinstance(history_size, int) or history_size <= 0:
            raise ValueError("history_size must be a positive integer")
        
        self._history_size = history_size
        self._metrics_history: deque = deque(maxlen=history_size)
        self._active_alerts: List[Alert] = []
        self._process = psutil.Process()
        self._last_update_time = time.time()
        self._frame_count = 0
        self._frame_timestamps: deque = deque(maxlen=30)  # Track last 30 frames for FPS
        
        # GPU monitoring (optional)
        self._gpu_available = False
        try:
            import pynvml
            pynvml.nvmlInit()
            self._gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self._gpu_available = True
            self._pynvml = pynvml
        except (ImportError, Exception):
            # GPU monitoring not available
            pass
    
    def update_metrics(self, metrics: PerformanceMetrics) -> None:
        """
        Update performance metrics.
        
        Args:
            metrics: New performance metrics snapshot
        """
        if not isinstance(metrics, PerformanceMetrics):
            raise TypeError("metrics must be a PerformanceMetrics instance")
        
        # Add to history
        self._metrics_history.append(metrics)
        
        # Update frame tracking
        self._frame_count += 1
        self._frame_timestamps.append(metrics.timestamp)
        self._last_update_time = metrics.timestamp
        
        # Check for alert conditions
        self._check_alert_conditions(metrics)
    
    def get_current_fps(self) -> float:
        """
        Get current frames per second.
        
        Returns:
            Current FPS based on recent frame timestamps
        """
        if len(self._frame_timestamps) < 2:
            return 0.0
        
        # Calculate FPS from frame timestamps
        time_span = self._frame_timestamps[-1] - self._frame_timestamps[0]
        if time_span <= 0:
            return 0.0
        
        fps = (len(self._frame_timestamps) - 1) / time_span
        return float(fps)
    
    def get_processing_latency(self) -> float:
        """
        Get current processing latency in milliseconds.
        
        Returns:
            Most recent processing latency, or 0.0 if no metrics available
        """
        if not self._metrics_history:
            return 0.0
        
        return float(self._metrics_history[-1].processing_latency_ms)
    
    def get_resource_usage(self) -> ResourceUsage:
        """
        Get current system resource usage.
        
        Returns:
            Current CPU, memory, and GPU usage
        """
        # Get CPU and memory usage
        cpu_percent = self._process.cpu_percent(interval=0.1)
        memory_info = self._process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)  # Convert bytes to MB
        memory_percent = self._process.memory_percent()
        
        # Get GPU usage if available
        gpu_percent = None
        gpu_memory_mb = None
        if self._gpu_available:
            try:
                gpu_util = self._pynvml.nvmlDeviceGetUtilizationRates(self._gpu_handle)
                gpu_percent = float(gpu_util.gpu)
                
                gpu_mem_info = self._pynvml.nvmlDeviceGetMemoryInfo(self._gpu_handle)
                gpu_memory_mb = gpu_mem_info.used / (1024 * 1024)  # Convert bytes to MB
            except Exception:
                # GPU monitoring failed, continue without it
                pass
        
        return ResourceUsage(
            cpu_percent=float(cpu_percent),
            memory_mb=float(memory_mb),
            memory_percent=float(memory_percent),
            gpu_percent=gpu_percent,
            gpu_memory_mb=gpu_memory_mb
        )
    
    def check_alerts(self) -> List[Alert]:
        """
        Get list of active performance alerts.
        
        Returns:
            List of currently active alerts
        """
        return self._active_alerts.copy()
    
    def display_metrics(self) -> Dict[str, any]:
        """
        Get current metrics for display.
        
        Returns:
            Dictionary containing current performance metrics
        """
        fps = self.get_current_fps()
        latency = self.get_processing_latency()
        resource_usage = self.get_resource_usage()
        
        metrics_display = {
            "fps": fps,
            "processing_latency_ms": latency,
            "cpu_percent": resource_usage.cpu_percent,
            "memory_mb": resource_usage.memory_mb,
            "memory_percent": resource_usage.memory_percent,
            "frame_count": self._frame_count,
            "alerts": len(self._active_alerts)
        }
        
        if resource_usage.gpu_percent is not None:
            metrics_display["gpu_percent"] = resource_usage.gpu_percent
            metrics_display["gpu_memory_mb"] = resource_usage.gpu_memory_mb
        
        return metrics_display
    
    def _check_alert_conditions(self, metrics: PerformanceMetrics) -> None:
        """
        Check if any alert conditions are met and update active alerts.
        
        Args:
            metrics: Current performance metrics
        """
        # Clear previous alerts
        self._active_alerts.clear()
        
        # Check FPS threshold
        current_fps = self.get_current_fps()
        if current_fps > 0 and current_fps < self.FPS_THRESHOLD:
            self._active_alerts.append(Alert(
                alert_type=AlertType.LOW_FPS,
                message=f"Frame rate degraded: {current_fps:.1f} FPS (threshold: {self.FPS_THRESHOLD} FPS)",
                timestamp=metrics.timestamp,
                severity="warning"
            ))
        
        # Check latency threshold
        if metrics.processing_latency_ms > self.LATENCY_THRESHOLD_MS:
            self._active_alerts.append(Alert(
                alert_type=AlertType.HIGH_LATENCY,
                message=f"Processing latency exceeded: {metrics.processing_latency_ms:.0f} ms (threshold: {self.LATENCY_THRESHOLD_MS:.0f} ms)",
                timestamp=metrics.timestamp,
                severity="warning"
            ))
        
        # Check detection accuracy threshold
        if metrics.detection_accuracy is not None and metrics.detection_accuracy < self.DETECTION_ACCURACY_THRESHOLD:
            self._active_alerts.append(Alert(
                alert_type=AlertType.LOW_DETECTION_ACCURACY,
                message=f"Detection quality degraded: {metrics.detection_accuracy*100:.1f}% (threshold: {self.DETECTION_ACCURACY_THRESHOLD*100:.0f}%)",
                timestamp=metrics.timestamp,
                severity="warning"
            ))
        
        # Check memory threshold
        if metrics.resource_usage is not None:
            if metrics.resource_usage.memory_percent > self.MEMORY_THRESHOLD_PERCENT:
                self._active_alerts.append(Alert(
                    alert_type=AlertType.HIGH_MEMORY_USAGE,
                    message=f"Memory pressure high: {metrics.resource_usage.memory_percent:.1f}% (threshold: {self.MEMORY_THRESHOLD_PERCENT:.0f}%)",
                    timestamp=metrics.timestamp,
                    severity="critical"
                ))
    
    def get_metrics_history(self) -> List[PerformanceMetrics]:
        """
        Get historical performance metrics.
        
        Returns:
            List of historical metrics (up to history_size)
        """
        return list(self._metrics_history)
    
    def reset(self) -> None:
        """Reset all metrics and alerts."""
        self._metrics_history.clear()
        self._active_alerts.clear()
        self._frame_count = 0
        self._frame_timestamps.clear()
        self._last_update_time = time.time()
