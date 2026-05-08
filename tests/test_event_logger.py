"""
Unit tests for EventLogger.

These tests validate specific functionality of the EventLogger class including
log structure validation, query filtering, and log rotation/retention.
"""

import pytest
import json
import tempfile
import time
from pathlib import Path
from datetime import datetime, timedelta

from umpirai.logging.event_logger import EventLogger, EventFilter, PerformanceMetrics
from umpirai.models.data_models import (
    Decision,
    EventType,
    Trajectory,
    Position3D,
    Vector3D,
    Detection,
    BoundingBox,
    VideoReference,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for logs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def event_logger(temp_log_dir):
    """Create an EventLogger instance with temporary directory."""
    return EventLogger(log_directory=temp_log_dir, retention_days=30)


@pytest.fixture
def sample_decision():
    """Create a sample Decision object for testing."""
    return Decision(
        decision_id="test_decision_001",
        event_type=EventType.WIDE,
        confidence=0.95,
        timestamp=time.time(),
        trajectory=Trajectory(
            positions=[Position3D(x=0.0, y=1.0, z=-10.0), Position3D(x=1.0, y=1.0, z=-5.0)],
            timestamps=[0.0, 0.1],
            velocities=[Vector3D(vx=10.0, vy=0.0, vz=50.0), Vector3D(vx=10.0, vy=0.0, vz=50.0)],
            start_position=Position3D(x=0.0, y=1.0, z=-10.0),
            end_position=Position3D(x=1.0, y=1.0, z=-5.0),
            speed_max=51.0,
            speed_avg=50.5
        ),
        detections=[
            Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100.0, y=200.0, width=50.0, height=50.0),
                confidence=0.92,
                position_3d=Position3D(x=0.5, y=1.0, z=-7.5)
            )
        ],
        reasoning="Ball crossed wide guideline",
        video_references=[
            VideoReference(camera_id="cam1", frame_number=1234, timestamp=time.time())
        ],
        requires_review=False
    )


@pytest.fixture
def sample_performance_metrics():
    """Create sample PerformanceMetrics for testing."""
    return PerformanceMetrics(
        timestamp=time.time(),
        fps=30.5,
        processing_latency_ms=45.2,
        cpu_usage_percent=65.3,
        memory_usage_mb=2048.5,
        gpu_usage_percent=78.9
    )


# ============================================================================
# Test Log Structure Validation
# ============================================================================

def test_log_event_with_valid_structure(event_logger):
    """Test logging an event with valid structure."""
    event = {
        "event_id": "test_001",
        "timestamp": time.time(),
        "event_type": "wide",
        "confidence": 0.95,
        "additional_field": "test_value"
    }
    
    # Should not raise any exception
    event_logger.log_event(event)
    
    # Verify event was logged
    all_events = event_logger.query_events(EventFilter())
    assert len(all_events) == 1
    assert all_events[0]["event_id"] == "test_001"


def test_log_event_missing_required_field(event_logger):
    """Test that logging an event without required fields raises ValueError."""
    # Missing event_id
    event = {
        "timestamp": time.time(),
        "event_type": "wide"
    }
    
    with pytest.raises(ValueError, match="Event missing required field: event_id"):
        event_logger.log_event(event)


def test_log_event_missing_timestamp(event_logger):
    """Test that logging an event without timestamp raises ValueError."""
    event = {
        "event_id": "test_001",
        "event_type": "wide"
    }
    
    with pytest.raises(ValueError, match="Event missing required field: timestamp"):
        event_logger.log_event(event)


def test_log_event_missing_event_type(event_logger):
    """Test that logging an event without event_type raises ValueError."""
    event = {
        "event_id": "test_001",
        "timestamp": time.time()
    }
    
    with pytest.raises(ValueError, match="Event missing required field: event_type"):
        event_logger.log_event(event)


