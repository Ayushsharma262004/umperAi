"""
Legal Delivery Counter for the UmpirAI system.

This module provides the LegalDeliveryCounter class which tracks legal deliveries
and detects over completion based on cricket rules.
"""

from typing import Optional
from dataclasses import dataclass

from umpirai.models.data_models import (
    Decision,
    EventType,
    Trajectory,
    VideoReference,
)


@dataclass
class MatchState:
    """Current match state for legal delivery tracking."""
    over_number: int
    ball_number: int  # within over (1-6)
    legal_deliveries: int  # count in current over
    total_deliveries: int  # total deliveries bowled (including extras)
    
    def __post_init__(self):
        """Validate match state."""
        if not isinstance(self.over_number, int) or self.over_number < 0:
            raise ValueError("over_number must be a non-negative integer")
        if not isinstance(self.ball_number, int) or not (0 <= self.ball_number <= 6):
            raise ValueError("ball_number must be in range [0, 6]")
        if not isinstance(self.legal_deliveries, int) or not (0 <= self.legal_deliveries <= 6):
            raise ValueError("legal_deliveries must be in range [0, 6]")
        if not isinstance(self.total_deliveries, int) or self.total_deliveries < 0:
            raise ValueError("total_deliveries must be a non-negative integer")
    
    def is_over_complete(self) -> bool:
        """Check if current over is complete."""
        return self.legal_deliveries >= 6


class LegalDeliveryCounter:
    """
    Tracks legal deliveries and detects over completion.
    
    Logic:
    1. For each delivery, check: NOT wide AND NOT no ball
    2. If legal: increment counter
    3. If counter reaches 6: signal OVER_COMPLETE
    4. Reset counter after over completion
    5. Track match state
    
    A legal delivery is one that is not classified as a wide ball or no ball.
    Wide balls and no balls are extras that do not count toward the over.
    """
    
    # Number of legal deliveries per over
    DELIVERIES_PER_OVER = 6
    
    def __init__(self, starting_over: int = 0):
        """
        Initialize legal delivery counter.
        
        Args:
            starting_over: Starting over number (default: 0)
        """
        if not isinstance(starting_over, int) or starting_over < 0:
            raise ValueError("starting_over must be a non-negative integer")
        
        self._match_state = MatchState(
            over_number=starting_over,
            ball_number=0,
            legal_deliveries=0,
            total_deliveries=0
        )
        
        # Track last decision for over completion detection
        self._last_decision: Optional[Decision] = None
    
    def process_delivery(self, decision: Decision) -> Optional[Decision]:
        """
        Process a delivery decision and update match state.
        
        Args:
            decision: Delivery decision (wide, no ball, legal, dismissal, etc.)
            
        Returns:
            Decision object with OVER_COMPLETE event if over is complete, None otherwise
        """
        if not isinstance(decision, EventType):
            # If decision is a Decision object, extract event_type
            if hasattr(decision, 'event_type'):
                event_type = decision.event_type
            else:
                raise TypeError("decision must be a Decision object or EventType")
        else:
            event_type = decision
        
        # Store decision
        self._last_decision = decision if hasattr(decision, 'event_type') else None
        
        # Increment total deliveries
        self._match_state.total_deliveries += 1
        
        # Check if delivery is legal
        is_legal = self.is_legal_delivery(event_type)
        
        if is_legal:
            # Increment legal delivery counter
            self._match_state.legal_deliveries += 1
            self._match_state.ball_number += 1
            
            # Check for over completion
            if self._match_state.legal_deliveries >= self.DELIVERIES_PER_OVER:
                # Over complete - create decision
                over_complete_decision = self._create_over_complete_decision(decision)
                
                # Reset counter for next over
                self.reset_counter()
                
                return over_complete_decision
        
        return None
    
    def is_legal_delivery(self, event_type: EventType) -> bool:
        """
        Check if a delivery is legal (not wide and not no ball).
        
        A legal delivery is one that:
        - Is NOT classified as WIDE
        - Is NOT classified as NO_BALL
        
        All other event types (LEGAL, BOWLED, CAUGHT, LBW) count as legal deliveries.
        
        Args:
            event_type: Event type of the delivery
            
        Returns:
            True if legal delivery, False otherwise
        """
        if not isinstance(event_type, EventType):
            raise TypeError("event_type must be an EventType enum")
        
        # Legal delivery is NOT wide AND NOT no ball
        return event_type not in (EventType.WIDE, EventType.NO_BALL)
    
    def get_match_state(self) -> MatchState:
        """
        Get current match state.
        
        Returns:
            Current match state
        """
        return self._match_state
    
    def reset_counter(self) -> None:
        """
        Reset legal delivery counter after over completion.
        
        This increments the over number and resets the ball number and
        legal deliveries count to zero.
        """
        self._match_state.over_number += 1
        self._match_state.ball_number = 0
        self._match_state.legal_deliveries = 0
    
    def _create_over_complete_decision(self, last_delivery: Decision) -> Decision:
        """
        Create an OVER_COMPLETE decision.
        
        Args:
            last_delivery: The last legal delivery that completed the over
            
        Returns:
            Decision object with OVER_COMPLETE event type
        """
        # Extract information from last delivery
        if hasattr(last_delivery, 'timestamp'):
            timestamp = last_delivery.timestamp
        else:
            timestamp = 0.0
        
        if hasattr(last_delivery, 'trajectory'):
            trajectory = last_delivery.trajectory
        else:
            # Create empty trajectory
            from umpirai.models.data_models import Position3D
            trajectory = Trajectory(
                positions=[],
                timestamps=[],
                velocities=[],
                start_position=Position3D(x=0.0, y=0.0, z=0.0)
            )
        
        if hasattr(last_delivery, 'detections'):
            detections = last_delivery.detections
        else:
            detections = []
        
        if hasattr(last_delivery, 'video_references'):
            video_references = last_delivery.video_references
        else:
            video_references = [
                VideoReference(
                    camera_id="cam1",
                    frame_number=int(timestamp * 30),
                    timestamp=timestamp
                )
            ]
        
        # Create decision ID
        decision_id = f"over_complete_{self._match_state.over_number}_{int(timestamp * 1000)}"
        
        # Create reasoning
        reasoning = (
            f"Over {self._match_state.over_number} complete: "
            f"{self.DELIVERIES_PER_OVER} legal deliveries bowled. "
            f"Total deliveries in over: {self._match_state.total_deliveries}."
        )
        
        return Decision(
            decision_id=decision_id,
            event_type=EventType.OVER_COMPLETE,
            confidence=1.0,  # Over completion is deterministic
            timestamp=timestamp,
            trajectory=trajectory,
            detections=detections,
            reasoning=reasoning,
            video_references=video_references,
            requires_review=False
        )
