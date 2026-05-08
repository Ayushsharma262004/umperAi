"""
Unit tests for LegalDeliveryCounter.

These tests validate specific examples and edge cases for legal delivery
classification, counting, over completion, and counter reset.
"""

import pytest
from umpirai.decision.legal_delivery_counter import LegalDeliveryCounter, MatchState
from umpirai.models.data_models import (
    Decision,
    EventType,
    Trajectory,
    Position3D,
    Vector3D,
    VideoReference,
)


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_decision(event_type: EventType, timestamp: float = 0.0) -> Decision:
    """Create a test decision with minimal required fields."""
    return Decision(
        decision_id=f"test_{event_type.value}_{int(timestamp * 1000)}",
        event_type=event_type,
        confidence=0.95,
        timestamp=timestamp,
        trajectory=Trajectory(
            positions=[Position3D(x=0.0, y=1.0, z=-10.0)],
            timestamps=[timestamp],
            velocities=[Vector3D(vx=0.0, vy=0.0, vz=20.0)],
            start_position=Position3D(x=0.0, y=1.0, z=-10.0)
        ),
        detections=[],
        reasoning=f"Test {event_type.value} decision",
        video_references=[
            VideoReference(
                camera_id="cam1",
                frame_number=int(timestamp * 30),
                timestamp=timestamp
            )
        ],
        requires_review=False
    )


# ============================================================================
# Initialization Tests
# ============================================================================

def test_initialization_default():
    """Test default initialization."""
    counter = LegalDeliveryCounter()
    match_state = counter.get_match_state()
    
    assert match_state.over_number == 0
    assert match_state.ball_number == 0
    assert match_state.legal_deliveries == 0
    assert match_state.total_deliveries == 0


def test_initialization_with_starting_over():
    """Test initialization with custom starting over."""
    counter = LegalDeliveryCounter(starting_over=5)
    match_state = counter.get_match_state()
    
    assert match_state.over_number == 5
    assert match_state.ball_number == 0
    assert match_state.legal_deliveries == 0
    assert match_state.total_deliveries == 0


def test_initialization_invalid_starting_over():
    """Test initialization with invalid starting over."""
    with pytest.raises(ValueError, match="starting_over must be a non-negative integer"):
        LegalDeliveryCounter(starting_over=-1)


# ============================================================================
# Legal Delivery Classification Tests
# ============================================================================

def test_is_legal_delivery_legal():
    """Test legal delivery classification for LEGAL event."""
    counter = LegalDeliveryCounter()
    assert counter.is_legal_delivery(EventType.LEGAL) is True


def test_is_legal_delivery_wide():
    """Test legal delivery classification for WIDE event."""
    counter = LegalDeliveryCounter()
    assert counter.is_legal_delivery(EventType.WIDE) is False


def test_is_legal_delivery_no_ball():
    """Test legal delivery classification for NO_BALL event."""
    counter = LegalDeliveryCounter()
    assert counter.is_legal_delivery(EventType.NO_BALL) is False


def test_is_legal_delivery_bowled():
    """Test legal delivery classification for BOWLED event."""
    counter = LegalDeliveryCounter()
    assert counter.is_legal_delivery(EventType.BOWLED) is True


def test_is_legal_delivery_caught():
    """Test legal delivery classification for CAUGHT event."""
    counter = LegalDeliveryCounter()
    assert counter.is_legal_delivery(EventType.CAUGHT) is True


def test_is_legal_delivery_lbw():
    """Test legal delivery classification for LBW event."""
    counter = LegalDeliveryCounter()
    assert counter.is_legal_delivery(EventType.LBW) is True


def test_is_legal_delivery_over_complete():
    """Test legal delivery classification for OVER_COMPLETE event."""
    counter = LegalDeliveryCounter()
    # OVER_COMPLETE is not a delivery type, but should be treated as legal
    assert counter.is_legal_delivery(EventType.OVER_COMPLETE) is True


def test_is_legal_delivery_invalid_type():
    """Test legal delivery classification with invalid type."""
    counter = LegalDeliveryCounter()
    with pytest.raises(TypeError, match="event_type must be an EventType enum"):
        counter.is_legal_delivery("invalid")


# ============================================================================
# Counter State Transition Tests
# ============================================================================

def test_process_single_legal_delivery():
    """Test processing a single legal delivery."""
    counter = LegalDeliveryCounter()
    decision = create_test_decision(EventType.LEGAL, timestamp=1.0)
    
    result = counter.process_delivery(decision)
    
    # Should not complete over
    assert result is None
    
    # Check state
    match_state = counter.get_match_state()
    assert match_state.legal_deliveries == 1
    assert match_state.ball_number == 1
    assert match_state.total_deliveries == 1
    assert match_state.over_number == 0


