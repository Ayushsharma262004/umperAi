"""
Unit tests for DecisionOutput.

These tests verify specific functionality of the DecisionOutput class including
output format switching, priority system, and latency measurement.
"""

import pytest
import numpy as np
import time

from umpirai.output.decision_output import (
    DecisionOutput,
    OutputConfig,
    OutputFormat,
    DecisionPriority,
)
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
def sample_trajectory():
    """Create a sample trajectory for testing."""
    return Trajectory(
        positions=[
            Position3D(x=0.0, y=1.0, z=-10.0),
            Position3D(x=0.0, y=1.0, z=-5.0),
            Position3D(x=0.0, y=1.0, z=0.0),
        ],
        timestamps=[0.0, 0.1, 0.2],
        velocities=[
            Vector3D(vx=0.0, vy=0.0, vz=20.0),
            Vector3D(vx=0.0, vy=0.0, vz=20.0),
            Vector3D(vx=0.0, vy=0.0, vz=20.0),
        ],
        start_position=Position3D(x=0.0, y=1.0, z=-10.0),
        end_position=Position3D(x=0.0, y=1.0, z=0.0),
        speed_max=20.0,
        speed_avg=20.0
    )


@pytest.fixture
def sample_detections():
    """Create sample detections for testing."""
    return [
        Detection(
            class_id=0,
            class_name="ball",
            bounding_box=BoundingBox(x=640.0, y=360.0, width=20.0, height=20.0),
            confidence=0.95
        ),
        Detection(
            class_id=1,
            class_name="stumps",
            bounding_box=BoundingBox(x=620.0, y=400.0, width=40.0, height=80.0),
            confidence=0.98
        )
    ]


@pytest.fixture
def sample_decision(sample_trajectory, sample_detections):
    """Create a sample decision for testing."""
    return Decision(
        decision_id="test_decision_1",
        event_type=EventType.LEGAL,
        confidence=0.92,
        timestamp=time.time(),
        trajectory=sample_trajectory,
        detections=sample_detections,
        reasoning="Legal delivery detected",
        video_references=[
            VideoReference(camera_id="cam1", frame_number=100, timestamp=1.0)
        ],
        requires_review=False
    )


@pytest.fixture
def sample_frame():
    """Create a sample video frame for testing."""
    return np.zeros((720, 1280, 3), dtype=np.uint8)


# ============================================================================
# Initialization Tests
# ============================================================================

def test_decision_output_initialization():
    """Test DecisionOutput initialization with default config."""
    output = DecisionOutput()
    
    assert output.config is not None
    assert output.config.enable_text is True
    assert output.config.enable_audio is True
    assert output.config.enable_visual is True
    assert output.latency_measurements == []
    assert output.last_output_time == 0.0
    assert output.last_output_priority is None


def test_decision_output_initialization_with_config():
    """Test DecisionOutput initialization with custom config."""
    config = OutputConfig(
        enable_text=True,
        enable_audio=False,
        enable_visual=True,
        audio_rate=200,
        audio_volume=0.8,
        overlay_duration_ms=5000
    )
    
    output = DecisionOutput(config=config)
    
    assert output.config.enable_text is True
    assert output.config.enable_audio is False
    assert output.config.enable_visual is True
    assert output.config.audio_rate == 200
    assert output.config.audio_volume == 0.8
    assert output.config.overlay_duration_ms == 5000


def test_output_config_validation():
    """Test OutputConfig validation."""
    # Valid config
    config = OutputConfig(audio_rate=150, audio_volume=0.5, overlay_duration_ms=3000)
    assert config.audio_rate == 150
    
    # Invalid audio_rate (non-positive)
    with pytest.raises(ValueError, match="audio_rate must be a positive integer"):
        OutputConfig(audio_rate=0)
    
    # Invalid audio_volume (out of range)
    with pytest.raises(ValueError, match="audio_volume must be in range"):
        OutputConfig(audio_volume=1.5)
    
    # Invalid overlay_duration_ms (non-positive)
    with pytest.raises(ValueError, match="overlay_duration_ms must be a positive integer"):
        OutputConfig(overlay_duration_ms=-100)


