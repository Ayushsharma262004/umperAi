"""
Unit tests for Decision Review System.

Tests specific scenarios, edge cases, and workflows for the decision
review and override functionality.
"""

import json
import tempfile
import time
from pathlib import Path

import pytest

from umpirai.decision.decision_review_system import (
    DecisionReviewSystem,
    User,
    UserRole,
    DecisionOverride,
    ReviewInterface,
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
# Fixtures
# ============================================================================

@pytest.fixture
def sample_trajectory():
    """Create a sample trajectory for testing."""
    positions = [
        Position3D(x=0.0, y=1.0, z=0.0),
        Position3D(x=1.0, y=1.5, z=1.0),
        Position3D(x=2.0, y=1.2, z=2.0),
    ]
    timestamps = [0.0, 0.033, 0.066]
    velocities = [
        Vector3D(vx=10.0, vy=5.0, vz=10.0),
        Vector3D(vx=9.0, vy=-3.0, vz=9.0),
        Vector3D(vx=8.0, vy=-5.0, vz=8.0),
    ]
    
    return Trajectory(
        positions=positions,
        timestamps=timestamps,
        velocities=velocities,
        start_position=positions[0],
        end_position=positions[-1],
        speed_max=15.0,
        speed_avg=12.0,
    )


@pytest.fixture
def sample_decision(sample_trajectory):
    """Create a sample decision for testing."""
    return Decision(
        decision_id="test_decision_001",
        event_type=EventType.WIDE,
        confidence=0.75,
        timestamp=time.time(),
        trajectory=sample_trajectory,
        detections=[],
        reasoning="Ball crossed wide guideline on leg side",
        video_references=[
            VideoReference(camera_id="cam1", frame_number=1000, timestamp=time.time()),
            VideoReference(camera_id="cam2", frame_number=1001, timestamp=time.time()),
        ],
        requires_review=True,
    )


@pytest.fixture
def authorized_user():
    """Create an authorized user (umpire)."""
    return User(user_id="user_001", username="umpire_john", role=UserRole.UMPIRE)


@pytest.fixture
def admin_user():
    """Create an admin user."""
    return User(user_id="user_002", username="admin_alice", role=UserRole.ADMIN)


@pytest.fixture
def unauthorized_user():
    """Create an unauthorized user (operator)."""
    return User(user_id="user_003", username="operator_bob", role=UserRole.OPERATOR)


@pytest.fixture
def review_system():
    """Create a review system with temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield DecisionReviewSystem(override_log_directory=temp_dir)


# ============================================================================
# Test Override Workflow
# ============================================================================

def test_override_workflow_complete(sample_decision, authorized_user):
    """
    Test complete override workflow from review to logging.
    
    **Validates: Requirements 20.1, 20.2, 20.3, 20.4, 20.5**
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        # Step 1: Create review interface
        review_interface = review_system.create_review_interface(sample_decision)
        
        assert isinstance(review_interface, ReviewInterface)
        assert review_interface.decision == sample_decision
        assert len(review_interface.video_clips) == 2  # Two video references
        assert review_interface.system_reasoning == sample_decision.reasoning
        assert "overall" in review_interface.confidence_breakdown
        
        # Step 2: Override the decision
        override = review_system.override_decision(
            decision=sample_decision,
            override_decision_type="legal",
            justification="Ball was within reach of batsman, not a wide",
            user=authorized_user,
            override_confidence=0.95,
        )
        
        assert isinstance(override, DecisionOverride)
        assert override.original_decision == sample_decision
        assert override.override_decision_type == "legal"
        assert override.override_confidence == 0.95
        assert override.user == authorized_user
        
        # Step 3: Verify override was logged
        override_log_path = Path(temp_dir) / "overrides.jsonl"
        assert override_log_path.exists()
        
        with open(override_log_path, 'r') as f:
            log_entry = json.loads(f.readline())
        
        assert log_entry["system_decision"]["event_type"] == "wide"
        assert log_entry["manual_override"]["decision_type"] == "legal"
        assert log_entry["manual_override"]["justification"] == "Ball was within reach of batsman, not a wide"
        
        # Step 4: Verify feedback was collected
        feedback_log_path = Path(temp_dir) / "feedback.jsonl"
        assert feedback_log_path.exists()
        
        with open(feedback_log_path, 'r') as f:
            feedback_entry = json.loads(f.readline())
        
        assert feedback_entry["original_decision"]["event_type"] == "wide"
        assert feedback_entry["correct_decision"]["event_type"] == "legal"


def test_override_with_admin_user(sample_decision, admin_user):
    """Test that admin users can override decisions."""
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        override = review_system.override_decision(
            decision=sample_decision,
            override_decision_type="no_ball",
            justification="Bowler overstepped",
            user=admin_user,
        )
        
        assert override.user.role == UserRole.ADMIN
        assert override.override_decision_type == "no_ball"


def test_override_with_custom_confidence(sample_decision, authorized_user):
    """Test override with custom confidence value."""
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        override = review_system.override_decision(
            decision=sample_decision,
            override_decision_type="legal",
            justification="Marginal call, but legal",
            user=authorized_user,
            override_confidence=0.85,
        )
        
        assert override.override_confidence == 0.85


# ============================================================================
# Test Authorization Logic
# ============================================================================

def test_unauthorized_user_cannot_override(sample_decision, unauthorized_user):
    """
    Test that unauthorized users (operators) cannot override decisions.
    
    **Validates: Requirement 20.2 (authorization)**
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        with pytest.raises(PermissionError) as exc_info:
            review_system.override_decision(
                decision=sample_decision,
                override_decision_type="legal",
                justification="Should not be allowed",
                user=unauthorized_user,
            )
        
        assert "not authorized" in str(exc_info.value).lower()
        assert unauthorized_user.username in str(exc_info.value)


def test_user_authorization_check():
    """Test User.is_authorized_to_override method."""
    umpire = User(user_id="u1", username="umpire", role=UserRole.UMPIRE)
    admin = User(user_id="u2", username="admin", role=UserRole.ADMIN)
    operator = User(user_id="u3", username="operator", role=UserRole.OPERATOR)
    
    assert umpire.is_authorized_to_override() is True
    assert admin.is_authorized_to_override() is True
    assert operator.is_authorized_to_override() is False


# ============================================================================
# Test Feedback Collection
# ============================================================================

def test_feedback_collection_includes_trajectory_data(sample_decision, authorized_user):
    """
    Test that feedback includes trajectory data for model improvement.
    
    **Validates: Requirement 20.5**
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        review_system.override_decision(
            decision=sample_decision,
            override_decision_type="legal",
            justification="Test feedback",
            user=authorized_user,
        )
        
        feedback_data = review_system.get_feedback_data()
        assert len(feedback_data) == 1
        
        feedback = feedback_data[0]
        assert "trajectory_data" in feedback
        assert "start_position" in feedback["trajectory_data"]
        assert feedback["trajectory_data"]["speed_max"] == 15.0
        assert feedback["trajectory_data"]["speed_avg"] == 12.0


def test_feedback_collection_includes_detection_data(sample_decision, authorized_user):
    """Test that feedback includes detection data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        review_system.override_decision(
            decision=sample_decision,
            override_decision_type="legal",
            justification="Test feedback",
            user=authorized_user,
        )
        
        feedback_data = review_system.get_feedback_data()
        feedback = feedback_data[0]
        
        assert "detections" in feedback
        # Empty in this test, but field should exist


def test_feedback_export_for_training(sample_decision, authorized_user):
    """Test exporting feedback data for model training."""
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        # Create multiple overrides
        for i in range(3):
            review_system.override_decision(
                decision=sample_decision,
                override_decision_type="legal",
                justification=f"Test feedback {i}",
                user=authorized_user,
            )
        
        # Export feedback
        export_path = Path(temp_dir) / "exported_feedback.json"
        result_path = review_system.export_feedback_for_training(str(export_path))
        
        assert Path(result_path).exists()
        
        with open(result_path, 'r') as f:
            exported_data = json.load(f)
        
        assert len(exported_data) == 3
        assert all("original_decision" in entry for entry in exported_data)
        assert all("correct_decision" in entry for entry in exported_data)


# ============================================================================
# Test Review Interface
# ============================================================================

def test_review_interface_creation(sample_decision):
    """
    Test creating review interface with decision and video.
    
    **Validates: Requirement 20.1**
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        review_interface = review_system.create_review_interface(sample_decision)
        
        assert review_interface.decision == sample_decision
        assert len(review_interface.video_clips) == 2
        assert review_interface.system_reasoning == sample_decision.reasoning
        
        # Check video clips have required fields
        for clip in review_interface.video_clips:
            assert "camera_id" in clip
            assert "frame_number" in clip
            assert "timestamp" in clip
            assert "clip_duration" in clip


def test_review_interface_confidence_breakdown(sample_decision):
    """Test that review interface includes confidence breakdown."""
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        review_interface = review_system.create_review_interface(sample_decision)
        
        assert "overall" in review_interface.confidence_breakdown
        assert "detection_quality" in review_interface.confidence_breakdown
        assert "trajectory_quality" in review_interface.confidence_breakdown
        
        assert review_interface.confidence_breakdown["overall"] == sample_decision.confidence


def test_review_interface_with_custom_video_clips(sample_decision):
    """Test creating review interface with custom video clips."""
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        custom_clips = [
            {"camera_id": "cam3", "frame_number": 2000, "timestamp": time.time(), "clip_duration": 10.0}
        ]
        
        review_interface = review_system.create_review_interface(
            sample_decision,
            video_clips=custom_clips
        )
        
        assert len(review_interface.video_clips) == 1
        assert review_interface.video_clips[0]["camera_id"] == "cam3"


# ============================================================================
# Test Override History and Querying
# ============================================================================

def test_get_override_history(sample_decision, authorized_user):
    """Test querying override history."""
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        # Create multiple overrides
        for i in range(3):
            review_system.override_decision(
                decision=sample_decision,
                override_decision_type="legal",
                justification=f"Override {i}",
                user=authorized_user,
            )
        
        # Query all overrides
        history = review_system.get_override_history()
        assert len(history) == 3


def test_get_override_history_with_time_filter(sample_decision, authorized_user):
    """Test querying override history with time range filter."""
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        start_time = time.time()
        
        # Create override
        review_system.override_decision(
            decision=sample_decision,
            override_decision_type="legal",
            justification="Test",
            user=authorized_user,
        )
        
        time.sleep(0.1)
        mid_time = time.time()
        time.sleep(0.1)
        
        # Create another override
        review_system.override_decision(
            decision=sample_decision,
            override_decision_type="no_ball",
            justification="Test 2",
            user=authorized_user,
        )
        
        end_time = time.time()
        
        # Query with time filter
        history_all = review_system.get_override_history(start_timestamp=start_time, end_timestamp=end_time)
        assert len(history_all) == 2
        
        history_first = review_system.get_override_history(start_timestamp=start_time, end_timestamp=mid_time)
        assert len(history_first) == 1


def test_get_override_history_with_user_filter(sample_decision, authorized_user, admin_user):
    """Test querying override history filtered by user."""
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        # Create overrides from different users
        review_system.override_decision(
            decision=sample_decision,
            override_decision_type="legal",
            justification="Umpire override",
            user=authorized_user,
        )
        
        review_system.override_decision(
            decision=sample_decision,
            override_decision_type="no_ball",
            justification="Admin override",
            user=admin_user,
        )
        
        # Query by user
        umpire_history = review_system.get_override_history(user_id=authorized_user.user_id)
        assert len(umpire_history) == 1
        assert umpire_history[0]["user_id"] == authorized_user.user_id
        
        admin_history = review_system.get_override_history(user_id=admin_user.user_id)
        assert len(admin_history) == 1
        assert admin_history[0]["user_id"] == admin_user.user_id


# ============================================================================
# Test Statistics
# ============================================================================

def test_get_override_statistics(sample_decision, authorized_user, admin_user):
    """Test getting override statistics."""
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        # Create overrides
        review_system.override_decision(
            decision=sample_decision,
            override_decision_type="legal",
            justification="Test 1",
            user=authorized_user,
        )
        
        review_system.override_decision(
            decision=sample_decision,
            override_decision_type="legal",
            justification="Test 2",
            user=authorized_user,
        )
        
        review_system.override_decision(
            decision=sample_decision,
            override_decision_type="no_ball",
            justification="Test 3",
            user=admin_user,
        )
        
        stats = review_system.get_override_statistics()
        
        assert stats["total_overrides"] == 3
        assert stats["overrides_by_user"][authorized_user.username] == 2
        assert stats["overrides_by_user"][admin_user.username] == 1
        assert stats["overrides_by_decision_type"]["wide"] == 3  # All original decisions were WIDE
        assert stats["average_system_confidence"] == 0.75  # All had 0.75 confidence


def test_get_override_statistics_empty():
    """Test statistics with no overrides."""
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        stats = review_system.get_override_statistics()
        
        assert stats["total_overrides"] == 0
        assert stats["overrides_by_user"] == {}
        assert stats["overrides_by_decision_type"] == {}
        assert stats["average_system_confidence"] == 0.0


# ============================================================================
# Test Edge Cases
# ============================================================================

def test_override_with_empty_justification_fails(sample_decision, authorized_user):
    """Test that override with empty justification is rejected."""
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        with pytest.raises(ValueError) as exc_info:
            review_system.override_decision(
                decision=sample_decision,
                override_decision_type="legal",
                justification="",  # Empty justification
                user=authorized_user,
            )
        
        assert "justification" in str(exc_info.value).lower()


def test_override_with_invalid_confidence_fails(sample_decision, authorized_user):
    """Test that override with invalid confidence is rejected."""
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        with pytest.raises(ValueError):
            review_system.override_decision(
                decision=sample_decision,
                override_decision_type="legal",
                justification="Test",
                user=authorized_user,
                override_confidence=1.5,  # Invalid: > 1.0
            )
        
        with pytest.raises(ValueError):
            review_system.override_decision(
                decision=sample_decision,
                override_decision_type="legal",
                justification="Test",
                user=authorized_user,
                override_confidence=-0.1,  # Invalid: < 0.0
            )


def test_override_with_empty_decision_type_fails(sample_decision, authorized_user):
    """Test that override with empty decision type is rejected."""
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        with pytest.raises(ValueError) as exc_info:
            review_system.override_decision(
                decision=sample_decision,
                override_decision_type="",  # Empty decision type
                justification="Test",
                user=authorized_user,
            )
        
        assert "override_decision_type" in str(exc_info.value).lower()


def test_review_interface_with_invalid_decision_fails():
    """Test that creating review interface with invalid decision fails."""
    with tempfile.TemporaryDirectory() as temp_dir:
        review_system = DecisionReviewSystem(override_log_directory=temp_dir)
        
        with pytest.raises(TypeError):
            review_system.create_review_interface(decision="not a decision")


# ============================================================================
# Test Data Validation
# ============================================================================

def test_user_validation():
    """Test User data validation."""
    # Valid user
    user = User(user_id="u1", username="test", role=UserRole.UMPIRE)
    assert user.user_id == "u1"
    
    # Invalid user_id
    with pytest.raises(ValueError):
        User(user_id="", username="test", role=UserRole.UMPIRE)
    
    # Invalid username
    with pytest.raises(ValueError):
        User(user_id="u1", username="", role=UserRole.UMPIRE)
    
    # Invalid role
    with pytest.raises(TypeError):
        User(user_id="u1", username="test", role="invalid")


def test_decision_override_validation(sample_decision, authorized_user):
    """Test DecisionOverride data validation."""
    # Valid override
    override = DecisionOverride(
        override_id="ov1",
        original_decision=sample_decision,
        override_decision_type="legal",
        override_confidence=0.9,
        justification="Test",
        user=authorized_user,
        timestamp=time.time(),
        video_references=[],
    )
    assert override.override_id == "ov1"
    
    # Invalid confidence
    with pytest.raises(ValueError):
        DecisionOverride(
            override_id="ov1",
            original_decision=sample_decision,
            override_decision_type="legal",
            override_confidence=1.5,
            justification="Test",
            user=authorized_user,
            timestamp=time.time(),
            video_references=[],
        )