def test_process_single_wide():
    """Test processing a single wide delivery."""
    counter = LegalDeliveryCounter()
    decision = create_test_decision(EventType.WIDE, timestamp=1.0)
    
    result = counter.process_delivery(decision)
    
    # Should not complete over
    assert result is None
    
    # Check state - wide doesn't count as legal
    match_state = counter.get_match_state()
    assert match_state.legal_deliveries == 0
    assert match_state.ball_number == 0
    assert match_state.total_deliveries == 1  # Total still increments
    assert match_state.over_number == 0


def test_process_single_no_ball():
    """Test processing a single no ball delivery."""
    counter = LegalDeliveryCounter()
    decision = create_test_decision(EventType.NO_BALL, timestamp=1.0)
    
    result = counter.process_delivery(decision)
    
    # Should not complete over
    assert result is None
    
    # Check state - no ball doesn't count as legal
    match_state = counter.get_match_state()
    assert match_state.legal_deliveries == 0
    assert match_state.ball_number == 0
    assert match_state.total_deliveries == 1  # Total still increments
    assert match_state.over_number == 0


def test_process_dismissal_as_legal():
    """Test that dismissals count as legal deliveries."""
    counter = LegalDeliveryCounter()
    
    # Test bowled dismissal
    decision = create_test_decision(EventType.BOWLED, timestamp=1.0)
    result = counter.process_delivery(decision)
    
    assert result is None
    match_state = counter.get_match_state()
    assert match_state.legal_deliveries == 1
    assert match_state.ball_number == 1


# ============================================================================
# Over Completion Tests
# ============================================================================

def test_over_completion_exactly_six_legal():
    """Test over completion with exactly 6 legal deliveries."""
    counter = LegalDeliveryCounter()
    
    # Process 6 legal deliveries
    for i in range(6):
        decision = create_test_decision(EventType.LEGAL, timestamp=float(i))
        result = counter.process_delivery(decision)
        
        if i < 5:
            # First 5 deliveries should not complete over
            assert result is None
        else:
            # 6th delivery should complete over
            assert result is not None
            assert result.event_type == EventType.OVER_COMPLETE
            assert result.confidence == 1.0
            assert "Over 0 complete" in result.reasoning
            assert "6 legal deliveries" in result.reasoning


def test_over_completion_with_extras():
    """Test over completion with extras (wides and no balls)."""
    counter = LegalDeliveryCounter()
    
    # Sequence: L, W, L, NB, L, L, W, L, L (6 legal, 3 extras)
    sequence = [
        EventType.LEGAL,
        EventType.WIDE,
        EventType.LEGAL,
        EventType.NO_BALL,
        EventType.LEGAL,
        EventType.LEGAL,
        EventType.WIDE,
        EventType.LEGAL,
        EventType.LEGAL,
    ]
    
    over_complete = False
    for i, event_type in enumerate(sequence):
        decision = create_test_decision(event_type, timestamp=float(i))
        result = counter.process_delivery(decision)
        
        if result is not None and result.event_type == EventType.OVER_COMPLETE:
            over_complete = True
            # Should happen on the 6th legal delivery (index 8)
            assert i == 8
            
            # Check reasoning includes total deliveries
            assert "Total deliveries in over: 9" in result.reasoning
            break
    
    assert over_complete


def test_over_completion_with_dismissals():
    """Test over completion with dismissals counting as legal."""
    counter = LegalDeliveryCounter()
    
    # Sequence: L, L, BOWLED, L, CAUGHT, L (6 legal including dismissals)
    sequence = [
        EventType.LEGAL,
        EventType.LEGAL,
        EventType.BOWLED,
        EventType.LEGAL,
        EventType.CAUGHT,
        EventType.LEGAL,
    ]
    
    over_complete = False
    for i, event_type in enumerate(sequence):
        decision = create_test_decision(event_type, timestamp=float(i))
        result = counter.process_delivery(decision)
        
        if result is not None and result.event_type == EventType.OVER_COMPLETE:
            over_complete = True
            assert i == 5  # 6th legal delivery
            break
    
    assert over_complete


# ============================================================================
# Counter Reset Tests
# ============================================================================

def test_counter_reset_after_over():
    """Test counter reset after over completion."""
    counter = LegalDeliveryCounter()
    
    # Complete first over
    for i in range(6):
        decision = create_test_decision(EventType.LEGAL, timestamp=float(i))
        counter.process_delivery(decision)
    
    # Check state after reset
    match_state = counter.get_match_state()
    assert match_state.legal_deliveries == 0
    assert match_state.ball_number == 0
    assert match_state.over_number == 1
    
    # Process another delivery in new over
    decision = create_test_decision(EventType.LEGAL, timestamp=10.0)
    result = counter.process_delivery(decision)
    
    assert result is None  # Should not complete over
    match_state = counter.get_match_state()
    assert match_state.legal_deliveries == 1
    assert match_state.ball_number == 1
    assert match_state.over_number == 1


