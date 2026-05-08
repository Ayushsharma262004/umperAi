"""
Property-based tests for Decision Review System.

Tests universal properties that should hold for all decision overrides
and feedback collection scenarios.
"""

import json
import tempfile
import time
from pathlib import Path

import pytest
from hypothesis import given, strategies as st, settings, assume

from umpirai.decision.decision_review_system import (
    DecisionReviewSystem,
    User,
    UserRole,
)
from umpirai.models.data_models import (
    Decision,
    EventType,
    Trajectory,
    Position3D,
    Vector3D,
    VideoReference,
)


# ============================================================================
# Custom Strategies
# ============================================================================

@st.composite
def user_strategy(draw, authorized=None):
    """Generate User instances."""
    user_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    username = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    
    if authorized is None:
        role = draw(st.sampled_from([UserRole.OPERATOR, UserRole.UMPIRE, UserRole.ADMIN]))
    elif authorized:
        role = draw(st.sampled_from([UserRole.UMPIRE, UserRole.ADMIN]))
    else:
        role = UserRole.OPERATOR
    
    return User(user_id=user_id, username=username, role=role)


@st.composite
def position_3d_strategy(draw):
    """Generate Position3D instances."""
    x = draw(st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False))
    y = draw(st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False))
    z = draw(st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False))
    return Position3D(x=x, y=y, z=z)


@st.composite
def vector_3d_strategy(draw):
    """Generate Vector3D instances."""
    vx = draw(st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False))
    vy = draw(st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False))
    vz = draw(st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False))
    return Vector3D(vx=vx, vy=vy, vz=vz)


@st.composite
def trajectory_strategy(draw):
    """Generate Trajectory instances."""
    num_positions = draw(st.integers(min_value=2, max_value=30))
    
    positions = [draw(position_3d_strategy()) for _ in range(num_positions)]
    timestamps = sorted([draw(st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False)) for _ in range(num_positions)])
    velocities = [draw(vector_3d_strategy()) for _ in range(num_positions)]
    
    start_position = positions[0]
    end_position = positions[-1] if len(positions) > 1 else None
    
    # Calculate speed metrics
    speeds = [v.magnitude() for v in velocities]
    speed_max = max(speeds) if speeds else 0.0
    speed_avg = sum(speeds) / len(speeds) if speeds else 0.0
    
    return Trajectory(
        positions=positions,
        timestamps=timestamps,
        velocities=velocities,
        start_position=start_position,
        end_position=end_position,
        speed_max=speed_max,
        speed_avg=speed_avg,
    )