# ============================================================================
# Output Format Switching Tests
# ============================================================================

def test_set_output_format_text():
    """Test setting output format to TEXT only."""
    output = DecisionOutput()
    output.set_output_format(OutputFormat.TEXT)
    
    assert output.config.enable_text is True
    assert output.config.enable_audio is False
    assert output.config.enable_visual is False
    assert output.get_output_format() == OutputFormat.TEXT


def test_set_output_format_audio():
    """Test setting output format to AUDIO only."""
    output = DecisionOutput()
    output.set_output_format(OutputFormat.AUDIO)
    
    assert output.config.enable_text is False
    assert output.config.enable_audio is True
    assert output.config.enable_visual is False
    assert output.get_output_format() == OutputFormat.AUDIO


def test_set_output_format_visual():
    """Test setting output format to VISUAL only."""
    output = DecisionOutput()
    output.set_output_format(OutputFormat.VISUAL)
    
    assert output.config.enable_text is False
    assert output.config.enable_audio is False
    assert output.config.enable_visual is True
    assert output.get_output_format() == OutputFormat.VISUAL


def test_set_output_format_all():
    """Test setting output format to ALL."""
    output = DecisionOutput()
    output.set_output_format(OutputFormat.ALL)
    
    assert output.config.enable_text is True
    assert output.config.enable_audio is True
    assert output.config.enable_visual is True
    assert output.get_output_format() == OutputFormat.ALL


def test_get_output_format_default():
    """Test getting output format with default config."""
    output = DecisionOutput()
    
    # Default is ALL
    assert output.get_output_format() == OutputFormat.ALL


# ============================================================================
# Priority System Tests
# ============================================================================

def test_priority_dismissal_events():
    """Test that dismissal events have HIGH priority."""
    output = DecisionOutput()
    
    # Test BOWLED
    bowled_decision = Decision(
        decision_id="bowled_1",
        event_type=EventType.BOWLED,
        confidence=0.90,
        timestamp=time.time(),
        trajectory=Trajectory(
            positions=[Position3D(x=0.0, y=1.0, z=-10.0)],
            timestamps=[1.0],
            velocities=[Vector3D(vx=0.0, vy=0.0, vz=20.0)],
            start_position=Position3D(x=0.0, y=1.0, z=-10.0)
        ),
        detections=[],
        reasoning="Bowled",
        video_references=[],
        requires_review=False
    )
    assert output.get_decision_priority(bowled_decision) == DecisionPriority.HIGH
    
    # Test CAUGHT
    caught_decision = Decision(
        decision_id="caught_1",
        event_type=EventType.CAUGHT,
        confidence=0.90,
        timestamp=time.time(),
        trajectory=Trajectory(
            positions=[Position3D(x=0.0, y=1.0, z=-10.0)],
            timestamps=[1.0],
            velocities=[Vector3D(vx=0.0, vy=0.0, vz=20.0)],
            start_position=Position3D(x=0.0, y=1.0, z=-10.0)
        ),
        detections=[],
        reasoning="Caught",
        video_references=[],
        requires_review=False
    )
    assert output.get_decision_priority(caught_decision) == DecisionPriority.HIGH
    
    # Test LBW
    lbw_decision = Decision(
        decision_id="lbw_1",
        event_type=EventType.LBW,
        confidence=0.90,
        timestamp=time.time(),
        trajectory=Trajectory(
            positions=[Position3D(x=0.0, y=1.0, z=-10.0)],
            timestamps=[1.0],
            velocities=[Vector3D(vx=0.0, vy=0.0, vz=20.0)],
            start_position=Position3D(x=0.0, y=1.0, z=-10.0)
        ),
        detections=[],
        reasoning="LBW",
        video_references=[],
        requires_review=False
    )
    assert output.get_decision_priority(lbw_decision) == DecisionPriority.HIGH