def test_log_decision_structure(event_logger, sample_decision):
    """Test that log_decision creates properly structured log entries."""
    event_logger.log_decision(sample_decision)
    
    # Query the logged decision
    all_events = event_logger.query_events(EventFilter())
    assert len(all_events) == 1
    
    logged_event = all_events[0]
    
    # Verify structure
    assert logged_event["event_id"] == sample_decision.decision_id
    assert logged_event["event_type"] == sample_decision.event_type.value
    assert logged_event["confidence"] == sample_decision.confidence
    assert logged_event["timestamp"] == sample_decision.timestamp
    assert "timestamp_iso" in logged_event
    assert logged_event["reasoning"] == sample_decision.reasoning
    assert logged_event["requires_review"] == sample_decision.requires_review
    
    # Verify trajectory structure
    assert "trajectory" in logged_event
    trajectory = logged_event["trajectory"]
    assert "start_position" in trajectory
    assert "end_position" in trajectory
    assert "speed_max" in trajectory
    assert "speed_avg" in trajectory
    assert "duration" in trajectory
    assert "length" in trajectory
    
    # Verify detections structure
    assert "detections" in logged_event
    assert len(logged_event["detections"]) == len(sample_decision.detections)
    
    # Verify video references structure
    assert "video_references" in logged_event
    assert len(logged_event["video_references"]) == len(sample_decision.video_references)


def test_log_performance_structure(event_logger, sample_performance_metrics):
    """Test that log_performance creates properly structured log entries."""
    event_logger.log_performance(sample_performance_metrics)
    
    # Read performance log directly
    performance_log_path = Path(event_logger.log_directory) / "performance.jsonl"
    assert performance_log_path.exists()
    
    with open(performance_log_path, 'r') as f:
        lines = f.readlines()
        assert len(lines) == 1
        
        logged_metrics = json.loads(lines[0])
        
        # Verify structure
        assert logged_metrics["timestamp"] == sample_performance_metrics.timestamp
        assert "timestamp_iso" in logged_metrics
        assert logged_metrics["fps"] == sample_performance_metrics.fps
        assert logged_metrics["processing_latency_ms"] == sample_performance_metrics.processing_latency_ms
        assert logged_metrics["cpu_usage_percent"] == sample_performance_metrics.cpu_usage_percent
        assert logged_metrics["memory_usage_mb"] == sample_performance_metrics.memory_usage_mb
        assert logged_metrics["gpu_usage_percent"] == sample_performance_metrics.gpu_usage_percent


# ============================================================================
# Test Query Filtering
# ============================================================================

def test_query_events_no_filter(event_logger, sample_decision):
    """Test querying all events without filters."""
    # Log multiple events
    for i in range(5):
        decision = Decision(
            decision_id=f"test_{i}",
            event_type=EventType.WIDE,
            confidence=0.9,
            timestamp=time.time() + i,
            trajectory=sample_decision.trajectory,
            detections=sample_decision.detections,
            reasoning="Test",
            video_references=sample_decision.video_references
        )
        event_logger.log_decision(decision)
    
    # Query all events
    all_events = event_logger.query_events(EventFilter())
    assert len(all_events) == 5


def test_query_events_by_event_type(event_logger, sample_decision):
    """Test filtering events by event type."""
    # Log events of different types
    event_types = [EventType.WIDE, EventType.NO_BALL, EventType.WIDE, EventType.LEGAL, EventType.WIDE]
    
    for i, event_type in enumerate(event_types):
        decision = Decision(
            decision_id=f"test_{i}",
            event_type=event_type,
            confidence=0.9,
            timestamp=time.time() + i,
            trajectory=sample_decision.trajectory,
            detections=sample_decision.detections,
            reasoning="Test",
            video_references=sample_decision.video_references
        )
        event_logger.log_decision(decision)
    
    # Query only WIDE events
    wide_events = event_logger.query_events(EventFilter(event_types=[EventType.WIDE]))
    assert len(wide_events) == 3
    assert all(e["event_type"] == EventType.WIDE.value for e in wide_events)


def test_query_events_by_confidence_range(event_logger, sample_decision):
    """Test filtering events by confidence range."""
    # Log events with different confidence levels
    confidences = [0.5, 0.7, 0.85, 0.92, 0.98]
    
    for i, confidence in enumerate(confidences):
        decision = Decision(
            decision_id=f"test_{i}",
            event_type=EventType.WIDE,
            confidence=confidence,
            timestamp=time.time() + i,
            trajectory=sample_decision.trajectory,
            detections=sample_decision.detections,
            reasoning="Test",
            video_references=sample_decision.video_references
        )
        event_logger.log_decision(decision)
    
    # Query events with confidence >= 0.8
    high_confidence_events = event_logger.query_events(
        EventFilter(min_confidence=0.8)
    )
    assert len(high_confidence_events) == 3
    assert all(e["confidence"] >= 0.8 for e in high_confidence_events)
    
    # Query events with confidence < 0.8
    low_confidence_events = event_logger.query_events(
        EventFilter(max_confidence=0.8)
    )
    assert len(low_confidence_events) == 2
    assert all(e["confidence"] <= 0.8 for e in low_confidence_events)


