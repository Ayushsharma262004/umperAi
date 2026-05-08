"""
Event Logger Module

This module provides event logging functionality for the UmpirAI system,
including structured JSON logging, querying, and retention management.
"""

import json
import os
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

from umpirai.models.data_models import (
    Decision,
    Detection,
    EventType,
    Position3D,
    VideoReference,
)


class EventFilter:
    """Filter criteria for querying events."""
    
    def __init__(
        self,
        event_types: Optional[List[EventType]] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        start_timestamp: Optional[float] = None,
        end_timestamp: Optional[float] = None,
        requires_review: Optional[bool] = None,
    ):
        """
        Initialize event filter.
        
        Args:
            event_types: List of event types to include
            min_confidence: Minimum confidence threshold
            max_confidence: Maximum confidence threshold
            start_timestamp: Start of time range
            end_timestamp: End of time range
            requires_review: Filter by review requirement
        """
        self.event_types = event_types
        self.min_confidence = min_confidence
        self.max_confidence = max_confidence
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        self.requires_review = requires_review


class PerformanceMetrics:
    """System performance metrics."""
    
    def __init__(
        self,
        timestamp: float,
        fps: float,
        processing_latency_ms: float,
        cpu_usage_percent: float,
        memory_usage_mb: float,
        gpu_usage_percent: Optional[float] = None,
    ):
        """
        Initialize performance metrics.
        
        Args:
            timestamp: Metric collection timestamp
            fps: Current frames per second
            processing_latency_ms: Processing latency in milliseconds
            cpu_usage_percent: CPU usage percentage
            memory_usage_mb: Memory usage in megabytes
            gpu_usage_percent: GPU usage percentage (if available)
        """
        self.timestamp = timestamp
        self.fps = fps
        self.processing_latency_ms = processing_latency_ms
        self.cpu_usage_percent = cpu_usage_percent
        self.memory_usage_mb = memory_usage_mb
        self.gpu_usage_percent = gpu_usage_percent