def test_priority_medium_events():
    """Test that no ball and wide events have MEDIUM priority."""
    output = DecisionOutput()
    
    # Test NO_BALL
    no_ball_decision = Decision(
        decision_id="no_ball_1",
        event_type=EventType.NO_BALL,
        confidence=0.90,
        timestamp=time.time(),
        trajectory=Trajectory(
            positions=[Position3D(x=0.0, y=1.0, z=-10.0)],
            timestamps=[1.0],
            velocities=[Vector3D(vx=0.0, vy=0.0, vz=20.0)],
            start_position=Position3D(x=0.0, y=1.0, z=-10.0)
        ),
        detections=[],
        reasoning="No ball",
        video_references=[],
        requires_review=False
    )
    assert output.get_decision_priority(no_ball_decision) == DecisionPriority.MEDIUM
    
    # Test WIDE
    wide_decision = Decision(
        decision_id="wide_1",
        event_type=EventType.WIDE,
        confidence=0.90,
        timestamp=time.time(),
        trajectory=Trajectory(
            positions=[Position3D(x=0.0, y=1.0, z=-10.0)],
            timestamps=[1.0],
            velocities=[Vector3D(vx=0.0, vy=0.0, vz=20.0)],
            start_position=Position3D(x=0.0, y=1.0, z=-10.0)
        ),
        detections=[],
        reasoning="Wide",
        video_references=[],
        requires_review=False
    )
    assert output.get_decision_priority(wide_decision) == DecisionPriority.MEDIUM


def test_priority_low_events():
    """Test that legal delivery has LOW priority."""
    output = DecisionOutput()
    
    legal_decision = Decision(
        decision_id="legal_1",
        event_type=EventType.LEGAL,
        confidence=0.90,
        timestamp=time.time(),
        trajectory=Trajectory(
            positions=[Position3D(x=0.0, y=1.0, z=-10.0)],
            timestamps=[1.0],
            velocities=[Vector3D(vx=0.0, vy=0.0, vz=20.0)],
            start_position=Position3D(x=0.0, y=1.0, z=-10.0)
        ),
        detections=[],
        reasoning="Legal",
        video_references=[],
        requires_review=False
    )
    assert output.get_decision_priority(legal_decision) == DecisionPriority.LOW


def test_priority_values():
    """Test that priority values are correctly ordered."""
    assert DecisionPriority.HIGH.value == 3
    assert DecisionPriority.MEDIUM.value == 2
    assert DecisionPriority.LOW.value == 1
    assert DecisionPriority.HIGH.value > DecisionPriority.MEDIUM.value
    assert DecisionPriority.MEDIUM.value > DecisionPriority.LOW.value


# ============================================================================
# Latency Measurement Tests
# ============================================================================

def test_latency_measurement(sample_decision):
    """Test that latency is measured when displaying decisions."""
    config = OutputConfig(enable_text=True, enable_audio=False, enable_visual=False)
    output = DecisionOutput(config=config)
    
    # Display decision
    output.display_decision(sample_decision, frame=None)
    
    # Check latency was measured
    stats = output.get_latency_stats()
    assert stats["count"] == 1
    assert stats["latest_ms"] >= 0.0
    assert stats["min_ms"] >= 0.0
    assert stats["max_ms"] >= 0.0
    assert stats["avg_ms"] >= 0.0


def test_latency_stats_multiple_decisions(sample_trajectory, sample_detections):
    """Test latency statistics with multiple decisions."""
    config = OutputConfig(enable_text=True, enable_audio=False, enable_visual=False)
    output = DecisionOutput(config=config)
    
    # Display multiple decisions
    for i in range(5):
        decision = Decision(
            decision_id=f"decision_{i}",
            event_type=EventType.LEGAL,
            confidence=0.90,
            timestamp=time.time(),
            trajectory=sample_trajectory,
            detections=sample_detections,
            reasoning="Test",
            video_references=[],
            requires_review=False
        )
        output.display_decision(decision, frame=None)
        time.sleep(0.01)  # Small delay between decisions
    
    # Check stats
    stats = output.get_latency_stats()
    assert stats["count"] == 5
    assert stats["min_ms"] <= stats["avg_ms"] <= stats["max_ms"]


