"""
Property-based tests for EventLogger.

These tests validate the correctness properties related to event logging
completeness and data integrity.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
import numpy as np
import time
import tempfile
import shutil
from pathlib import Path

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
# Hypothesis Strategies
# ============================================================================

@st.composite
def position_3d_strategy(draw):
    """Generate random 3D positions."""
    return Position3D(
        x=draw(st.floats(min_value=-10.0, max_value=10.0)),
        y=draw(st.floats(min_value=0.0, max_value=5.0)),
        z=draw(st.floats(min_value=-20.0, max_value=20.0))
    )


@st.composite
def vector_3d_strategy(draw):
    """Generate random 3D vectors."""
    return Vector3D(
        vx=draw(st.floats(min_value=-30.0, max_value=30.0)),
        vy=draw(st.floats(min_value=-30.0, max_value=30.0)),
        vz=draw(st.floats(min_value=-30.0, max_value=30.0))
    )


@st.composite
def trajectory_strategy(draw, min_length=1, max_length=30):
    """Generate random Trajectory objects."""
    length = draw(st.integers(min_value=min_length, max_value=max_length))
    
    positions = [draw(position_3d_strategy()) for _ in range(length)]
    timestamps = sorted([draw(st.floats(min_value=0.0, max_value=10.0)) for _ in range(length)])
    velocities = [draw(vector_3d_strategy()) for _ in range(length)]
    
    return Trajectory(
        positions=positions,
        timestamps=timestamps,
        velocities=velocities,
        start_position=positions[0] if positions else Position3D(x=0.0, y=1.0, z=-10.0),
        end_position=positions[-1] if positions else None,
        speed_max=draw(st.floats(min_value=0.0, max_value=50.0)),
        speed_avg=draw(st.floats(min_value=0.0, max_value=40.0))
    )


@st.composite
def detection_strategy(draw, class_id=None, confidence=None):
    """Generate random Detection objects."""
    if class_id is None:
        class_id = draw(st.integers(min_value=0, max_value=7))
    if confidence is None:
        confidence = draw(st.floats(min_value=0.0, max_value=1.0))
    
    return Detection(
        class_id=class_id,
        class_name=f"class_{class_id}",
        bounding_box=BoundingBox(
            x=draw(st.floats(min_value=0.0, max_value=1280.0)),
            y=draw(st.floats(min_value=0.0, max_value=720.0)),
            width=draw(st.floats(min_value=10.0, max_value=200.0)),
            height=draw(st.floats(min_value=10.0, max_value=200.0))
        ),
        confidence=confidence,
        position_3d=draw(st.one_of(st.none(), position_3d_strategy()))
    )


@st.composite
def video_reference_strategy(draw):
    """Generate random VideoReference objects."""
    return VideoReference(
        camera_id=draw(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        frame_number=draw(st.integers(min_value=0, max_value=100000)),
        timestamp=draw(st.floats(min_value=0.0, max_value=1000.0))
    )


@st.composite
def decision_strategy(draw, event_type=None, confidence=None):
    """Generate random Decision objects."""
    if event_type is None:
        event_type = draw(st.sampled_from(list(EventType)))
    if confidence is None:
        confidence = draw(st.floats(min_value=0.0, max_value=1.0))
    
    trajectory = draw(trajectory_strategy(min_length=2, max_length=10))
    detections = [draw(detection_strategy()) for _ in range(draw(st.integers(min_value=1, max_value=5)))]
    video_refs = [draw(video_reference_strategy()) for _ in range(draw(st.integers(min_value=1, max_value=3)))]
    
    return Decision(
        decision_id=draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        event_type=event_type,
        confidence=confidence,
        timestamp=draw(st.floats(min_value=0.0, max_value=1000.0)),
        trajectory=trajectory,
        detections=detections,
        reasoning=draw(st.text(min_size=1, max_size=100)),
        video_references=video_refs,
        requires_review=confidence < 0.80
    )


@st.composite
def performance_metrics_strategy(draw):
    """Generate random PerformanceMetrics objects."""
    return PerformanceMetrics(
        timestamp=draw(st.floats(min_value=0.0, max_value=1000.0)),
        fps=draw(st.floats(min_value=0.0, max_value=120.0)),
        processing_latency_ms=draw(st.floats(min_value=0.0, max_value=5000.0)),
        cpu_usage_percent=draw(st.floats(min_value=0.0, max_value=100.0)),
        memory_usage_mb=draw(st.floats(min_value=0.0, max_value=16384.0)),
        gpu_usage_percent=draw(st.one_of(st.none(), st.floats(min_value=0.0, max_value=100.0)))
    )


# ============================================================================
# Property 29: Event Logging Completeness
# ============================================================================

@given(decision=decision_strategy())
@settings(max_examples=100, deadline=None)
def test_property_29_event_logging_completeness(decision):
    """
    Property 29: Event Logging Completeness
    
    For any match event detected by the system, the event log SHALL contain
    the event type, timestamp, confidence score, and video frame references
    in structured JSON format.
    
    Validates: Requirements 15.1, 15.2, 15.3
    """
    # Create temporary log directory
    with tempfile.TemporaryDirectory() as temp_dir:
        logger = EventLogger(log_directory=temp_dir, retention_days=30)
        
        # Log the decision
        logger.log_decision(decision)
        
        # Query all events
        all_events = logger.query_events(EventFilter())
        
        # Verify at least one event was logged
        assert len(all_events) > 0, "No events were logged"
        
        # Find the logged event
        logged_event = None
        for event in all_events:
            if event.get("event_id") == decision.decision_id:
                logged_event = event
                break
        
        assert logged_event is not None, f"Decision {decision.decision_id} was not found in logs"
        
        # Property: Event log SHALL contain event type
        assert "event_type" in logged_event, "Event log missing event_type field"
        assert logged_event["event_type"] == decision.event_type.value, \
            f"Event type mismatch: expected {decision.event_type.value}, got {logged_event['event_type']}"
        
        # Property: Event log SHALL contain timestamp
        assert "timestamp" in logged_event, "Event log missing timestamp field"
        assert logged_event["timestamp"] == decision.timestamp, \
            f"Timestamp mismatch: expected {decision.timestamp}, got {logged_event['timestamp']}"
        
        # Property: Event log SHALL contain confidence score
        assert "confidence" in logged_event, "Event log missing confidence field"
        assert logged_event["confidence"] == decision.confidence, \
            f"Confidence mismatch: expected {decision.confidence}, got {logged_event['confidence']}"
        
        # Property: Event log SHALL contain video frame references
        assert "video_references" in logged_event, "Event log missing video_references field"
        assert isinstance(logged_event["video_references"], list), \
            "video_references must be a list"
        assert len(logged_event["video_references"]) == len(decision.video_references), \
            f"Video reference count mismatch: expected {len(decision.video_references)}, got {len(logged_event['video_references'])}"
        
        # Verify video reference structure
        for i, video_ref in enumerate(logged_event["video_references"]):
            assert "camera_id" in video_ref, f"Video reference {i} missing camera_id"
            assert "frame_number" in video_ref, f"Video reference {i} missing frame_number"
            assert "timestamp" in video_ref, f"Video reference {i} missing timestamp"
            
            # Verify values match
            original_ref = decision.video_references[i]
            assert video_ref["camera_id"] == original_ref.camera_id, \
                f"Camera ID mismatch in reference {i}"
            assert video_ref["frame_number"] == original_ref.frame_number, \
                f"Frame number mismatch in reference {i}"
            assert video_ref["timestamp"] == original_ref.timestamp, \
                f"Timestamp mismatch in reference {i}"
        
        # Property: Event log SHALL be in structured JSON format
        # (Already validated by successful parsing in query_events)
        assert "timestamp_iso" in logged_event, "Event log missing ISO timestamp"
        assert "reasoning" in logged_event, "Event log missing reasoning field"
        assert "trajectory" in logged_event, "Event log missing trajectory field"
        assert "detections" in logged_event, "Event log missing detections field"


@given(
    decisions=st.lists(decision_strategy(), min_size=1, max_size=10),
    event_type_filter=st.sampled_from(list(EventType))
)
@settings(max_examples=50, deadline=None)
def test_event_logging_query_by_event_type(decisions, event_type_filter):
    """
    Test that querying events by event type returns only matching events.
    
    This validates that the event logging system correctly indexes and
    filters events by type.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        logger = EventLogger(log_directory=temp_dir, retention_days=30)
        
        # Log all decisions
        for decision in decisions:
            logger.log_decision(decision)
        
        # Query by event type
        filtered_events = logger.query_events(
            EventFilter(event_types=[event_type_filter])
        )
        
        # Verify all returned events match the filter
        for event in filtered_events:
            assert event["event_type"] == event_type_filter.value, \
                f"Event type mismatch: expected {event_type_filter.value}, got {event['event_type']}"
        
        # Verify we got all matching events
        expected_count = sum(1 for d in decisions if d.event_type == event_type_filter)
        assert len(filtered_events) == expected_count, \
            f"Expected {expected_count} events, got {len(filtered_events)}"