def test_query_events_by_timestamp_range(event_logger, sample_decision):
    """Test filtering events by timestamp range."""
    base_time = time.time()
    
    # Log events at different times
    for i in range(5):
        decision = Decision(
            decision_id=f"test_{i}",
            event_type=EventType.WIDE,
            confidence=0.9,
            timestamp=base_time + i * 10,
            trajectory=sample_decision.trajectory,
            detections=sample_decision.detections,
            reasoning="Test",
            video_references=sample_decision.video_references
        )
        event_logger.log_decision(decision)
    
    # Query events in middle time range
    filtered_events = event_logger.query_events(
        EventFilter(
            start_timestamp=base_time + 10,
            end_timestamp=base_time + 30
        )
    )
    assert len(filtered_events) == 3


def test_query_events_by_requires_review(event_logger, sample_decision):
    """Test filtering events by review requirement."""
    # Log events with different confidence levels (affects requires_review)
    confidences = [0.95, 0.75, 0.85, 0.65, 0.90]  # <0.8 requires review
    
    for i, confidence in enumerate(confidences):
        decision = Decision(
            decision_id=f"test_{i}",
            event_type=EventType.WIDE,
            confidence=confidence,
            timestamp=time.time() + i,
            trajectory=sample_decision.trajectory,
            detections=sample_decision.detections,
            reasoning="Test",
            video_references=sample_decision.video_references
        )
        event_logger.log_decision(decision)
    
    # Query events requiring review
    review_events = event_logger.query_events(
        EventFilter(requires_review=True)
    )
    assert len(review_events) == 2  # 0.75 and 0.65
    assert all(e["requires_review"] for e in review_events)


def test_query_events_combined_filters(event_logger, sample_decision):
    """Test combining multiple filters."""
    base_time = time.time()
    
    # Log diverse events
    test_cases = [
        (EventType.WIDE, 0.95, base_time),
        (EventType.NO_BALL, 0.85, base_time + 10),
        (EventType.WIDE, 0.75, base_time + 20),
        (EventType.LEGAL, 0.90, base_time + 30),
        (EventType.WIDE, 0.88, base_time + 40),
    ]
    
    for i, (event_type, confidence, timestamp) in enumerate(test_cases):
        decision = Decision(
            decision_id=f"test_{i}",
            event_type=event_type,
            confidence=confidence,
            timestamp=timestamp,
            trajectory=sample_decision.trajectory,
            detections=sample_decision.detections,
            reasoning="Test",
            video_references=sample_decision.video_references
        )
        event_logger.log_decision(decision)
    
    # Query WIDE events with confidence >= 0.85 in time range
    filtered_events = event_logger.query_events(
        EventFilter(
            event_types=[EventType.WIDE],
            min_confidence=0.85,
            start_timestamp=base_time,
            end_timestamp=base_time + 50
        )
    )
    assert len(filtered_events) == 2  # WIDE with 0.95 and 0.88


# ============================================================================
# Test Log Rotation and Retention
# ============================================================================

def test_cleanup_old_logs(event_logger, sample_decision):
    """Test that old logs are removed based on retention period."""
    current_time = time.time()
    
    # Log events at different times
    # Old events (35 days ago - should be removed)
    old_time = current_time - (35 * 24 * 60 * 60)
    for i in range(3):
        decision = Decision(
            decision_id=f"old_{i}",
            event_type=EventType.WIDE,
            confidence=0.9,
            timestamp=old_time + i,
            trajectory=sample_decision.trajectory,
            detections=sample_decision.detections,
            reasoning="Old event",
            video_references=sample_decision.video_references
        )
        event_logger.log_decision(decision)
    
    # Recent events (10 days ago - should be kept)
    recent_time = current_time - (10 * 24 * 60 * 60)
    for i in range(2):
        decision = Decision(
            decision_id=f"recent_{i}",
            event_type=EventType.WIDE,
            confidence=0.9,
            timestamp=recent_time + i,
            trajectory=sample_decision.trajectory,
            detections=sample_decision.detections,
            reasoning="Recent event",
            video_references=sample_decision.video_references
        )
        event_logger.log_decision(decision)
    
    # Verify all events are present before cleanup
    all_events = event_logger.query_events(EventFilter())
    assert len(all_events) == 5
    
    # Run cleanup
    # Note: log_decision writes to both events.jsonl and decisions.jsonl,
    # so removed_count will be 6 (3 old events × 2 log files)
    removed_count = event_logger.cleanup_old_logs()
    assert removed_count == 6
    
    # Verify only recent events remain
    remaining_events = event_logger.query_events(EventFilter())
    assert len(remaining_events) == 2
    assert all("recent" in e["event_id"] for e in remaining_events)


