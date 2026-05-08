"""
Property-based tests for LegalDeliveryCounter.

These tests validate the correctness properties related to legal delivery
classification, counting, over completion, and counter reset.
"""

import pytest
from hypothesis import given, strategies as st, assume
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
# Hypothesis Strategies
# ============================================================================

@st.composite
def event_type_strategy(draw):
    """Generate random event types."""
    return draw(st.sampled_from(list(EventType)))


@st.composite
def decision_strategy(draw, event_type=None):
    """Generate random Decision objects."""
    if event_type is None:
        event_type = draw(event_type_strategy())
    
    timestamp = draw(st.floats(min_value=0.0, max_value=1000.0))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0))
    
    # Create minimal trajectory
    trajectory = Trajectory(
        positions=[Position3D(x=0.0, y=1.0, z=-10.0)],
        timestamps=[timestamp],
        velocities=[Vector3D(vx=0.0, vy=0.0, vz=20.0)],
        start_position=Position3D(x=0.0, y=1.0, z=-10.0)
    )
    
    decision_id = f"test_{event_type.value}_{int(timestamp * 1000)}"
    
    return Decision(
        decision_id=decision_id,
        event_type=event_type,
        confidence=confidence,
        timestamp=timestamp,
        trajectory=trajectory,
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


@st.composite
def delivery_sequence_strategy(draw, min_length=1, max_length=20):
    """Generate a sequence of delivery decisions."""
    length = draw(st.integers(min_value=min_length, max_value=max_length))
    return [draw(decision_strategy()) for _ in range(length)]


# ============================================================================
# Property 17: Legal Delivery Classification
# ============================================================================

@given(event_type=event_type_strategy())
def test_property_17_legal_delivery_classification(event_type):
    """
    Property 17: Legal Delivery Classification
    
    For any delivery that is not classified as a Wide_Ball and not classified
    as a No_Ball, the Decision Engine SHALL classify it as a Legal_Delivery.
    
    Validates: Requirements 9.1
    """
    counter = LegalDeliveryCounter()
    
    # Check if delivery is legal
    is_legal = counter.is_legal_delivery(event_type)
    
    # Property: Legal delivery is NOT wide AND NOT no ball
    expected_legal = event_type not in (EventType.WIDE, EventType.NO_BALL)
    
    assert is_legal == expected_legal, (
        f"Legal delivery classification failed for {event_type.value}: "
        f"expected {expected_legal}, got {is_legal}"
    )


# ============================================================================
# Property 18: Legal Delivery Counting
# ============================================================================

@given(deliveries=delivery_sequence_strategy(min_length=1, max_length=20))
def test_property_18_legal_delivery_counting(deliveries):
    """
    Property 18: Legal Delivery Counting
    
    For any sequence of deliveries within an over, the Decision Engine SHALL
    maintain an accurate count of Legal_Delivery occurrences.
    
    Validates: Requirements 9.2
    """
    counter = LegalDeliveryCounter()
    
    # Count expected legal deliveries
    expected_legal_count = sum(
        1 for d in deliveries
        if d.event_type not in (EventType.WIDE, EventType.NO_BALL)
    )
    
    # Limit to 6 legal deliveries (one over)
    expected_legal_count = min(expected_legal_count, 6)
    
    # Process deliveries
    legal_count = 0
    for delivery in deliveries:
        result = counter.process_delivery(delivery)
        
        # Count legal deliveries processed
        if counter.is_legal_delivery(delivery.event_type):
            legal_count += 1
        
        # Stop if over complete
        if result is not None and result.event_type == EventType.OVER_COMPLETE:
            break
    
    # Get final match state
    match_state = counter.get_match_state()
    
    # Property: Counter maintains accurate count of legal deliveries
    # If over completed, legal_deliveries should be 0 (reset)
    # Otherwise, should match the count
    if legal_count >= 6:
        # Over completed, counter should be reset
        assert match_state.legal_deliveries == 0, (
            f"Legal delivery count should be reset after over completion, "
            f"but got {match_state.legal_deliveries}"
        )
    else:
        # Over not complete, counter should match
        assert match_state.legal_deliveries == legal_count, (
            f"Legal delivery count mismatch: expected {legal_count}, "
            f"got {match_state.legal_deliveries}"
        )


# ============================================================================
# Property 19: Over Completion Signal
# ============================================================================

@given(
    legal_deliveries=st.integers(min_value=6, max_value=6),
    extra_deliveries=st.integers(min_value=0, max_value=10)
)
def test_property_19_over_completion_signal(legal_deliveries, extra_deliveries):
    """
    Property 19: Over Completion Signal
    
    For any sequence of deliveries where exactly 6 Legal_Delivery events have
    occurred, the Decision Engine SHALL signal Over_Completion.
    
    Validates: Requirements 9.3
    """
    counter = LegalDeliveryCounter()
    
    # Create sequence with exactly 6 legal deliveries plus extras
    deliveries = []
    
    # Add legal deliveries
    for i in range(legal_deliveries):
        deliveries.append(Decision(
            decision_id=f"legal_{i}",
            event_type=EventType.LEGAL,
            confidence=0.95,
            timestamp=float(i),
            trajectory=Trajectory(
                positions=[Position3D(x=0.0, y=1.0, z=-10.0)],
                timestamps=[float(i)],
                velocities=[Vector3D(vx=0.0, vy=0.0, vz=20.0)],
                start_position=Position3D(x=0.0, y=1.0, z=-10.0)
            ),
            detections=[],
            reasoning="Legal delivery",
            video_references=[],
            requires_review=False
        ))
    
    # Add extra deliveries (wides/no balls) before the 6th legal delivery
    for i in range(extra_deliveries):
        # Insert extras at random positions
        insert_pos = min(i, len(deliveries) - 1)
        extra_type = EventType.WIDE if i % 2 == 0 else EventType.NO_BALL
        deliveries.insert(insert_pos, Decision(
            decision_id=f"extra_{i}",
            event_type=extra_type,
            confidence=0.95,
            timestamp=float(i + 100),
            trajectory=Trajectory(
                positions=[Position3D(x=0.0, y=1.0, z=-10.0)],
                timestamps=[float(i + 100)],
                velocities=[Vector3D(vx=0.0, vy=0.0, vz=20.0)],
                start_position=Position3D(x=0.0, y=1.0, z=-10.0)
            ),
            detections=[],
            reasoning="Extra delivery",
            video_references=[],
            requires_review=False
        ))
    
    # Process deliveries
    over_complete_signaled = False
    for delivery in deliveries:
        result = counter.process_delivery(delivery)
        
        if result is not None and result.event_type == EventType.OVER_COMPLETE:
            over_complete_signaled = True
            break
    
    # Property: Over completion SHALL be signaled after exactly 6 legal deliveries
    assert over_complete_signaled, (
        f"Over completion not signaled after {legal_deliveries} legal deliveries"
    )


# ============================================================================
# Property 20: Over Counter Reset
# ============================================================================

@given(starting_over=st.integers(min_value=0, max_value=50))
def test_property_20_over_counter_reset(starting_over):
    """
    Property 20: Over Counter Reset
    
    For any Over_Completion event, the Decision Engine SHALL reset the
    Legal_Delivery count to zero.
    
    Validates: Requirements 9.4
    """
    counter = LegalDeliveryCounter(starting_over=starting_over)
    
    # Create 6 legal deliveries to complete an over
    for i in range(6):
        decision = Decision(
            decision_id=f"legal_{i}",
            event_type=EventType.LEGAL,
            confidence=0.95,
            timestamp=float(i),
            trajectory=Trajectory(
                positions=[Position3D(x=0.0, y=1.0, z=-10.0)],
                timestamps=[float(i)],
                velocities=[Vector3D(vx=0.0, vy=0.0, vz=20.0)],
                start_position=Position3D(x=0.0, y=1.0, z=-10.0)
            ),
            detections=[],
            reasoning="Legal delivery",
            video_references=[],
            requires_review=False
        )
        
        result = counter.process_delivery(decision)
        
        if result is not None and result.event_type == EventType.OVER_COMPLETE:
            # Over complete - check counter reset
            match_state = counter.get_match_state()
            
            # Property: Legal delivery count SHALL be reset to zero
            assert match_state.legal_deliveries == 0, (
                f"Legal delivery count not reset after over completion: "
                f"expected 0, got {match_state.legal_deliveries}"
            )
            
            # Property: Ball number SHALL be reset to zero
            assert match_state.ball_number == 0, (
                f"Ball number not reset after over completion: "
                f"expected 0, got {match_state.ball_number}"
            )
            
            # Property: Over number SHALL be incremented
            assert match_state.over_number == starting_over + 1, (
                f"Over number not incremented after over completion: "
                f"expected {starting_over + 1}, got {match_state.over_number}"
            )
            
            return
    
    # Should have completed over
    pytest.fail("Over completion not triggered after 6 legal deliveries")


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

def test_legal_delivery_counter_initialization():
    """Test LegalDeliveryCounter initialization."""
    counter = LegalDeliveryCounter()
    match_state = counter.get_match_state()
    
    assert match_state.over_number == 0
    assert match_state.ball_number == 0
    assert match_state.legal_deliveries == 0
    assert match_state.total_deliveries == 0


def test_legal_delivery_counter_with_starting_over():
    """Test LegalDeliveryCounter with custom starting over."""
    counter = LegalDeliveryCounter(starting_over=10)
    match_state = counter.get_match_state()
    
    assert match_state.over_number == 10
    assert match_state.ball_number == 0
    assert match_state.legal_deliveries == 0


def test_legal_delivery_counter_mixed_deliveries():
    """Test counter with mixed legal and extra deliveries."""
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
        decision = Decision(
            decision_id=f"delivery_{i}",
            event_type=event_type,
            confidence=0.95,
            timestamp=float(i),
            trajectory=Trajectory(
                positions=[Position3D(x=0.0, y=1.0, z=-10.0)],
                timestamps=[float(i)],
                velocities=[Vector3D(vx=0.0, vy=0.0, vz=20.0)],
                start_position=Position3D(x=0.0, y=1.0, z=-10.0)
            ),
            detections=[],
            reasoning=f"{event_type.value} delivery",
            video_references=[],
            requires_review=False
        )
        
        result = counter.process_delivery(decision)
        
        if result is not None and result.event_type == EventType.OVER_COMPLETE:
            over_complete = True
            # Should happen after 6th legal delivery (index 8)
            assert i == 8, f"Over complete at wrong index: {i}"
            break
    
    assert over_complete, "Over not completed after 6 legal deliveries"
    
    # Check final state
    match_state = counter.get_match_state()
    assert match_state.legal_deliveries == 0  # Reset
    assert match_state.over_number == 1  # Incremented
    assert match_state.total_deliveries == 9  # All deliveries counted


def test_dismissal_counts_as_legal():
    """Test that dismissals count as legal deliveries."""
    counter = LegalDeliveryCounter()
    
    # Dismissals should count as legal deliveries
    dismissal_types = [EventType.BOWLED, EventType.CAUGHT, EventType.LBW]
    
    for dismissal_type in dismissal_types:
        assert counter.is_legal_delivery(dismissal_type), (
            f"{dismissal_type.value} should count as legal delivery"
        )