@given(
    decisions=st.lists(decision_strategy(), min_size=1, max_size=10),
    min_confidence=st.floats(min_value=0.0, max_value=1.0)
)
@settings(max_examples=50, deadline=None)
def test_event_logging_query_by_confidence(decisions, min_confidence):
    """
    Test that querying events by confidence threshold returns only matching events.
    
    This validates that the event logging system correctly filters events
    by confidence level.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        logger = EventLogger(log_directory=temp_dir, retention_days=30)
        
        # Log all decisions
        for decision in decisions:
            logger.log_decision(decision)
        
        # Query by minimum confidence
        filtered_events = logger.query_events(
            EventFilter(min_confidence=min_confidence)
        )
        
        # Verify all returned events meet the confidence threshold
        for event in filtered_events:
            assert event["confidence"] >= min_confidence, \
                f"Confidence below threshold: {event['confidence']} < {min_confidence}"
        
        # Verify we got all matching events
        expected_count = sum(1 for d in decisions if d.confidence >= min_confidence)
        assert len(filtered_events) == expected_count, \
            f"Expected {expected_count} events, got {len(filtered_events)}"


@given(metrics=performance_metrics_strategy())
@settings(max_examples=50, deadline=None)
def test_performance_logging_completeness(metrics):
    """
    Test that performance metrics are logged with all required fields.
    
    This validates that the performance logging functionality captures
    all necessary system metrics.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        logger = EventLogger(log_directory=temp_dir, retention_days=30)
        
        # Log performance metrics
        logger.log_performance(metrics)
        
        # Read the performance log
        performance_log_path = Path(temp_dir) / "performance.jsonl"
        assert performance_log_path.exists(), "Performance log file not created"
        
        # Parse the log
        import json
        with open(performance_log_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) > 0, "No performance metrics logged"
            
            logged_metrics = json.loads(lines[-1])
            
            # Verify all required fields are present
            assert "timestamp" in logged_metrics, "Missing timestamp"
            assert "timestamp_iso" in logged_metrics, "Missing ISO timestamp"
            assert "fps" in logged_metrics, "Missing fps"
            assert "processing_latency_ms" in logged_metrics, "Missing processing_latency_ms"
            assert "cpu_usage_percent" in logged_metrics, "Missing cpu_usage_percent"
            assert "memory_usage_mb" in logged_metrics, "Missing memory_usage_mb"
            
            # Verify values match
            assert logged_metrics["timestamp"] == metrics.timestamp
            assert logged_metrics["fps"] == metrics.fps
            assert logged_metrics["processing_latency_ms"] == metrics.processing_latency_ms
            assert logged_metrics["cpu_usage_percent"] == metrics.cpu_usage_percent
            assert logged_metrics["memory_usage_mb"] == metrics.memory_usage_mb
            
            if metrics.gpu_usage_percent is not None:
                assert logged_metrics["gpu_usage_percent"] == metrics.gpu_usage_percent


@given(decisions=st.lists(decision_strategy(), min_size=2, max_size=20))
@settings(max_examples=30, deadline=None)
def test_event_logging_persistence(decisions):
    """
    Test that logged events persist across EventLogger instances.
    
    This validates that the event logging system correctly saves events
    to disk and can reload them.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create first logger and log events
        logger1 = EventLogger(log_directory=temp_dir, retention_days=30)
        for decision in decisions:
            logger1.log_decision(decision)
        
        # Create second logger with same directory
        logger2 = EventLogger(log_directory=temp_dir, retention_days=30)
        
        # Query all events from second logger
        all_events = logger2.query_events(EventFilter())
        
        # Verify all events were persisted
        assert len(all_events) == len(decisions), \
            f"Expected {len(decisions)} events, got {len(all_events)}"
        
        # Verify event IDs match
        logged_ids = {event["event_id"] for event in all_events}
        expected_ids = {decision.decision_id for decision in decisions}
        assert logged_ids == expected_ids, "Event IDs do not match after reload"