def test_latency_reset(sample_decision):
    """Test resetting latency measurements."""
    config = OutputConfig(enable_text=True, enable_audio=False, enable_visual=False)
    output = DecisionOutput(config=config)
    
    # Display decision
    output.display_decision(sample_decision, frame=None)
    
    # Verify measurement exists
    stats = output.get_latency_stats()
    assert stats["count"] == 1
    
    # Reset
    output.reset_latency_measurements()
    
    # Verify measurements cleared
    stats = output.get_latency_stats()
    assert stats["count"] == 0
    assert stats["min_ms"] == 0.0
    assert stats["max_ms"] == 0.0
    assert stats["avg_ms"] == 0.0
    assert stats["latest_ms"] == 0.0


def test_latency_stats_empty():
    """Test latency stats when no measurements exist."""
    output = DecisionOutput()
    
    stats = output.get_latency_stats()
    assert stats["count"] == 0
    assert stats["min_ms"] == 0.0
    assert stats["max_ms"] == 0.0
    assert stats["avg_ms"] == 0.0
    assert stats["latest_ms"] == 0.0


# ============================================================================
# Display Decision Tests
# ============================================================================

def test_display_decision_without_frame(sample_decision):
    """Test displaying decision without frame (console output)."""
    config = OutputConfig(enable_text=True, enable_audio=False, enable_visual=False)
    output = DecisionOutput(config=config)
    
    result = output.display_decision(sample_decision, frame=None)
    
    assert result is None
    assert len(output.latency_measurements) == 1


def test_display_decision_with_frame(sample_decision, sample_frame):
    """Test displaying decision with frame (overlay)."""
    config = OutputConfig(enable_text=True, enable_audio=False, enable_visual=False)
    output = DecisionOutput(config=config)
    
    result = output.display_decision(sample_decision, frame=sample_frame)
    
    # Result should be a frame (numpy array)
    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.shape == sample_frame.shape
    assert len(output.latency_measurements) == 1


def test_display_decision_disabled(sample_decision):
    """Test that display is skipped when text output is disabled."""
    config = OutputConfig(enable_text=False, enable_audio=False, enable_visual=False)
    output = DecisionOutput(config=config)
    
    result = output.display_decision(sample_decision, frame=None)
    
    assert result is None
    # Latency should not be measured when output is disabled
    assert len(output.latency_measurements) == 0


# ============================================================================
# Visual Indicator Tests
# ============================================================================

def test_visual_indicator_colors(sample_trajectory, sample_detections, sample_frame):
    """Test that visual indicators use correct colors for each event type."""
    config = OutputConfig(enable_text=False, enable_audio=False, enable_visual=True)
    output = DecisionOutput(config=config)
    
    # Test each event type
    event_types = [
        (EventType.LEGAL, (0, 255, 0)),  # Green
        (EventType.WIDE, (0, 255, 255)),  # Yellow
        (EventType.NO_BALL, (0, 0, 255)),  # Red
        (EventType.BOWLED, (255, 0, 0)),  # Blue
        (EventType.CAUGHT, (255, 0, 0)),  # Blue
        (EventType.LBW, (255, 0, 0)),  # Blue
    ]
    
    for event_type, expected_color in event_types:
        decision = Decision(
            decision_id=f"test_{event_type.value}",
            event_type=event_type,
            confidence=0.90,
            timestamp=time.time(),
            trajectory=sample_trajectory,
            detections=sample_detections,
            reasoning="Test",
            video_references=[],
            requires_review=False
        )
        
        result = output.display_visual_indicator(decision, sample_frame.copy())
        
        # Verify result is a frame
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.shape == sample_frame.shape
        
        # Verify color is used (check border pixels)
        # Top border should have the expected color
        assert tuple(result[5, 640]) == expected_color


def test_visual_indicator_disabled(sample_decision, sample_frame):
    """Test that visual indicator is skipped when disabled."""
    config = OutputConfig(enable_text=False, enable_audio=False, enable_visual=False)
    output = DecisionOutput(config=config)
    
    result = output.display_visual_indicator(sample_decision, sample_frame)
    
    # Should return original frame unchanged
    assert np.array_equal(result, sample_frame)


# ============================================================================
# Format Text Tests
# ============================================================================

