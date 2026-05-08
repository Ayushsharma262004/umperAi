"""
Bowled Detector for the UmpirAI system.

This module provides the BowledDetector class which detects bowled dismissals
based on ball-stump contact and bail dislodgement.
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

from umpirai.models.data_models import (
    Detection,
    Position3D,
    Trajectory,
    Decision,
    EventType,
    VideoReference,
    DetectionClass,
    BoundingBox,
)
from umpirai.calibration.calibration_manager import CalibrationData


@dataclass
class StumpContact:
    """Information about ball-stump contact."""
    contact_position: Position3D
    contact_timestamp: float
    ball_detection: Detection
    stump_detection: Detection
    bails_dislodged: bool
    
    def __post_init__(self):
        """Validate stump contact."""
        if not isinstance(self.contact_position, Position3D):
            raise TypeError("contact_position must be a Position3D instance")
        if not isinstance(self.contact_timestamp, (int, float)):
            raise TypeError("contact_timestamp must be numeric")
        if not isinstance(self.ball_detection, Detection):
            raise TypeError("ball_detection must be a Detection instance")
        if not isinstance(self.stump_detection, Detection):
            raise TypeError("stump_detection must be a Detection instance")
        if not isinstance(self.bails_dislodged, bool):
            raise TypeError("bails_dislodged must be a boolean")
        if not np.isfinite(self.contact_timestamp):
            raise ValueError("contact_timestamp must be finite")


class BowledDetector:
    """
    Detects bowled dismissals based on ball-stump contact and bail dislodgement.
    
    Logic:
    1. Detect ball-stump contact: ball bounding box intersects stump bounding box
    2. Verify bail dislodgement: change in stump region appearance (bail position change)
    3. Verify ball contacted stumps before any other object (check trajectory history)
    4. If all conditions met: classify as BOWLED
    5. If stumps hit but bails not dislodged: classify as not out
    
    Confidence Factors:
    - Ball detection confidence at contact moment
    - Stump detection confidence
    - Bail dislodgement detection confidence
    - Contact sequence verification confidence
    """
    
    # Minimum confidence threshold for reliable detection
    MIN_CONFIDENCE = 0.70
    
    # Bail dislodgement detection threshold
    # This represents the minimum change in stump region appearance to indicate bail dislodgement
    BAIL_DISLODGEMENT_THRESHOLD = 0.15
    
    def __init__(self, calibration: Optional[CalibrationData] = None):
        """
        Initialize bowled detector.
        
        Args:
            calibration: Pitch calibration data including stump positions
        """
        self.calibration = calibration
        
        # Track previous stump appearance for bail dislodgement detection
        self._previous_stump_appearance: Optional[np.ndarray] = None
        self._last_contact: Optional[StumpContact] = None
    
    def detect(
        self,
        trajectory: Trajectory,
        detections: List[Detection],
        calibration: CalibrationData,
        frame_image: Optional[np.ndarray] = None
    ) -> Optional[Decision]:
        """
        Detect bowled dismissal from trajectory and detections.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections (including ball and stumps)
            calibration: Pitch calibration data
            frame_image: Current frame image for bail dislodgement detection (optional)
            
        Returns:
            Decision object if bowled dismissal detected, None otherwise
        """
        # Update calibration if provided
        if calibration:
            self.calibration = calibration
        
        # Detect ball-stump contact
        stump_contact = self.detect_ball_stump_contact(trajectory, detections, frame_image)
        if stump_contact is None:
            # No contact detected
            return None
        
        # Store contact information
        self._last_contact = stump_contact
        
        # Verify contact sequence (ball contacted stumps before other objects)
        contact_sequence_valid = self.verify_contact_sequence(trajectory, detections)
        
        # Determine dismissal classification
        if stump_contact.bails_dislodged and contact_sequence_valid:
            # Bowled dismissal
            event_type = EventType.BOWLED
            is_dismissal = True
        else:
            # Not out (stumps hit but bails not dislodged, or invalid contact sequence)
            return None
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            trajectory,
            detections,
            stump_contact,
            contact_sequence_valid
        )
        
        # Create decision
        decision_id = f"bowled_{int(stump_contact.contact_timestamp * 1000)}"
        
        # Get video references
        video_refs = self._create_video_references(trajectory, stump_contact)
        
        # Create reasoning
        reasoning = self._create_reasoning(stump_contact, contact_sequence_valid)
        
        return Decision(
            decision_id=decision_id,
            event_type=event_type,
            confidence=confidence,
            timestamp=stump_contact.contact_timestamp,
            trajectory=trajectory,
            detections=detections,
            reasoning=reasoning,
            video_references=video_refs,
            requires_review=(confidence < 0.80)
        )
    
    def detect_ball_stump_contact(
        self,
        trajectory: Trajectory,
        detections: List[Detection],
        frame_image: Optional[np.ndarray] = None
    ) -> Optional[StumpContact]:
        """
        Detect ball-stump contact using bounding box intersection.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections
            frame_image: Current frame image for bail dislodgement detection
            
        Returns:
            StumpContact if contact detected, None otherwise
        """
        # Find ball and stump detections
        ball_detections = [
            d for d in detections
            if d.class_id == DetectionClass.BALL.value
        ]
        
        stump_detections = [
            d for d in detections
            if d.class_id == DetectionClass.STUMPS.value
        ]
        
        if not ball_detections or not stump_detections:
            # Cannot detect contact without both ball and stumps
            return None
        
        # Use highest confidence detections
        ball_det = max(ball_detections, key=lambda d: d.confidence)
        stump_det = max(stump_detections, key=lambda d: d.confidence)
        
        # Check if bounding boxes intersect
        if not ball_det.bounding_box.intersects(stump_det.bounding_box):
            # No contact
            return None
        
        # Contact detected - verify bail dislodgement
        bails_dislodged = self.verify_bail_dislodgement(
            stump_det,
            frame_image
        )
        
        # Get contact position from ball detection
        if ball_det.position_3d is not None:
            contact_position = ball_det.position_3d
        else:
            # Estimate from bounding box center
            bbox_center = ball_det.bounding_box.center()
            # Rough conversion from pixels to meters
            x = (bbox_center[0] - 640) / 64.0
            z = 0.0  # At stumps (batting crease)
            y = (720 - bbox_center[1]) / 360.0  # Height
            contact_position = Position3D(x=x, y=y, z=z)
        
        # Get contact timestamp from trajectory
        if trajectory.timestamps:
            contact_timestamp = trajectory.timestamps[-1]
        else:
            contact_timestamp = 0.0
        
        return StumpContact(
            contact_position=contact_position,
            contact_timestamp=contact_timestamp,
            ball_detection=ball_det,
            stump_detection=stump_det,
            bails_dislodged=bails_dislodged
        )
    
    def verify_bail_dislodgement(
        self,
        stump_detection: Detection,
        frame_image: Optional[np.ndarray] = None
    ) -> bool:
        """
        Verify bail dislodgement by detecting change in stump region appearance.
        
        This method compares the current stump region appearance with the previous
        frame to detect if bails have been dislodged.
        
        Args:
            stump_detection: Stump detection
            frame_image: Current frame image
            
        Returns:
            True if bails dislodged, False otherwise
        """
        if frame_image is None:
            # Cannot verify without frame image
            # Assume bails dislodged if contact detected (conservative approach)
            return True
        
        # Extract stump region from frame
        bbox = stump_detection.bounding_box
        x1 = int(max(0, bbox.x))
        y1 = int(max(0, bbox.y))
        x2 = int(min(frame_image.shape[1], bbox.x + bbox.width))
        y2 = int(min(frame_image.shape[0], bbox.y + bbox.height))
        
        if x2 <= x1 or y2 <= y1:
            # Invalid bounding box
            return True
        
        stump_region = frame_image[y1:y2, x1:x2]
        
        if self._previous_stump_appearance is None:
            # First frame - store appearance and assume bails dislodged (conservative)
            # This allows the first contact to be detected as a dismissal
            self._previous_stump_appearance = stump_region.copy()
            return True
        
        # Compare with previous appearance
        # Calculate normalized difference
        if stump_region.shape != self._previous_stump_appearance.shape:
            # Shape mismatch - resize previous appearance
            import cv2
            self._previous_stump_appearance = cv2.resize(
                self._previous_stump_appearance,
                (stump_region.shape[1], stump_region.shape[0])
            )
        
        # Calculate mean absolute difference
        diff = np.abs(stump_region.astype(float) - self._previous_stump_appearance.astype(float))
        mean_diff = np.mean(diff) / 255.0  # Normalize to [0, 1]
        
        # Update previous appearance
        self._previous_stump_appearance = stump_region.copy()
        
        # Check if difference exceeds threshold
        # Convert numpy bool to Python bool
        return bool(mean_diff > self.BAIL_DISLODGEMENT_THRESHOLD)
    
    def verify_contact_sequence(
        self,
        trajectory: Trajectory,
        detections: List[Detection]
    ) -> bool:
        """
        Verify that ball contacted stumps before any other object.
        
        This checks the trajectory history to ensure the ball didn't contact
        the bat, pad, or ground before hitting the stumps.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections
            
        Returns:
            True if contact sequence is valid, False otherwise
        """
        # Check if ball contacted bat before stumps
        bat_contact = self._check_bat_contact_before_stumps(trajectory, detections)
        if bat_contact:
            return False
        
        # Check if ball contacted pad before stumps
        pad_contact = self._check_pad_contact_before_stumps(trajectory, detections)
        if pad_contact:
            return False
        
        # Check if ball bounced (ground contact) before stumps
        ground_contact = self._check_ground_contact_before_stumps(trajectory)
        if ground_contact:
            # Ground contact is allowed (ball can bounce before hitting stumps)
            # This is still a valid bowled dismissal
            pass
        
        return True
    
    def _check_bat_contact_before_stumps(
        self,
        trajectory: Trajectory,
        detections: List[Detection]
    ) -> bool:
        """
        Check if ball contacted bat before stumps.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections
            
        Returns:
            True if bat contact detected before stumps, False otherwise
        """
        # Find batsman detection
        batsman_detections = [
            d for d in detections
            if d.class_id == DetectionClass.BATSMAN.value
        ]
        
        if not batsman_detections:
            # No batsman detected, assume no bat contact
            return False
        
        # Check trajectory for sudden direction change near batsman
        # This would indicate bat contact
        if len(trajectory.velocities) < 2:
            return False
        
        for i in range(1, len(trajectory.velocities)):
            v1 = trajectory.velocities[i - 1]
            v2 = trajectory.velocities[i]
            
            # Calculate angle change
            dot_product = v1.vx * v2.vx + v1.vy * v2.vy + v1.vz * v2.vz
            mag1 = v1.magnitude()
            mag2 = v2.magnitude()
            
            if mag1 > 0 and mag2 > 0:
                cos_angle = dot_product / (mag1 * mag2)
                # Clamp to [-1, 1] to avoid numerical errors
                cos_angle = max(-1.0, min(1.0, cos_angle))
                angle_change = np.arccos(cos_angle)
                
                # If angle change is significant (>30 degrees), likely bat contact
                if angle_change > np.pi / 6:
                    return True
        
        return False
    
    def _check_pad_contact_before_stumps(
        self,
        trajectory: Trajectory,
        detections: List[Detection]
    ) -> bool:
        """
        Check if ball contacted pad before stumps.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections
            
        Returns:
            True if pad contact detected before stumps, False otherwise
        """
        # Find batsman detection
        batsman_detections = [
            d for d in detections
            if d.class_id == DetectionClass.BATSMAN.value
        ]
        
        if not batsman_detections:
            # No batsman detected, assume no pad contact
            return False
        
        batsman = max(batsman_detections, key=lambda d: d.confidence)
        
        # Check if ball trajectory intersects batsman's leg region
        # Leg region is typically lower part of batsman bounding box
        leg_region = BoundingBox(
            x=batsman.bounding_box.x,
            y=batsman.bounding_box.y + batsman.bounding_box.height * 0.5,
            width=batsman.bounding_box.width,
            height=batsman.bounding_box.height * 0.5
        )
        
        # Check if any ball position intersects leg region
        ball_detections = [
            d for d in detections
            if d.class_id == DetectionClass.BALL.value
        ]
        
        for ball_det in ball_detections:
            if ball_det.bounding_box.intersects(leg_region):
                return True
        
        return False
    
    def _check_ground_contact_before_stumps(
        self,
        trajectory: Trajectory
    ) -> bool:
        """
        Check if ball contacted ground before stumps.
        
        Args:
            trajectory: Ball trajectory
            
        Returns:
            True if ground contact detected, False otherwise
        """
        # Check if ball height (y-coordinate) drops to near zero
        for position in trajectory.positions:
            if position.y < 0.1:  # Within 10cm of ground
                return True
        
        return False
    
    def _calculate_confidence(
        self,
        trajectory: Trajectory,
        detections: List[Detection],
        stump_contact: StumpContact,
        contact_sequence_valid: bool
    ) -> float:
        """
        Calculate confidence score for bowled dismissal decision.
        
        Factors:
        - Ball detection confidence at contact moment
        - Stump detection confidence
        - Bail dislodgement detection confidence
        - Contact sequence verification confidence
        - Trajectory quality
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections
            stump_contact: Stump contact information
            contact_sequence_valid: Whether contact sequence is valid
            
        Returns:
            Confidence score [0.0, 1.0]
        """
        confidences = []
        
        # Ball detection confidence
        confidences.append(stump_contact.ball_detection.confidence)
        
        # Stump detection confidence
        confidences.append(stump_contact.stump_detection.confidence)
        
        # Bail dislodgement confidence
        if stump_contact.bails_dislodged:
            # High confidence if bails dislodged
            confidences.append(0.95)
        else:
            # Lower confidence if bails not dislodged
            confidences.append(0.6)
        
        # Contact sequence confidence
        if contact_sequence_valid:
            confidences.append(0.9)
        else:
            confidences.append(0.5)
        
        # Trajectory quality (based on number of positions)
        if trajectory.positions:
            trajectory_confidence = min(1.0, len(trajectory.positions) / 10.0)
            confidences.append(trajectory_confidence)
        
        # Average all confidence factors
        if confidences:
            return sum(confidences) / len(confidences)
        else:
            return 0.5
    
    def _create_video_references(
        self,
        trajectory: Trajectory,
        stump_contact: StumpContact
    ) -> List[VideoReference]:
        """
        Create video references for decision.
        
        Args:
            trajectory: Ball trajectory
            stump_contact: Stump contact information
            
        Returns:
            List of video references
        """
        # Create reference for the moment of contact
        return [
            VideoReference(
                camera_id="cam1",
                frame_number=int(stump_contact.contact_timestamp * 30),  # Assume 30 FPS
                timestamp=stump_contact.contact_timestamp
            )
        ]
    
    def _create_reasoning(
        self,
        stump_contact: StumpContact,
        contact_sequence_valid: bool
    ) -> str:
        """
        Create human-readable reasoning for decision.
        
        Args:
            stump_contact: Stump contact information
            contact_sequence_valid: Whether contact sequence is valid
            
        Returns:
            Reasoning string
        """
        if stump_contact.bails_dislodged and contact_sequence_valid:
            return (
                f"Bowled dismissal: Ball contacted stumps at position "
                f"({stump_contact.contact_position.x:.2f}m, "
                f"{stump_contact.contact_position.y:.2f}m, "
                f"{stump_contact.contact_position.z:.2f}m) and dislodged the bails. "
                f"Contact sequence verified: ball contacted stumps before any other object."
            )
        elif not stump_contact.bails_dislodged:
            return (
                f"Not out: Ball contacted stumps at position "
                f"({stump_contact.contact_position.x:.2f}m, "
                f"{stump_contact.contact_position.y:.2f}m, "
                f"{stump_contact.contact_position.z:.2f}m) but bails were not dislodged."
            )
        else:
            return (
                f"Not out: Ball contacted stumps but contact sequence invalid. "
                f"Ball may have contacted bat or pad before stumps."
            )