class EventLogger:
    """
    Event logger for UmpirAI system.
    
    Logs match events, decisions, and performance metrics in structured JSON format
    with support for querying, filtering, and automatic retention management.
    """
    
    def __init__(self, log_directory: str = "logs", retention_days: int = 30):
        """
        Initialize event logger.
        
        Args:
            log_directory: Directory for storing log files
            retention_days: Number of days to retain logs (default: 30)
        """
        self.log_directory = Path(log_directory)
        self.retention_days = retention_days
        
        # Create log directory if it doesn't exist
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Log file paths
        self.events_log_path = self.log_directory / "events.jsonl"
        self.decisions_log_path = self.log_directory / "decisions.jsonl"
        self.performance_log_path = self.log_directory / "performance.jsonl"
        
        # In-memory index for fast querying
        self._event_index: Dict[str, List[Dict[str, Any]]] = {
            "by_timestamp": [],
            "by_event_type": {},
            "by_confidence": [],
        }
        
        # Load existing logs into index
        self._load_index()
    
    def _load_index(self) -> None:
        """Load existing logs into in-memory index."""
        if self.events_log_path.exists():
            with open(self.events_log_path, 'r') as f:
                for line in f:
                    if line.strip():
                        event = json.loads(line)
                        self._index_event(event)
    
    def _index_event(self, event: Dict[str, Any]) -> None:
        """
        Add event to in-memory index.
        
        Args:
            event: Event dictionary to index
        """
        # Index by timestamp
        self._event_index["by_timestamp"].append(event)
        
        # Index by event type
        event_type = event.get("event_type")
        if event_type:
            if event_type not in self._event_index["by_event_type"]:
                self._event_index["by_event_type"][event_type] = []
            self._event_index["by_event_type"][event_type].append(event)
        
        # Index by confidence (sorted)
        confidence = event.get("confidence")
        if confidence is not None:
            self._event_index["by_confidence"].append(event)
            # Keep confidence index sorted
            self._event_index["by_confidence"].sort(key=lambda e: e.get("confidence", 0))
    
    def log_event(self, event: Dict[str, Any]) -> None:
        """
        Log a match event with structured JSON format.
        
        Args:
            event: Event dictionary containing event data
            
        The event dictionary should contain:
            - event_id: Unique identifier
            - timestamp: Event timestamp
            - event_type: Type of event (WIDE, NO_BALL, etc.)
            - confidence: Confidence score
            - Additional event-specific fields
        """
        # Validate required fields
        required_fields = ["event_id", "timestamp", "event_type"]
        for field in required_fields:
            if field not in event:
                raise ValueError(f"Event missing required field: {field}")
        
        # Add ISO8601 timestamp for human readability
        event["timestamp_iso"] = datetime.fromtimestamp(event["timestamp"]).isoformat()
        
        # Write to log file (JSON Lines format)
        with open(self.events_log_path, 'a') as f:
            f.write(json.dumps(event) + '\n')
        
        # Update index
        self._index_event(event)
    
    def log_decision(self, decision: Decision, video_ref: Optional[VideoReference] = None) -> None:
        """
        Log an umpiring decision with video frame references.
        
        Args:
            decision: Decision object to log
            video_ref: Optional additional video reference
        """
        # Convert decision to dictionary
        decision_dict = {
            "event_id": decision.decision_id,
            "timestamp": decision.timestamp,
            "timestamp_iso": datetime.fromtimestamp(decision.timestamp).isoformat(),
            "event_type": decision.event_type.value,
            "confidence": decision.confidence,
            "requires_review": decision.requires_review,
            "reasoning": decision.reasoning,
            "video_references": [
                {
                    "camera_id": vr.camera_id,
                    "frame_number": vr.frame_number,
                    "timestamp": vr.timestamp,
                }
                for vr in decision.video_references
            ],
            "trajectory": {
                "start_position": {
                    "x": decision.trajectory.start_position.x,
                    "y": decision.trajectory.start_position.y,
                    "z": decision.trajectory.start_position.z,
                },
                "end_position": {
                    "x": decision.trajectory.end_position.x if decision.trajectory.end_position else None,
                    "y": decision.trajectory.end_position.y if decision.trajectory.end_position else None,
                    "z": decision.trajectory.end_position.z if decision.trajectory.end_position else None,
                } if decision.trajectory.end_position else None,
                "speed_max": decision.trajectory.speed_max,
                "speed_avg": decision.trajectory.speed_avg,
                "duration": decision.trajectory.duration(),
                "length": decision.trajectory.length(),
            },
            "detections": [
                {
                    "class_id": d.class_id,
                    "class_name": d.class_name,
                    "confidence": d.confidence,
                    "bounding_box": {
                        "x": d.bounding_box.x,
                        "y": d.bounding_box.y,
                        "width": d.bounding_box.width,
                        "height": d.bounding_box.height,
                    },
                    "position_3d": {
                        "x": d.position_3d.x,
                        "y": d.position_3d.y,
                        "z": d.position_3d.z,
                    } if d.position_3d else None,
                }
                for d in decision.detections
            ],
        }
        
        # Add additional video reference if provided
        if video_ref:
            decision_dict["video_references"].append({
                "camera_id": video_ref.camera_id,
                "frame_number": video_ref.frame_number,
                "timestamp": video_ref.timestamp,
            })
        
        # Write to decisions log
        with open(self.decisions_log_path, 'a') as f:
            f.write(json.dumps(decision_dict) + '\n')
        
        # Also log as event
        self.log_event(decision_dict)
    
    def log_performance(self, metrics: PerformanceMetrics) -> None:
        """
        Log system performance metrics.
        
        Args:
            metrics: Performance metrics to log
        """
        metrics_dict = {
            "timestamp": metrics.timestamp,
            "timestamp_iso": datetime.fromtimestamp(metrics.timestamp).isoformat(),
            "fps": metrics.fps,
            "processing_latency_ms": metrics.processing_latency_ms,
            "cpu_usage_percent": metrics.cpu_usage_percent,
            "memory_usage_mb": metrics.memory_usage_mb,
            "gpu_usage_percent": metrics.gpu_usage_percent,
        }
        
        # Write to performance log
        with open(self.performance_log_path, 'a') as f:
            f.write(json.dumps(metrics_dict) + '\n')
    
    def export_logs(self, output_path: str, log_type: str = "events") -> str:
        """
        Export logs to a file in JSON Lines format.
        
        Args:
            output_path: Path for exported log file
            log_type: Type of logs to export ("events", "decisions", "performance")
            
        Returns:
            Path to exported file
        """
        # Determine source log file
        if log_type == "events":
            source_path = self.events_log_path
        elif log_type == "decisions":
            source_path = self.decisions_log_path
        elif log_type == "performance":
            source_path = self.performance_log_path
        else:
            raise ValueError(f"Invalid log_type: {log_type}")
        
        # Check if source exists
        if not source_path.exists():
            raise FileNotFoundError(f"Log file not found: {source_path}")
        
        # Copy to output path
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(source_path, 'r') as src, open(output_file, 'w') as dst:
            dst.write(src.read())
        
        return str(output_file)
    
    def query_events(self, filter: EventFilter) -> List[Dict[str, Any]]:
        """
        Query events with filtering capabilities.
        
        Args:
            filter: EventFilter specifying query criteria
            
        Returns:
            List of events matching the filter criteria
        """
        results = []
        
        # Start with all events
        candidates = self._event_index["by_timestamp"]
        
        # Apply filters
        for event in candidates:
            # Filter by event type
            if filter.event_types is not None:
                event_type_str = event.get("event_type")
                if event_type_str not in [et.value for et in filter.event_types]:
                    continue
            
            # Filter by confidence range
            confidence = event.get("confidence")
            if confidence is not None:
                if filter.min_confidence is not None and confidence < filter.min_confidence:
                    continue
                if filter.max_confidence is not None and confidence > filter.max_confidence:
                    continue
            
            # Filter by timestamp range
            timestamp = event.get("timestamp")
            if timestamp is not None:
                if filter.start_timestamp is not None and timestamp < filter.start_timestamp:
                    continue
                if filter.end_timestamp is not None and timestamp > filter.end_timestamp:
                    continue
            
            # Filter by review requirement
            if filter.requires_review is not None:
                requires_review = event.get("requires_review", False)
                if requires_review != filter.requires_review:
                    continue
            
            results.append(event)
        
        return results
    
    def cleanup_old_logs(self) -> int:
        """
        Remove logs older than retention period.
        
        Returns:
            Number of log entries removed
        """
        cutoff_timestamp = (datetime.now() - timedelta(days=self.retention_days)).timestamp()
        removed_count = 0
        
        # Process each log file
        for log_path in [self.events_log_path, self.decisions_log_path, self.performance_log_path]:
            if not log_path.exists():
                continue
            
            # Read all logs
            retained_logs = []
            with open(log_path, 'r') as f:
                for line in f:
                    if line.strip():
                        log_entry = json.loads(line)
                        timestamp = log_entry.get("timestamp", 0)
                        
                        if timestamp >= cutoff_timestamp:
                            retained_logs.append(line)
                        else:
                            removed_count += 1
            
            # Rewrite log file with retained entries
            with open(log_path, 'w') as f:
                f.writelines(retained_logs)
        
        # Rebuild index
        self._event_index = {
            "by_timestamp": [],
            "by_event_type": {},
            "by_confidence": [],
        }
        self._load_index()
        
        return removed_count
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about logged events.
        
        Returns:
            Dictionary containing log statistics
        """
        total_events = len(self._event_index["by_timestamp"])
        
        # Count by event type
        event_type_counts = {
            event_type: len(events)
            for event_type, events in self._event_index["by_event_type"].items()
        }
        
        # Count events requiring review
        review_count = sum(
            1 for event in self._event_index["by_timestamp"]
            if event.get("requires_review", False)
        )
        
        # Calculate average confidence
        confidences = [
            event.get("confidence", 0)
            for event in self._event_index["by_timestamp"]
            if "confidence" in event
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            "total_events": total_events,
            "event_type_counts": event_type_counts,
            "events_requiring_review": review_count,
            "average_confidence": avg_confidence,
            "log_directory": str(self.log_directory),
            "retention_days": self.retention_days,
        }
