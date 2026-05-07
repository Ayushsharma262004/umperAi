"""
Wide Ball Detector for the UmpirAI system.

This module provides the WideBallDetector class which detects wide ball deliveries
based on ball trajectory relative to batsman stance position.
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
)
from umpirai.calibration.calibration_manager import CalibrationData


@dataclass
class WideGuidelines:
    """Wide guideline positions relative to batsman stance."""
    left: float  # meters from pitch center
    right: float  # meters from pitch center
    batsman_center: float  # batsman center position (x-coordinate)
    
    def __post_init__(self):
        """Validate wide guidelines."""
        if not isinstance(self.left, (int, float)):
            raise TypeError("left must be numeric")
        if not isinstance(self.right, (int, float)):
            raise TypeError("right must be numeric")
        if not isinstance(self.batsman_center, (int, float)):
            raise TypeError("batsman_center must be numeric")
        if not np.isfinite(self.left) or not np.isfinite(self.right) or not np.isfinite(self.batsman_center):
            raise ValueError("guideline values must be finite")


class WideBallDetector:
    """
    Detects wide ball deliveries based on ball trajectory relative to batsman stance.
    
    Logic:
    1. Identify batsman stance position from detection
    2. Define wide guidelines: ±1.0m from batsman center
    3. Track ball path as it crosses batsman's crease line
    4. If ball crosses outside guidelines: classify as WIDE
    5. Adjust guidelines if batsman moves significantly (>0.5m from original stance)
    
    Confidence Factors:
    - Ball detection confidence at crossing point
    - Batsman position detection confidence
    - Guideline calibration quality
    """
    
    # Default wide guideline offsets from batsman center (meters)
    DEFAULT_WIDE_OFFSET = 1.0
    
    # Batsman movement threshold for guideline adaptation (meters)
    BATSMAN_MOVEMENT_THRESHOLD = 0.5
    
    # Minimum confidence threshold for reliable detection
    MIN_CONFIDENCE = 0.70
    
    def __init__(self, calibration: Optional[CalibrationData] = None):
        """
        Initialize wide ball detector.
        
        Args:
            calibration: Pitch calibration data including wide guidelines
        """
        self.calibration = calibration
        
        # Batsman stance tracking
        self._original_batsman_stance: Optional[Position3D] = None
        self._current_batsman_stance: Optional[Position3D] = None
        
        # Wide guidelines (initialized from calibration or defaults)
        self._wide_guidelines: Optional[WideGuidelines] = None
        
        # Initialize guidelines from calibration if available
        if calibration and calibration.wide_guidelines:
            self._initialize_guidelines_from_calibration()
    
    def detect(
        self,
        trajectory: Trajectory,
        detections: List[Detection],
        calibration: CalibrationData
    ) -> Optional[Decision]:
        """
        Detect wide ball from trajectory and detections.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections (including batsman)
            calibration: Pitch calibration data
            
        Returns:
            Decision object if wide ball detected, None otherwise
        """
        # Update calibration if provided
        if calibration:
            self.calibration = calibration
        
        # Identify batsman stance position
        batsman_position = self._identify_batsman_stance(detections)
        if batsman_position is None:
            # Cannot determine wide without batsman position
            return None
        
        # Set or update batsman stance
        self.set_batsman_stance(batsman_position)
        
        # Get current wide guidelines
        guidelines = self.get_wide_guidelines()
        if guidelines is None:
            # Cannot determine wide without guidelines
            return None
        
        # Find ball position at batsman's crease line
        ball_at_crease = self._get_ball_at_crease(trajectory, calibration)
        if ball_at_crease is None:
            # Ball hasn't crossed crease yet or trajectory incomplete
            return None
        
        # Check if ball is wide
        is_wide = self.is_wide_ball(ball_at_crease)
        
        if not is_wide:
            return None
        
        # Calculate confidence
        confidence = self._calculate_confidence(trajectory, detections, ball_at_crease)
        
        # Create decision
        decision_id = f"wide_{int(trajectory.timestamps[-1] * 1000)}"
        
        # Get ball detection at crease for video reference
        video_refs = self._create_video_references(trajectory, detections)
        
        # Create reasoning
        reasoning = self._create_reasoning(ball_at_crease, self._wide_guidelines)
        
        return Decision(
            decision_id=decision_id,
            event_type=EventType.WIDE,
            confidence=confidence,
            timestamp=trajectory.timestamps[-1] if trajectory.timestamps else 0.0,
            trajectory=trajectory,
            detections=detections,
            reasoning=reasoning,
            video_references=video_refs,
            requires_review=(confidence < 0.80)
        )
    
    def set_batsman_stance(self, position: Position3D) -> None:
        """
        Set batsman stance position and update wide guidelines.
        
        If batsman has moved significantly (>0.5m) from original stance,
        guidelines are adapted to the new position.
        
        Args:
            position: Batsman stance position
        """
        if not isinstance(position, Position3D):
            raise TypeError("position must be a Position3D instance")
        
        # Set original stance if not yet set
        if self._original_batsman_stance is None:
            self._original_batsman_stance = position
            self._current_batsman_stance = position
            self._update_guidelines(position)
            return
        
        # Check if batsman has moved significantly
        movement = self._calculate_movement(self._original_batsman_stance, position)
        
        if movement > self.BATSMAN_MOVEMENT_THRESHOLD:
            # Batsman has moved significantly, adapt guidelines
            self._current_batsman_stance = position
            self._update_guidelines(position)
        else:
            # Minor movement, keep current stance
            self._current_batsman_stance = position
    
    def get_wide_guidelines(self) -> Optional[Tuple[float, float]]:
        """
        Get current wide guideline positions.
        
        Returns:
            Tuple of (left, right) guideline positions in meters from pitch center,
            or None if guidelines not initialized
        """
        if self._wide_guidelines is None:
            return None
        
        return (self._wide_guidelines.left, self._wide_guidelines.right)
    
    def is_wide_ball(self, ball_position: Position3D) -> bool:
        """
        Check if ball position is outside wide guidelines.
        
        Args:
            ball_position: Ball position at batsman's crease
            
        Returns:
            True if ball is wide, False otherwise
        """
        if not isinstance(ball_position, Position3D):
            raise TypeError("ball_position must be a Position3D instance")
        
        if self._wide_guidelines is None:
            raise RuntimeError("Wide guidelines not initialized")
        
        # Check if ball x-coordinate is outside guidelines
        ball_x = ball_position.x
        
        return ball_x < self._wide_guidelines.left or ball_x > self._wide_guidelines.right
    
    def _identify_batsman_stance(self, detections: List[Detection]) -> Optional[Position3D]:
        """
        Identify batsman stance position from detections.
        
        Args:
            detections: List of detections in current frame
            
        Returns:
            Batsman position, or None if not detected
        """
        # Find batsman detection
        batsman_detections = [
            d for d in detections
            if d.class_id == DetectionClass.BATSMAN.value
        ]
        
        if not batsman_detections:
            return None
        
        # Use highest confidence batsman detection
        batsman = max(batsman_detections, key=lambda d: d.confidence)
        
        # Use 3D position if available
        if batsman.position_3d is not None:
            return batsman.position_3d
        
        # Otherwise, estimate from bounding box
        # Assume batsman is at batting crease (z coordinate)
        # and use bounding box center for x coordinate
        bbox_center = batsman.bounding_box.center()
        
        # Rough conversion from pixels to meters (simplified)
        # In production, this would use camera calibration
        x = (bbox_center[0] - 640) / 64.0  # Assume 1280x720 image
        z = 0.0  # At batting crease
        y = 1.0  # Typical batsman height
        
        return Position3D(x=x, y=y, z=z)
    
    def _get_ball_at_crease(
        self,
        trajectory: Trajectory,
        calibration: CalibrationData
    ) -> Optional[Position3D]:
        """
        Get ball position when it crosses batsman's crease line.
        
        Args:
            trajectory: Ball trajectory
            calibration: Pitch calibration data
            
        Returns:
            Ball position at crease, or None if not yet crossed
        """
        if not trajectory.positions:
            return None
        
        # Get batting crease z-coordinate from calibration
        batting_crease_z = self._get_batting_crease_z(calibration)
        
        # Find position where ball crosses crease
        for i in range(len(trajectory.positions) - 1):
            pos1 = trajectory.positions[i]
            pos2 = trajectory.positions[i + 1]
            
            # Check if ball crossed crease between these positions
            if (pos1.z <= batting_crease_z <= pos2.z) or (pos2.z <= batting_crease_z <= pos1.z):
                # Interpolate position at crease
                if pos2.z != pos1.z:
                    t = (batting_crease_z - pos1.z) / (pos2.z - pos1.z)
                    x = pos1.x + t * (pos2.x - pos1.x)
                    y = pos1.y + t * (pos2.y - pos1.y)
                    return Position3D(x=x, y=y, z=batting_crease_z)
                else:
                    # Ball moving parallel to crease, use current position
                    return pos1
        
        # Ball hasn't crossed crease yet
        return None
    
    def _get_batting_crease_z(self, calibration: CalibrationData) -> float:
        """
        Get batting crease z-coordinate from calibration.
        
        Args:
            calibration: Pitch calibration data
            
        Returns:
            Z-coordinate of batting crease in meters
        """
        if calibration and calibration.crease_lines and "batting" in calibration.crease_lines:
            # Use calibrated batting crease position
            batting_crease = calibration.crease_lines["batting"]
            if len(batting_crease) >= 2:
                # Average z-coordinate of crease line points
                # Note: In 2D calibration, this would be converted to 3D
                # For now, assume batting crease is at z=0
                return 0.0
        
        # Default: batting crease at origin
        return 0.0
    
    def _calculate_movement(self, pos1: Position3D, pos2: Position3D) -> float:
        """
        Calculate distance between two positions.
        
        Args:
            pos1: First position
            pos2: Second position
            
        Returns:
            Distance in meters
        """
        dx = pos2.x - pos1.x
        dy = pos2.y - pos1.y
        dz = pos2.z - pos1.z
        return float(np.sqrt(dx**2 + dy**2 + dz**2))
    
    def _update_guidelines(self, batsman_position: Position3D) -> None:
        """
        Update wide guidelines based on batsman position.
        
        Args:
            batsman_position: Current batsman stance position
        """
        # Get wide offset from calibration or use default
        wide_offset = self.DEFAULT_WIDE_OFFSET
        
        if self.calibration and self.calibration.wide_guidelines:
            # Use calibrated offsets if available
            left_offset = self.calibration.wide_guidelines.get("left", -wide_offset)
            right_offset = self.calibration.wide_guidelines.get("right", wide_offset)
        else:
            # Use default symmetric offsets
            left_offset = -wide_offset
            right_offset = wide_offset
        
        # Calculate guideline positions relative to batsman
        batsman_x = batsman_position.x
        
        self._wide_guidelines = WideGuidelines(
            left=batsman_x + left_offset,
            right=batsman_x + right_offset,
            batsman_center=batsman_x
        )
    
    def _initialize_guidelines_from_calibration(self) -> None:
        """Initialize wide guidelines from calibration data."""
        if self.calibration and self.calibration.wide_guidelines:
            # Guidelines are defined relative to pitch center initially
            # They will be adjusted when batsman stance is set
            left_offset = self.calibration.wide_guidelines.get("left", -self.DEFAULT_WIDE_OFFSET)
            right_offset = self.calibration.wide_guidelines.get("right", self.DEFAULT_WIDE_OFFSET)
            
            self._wide_guidelines = WideGuidelines(
                left=left_offset,
                right=right_offset,
                batsman_center=0.0  # Pitch center initially
            )
    
    def _calculate_confidence(
        self,
        trajectory: Trajectory,
        detections: List[Detection],
        ball_at_crease: Position3D
    ) -> float:
        """
        Calculate confidence score for wide ball decision.
        
        Factors:
        - Ball detection confidence at crossing point
        - Batsman position detection confidence
        - Guideline calibration quality
        - Trajectory quality
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections
            ball_at_crease: Ball position at crease
            
        Returns:
            Confidence score [0.0, 1.0]
        """
        confidences = []
        
        # Ball trajectory confidence (based on number of positions)
        if trajectory.positions:
            trajectory_confidence = min(1.0, len(trajectory.positions) / 10.0)
            confidences.append(trajectory_confidence)
        
        # Batsman detection confidence
        batsman_detections = [
            d for d in detections
            if d.class_id == DetectionClass.BATSMAN.value
        ]
        if batsman_detections:
            batsman_confidence = max(d.confidence for d in batsman_detections)
            confidences.append(batsman_confidence)
        else:
            # No batsman detected, lower confidence
            confidences.append(0.5)
        
        # Calibration quality (assume high if calibration provided)
        if self.calibration:
            calibration_confidence = 0.95
        else:
            calibration_confidence = 0.7
        confidences.append(calibration_confidence)
        
        # Average all confidence factors
        if confidences:
            return sum(confidences) / len(confidences)
        else:
            return 0.5
    
    def _create_video_references(
        self,
        trajectory: Trajectory,
        detections: List[Detection]
    ) -> List[VideoReference]:
        """
        Create video references for decision.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections
            
        Returns:
            List of video references
        """
        # Create reference for the moment ball crossed crease
        # In production, this would include actual frame numbers and camera IDs
        if trajectory.timestamps:
            return [
                VideoReference(
                    camera_id="cam1",
                    frame_number=int(trajectory.timestamps[-1] * 30),  # Assume 30 FPS
                    timestamp=trajectory.timestamps[-1]
                )
            ]
        return []
    
    def _create_reasoning(
        self,
        ball_at_crease: Position3D,
        guidelines: WideGuidelines
    ) -> str:
        """
        Create human-readable reasoning for decision.
        
        Args:
            ball_at_crease: Ball position at crease
            guidelines: Wide guidelines
            
        Returns:
            Reasoning string
        """
        ball_x = ball_at_crease.x
        
        if ball_x < guidelines.left:
            distance = guidelines.left - ball_x
            return (
                f"Wide ball: Ball crossed crease at x={ball_x:.2f}m, "
                f"which is {distance:.2f}m outside left guideline ({guidelines.left:.2f}m). "
                f"Batsman center at x={guidelines.batsman_center:.2f}m."
            )
        elif ball_x > guidelines.right:
            distance = ball_x - guidelines.right
            return (
                f"Wide ball: Ball crossed crease at x={ball_x:.2f}m, "
                f"which is {distance:.2f}m outside right guideline ({guidelines.right:.2f}m). "
                f"Batsman center at x={guidelines.batsman_center:.2f}m."
            )
        else:
            return "Not a wide ball: Ball within guidelines."