def test_format_decision_text(sample_decision):
    """Test decision text formatting."""
    output = DecisionOutput()
    
    text = output._format_decision_text(sample_decision, 450.0)
    
    # Verify text contains key information
    assert "LEGAL" in text
    assert "Confidence:" in text
    assert "92.0%" in text
    assert "Latency:" in text
    assert "450ms" in text


def test_format_decision_text_with_review(sample_decision):
    """Test decision text formatting with review flag."""
    output = DecisionOutput()
    sample_decision.requires_review = True
    
    text = output._format_decision_text(sample_decision, 450.0)
    
    assert "REVIEW REQUIRED" in text


def test_format_announcement_text(sample_trajectory, sample_detections):
    """Test announcement text formatting for different event types."""
    output = DecisionOutput()
    
    # Test dismissals
    dismissal_events = [
        (EventType.BOWLED, "Out! bowled"),
        (EventType.CAUGHT, "Out! caught"),
        (EventType.LBW, "Out! lbw"),
    ]
    
    for event_type, expected_text in dismissal_events:
        decision = Decision(
            decision_id="test",
            event_type=event_type,
            confidence=0.90,
            timestamp=time.time(),
            trajectory=sample_trajectory,
            detections=sample_detections,
            reasoning="Test",
            video_references=[],
            requires_review=False
        )
        
        text = output._format_announcement_text(decision)
        assert text == expected_text
    
    # Test other events
    other_events = [
        (EventType.WIDE, "Wide ball"),
        (EventType.NO_BALL, "No ball"),
        (EventType.OVER_COMPLETE, "Over complete"),
    ]
    
    for event_type, expected_text in other_events:
        decision = Decision(
            decision_id="test",
            event_type=event_type,
            confidence=0.90,
            timestamp=time.time(),
            trajectory=sample_trajectory,
            detections=sample_detections,
            reasoning="Test",
            video_references=[],
            requires_review=False
        )
        
        text = output._format_announcement_text(decision)
        assert text == expected_text


# ============================================================================
# Output Decision Tests
# ============================================================================

def test_output_decision_all_formats(sample_decision, sample_frame):
    """Test outputting decision with all formats."""
    config = OutputConfig(enable_text=True, enable_audio=False, enable_visual=True)
    output = DecisionOutput(config=config)
    
    result = output.output_decision(sample_decision, sample_frame, OutputFormat.ALL)
    
    # Should return frame with overlays
    assert result is not None
    assert isinstance(result, np.ndarray)
    assert len(output.latency_measurements) == 1


def test_output_decision_text_only(sample_decision):
    """Test outputting decision with text only."""
    config = OutputConfig(enable_text=True, enable_audio=False, enable_visual=False)
    output = DecisionOutput(config=config)
    
    result = output.output_decision(sample_decision, None, OutputFormat.TEXT)
    
    assert result is None
    assert len(output.latency_measurements) == 1


def test_output_decision_priority_filtering(sample_trajectory, sample_detections):
    """Test that lower priority decisions are filtered when higher priority was recent."""
    config = OutputConfig(enable_text=True, enable_audio=False, enable_visual=False)
    output = DecisionOutput(config=config)
    
    # Output high priority decision (dismissal)
    high_priority_decision = Decision(
        decision_id="high",
        event_type=EventType.BOWLED,
        confidence=0.90,
        timestamp=time.time(),
        trajectory=sample_trajectory,
        detections=sample_detections,
        reasoning="Bowled",
        video_references=[],
        requires_review=False
    )
    
    output.output_decision(high_priority_decision, None, OutputFormat.TEXT)
    assert len(output.latency_measurements) == 1
    
    # Immediately try to output low priority decision (should be filtered)
    low_priority_decision = Decision(
        decision_id="low",
        event_type=EventType.LEGAL,
        confidence=0.90,
        timestamp=time.time(),
        trajectory=sample_trajectory,
        detections=sample_detections,
        reasoning="Legal",
        video_references=[],
        requires_review=False
    )
    
    output.output_decision(low_priority_decision, None, OutputFormat.TEXT)
    # Should still be 1 because low priority was filtered
    assert len(output.latency_measurements) == 1