@st.composite
def video_reference_strategy(draw):
    """Generate VideoReference instances."""
    camera_id = draw(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    frame_number = draw(st.integers(min_value=0, max_value=100000))
    timestamp = draw(st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    
    return VideoReference(
        camera_id=camera_id,
        frame_number=frame_number,
        timestamp=timestamp,
    )


@st.composite
def decision_strategy(draw):
    """Generate Decision instances."""
    decision_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    event_type = draw(st.sampled_from(list(EventType)))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    timestamp = draw(st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    trajectory = draw(trajectory_strategy())
    reasoning = draw(st.text(min_size=1, max_size=100))
    
    num_video_refs = draw(st.integers(min_value=1, max_value=3))
    video_references = [draw(video_reference_strategy()) for _ in range(num_video_refs)]
    
    return Decision(
        decision_id=decision_id,
        event_type=event_type,
        confidence=confidence,
        timestamp=timestamp,
        trajectory=trajectory,
        detections=[],  # Empty for simplicity
        reasoning=reasoning,
        video_references=video_references,
        requires_review=(confidence < 0.80),
    )


# ============================================================================
# Property 38: Decision Override Logging
# ============================================================================

@given(
    decision=decision_strategy(),
    override_type=st.sampled_from(["wide", "no_ball", "bowled", "caught", "lbw", "legal"]),
    justification=st.text(min_size=1, max_size=200),
    user=user_strategy(authorized=True),
    override_confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100, deadline=None)
def test_property_38_decision_override_logging(
    decision, override_type, justification, user, override_confidence
):
    """
    Feature: ai-auto-umpiring-system, Property 38: Decision Override Logging
    
    **Validates: Requirements 20.3, 20.4**
    
    For any manual override of a system decision, the system SHALL log both
    the original system decision and the override with justification.
    
    This property verifies that:
    1. Override logs contain both system decision and manual override
    2. Justification is included in the log
    3. User information is recorded
    4. Video references are preserved
    5. Timestamps are recorded
    """
    # Arrange: Create temporary directory for logs
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        # Act: Override the decision
        override = review_system.override_decision(
            decision=decision,
            override_decision_type=override_type,
            justification=justification,
            user=user,
            override_confidence=override_confidence,
        )
        
        # Assert: Verify override was logged
        override_log_path = Path(temp_dir) / "overrides.jsonl"
        assert override_log_path.exists(), "Override log file should exist"
        
        # Read the log
        with open(override_log_path, 'r') as f:
            log_lines = f.readlines()
        
        assert len(log_lines) >= 1, "At least one override should be logged"
        
        # Parse the last log entry
        log_entry = json.loads(log_lines[-1])
        
        # Property: Log contains both system decision and manual override
        assert "system_decision" in log_entry, "Log must contain system_decision"
        assert "manual_override" in log_entry, "Log must contain manual_override"
        
        # Property: System decision details are preserved
        assert log_entry["system_decision"]["decision_id"] == decision.decision_id
        assert log_entry["system_decision"]["event_type"] == decision.event_type.value
        assert log_entry["system_decision"]["confidence"] == decision.confidence
        assert log_entry["system_decision"]["reasoning"] == decision.reasoning
        
        # Property: Manual override details are recorded
        assert log_entry["manual_override"]["decision_type"] == override_type
        assert log_entry["manual_override"]["confidence"] == override_confidence
        assert log_entry["manual_override"]["justification"] == justification
        
        # Property: User information is recorded
        assert log_entry["user_id"] == user.user_id
        assert log_entry["username"] == user.username
        assert log_entry["user_role"] == user.role.value
        
        # Property: Video references are preserved
        assert "video_references" in log_entry
        assert len(log_entry["video_references"]) == len(decision.video_references)
        
        # Property: Timestamps are recorded
        assert "timestamp" in log_entry
        assert "timestamp_iso" in log_entry
        assert log_entry["timestamp"] > 0


# ============================================================================
# Property 39: Override Feedback Collection
# ============================================================================

@given(
    decision=decision_strategy(),
    override_type=st.sampled_from(["wide", "no_ball", "bowled", "caught", "lbw", "legal"]),
    justification=st.text(min_size=1, max_size=200),
    user=user_strategy(authorized=True),
    override_confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=100, deadline=None)
def test_property_39_override_feedback_collection(
    decision, override_type, justification, user, override_confidence
):
    """
    Feature: ai-auto-umpiring-system, Property 39: Override Feedback Collection
    
    **Validates: Requirements 20.5**
    
    For any decision override, the system SHALL collect the override as
    feedback data for model improvement.
    
    This property verifies that:
    1. Feedback is collected for every override
    2. Feedback contains original and correct decisions
    3. Feedback includes trajectory and detection data
    4. Feedback is stored in a format suitable for model training
    5. Video references are included for retraining
    """
    # Arrange: Create temporary directory for logs
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        # Act: Override the decision
        override = review_system.override_decision(
            decision=decision,
            override_decision_type=override_type,
            justification=justification,
            user=user,
            override_confidence=override_confidence,
        )
        
        # Assert: Verify feedback was collected
        feedback_log_path = Path(temp_dir) / "feedback.jsonl"
        assert feedback_log_path.exists(), "Feedback log file should exist"
        
        # Read the feedback log
        with open(feedback_log_path, 'r') as f:
            feedback_lines = f.readlines()
        
        assert len(feedback_lines) >= 1, "At least one feedback entry should be logged"
        
        # Parse the last feedback entry
        feedback_entry = json.loads(feedback_lines[-1])
        
        # Property: Feedback contains original decision
        assert "original_decision" in feedback_entry
        assert feedback_entry["original_decision"]["event_type"] == decision.event_type.value
        assert feedback_entry["original_decision"]["confidence"] == decision.confidence
        
        # Property: Feedback contains correct decision
        assert "correct_decision" in feedback_entry
        assert feedback_entry["correct_decision"]["event_type"] == override_type
        assert feedback_entry["correct_decision"]["confidence"] == override_confidence
        
        # Property: Feedback includes justification
        assert "justification" in feedback_entry
        assert feedback_entry["justification"] == justification
        
        # Property: Feedback includes trajectory data
        assert "trajectory_data" in feedback_entry
        assert "start_position" in feedback_entry["trajectory_data"]
        assert "speed_max" in feedback_entry["trajectory_data"]
        assert "speed_avg" in feedback_entry["trajectory_data"]
        
        # Property: Feedback includes detection data
        assert "detections" in feedback_entry
        # (May be empty in this test, but field should exist)
        
        # Property: Feedback includes video references for retraining
        assert "video_references" in feedback_entry
        assert len(feedback_entry["video_references"]) == len(decision.video_references)
        
        # Property: Feedback includes user role (for weighting feedback)
        assert "user_role" in feedback_entry
        assert feedback_entry["user_role"] == user.role.value
        
        # Property: Feedback has unique ID
        assert "feedback_id" in feedback_entry
        assert feedback_entry["feedback_id"].startswith("feedback_")
        
        # Property: Feedback has timestamp
        assert "timestamp" in feedback_entry
        assert "timestamp_iso" in feedback_entry


# ============================================================================
# Additional Property Tests
# ============================================================================

@given(
    decision=decision_strategy(),
    override_type=st.sampled_from(["wide", "no_ball", "bowled", "caught", "lbw", "legal"]),
    justification=st.text(min_size=1, max_size=200),
    user=user_strategy(authorized=False),  # Unauthorized user
)
@settings(max_examples=50, deadline=None)
def test_property_unauthorized_override_rejected(
    decision, override_type, justification, user
):
    """
    Property: Unauthorized users cannot override decisions.
    
    For any user without override authorization (OPERATOR role),
    the system SHALL reject override attempts with PermissionError.
    """
    # Arrange
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        # Act & Assert: Attempt to override should raise PermissionError
        with pytest.raises(PermissionError) as exc_info:
            review_system.override_decision(
                decision=decision,
                override_decision_type=override_type,
                justification=justification,
                user=user,
            )
        
        # Verify error message mentions authorization
        assert "not authorized" in str(exc_info.value).lower()
        
        # Verify no override was logged
        override_log_path = Path(temp_dir) / "overrides.jsonl"
        if override_log_path.exists():
            with open(override_log_path, 'r') as f:
                log_lines = f.readlines()
            assert len(log_lines) == 0, "No overrides should be logged for unauthorized users"


@given(
    decisions=st.lists(decision_strategy(), min_size=1, max_size=10),
    override_types=st.lists(
        st.sampled_from(["wide", "no_ball", "bowled", "caught", "lbw", "legal"]),
        min_size=1,
        max_size=10
    ),
    justifications=st.lists(st.text(min_size=1, max_size=200), min_size=1, max_size=10),
    user=user_strategy(authorized=True),
)
@settings(max_examples=50, deadline=None)
def test_property_multiple_overrides_all_logged(
    decisions, override_types, justifications, user
):
    """
    Property: All overrides are logged independently.
    
    For any sequence of decision overrides, the system SHALL log each
    override independently with complete information.
    """
    # Ensure lists have same length
    min_len = min(len(decisions), len(override_types), len(justifications))
    decisions = decisions[:min_len]
    override_types = override_types[:min_len]
    justifications = justifications[:min_len]
    
    assume(min_len > 0)
    
    # Arrange
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        # Act: Override multiple decisions
        for decision, override_type, justification in zip(decisions, override_types, justifications):
            review_system.override_decision(
                decision=decision,
                override_decision_type=override_type,
                justification=justification,
                user=user,
            )
        
        # Assert: Verify all overrides were logged
        override_log_path = Path(temp_dir) / "overrides.jsonl"
        assert override_log_path.exists()
        
        with open(override_log_path, 'r') as f:
            log_lines = f.readlines()
        
        # Property: Number of log entries equals number of overrides
        assert len(log_lines) == len(decisions)
        
        # Property: Each log entry is valid JSON
        for line in log_lines:
            log_entry = json.loads(line)
            assert "system_decision" in log_entry
            assert "manual_override" in log_entry
            assert "user_id" in log_entry
        
        # Verify feedback was collected for all overrides
        feedback_log_path = Path(temp_dir) / "feedback.jsonl"
        assert feedback_log_path.exists()
        
        with open(feedback_log_path, 'r') as f:
            feedback_lines = f.readlines()
        
        # Property: Number of feedback entries equals number of overrides
        assert len(feedback_lines) == len(decisions)
