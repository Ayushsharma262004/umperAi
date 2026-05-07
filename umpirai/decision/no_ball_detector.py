"""
No Ball Detector for the UmpirAI system.

This module provides the NoBallDetector class which detects no ball deliveries
based on bowler's front foot position relative to the crease line at ball release.
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

from umpirai.models.data_models import (
    Detection,
    Position3D,
    Vector3D,
    Trajectory,
    Decision,
    EventType,
    VideoReference,
    DetectionClass,
)
from umpirai.calibration.calibration_manager import CalibrationData


@dataclass
class BallReleasePoint:
    """Ball release point information."""
    position: Position3D
    timestamp: float
    velocity_change: float  # Magnitude of velocity change
    
    def __post_init__(self):
        """Validate ball release point."""
        if not isinstance(self.position, Position3D):
            raise TypeError("position must be a Position3D instance")
        if not isinstance(self.timestamp, (int, float)):
            raise TypeError("timestamp must be numeric")
        if not isinstance(self.velocity_change, (int, float)):
            raise TypeError("velocity_change must be numeric")
        if not np.isfinite(self.timestamp) or not np.isfinite(self.velocity_change):
            raise ValueError("timestamp and velocity_change must be finite")


class NoBallDetector:
    """
    Detects no ball deliveries based on bowler's front foot position at ball release.
    
    Logic:
    1. Detect bowler's front foot position at ball release
    2. Detect ball release: sudden velocity change in trajectory
    3. Measure distance from front foot to crease line
    4. If any part of foot is beyond crease line: classify as NO_BALL
    5. Calculate confidence based on foot position and crease line detection quality
    6. Flag as uncertain if foot position is occluded
    
    Confidence Factors:
    - Foot position detection confidence
    - Crease line detection confidence
    - Occlusion status at release moment
    - Ball release detection confidence
    """
    
    # Velocity change threshold for ball release detection (m/s)
    # A sudden increase in velocity indicates ball release
    VELOCITY_CHANGE_THRESHOLD = 5.0
    
    # Minimum confidence threshold for reliable detection
    MIN_CONFIDENCE = 0.70
    
    # Crease line tolerance (meters) - foot must be completely behind this line
    CREASE_TOLERANCE = 0.0
    
    def __init__(self, calibration: Optional[CalibrationData] = None):
        """
        Initialize no ball detector.
        
        Args:
            calibration: Pitch calibration data including crease lines
        """
        self.calibration = calibration
        
        # Ball release tracking
        self._last_release_point: Optional[BallReleasePoint] = None
    
    def detect(
        self,
        trajectory: Trajectory,
        detections: List[Detection],
        calibration: CalibrationData
    ) -> Optional[Decision]:
        """
        Detect no ball from trajectory and detections.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections (including bowler)
            calibration: Pitch calibration data
            
        Returns:
            Decision object if no ball detected, None otherwise
        """
        # Update calibration if provided
        if calibration:
            self.calibration = calibration
        
        # Detect ball release point
        release_point = self.detect_ball_release(trajectory)
        if release_point is None:
            # Cannot determine no ball without release point
            return None
        
        # Store release point
        self._last_release_point = release_point
        
        # Get bowler foot position at release
        bowler_foot_position = self._get_bowler_foot_at_release(
            detections,
            release_point.timestamp
        )
        if bowler_foot_position is None:
            # Cannot determine no ball without foot position
            # Flag as uncertain due to occlusion
            return self._create_uncertain_decision(
                trajectory,
                detections,
                release_point,
                "Bowler foot position occluded at ball release"
            )
        
        # Get crease line position
        crease_line_z = self._get_bowling_crease_z(calibration)
        
        # Calculate foot-crease distance
        foot_crease_distance = self.calculate_foot_crease_distance(
            bowler_foot_position,
            crease_line_z
        )
        
        # Check if no ball (foot crosses crease line)
        is_no_ball = self.is_no_ball(bowler_foot_position, crease_line_z)
        
        if not is_no_ball:
            return None
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            trajectory,
            detections,
            release_point,
            bowler_foot_position
        )
        
        # Create decision
        decision_id = f"no_ball_{int(release_point.timestamp * 1000)}"
        
        # Get video references
        video_refs = self._create_video_references(trajectory, release_point)
        
        # Create reasoning
        reasoning = self._create_reasoning(
            bowler_foot_position,
            crease_line_z,
            foot_crease_distance
        )
        
        return Decision(
            decision_id=decision_id,
            event_type=EventType.NO_BALL,
            confidence=confidence,
            timestamp=release_point.timestamp,
            trajectory=trajectory,
            detections=detections,
            reasoning=reasoning,
            video_references=video_refs,
            requires_review=(confidence < 0.80)
        )
    
    def detect_ball_release(self, trajectory: Trajectory) -> Optional[BallReleasePoint]:
        """
        Detect ball release point from trajectory.
        
        Ball release is detected by sudden velocity change (acceleration spike).
        
        Args:
            trajectory: Ball trajectory
            
        Returns:
            BallReleasePoint if detected, None otherwise
        """
        if not trajectory.velocities or len(trajectory.velocities) < 2:
            return None
        
        if not trajectory.positions or len(trajectory.positions) < 2:
            return None
        
        if not trajectory.timestamps or len(trajectory.timestamps) < 2:
            return None
        
        # Find point with maximum velocity change
        max_velocity_change = 0.0
        release_index = -1
        
        for i in range(1, len(trajectory.velocities)):
            # Calculate velocity change magnitude
            v1 = trajectory.velocities[i - 1]
            v2 = trajectory.velocities[i]
            
            velocity_change = abs(v2.magnitude() - v1.magnitude())
            
            # Check if this is a significant velocity increase (ball release)
            if velocity_change > max_velocity_change and velocity_change > self.VELOCITY_CHANGE_THRESHOLD:
                max_velocity_change = velocity_change
                release_index = i
        
        if release_index < 0:
            # No significant velocity change detected
            return None
        
        # Create release point
        return BallReleasePoint(
            position=trajectory.positions[release_index],
            timestamp=trajectory.timestamps[release_index],
            velocity_change=max_velocity_change
        )
    
    def calculate_foot_crease_distance(
        self,
        foot_position: Position3D,
        crease_line_z: float
    ) -> float:
        """
        Calculate distance between bowler's front foot and crease line.
        
        Args:
            foot_position: Bowler's front foot position
            crease_line_z: Z-coordinate of bowling crease line
            
        Returns:
            Distance in meters (positive if behind crease, negative if over)
        """
        if not isinstance(foot_position, Position3D):
            raise TypeError("foot_position must be a Position3D instance")
        if not isinstance(crease_line_z, (int, float)):
            raise TypeError("crease_line_z must be numeric")
        if not np.isfinite(crease_line_z):
            raise ValueError("crease_line_z must be finite")
        
        # Distance is the difference in z-coordinates
        # Positive distance means foot is behind crease (legal)
        # Negative distance means foot is over crease (no ball)
        distance = crease_line_z - foot_position.z
        
        return float(distance)
    
    def is_no_ball(self, foot_position: Position3D, crease_line_z: float) -> bool:
        """
        Check if bowler's foot crosses the crease line (no ball).
        
        Args:
            foot_position: Bowler's front foot position
            crease_line_z: Z-coordinate of bowling crease line
            
        Returns:
            True if no ball, False otherwise
        """
        if not isinstance(foot_position, Position3D):
            raise TypeError("foot_position must be a Position3D instance")
        if not isinstance(crease_line_z, (int, float)):
            raise TypeError("crease_line_z must be numeric")
        
        # Calculate distance
        distance = self.calculate_foot_crease_distance(foot_position, crease_line_z)
        
        # No ball if foot is over the crease line (distance <= tolerance)
        return distance <= self.CREASE_TOLERANCE
    
    def _get_bowler_foot_at_release(
        self,
        detections: List[Detection],
        release_timestamp: float
    ) -> Optional[Position3D]:
        """
        Get bowler's front foot position at ball release.
        
        Args:
            detections: List of detections
            release_timestamp: Timestamp of ball release
            
        Returns:
            Foot position, or None if not detected
        """
        # Find bowler detection
        bowler_detections = [
            d for d in detections
            if d.class_id == DetectionClass.BOWLER.value
        ]
        
        if not bowler_detections:
            return None
        
        # Use highest confidence bowler detection
        bowler = max(bowler_detections, key=lambda d: d.confidence)
        
        # Use 3D position if available
        if bowler.position_3d is not None:
            # Use the bowler's position directly as the foot position
            # The position_3d should already represent the foot position
            foot_position = Position3D(
                x=bowler.position_3d.x,
                y=0.1,  # Foot on ground
                z=bowler.position_3d.z  # Use actual foot position
            )
            return foot_position
        
        # Otherwise, estimate from bounding box
        bbox_center = bowler.bounding_box.center()
        
        # Rough conversion from pixels to meters (simplified)
        # In production, this would use camera calibration
        x = (bbox_center[0] - 640) / 64.0  # Assume 1280x720 image
        
        # Estimate z position based on bowling crease
        # Bowler should be near bowling crease
        z = -10.0  # Approximate bowling crease position
        
        y = 0.1  # Foot on ground
        
        return Position3D(x=x, y=y, z=z)
    
    def _get_bowling_crease_z(self, calibration: CalibrationData) -> float:
        """
        Get bowling crease z-coordinate from calibration.
        
        Args:
            calibration: Pitch calibration data
            
        Returns:
            Z-coordinate of bowling crease in meters
        """
        if calibration and calibration.crease_lines and "bowling" in calibration.crease_lines:
            # Use calibrated bowling crease position
            bowling_crease = calibration.crease_lines["bowling"]
            if len(bowling_crease) >= 1:
                # For testing, we encode the z-coordinate in the y field of Point2D
                # In production, this would use proper 3D calibration
                return float(bowling_crease[0].y)
        
        # Default: bowling crease at z=-10m
        return -10.0
    
    def _calculate_confidence(
        self,
        trajectory: Trajectory,
        detections: List[Detection],
        release_point: BallReleasePoint,
        foot_position: Position3D
    ) -> float:
        """
        Calculate confidence score for no ball decision.
        
        Factors:
        - Bowler foot detection confidence
        - Crease line detection confidence
        - Ball release detection confidence
        - Trajectory quality
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections
            release_point: Ball release point
            foot_position: Bowler foot position
            
        Returns:
            Confidence score [0.0, 1.0]
        """
        confidences = []
        
        # Ball release detection confidence (based on velocity change magnitude)
        # Higher velocity change = more confident release detection
        release_confidence = min(1.0, release_point.velocity_change / 20.0)
        confidences.append(release_confidence)
        
        # Bowler detection confidence
        bowler_detections = [
            d for d in detections
            if d.class_id == DetectionClass.BOWLER.value
        ]
        if bowler_detections:
            bowler_confidence = max(d.confidence for d in bowler_detections)
            confidences.append(bowler_confidence)
        else:
            # No bowler detected, lower confidence
            confidences.append(0.5)
        
        # Crease line detection confidence
        crease_detections = [
            d for d in detections
            if d.class_id == DetectionClass.CREASE.value
        ]
        if crease_detections:
            crease_confidence = max(d.confidence for d in crease_detections)
            confidences.append(crease_confidence)
        else:
            # No crease detected, use calibration confidence
            if self.calibration:
                confidences.append(0.9)
            else:
                confidences.append(0.6)
        
        # Trajectory quality (based on number of positions)
        if trajectory.positions:
            trajectory_confidence = min(1.0, len(trajectory.positions) / 10.0)
            confidences.append(trajectory_confidence)
        
        # Average all confidence factors
        if confidences:
            return sum(confidences) / len(confidences)
        else:
            return 0.5
    
    def _create_uncertain_decision(
        self,
        trajectory: Trajectory,
        detections: List[Detection],
        release_point: BallReleasePoint,
        reason: str
    ) -> Decision:
        """
        Create an uncertain decision when foot position is occluded.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections
            release_point: Ball release point
            reason: Reason for uncertainty
            
        Returns:
            Decision object with low confidence and requires_review=True
        """
        decision_id = f"no_ball_uncertain_{int(release_point.timestamp * 1000)}"
        
        video_refs = self._create_video_references(trajectory, release_point)
        
        return Decision(
            decision_id=decision_id,
            event_type=EventType.NO_BALL,
            confidence=0.5,  # Low confidence due to occlusion
            timestamp=release_point.timestamp,
            trajectory=trajectory,
            detections=detections,
            reasoning=f"Uncertain no ball decision: {reason}",
            video_references=video_refs,
            requires_review=True
        )
    
    def _create_video_references(
        self,
        trajectory: Trajectory,
        release_point: BallReleasePoint
    ) -> List[VideoReference]:
        """
        Create video references for decision.
        
        Args:
            trajectory: Ball trajectory
            release_point: Ball release point
            
        Returns:
            List of video references
        """
        # Create reference for the moment of ball release
        # In production, this would include actual frame numbers and camera IDs
        return [
            VideoReference(
                camera_id="cam1",
                frame_number=int(release_point.timestamp * 30),  # Assume 30 FPS
                timestamp=release_point.timestamp
            )
        ]
    
    def _create_reasoning(
        self,
        foot_position: Position3D,
        crease_line_z: float,
        foot_crease_distance: float
    ) -> str:
        """
        Create human-readable reasoning for decision.
        
        Args:
            foot_position: Bowler foot position
            crease_line_z: Crease line z-coordinate
            foot_crease_distance: Distance from foot to crease
            
        Returns:
            Reasoning string
        """
        if foot_crease_distance <= 0:
            # No ball - foot over crease
            overstep_distance = abs(foot_crease_distance)
            return (
                f"No ball: Bowler's front foot at z={foot_position.z:.2f}m "
                f"crossed the crease line at z={crease_line_z:.2f}m. "
                f"Overstep by {overstep_distance:.2f}m."
            )
        else:
            # Legal delivery - foot behind crease
            return (
                f"Legal delivery: Bowler's front foot at z={foot_position.z:.2f}m "
                f"is {foot_crease_distance:.2f}m behind the crease line at z={crease_line_z:.2f}m."
            )