def test_cleanup_preserves_recent_logs(event_logger, sample_decision):
    """Test that cleanup preserves logs within retention period."""
    current_time = time.time()
    
    # Log only recent events
    for i in range(5):
        decision = Decision(
            decision_id=f"test_{i}",
            event_type=EventType.WIDE,
            confidence=0.9,
            timestamp=current_time + i,
            trajectory=sample_decision.trajectory,
            detections=sample_decision.detections,
            reasoning="Test",
            video_references=sample_decision.video_references
        )
        event_logger.log_decision(decision)
    
    # Run cleanup
    removed_count = event_logger.cleanup_old_logs()
    assert removed_count == 0
    
    # Verify all events remain
    all_events = event_logger.query_events(EventFilter())
    assert len(all_events) == 5


# ============================================================================
# Test Export Functionality
# ============================================================================

def test_export_logs_events(event_logger, sample_decision, temp_log_dir):
    """Test exporting event logs."""
    # Log some events
    for i in range(3):
        decision = Decision(
            decision_id=f"test_{i}",
            event_type=EventType.WIDE,
            confidence=0.9,
            timestamp=time.time() + i,
            trajectory=sample_decision.trajectory,
            detections=sample_decision.detections,
            reasoning="Test",
            video_references=sample_decision.video_references
        )
        event_logger.log_decision(decision)
    
    # Export logs
    export_path = Path(temp_log_dir) / "exported_events.jsonl"
    result_path = event_logger.export_logs(str(export_path), log_type="events")
    
    assert Path(result_path).exists()
    
    # Verify exported content
    with open(result_path, 'r') as f:
        lines = f.readlines()
        assert len(lines) == 3


def test_export_logs_invalid_type(event_logger):
    """Test that exporting with invalid log type raises ValueError."""
    with pytest.raises(ValueError, match="Invalid log_type"):
        event_logger.export_logs("output.jsonl", log_type="invalid")


def test_export_logs_nonexistent_file(event_logger):
    """Test that exporting nonexistent log file raises FileNotFoundError."""
    # Don't log anything, so performance log doesn't exist
    with pytest.raises(FileNotFoundError):
        event_logger.export_logs("output.jsonl", log_type="performance")


# ============================================================================
# Test Statistics
# ============================================================================

def test_get_log_statistics(event_logger, sample_decision):
    """Test retrieving log statistics."""
    # Log diverse events
    event_types = [EventType.WIDE, EventType.NO_BALL, EventType.WIDE, EventType.LEGAL]
    confidences = [0.95, 0.75, 0.88, 0.92]
    
    for i, (event_type, confidence) in enumerate(zip(event_types, confidences)):
        decision = Decision(
            decision_id=f"test_{i}",
            event_type=event_type,
            confidence=confidence,
            timestamp=time.time() + i,
            trajectory=sample_decision.trajectory,
            detections=sample_decision.detections,
            reasoning="Test",
            video_references=sample_decision.video_references
        )
        event_logger.log_decision(decision)
    
    # Get statistics
    stats = event_logger.get_log_statistics()
    
    assert stats["total_events"] == 4
    assert stats["event_type_counts"]["wide"] == 2
    assert stats["event_type_counts"]["no_ball"] == 1
    assert stats["event_type_counts"]["legal"] == 1
    assert stats["events_requiring_review"] == 1  # 0.75 confidence
    assert 0.8 < stats["average_confidence"] < 0.9
    assert stats["retention_days"] == 30


def test_get_log_statistics_empty(event_logger):
    """Test statistics with no logged events."""
    stats = event_logger.get_log_statistics()
    
    assert stats["total_events"] == 0
    assert stats["event_type_counts"] == {}
    assert stats["events_requiring_review"] == 0
    assert stats["average_confidence"] == 0.0
