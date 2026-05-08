"""
Decision Engine for the UmpirAI system.

This module provides the DecisionEngine class which integrates all sub-detectors
and coordinates decision-making for cricket match events.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import numpy as np

from umpirai.models.data_models import (
    Detection,
    DetectionResult,
    TrackState,
    Trajectory,
    Decision,
    EventType,
    MatchContext,
)
from umpirai.calibration.calibration_manager import CalibrationData
from umpirai.decision.wide_ball_detector import WideBallDetector
from umpirai.decision.no_ball_detector import NoBallDetector
from umpirai.decision.bowled_detector import BowledDetector
from umpirai.decision.caught_detector import CaughtDetector
from umpirai.decision.lbw_detector import LBWDetector
from umpirai.decision.legal_delivery_counter import LegalDeliveryCounter, MatchState

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class DecisionEngineConfig:
    """Configuration for DecisionEngine."""
    enable_wide_detection: bool = True
    enable_no_ball_detection: bool = True
    enable_bowled_detection: bool = True
    enable_caught_detection: bool = True
    enable_lbw_detection: bool = True
    enable_legal_delivery_counting: bool = True
    
    # Confidence thresholds
    min_confidence_threshold: float = 0.70
    review_threshold: float = 0.80
    
    def __post_init__(self):
        """Validate configuration."""
        if not isinstance(self.min_confidence_threshold, (int, float)):
            raise TypeError("min_confidence_threshold must be numeric")
        if not (0.0 <= self.min_confidence_threshold <= 1.0):
            raise ValueError("min_confidence_threshold must be in range [0.0, 1.0]")
        if not isinstance(self.review_threshold, (int, float)):
            raise TypeError("review_threshold must be numeric")
        if not (0.0 <= self.review_threshold <= 1.0):
            raise ValueError("review_threshold must be in range [0.0, 1.0]")


@dataclass
class ProcessingError:
    """Information about a processing error."""
    error_type: str  # "detector_failure", "insufficient_data", "calibration_missing", "transient_error", "critical_error"
    timestamp: float
    message: str
    component: str  # Which component raised the error
    diagnostic_info: Dict[str, any]
    is_critical: bool = False  # Whether this requires shutdown


class DecisionEngine:
    """
    Main decision engine that integrates all sub-detectors.
    
    The DecisionEngine coordinates all detection components and applies cricket
    rules to classify match events. It implements decision priority logic,
    confidence aggregation, and uncertainty flagging.
    
    Decision Priority (highest to lowest):
    1. Dismissals (BOWLED, CAUGHT, LBW)
    2. No Ball
    3. Wide
    4. Legal Delivery
    5. Over Complete
    
    Confidence Handling:
    - Confidence <80%: Flag for manual review
    - Confidence <70%: Flag as uncertain
    - Aggregate confidence from all relevant detectors
    """
    
    def __init__(
        self,
        calibration: Optional[CalibrationData] = None,
        config: Optional[DecisionEngineConfig] = None
    ):
        """
        Initialize decision engine with all sub-detectors.
        
        Args:
            calibration: Pitch calibration data
            config: Engine configuration
        """
        self.calibration = calibration
        self.config = config or DecisionEngineConfig()
        
        # Initialize sub-detectors
        self.wide_detector = WideBallDetector(calibration=calibration)
        self.no_ball_detector = NoBallDetector(calibration=calibration)
        self.bowled_detector = BowledDetector(calibration=calibration)
        self.caught_detector = CaughtDetector()  # CaughtDetector doesn't take calibration
        self.lbw_detector = LBWDetector(calibration=calibration)
        self.legal_delivery_counter = LegalDeliveryCounter()
        
        # Track last decisions for conflict resolution
        self._last_decisions: List[Decision] = []
        
        # Error tracking
        self.errors: List[ProcessingError] = []
        self.last_error: Optional[ProcessingError] = None
        
        # Match data for critical error preservation
        self.match_data: Dict[str, Any] = {
            "decisions": [],
            "errors": [],
            "match_state": None
        }
    
    def process_frame(
        self,
        detection_result: DetectionResult,
        track_state: TrackState,
        trajectory: Trajectory,
        calibration: Optional[CalibrationData] = None,
        frame_image: Optional[np.ndarray] = None
    ) -> Optional[Decision]:
        """
        Process a frame and generate umpiring decision.
        
        This method coordinates all sub-detectors and applies decision priority
        logic to determine the final decision. Includes error handling to continue
        operation even when individual detectors fail.
        
        Args:
            detection_result: Detection result for current frame
            track_state: Ball tracking state
            trajectory: Ball trajectory
            calibration: Pitch calibration data (optional, uses stored if not provided)
            frame_image: Current frame image for visual analysis (optional)
            
        Returns:
            Decision object if an event is detected, None otherwise
        """
        try:
            # Update calibration if provided
            if calibration:
                self.calibration = calibration
            
            # Use stored calibration if available
            calib = calibration or self.calibration
            if calib is None:
                # Cannot make decisions without calibration
                error = ProcessingError(
                    error_type="calibration_missing",
                    timestamp=detection_result.frame.timestamp,
                    message="No calibration data available for decision making",
                    component="DecisionEngine",
                    diagnostic_info={
                        "frame_number": detection_result.frame.frame_number
                    },
                    is_critical=False
                )
                self._handle_error(error)
                return None
            
            detections = detection_result.detections
            
            # Check for insufficient data
            if not detections or len(detections) == 0:
                error = ProcessingError(
                    error_type="insufficient_data",
                    timestamp=detection_result.frame.timestamp,
                    message="No detections available for decision making",
                    component="DecisionEngine",
                    diagnostic_info={
                        "frame_number": detection_result.frame.frame_number
                    },
                    is_critical=False
                )
                self._handle_error(error)
                # Continue with empty detections - will create uncertain decision
            
            # Run all detectors and collect decisions
            decisions: List[Decision] = []
            
            # Check for dismissals (highest priority)
            if self.config.enable_bowled_detection:
                try:
                    bowled_decision = self.bowled_detector.detect(
                        trajectory, detections, calib, frame_image
                    )
                    if bowled_decision:
                        decisions.append(bowled_decision)
                except Exception as e:
                    self._handle_detector_error("BowledDetector", e, detection_result.frame.timestamp)
            
            if self.config.enable_caught_detection:
                try:
                    caught_decision = self.caught_detector.detect(
                        trajectory, detections
                    )
                    if caught_decision:
                        decisions.append(caught_decision)
                except Exception as e:
                    self._handle_detector_error("CaughtDetector", e, detection_result.frame.timestamp)
            
            if self.config.enable_lbw_detection:
                try:
                    lbw_decision = self.lbw_detector.detect(
                        trajectory, detections, calib
                    )
                    if lbw_decision:
                        decisions.append(lbw_decision)
                except Exception as e:
                    self._handle_detector_error("LBWDetector", e, detection_result.frame.timestamp)
            
            # Check for no ball (second priority)
            if self.config.enable_no_ball_detection:
                try:
                    no_ball_decision = self.no_ball_detector.detect(
                        trajectory, detections, calib
                    )
                    if no_ball_decision:
                        decisions.append(no_ball_decision)
                except Exception as e:
                    self._handle_detector_error("NoBallDetector", e, detection_result.frame.timestamp)
            
            # Check for wide (third priority)
            if self.config.enable_wide_detection:
                try:
                    wide_decision = self.wide_detector.detect(
                        trajectory, detections, calib
                    )
                    if wide_decision:
                        decisions.append(wide_decision)
                except Exception as e:
                    self._handle_detector_error("WideBallDetector", e, detection_result.frame.timestamp)
            
            # Apply decision priority logic
            final_decision = self._apply_decision_priority(decisions)
            
            # If no specific event detected, classify as legal delivery
            if final_decision is None:
                final_decision = self._create_legal_delivery_decision(
                    trajectory, detections, detection_result.frame.timestamp
                )
            
            # Flag decision as uncertain if errors occurred
            if len(self.errors) > 0 and self.errors[-1].timestamp == detection_result.frame.timestamp:
                # Create new decision with requires_review=True
                from dataclasses import replace
                final_decision = replace(
                    final_decision,
                    requires_review=True,
                    reasoning=final_decision.reasoning + " (Decision flagged due to processing errors)"
                )
            
            # Store decision
            self._last_decisions.append(final_decision)
            self.match_data["decisions"].append(final_decision)
            
            # Process through legal delivery counter
            if self.config.enable_legal_delivery_counting:
                try:
                    over_complete_decision = self.legal_delivery_counter.process_delivery(
                        final_decision
                    )
                    if over_complete_decision:
                        # Over complete - return this instead
                        return over_complete_decision
                except Exception as e:
                    self._handle_detector_error("LegalDeliveryCounter", e, detection_result.frame.timestamp)
            
            return final_decision
            
        except Exception as e:
            # Critical error - log and continue
            error = ProcessingError(
                error_type="critical_error",
                timestamp=detection_result.frame.timestamp if detection_result else 0.0,
                message=f"Critical error in process_frame: {str(e)}",
                component="DecisionEngine",
                diagnostic_info={
                    "exception_type": type(e).__name__,
                    "exception_message": str(e)
                },
                is_critical=True
            )
            self._handle_error(error)
            
            # Return None to continue operation
            return None
    
    def classify_delivery(
        self,
        trajectory: Trajectory,
        detections: List[Detection],
        calibration: CalibrationData
    ) -> Decision:
        """
        Classify a delivery based on trajectory and detections.
        
        This is a simplified interface that runs all detectors and returns
        the highest priority decision.
        
        Args:
            trajectory: Ball trajectory
            detections: List of detections
            calibration: Pitch calibration data
            
        Returns:
            Decision object
        """
        # Run all detectors
        decisions: List[Decision] = []
        
        # Dismissals
        if self.config.enable_bowled_detection:
            bowled = self.bowled_detector.detect(trajectory, detections, calibration)
            if bowled:
                decisions.append(bowled)
        
        if self.config.enable_caught_detection:
            caught = self.caught_detector.detect(trajectory, detections)
            if caught:
                decisions.append(caught)
        
        if self.config.enable_lbw_detection:
            lbw = self.lbw_detector.detect(trajectory, detections, calibration)
            if lbw:
                decisions.append(lbw)
        
        # No ball
        if self.config.enable_no_ball_detection:
            no_ball = self.no_ball_detector.detect(trajectory, detections, calibration)
            if no_ball:
                decisions.append(no_ball)
        
        # Wide
        if self.config.enable_wide_detection:
            wide = self.wide_detector.detect(trajectory, detections, calibration)
            if wide:
                decisions.append(wide)
        
        # Apply priority logic
        final_decision = self._apply_decision_priority(decisions)
        
        # If no event detected, classify as legal
        if final_decision is None:
            timestamp = trajectory.timestamps[-1] if trajectory.timestamps else 0.0
            final_decision = self._create_legal_delivery_decision(
                trajectory, detections, timestamp
            )
        
        return final_decision
    
    def get_match_state(self) -> MatchState:
        """
        Get current match state from legal delivery counter.
        
        Returns:
            Current match state
        """
        return self.legal_delivery_counter.get_match_state()
    
    def _apply_decision_priority(self, decisions: List[Decision]) -> Optional[Decision]:
        """
        Apply decision priority logic to select final decision.
        
        Priority order:
        1. Dismissals (BOWLED, CAUGHT, LBW) - highest confidence wins
        2. No Ball
        3. Wide
        4. Legal Delivery
        
        Conflicting rules resolution:
        - If both wide and no ball detected, no ball takes priority
        - If dismissal and no ball detected, both are recorded (dismissal + no ball)
        - If dismissal and wide detected, dismissal takes priority
        
        Args:
            decisions: List of decisions from sub-detectors
            
        Returns:
            Final decision, or None if no decisions
        """
        if not decisions:
            return None
        
        # Separate by priority
        dismissals = [d for d in decisions if d.event_type in (
            EventType.BOWLED, EventType.CAUGHT, EventType.LBW
        )]
        no_balls = [d for d in decisions if d.event_type == EventType.NO_BALL]
        wides = [d for d in decisions if d.event_type == EventType.WIDE]
        
        # Priority 1: Dismissals (select highest confidence)
        if dismissals:
            dismissal = max(dismissals, key=lambda d: d.confidence)
            
            # Check for conflicting no ball
            if no_balls:
                # Dismissal + no ball: Update reasoning to include both
                no_ball = max(no_balls, key=lambda d: d.confidence)
                dismissal.reasoning += (
                    f" Note: No ball also detected (confidence: {no_ball.confidence:.2f}). "
                    f"Dismissal may be invalidated by no ball."
                )
                # Average confidence
                dismissal.confidence = (dismissal.confidence + no_ball.confidence) / 2
                dismissal.requires_review = True
            
            return dismissal
        
        # Priority 2: No Ball
        if no_balls:
            return max(no_balls, key=lambda d: d.confidence)
        
        # Priority 3: Wide
        if wides:
            return max(wides, key=lambda d: d.confidence)
        
        # No priority decision found
        return None
    
    def _create_legal_delivery_decision(
        self,
        trajectory: Trajectory,
        detections: List[Detection],
        timestamp: float
    ) -> Decision:
        """
        Create a legal delivery decision.
        
        Args:
            trajectory: Ball trajectory
            detections: List of detections
            timestamp: Decision timestamp
            
        Returns:
            Decision object for legal delivery
        """
        from umpirai.models.data_models import VideoReference
        
        decision_id = f"legal_{int(timestamp * 1000)}"
        
        # Calculate confidence based on detection quality
        confidence = self._calculate_legal_delivery_confidence(detections)
        
        return Decision(
            decision_id=decision_id,
            event_type=EventType.LEGAL,
            confidence=confidence,
            timestamp=timestamp,
            trajectory=trajectory,
            detections=detections,
            reasoning="Legal delivery: No wide, no ball, or dismissal detected.",
            video_references=[
                VideoReference(
                    camera_id="cam1",
                    frame_number=int(timestamp * 30),
                    timestamp=timestamp
                )
            ],
            requires_review=(confidence < self.config.review_threshold)
        )
    
    def _calculate_legal_delivery_confidence(
        self,
        detections: List[Detection]
    ) -> float:
        """
        Calculate confidence for legal delivery classification.
        
        Args:
            detections: List of detections
            
        Returns:
            Confidence score [0.0, 1.0]
        """
        if not detections:
            return 0.5
        
        # Average confidence of all detections
        confidences = [d.confidence for d in detections]
        return sum(confidences) / len(confidences)
    
    def reset_match_state(self, starting_over: int = 0) -> None:
        """
        Reset match state to start of new match or innings.
        
        Args:
            starting_over: Starting over number
        """
        self.legal_delivery_counter = LegalDeliveryCounter(starting_over=starting_over)
        self._last_decisions = []
    
    def get_last_decisions(self, count: int = 10) -> List[Decision]:
        """
        Get last N decisions made by the engine.
        
        Args:
            count: Number of decisions to retrieve
            
        Returns:
            List of recent decisions
        """
        return self._last_decisions[-count:]
    
    def update_calibration(self, calibration: CalibrationData) -> None:
        """
        Update calibration for all sub-detectors.
        
        Args:
            calibration: New calibration data
        """
        self.calibration = calibration
        self.wide_detector.calibration = calibration
        self.no_ball_detector.calibration = calibration
        self.bowled_detector.calibration = calibration
        # CaughtDetector doesn't use calibration
        self.lbw_detector.calibration = calibration
    
    def _handle_error(self, error: ProcessingError) -> None:
        """
        Handle a processing error.
        
        Args:
            error: Error information
        """
        self.last_error = error
        self.errors.append(error)
        self.match_data["errors"].append(error)
        
        # Log error
        if error.is_critical:
            logger.critical(
                f"CRITICAL ERROR in {error.component}: {error.message}. "
                f"Diagnostic info: {error.diagnostic_info}"
            )
        else:
            logger.error(
                f"Error in {error.component}: {error.error_type} - {error.message}. "
                f"Diagnostic info: {error.diagnostic_info}"
            )
    
    def _handle_detector_error(self, detector_name: str, exception: Exception, timestamp: float) -> None:
        """
        Handle an error from a sub-detector.
        
        Args:
            detector_name: Name of the detector that failed
            exception: The exception that was raised
            timestamp: Current timestamp
        """
        error = ProcessingError(
            error_type="detector_failure",
            timestamp=timestamp,
            message=f"{detector_name} failed: {str(exception)}",
            component=detector_name,
            diagnostic_info={
                "exception_type": type(exception).__name__,
                "exception_message": str(exception)
            },
            is_critical=False
        )
        self._handle_error(error)
    
    def get_errors(self) -> List[ProcessingError]:
        """
        Get all errors that have occurred.
        
        Returns:
            List of errors
        """
        return self.errors.copy()
    
    def get_last_error(self) -> Optional[ProcessingError]:
        """
        Get the last error that occurred.
        
        Returns:
            Last error, or None if no errors
        """
        return self.last_error
    
    def save_match_data(self, filepath: str) -> None:
        """
        Save all match data before shutdown (for critical errors).
        
        Args:
            filepath: Path to save match data
        """
        import json
        from datetime import datetime
        
        try:
            # Update match state
            self.match_data["match_state"] = {
                "over_number": self.legal_delivery_counter.get_match_state().over_number,
                "ball_number": self.legal_delivery_counter.get_match_state().ball_number,
                "legal_deliveries": self.legal_delivery_counter.get_match_state().legal_deliveries
            }
            
            # Add metadata
            self.match_data["metadata"] = {
                "saved_at": datetime.now().isoformat(),
                "total_decisions": len(self.match_data["decisions"]),
                "total_errors": len(self.match_data["errors"])
            }
            
            # Convert decisions and errors to dictionaries
            data_to_save = {
                "metadata": self.match_data["metadata"],
                "match_state": self.match_data["match_state"],
                "decisions": [
                    {
                        "decision_id": d.decision_id,
                        "event_type": d.event_type.value if hasattr(d.event_type, 'value') else str(d.event_type),
                        "confidence": d.confidence,
                        "timestamp": d.timestamp,
                        "reasoning": d.reasoning,
                        "requires_review": d.requires_review
                    }
                    for d in self.match_data["decisions"]
                ],
                "errors": [
                    {
                        "error_type": e.error_type,
                        "timestamp": e.timestamp,
                        "message": e.message,
                        "component": e.component,
                        "is_critical": e.is_critical
                    }
                    for e in self.match_data["errors"]
                ]
            }
            
            with open(filepath, 'w') as f:
                json.dump(data_to_save, f, indent=2)
            
            logger.info(f"Match data saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save match data: {e}")
    
    def has_critical_error(self) -> bool:
        """
        Check if a critical error has occurred.
        
        Returns:
            True if a critical error has occurred
        """
        return any(error.is_critical for error in self.errors)