def test_multiple_overs():
    """Test multiple consecutive overs."""
    counter = LegalDeliveryCounter()
    
    # Complete 3 overs
    for over in range(3):
        for ball in range(6):
            decision = create_test_decision(EventType.LEGAL, timestamp=float(over * 10 + ball))
            result = counter.process_delivery(decision)
            
            if ball == 5:
                # Last ball of over
                assert result is not None
                assert result.event_type == EventType.OVER_COMPLETE
                assert f"Over {over} complete" in result.reasoning
            else:
                assert result is None
        
        # Check state after each over
        match_state = counter.get_match_state()
        assert match_state.over_number == over + 1
        assert match_state.legal_deliveries == 0
        assert match_state.ball_number == 0


def test_manual_reset():
    """Test manual counter reset."""
    counter = LegalDeliveryCounter()
    
    # Process some deliveries
    for i in range(3):
        decision = create_test_decision(EventType.LEGAL, timestamp=float(i))
        counter.process_delivery(decision)
    
    # Check state before reset
    match_state = counter.get_match_state()
    assert match_state.legal_deliveries == 3
    assert match_state.over_number == 0
    
    # Manual reset
    counter.reset_counter()
    
    # Check state after reset
    match_state = counter.get_match_state()
    assert match_state.legal_deliveries == 0
    assert match_state.ball_number == 0
    assert match_state.over_number == 1


# ============================================================================
# Edge Cases
# ============================================================================

def test_empty_over_with_only_extras():
    """Test over with only extras (no legal deliveries)."""
    counter = LegalDeliveryCounter()
    
    # Process 10 extras
    for i in range(10):
        event_type = EventType.WIDE if i % 2 == 0 else EventType.NO_BALL
        decision = create_test_decision(event_type, timestamp=float(i))
        result = counter.process_delivery(decision)
        
        # Should never complete over
        assert result is None
    
    # Check state
    match_state = counter.get_match_state()
    assert match_state.legal_deliveries == 0
    assert match_state.ball_number == 0
    assert match_state.total_deliveries == 10
    assert match_state.over_number == 0


def test_over_completion_decision_fields():
    """Test that over completion decision has correct fields."""
    counter = LegalDeliveryCounter()
    
    # Complete an over
    for i in range(6):
        decision = create_test_decision(EventType.LEGAL, timestamp=float(i))
        result = counter.process_delivery(decision)
    
    # Check over completion decision
    assert result is not None
    assert result.event_type == EventType.OVER_COMPLETE
    assert result.confidence == 1.0
    assert result.requires_review is False
    assert result.decision_id.startswith("over_complete_0_")
    assert len(result.video_references) > 0
    assert result.trajectory is not None
    assert isinstance(result.detections, list)


def test_match_state_validation():
    """Test MatchState validation."""
    # Valid state
    state = MatchState(
        over_number=5,
        ball_number=3,
        legal_deliveries=3,
        total_deliveries=5
    )
    assert state.over_number == 5
    
    # Invalid over_number
    with pytest.raises(ValueError, match="over_number must be a non-negative integer"):
        MatchState(over_number=-1, ball_number=0, legal_deliveries=0, total_deliveries=0)
    
    # Invalid ball_number
    with pytest.raises(ValueError, match="ball_number must be in range"):
        MatchState(over_number=0, ball_number=7, legal_deliveries=0, total_deliveries=0)
    
    # Invalid legal_deliveries
    with pytest.raises(ValueError, match="legal_deliveries must be in range"):
        MatchState(over_number=0, ball_number=0, legal_deliveries=7, total_deliveries=0)
    
    # Invalid total_deliveries
    with pytest.raises(ValueError, match="total_deliveries must be a non-negative integer"):
        MatchState(over_number=0, ball_number=0, legal_deliveries=0, total_deliveries=-1)


def test_is_over_complete_method():
    """Test MatchState.is_over_complete() method."""
    # Not complete
    state = MatchState(over_number=0, ball_number=3, legal_deliveries=3, total_deliveries=3)
    assert state.is_over_complete() is False
    
    # Complete (exactly 6)
    state = MatchState(over_number=0, ball_number=6, legal_deliveries=6, total_deliveries=6)
    assert state.is_over_complete() is True
    
    # After reset
    state = MatchState(over_number=1, ball_number=0, legal_deliveries=0, total_deliveries=10)
    assert state.is_over_complete() is False
