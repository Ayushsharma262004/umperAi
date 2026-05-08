"""
LBW (Leg Before Wicket) Detector for the UmpirAI system.

This module provides the LBWDetector class which detects LBW dismissals
based on ball-pad contact, pitching point, impact point, and trajectory projection.
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
    BoundingBox,
)
from umpirai.calibration.calibration_manager import CalibrationData


@dataclass
class PadContact:
    """Information about ball-pad contact."""
    contact_position: Position3D
    contact_timestamp: float
    ball_detection: Detection
    batsman_detection: Detection
    
    def __post_init__(self):
        """Validate pad contact."""
        if not isinstance(self.contact_position, Position3D):
            raise TypeError("contact_position must be a Position3D instance")
        if not isinstance(self.contact_timestamp, (int, float)):
            raise TypeError("contact_timestamp must be numeric")
        if not isinstance(self.ball_detection, Detection):
            raise TypeError("ball_detection must be a Detection instance")
        if not isinstance(self.batsman_detection, Detection):
            raise TypeError("batsman_detection must be a Detection instance")
        if not np.isfinite(self.contact_timestamp):
            raise ValueError("contact_timestamp must be finite")


@dataclass
class LBWAnalysis:
    """Complete LBW analysis result."""
    pad_contact: PadContact
    pitching_point: Position3D
    impact_point: Position3D
    projected_stump_intersection: Optional[Position3D]
    pitched_in_line: bool
    impact_in_line: bool
    would_hit_stumps: bool
    bat_first: bool
    trajectory_visualization: List[Position3D]
    
    def __post_init__(self):
        """Validate LBW analysis."""
        if not isinstance(self.pad_contact, PadContact):
            raise TypeError("pad_contact must be a PadContact instance")
        if not isinstance(self.pitching_point, Position3D):
            raise TypeError("pitching_point must be a Position3D instance")
        if not isinstance(self.impact_point, Position3D):
            raise TypeError("impact_point must be a Position3D instance")
        if self.projected_stump_intersection is not None and not isinstance(self.projected_stump_intersection, Position3D):
            raise TypeError("projected_stump_intersection must be a Position3D instance or None")
        if not isinstance(self.pitched_in_line, bool):
            raise TypeError("pitched_in_line must be a boolean")
        if not isinstance(self.impact_in_line, bool):
            raise TypeError("impact_in_line must be a boolean")
        if not isinstance(self.would_hit_stumps, bool):
            raise TypeError("would_hit_stumps must be a boolean")
        if not isinstance(self.bat_first, bool):
            raise TypeError("bat_first must be a boolean")
        if not isinstance(self.trajectory_visualization, list):
            raise TypeError("trajectory_visualization must be a list")
        if not all(isinstance(p, Position3D) for p in self.trajectory_visualization):
            raise TypeError("all trajectory_visualization elements must be Position3D instances")


class LBWDetector:
    """
    Detects LBW (Leg Before Wicket) dismissals based on ball-pad contact and trajectory analysis.
    
    Logic:
    1. Detect ball-pad contact: trajectory intersects batsman leg region
    2. Determine pitching point: check if ball pitched in line with stumps
    3. Determine impact point: check if contact in line with stumps
    4. Project trajectory: extend ball path to stumps using physics model
    5. Calculate stump intersection
    6. Apply LBW decision logic: all conditions satisfied
    7. Exclude bat-first: classify as not out if bat contacted before pad
    8. Generate trajectory visualization
    
    Confidence Factors:
    - Ball detection confidence at contact moment
    - Batsman detection confidence
    - Trajectory quality and prediction uncertainty
    - Pitching and impact point determination confidence
    """
    
    # Minimum confidence threshold for reliable detection
    MIN_CONFIDENCE = 0.70
    
    # Stump dimensions (meters)
    STUMP_WIDTH = 0.23  # Width of three stumps (22.86 cm)
    STUMP_HEIGHT = 0.71  # Height of stumps (71.12 cm)
    
    # Line tolerance for pitching and impact (meters)
    # Ball is "in line" if within this distance from stump line
    LINE_TOLERANCE = 0.15
    
    # Gravity constant (m/s²)
    GRAVITY = 9.81
    
    # Air resistance coefficient (simplified)
    DRAG_COEFFICIENT = 0.98
    
    def __init__(self, calibration: Optional[CalibrationData] = None):
        """
        Initialize LBW detector.
        
        Args:
            calibration: Pitch calibration data including stump positions
        """
        self.calibration = calibration
        
        # Track last analysis for debugging
        self._last_analysis: Optional[LBWAnalysis] = None
    
    def detect(
        self,
        trajectory: Trajectory,
        detections: List[Detection],
        calibration: CalibrationData
    ) -> Optional[Decision]:
        """
        Detect LBW dismissal from trajectory and detections.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections (including ball and batsman)
            calibration: Pitch calibration data
            
        Returns:
            Decision object if LBW detected, None otherwise
        """
        # Update calibration if provided
        if calibration:
            self.calibration = calibration
        
        # Detect ball-pad contact
        pad_contact = self.detect_ball_pad_contact(trajectory, detections)
        if pad_contact is None:
            # No pad contact detected
            return None
        
        # Check for bat-first contact (excludes LBW)
        bat_first = self._check_bat_first_contact(trajectory, detections)
        if bat_first:
            # Bat contacted before pad - not out
            return None
        
        # Perform complete LBW analysis
        lbw_analysis = self.analyze_lbw(trajectory, pad_contact, calibration)
        
        # Store analysis
        self._last_analysis = lbw_analysis
        
        # Check if all LBW conditions are satisfied
        is_lbw = self.is_lbw_out(lbw_analysis)
        
        if not is_lbw:
            return None
        
        # Calculate confidence
        confidence = self._calculate_confidence(trajectory, detections, lbw_analysis)
        
        # Create decision
        decision_id = f"lbw_{int(pad_contact.contact_timestamp * 1000)}"
        
        # Get video references
        video_refs = self._create_video_references(trajectory, pad_contact)
        
        # Create reasoning
        reasoning = self._create_reasoning(lbw_analysis)
        
        return Decision(
            decision_id=decision_id,
            event_type=EventType.LBW,
            confidence=confidence,
            timestamp=pad_contact.contact_timestamp,
            trajectory=trajectory,
            detections=detections,
            reasoning=reasoning,
            video_references=video_refs,
            requires_review=(confidence < 0.80)
        )
    
    def detect_ball_pad_contact(
        self,
        trajectory: Trajectory,
        detections: List[Detection]
    ) -> Optional[PadContact]:
        """
        Detect ball-pad contact by checking if trajectory intersects batsman leg region.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections
            
        Returns:
            PadContact if contact detected, None otherwise
        """
        # Find ball and batsman detections
        ball_detections = [
            d for d in detections
            if d.class_id == DetectionClass.BALL.value
        ]
        
        batsman_detections = [
            d for d in detections
            if d.class_id == DetectionClass.BATSMAN.value
        ]
        
        if not ball_detections or not batsman_detections:
            # Cannot detect contact without both ball and batsman
            return None
        
        # Use highest confidence detections
        ball_det = max(ball_detections, key=lambda d: d.confidence)
        batsman_det = max(batsman_detections, key=lambda d: d.confidence)
        
        # Define batsman leg region (lower half of batsman bounding box)
        leg_region = BoundingBox(
            x=batsman_det.bounding_box.x,
            y=batsman_det.bounding_box.y + batsman_det.bounding_box.height * 0.5,
            width=batsman_det.bounding_box.width,
            height=batsman_det.bounding_box.height * 0.5
        )
        
        # Check if ball bounding box intersects leg region
        if not ball_det.bounding_box.intersects(leg_region):
            # No contact
            return None
        
        # Contact detected - get contact position
        if ball_det.position_3d is not None:
            contact_position = ball_det.position_3d
        else:
            # Estimate from bounding box center
            bbox_center = ball_det.bounding_box.center()
            # Rough conversion from pixels to meters
            x = (bbox_center[0] - 640) / 64.0
            z = 0.0  # At batting crease
            y = (720 - bbox_center[1]) / 360.0  # Height
            contact_position = Position3D(x=x, y=y, z=z)
        
        # Get contact timestamp from trajectory
        if trajectory.timestamps:
            contact_timestamp = trajectory.timestamps[-1]
        else:
            contact_timestamp = 0.0
        
        return PadContact(
            contact_position=contact_position,
            contact_timestamp=contact_timestamp,
            ball_detection=ball_det,
            batsman_detection=batsman_det
        )
    
    def analyze_lbw(
        self,
        trajectory: Trajectory,
        pad_contact: PadContact,
        calibration: CalibrationData
    ) -> LBWAnalysis:
        """
        Perform complete LBW analysis.
        
        Args:
            trajectory: Ball trajectory
            pad_contact: Pad contact information
            calibration: Pitch calibration data
            
        Returns:
            LBWAnalysis with all LBW decision factors
        """
        # Determine pitching point (where ball first bounced)
        pitching_point = self.determine_pitching_point(trajectory)
        
        # Impact point is the pad contact position
        impact_point = pad_contact.contact_position
        
        # Get stump position from calibration
        stump_position = self._get_stump_position(calibration)
        
        # Check if pitched in line with stumps
        pitched_in_line = self.is_pitched_in_line(pitching_point, stump_position)
        
        # Check if impact in line with stumps
        impact_in_line = self.is_impact_in_line(impact_point, stump_position)
        
        # Project trajectory to stumps
        projected_intersection = self.project_trajectory_to_stumps(
            trajectory,
            pad_contact,
            stump_position
        )
        
        # Check if would hit stumps
        would_hit_stumps = self.would_hit_stumps(projected_intersection, stump_position)
        
        # Generate trajectory visualization
        trajectory_viz = self.generate_trajectory_visualization(
            trajectory,
            pad_contact,
            projected_intersection
        )
        
        return LBWAnalysis(
            pad_contact=pad_contact,
            pitching_point=pitching_point,
            impact_point=impact_point,
            projected_stump_intersection=projected_intersection,
            pitched_in_line=pitched_in_line,
            impact_in_line=impact_in_line,
            would_hit_stumps=would_hit_stumps,
            bat_first=False,  # Already checked before calling analyze_lbw
            trajectory_visualization=trajectory_viz
        )
    
    def determine_pitching_point(self, trajectory: Trajectory) -> Position3D:
        """
        Determine where the ball pitched (first bounce).
        
        Args:
            trajectory: Ball trajectory
            
        Returns:
            Pitching point position
        """
        if not trajectory.positions:
            # No trajectory data, return default
            return Position3D(x=0.0, y=0.0, z=-5.0)
        
        # Find the point where ball height (y) is minimum (closest to ground)
        # This indicates a bounce
        min_height = float('inf')
        pitching_index = 0
        
        for i, pos in enumerate(trajectory.positions):
            if pos.y < min_height:
                min_height = pos.y
                pitching_index = i
        
        # If ball never got close to ground, use first position
        if min_height > 0.5:  # Ball never bounced (full toss)
            return trajectory.positions[0]
        
        return trajectory.positions[pitching_index]
    
    def is_pitched_in_line(
        self,
        pitching_point: Position3D,
        stump_position: Position3D
    ) -> bool:
        """
        Check if ball pitched in line with stumps.
        
        Args:
            pitching_point: Where ball pitched
            stump_position: Stump center position
            
        Returns:
            True if pitched in line, False otherwise
        """
        if not isinstance(pitching_point, Position3D):
            raise TypeError("pitching_point must be a Position3D instance")
        if not isinstance(stump_position, Position3D):
            raise TypeError("stump_position must be a Position3D instance")
        
        # Check lateral distance from stump line
        # Ball is in line if x-coordinate is within tolerance of stump x-coordinate
        lateral_distance = abs(pitching_point.x - stump_position.x)
        
        return lateral_distance <= self.LINE_TOLERANCE
    
    def is_impact_in_line(
        self,
        impact_point: Position3D,
        stump_position: Position3D
    ) -> bool:
        """
        Check if impact point is in line with stumps.
        
        Args:
            impact_point: Where ball contacted pad
            stump_position: Stump center position
            
        Returns:
            True if impact in line, False otherwise
        """
        if not isinstance(impact_point, Position3D):
            raise TypeError("impact_point must be a Position3D instance")
        if not isinstance(stump_position, Position3D):
            raise TypeError("stump_position must be a Position3D instance")
        
        # Check lateral distance from stump line
        lateral_distance = abs(impact_point.x - stump_position.x)
        
        return lateral_distance <= self.LINE_TOLERANCE
    
    def project_trajectory_to_stumps(
        self,
        trajectory: Trajectory,
        pad_contact: PadContact,
        stump_position: Position3D
    ) -> Optional[Position3D]:
        """
        Project ball trajectory to stumps using physics model.
        
        Args:
            trajectory: Ball trajectory
            pad_contact: Pad contact information
            stump_position: Stump center position
            
        Returns:
            Projected intersection point with stump plane, or None if no intersection
        """
        if not trajectory.velocities or not trajectory.positions:
            return None
        
        # Get ball velocity at impact
        if trajectory.velocities:
            velocity_at_impact = trajectory.velocities[-1]
        else:
            # Estimate velocity from last two positions
            if len(trajectory.positions) >= 2:
                p1 = trajectory.positions[-2]
                p2 = trajectory.positions[-1]
                if len(trajectory.timestamps) >= 2:
                    dt = trajectory.timestamps[-1] - trajectory.timestamps[-2]
                    if dt > 0:
                        vx = (p2.x - p1.x) / dt
                        vy = (p2.y - p1.y) / dt
                        vz = (p2.z - p1.z) / dt
                        velocity_at_impact = Vector3D(vx=vx, vy=vy, vz=vz)
                    else:
                        return None
                else:
                    return None
            else:
                return None
        
        # Starting position is the impact point
        start_pos = pad_contact.contact_position
        
        # Project trajectory forward using physics model
        # We need to find where the ball crosses the stump plane (z = stump_position.z)
        
        # Time step for simulation (seconds)
        dt = 0.01
        max_steps = 1000  # Maximum simulation steps
        
        current_pos = Position3D(x=start_pos.x, y=start_pos.y, z=start_pos.z)
        current_vel = Vector3D(vx=velocity_at_impact.vx, vy=velocity_at_impact.vy, vz=velocity_at_impact.vz)
        
        for step in range(max_steps):
            # Update position
            new_x = current_pos.x + current_vel.vx * dt
            new_y = current_pos.y + current_vel.vy * dt
            new_z = current_pos.z + current_vel.vz * dt
            
            # Check if we've crossed the stump plane
            if (current_pos.z <= stump_position.z <= new_z) or (new_z <= stump_position.z <= current_pos.z):
                # Interpolate exact intersection point
                if new_z != current_pos.z:
                    t = (stump_position.z - current_pos.z) / (new_z - current_pos.z)
                    intersection_x = current_pos.x + t * (new_x - current_pos.x)
                    intersection_y = current_pos.y + t * (new_y - current_pos.y)
                    return Position3D(x=intersection_x, y=intersection_y, z=stump_position.z)
                else:
                    return Position3D(x=new_x, y=new_y, z=stump_position.z)
            
            # Update velocity (apply gravity and air resistance)
            new_vx = current_vel.vx * self.DRAG_COEFFICIENT
            new_vy = current_vel.vy * self.DRAG_COEFFICIENT - self.GRAVITY * dt
            new_vz = current_vel.vz * self.DRAG_COEFFICIENT
            
            # Update current state
            current_pos = Position3D(x=new_x, y=new_y, z=new_z)
            current_vel = Vector3D(vx=new_vx, vy=new_vy, vz=new_vz)
            
            # Stop if ball hits ground
            if current_pos.y <= 0:
                return None
        
        # No intersection found within max steps
        return None
    
    def would_hit_stumps(
        self,
        projected_intersection: Optional[Position3D],
        stump_position: Position3D
    ) -> bool:
        """
        Check if projected trajectory would hit the stumps.
        
        Args:
            projected_intersection: Projected intersection with stump plane
            stump_position: Stump center position
            
        Returns:
            True if would hit stumps, False otherwise
        """
        if projected_intersection is None:
            return False
        
        if not isinstance(projected_intersection, Position3D):
            raise TypeError("projected_intersection must be a Position3D instance")
        if not isinstance(stump_position, Position3D):
            raise TypeError("stump_position must be a Position3D instance")
        
        # Check if intersection point is within stump dimensions
        # Lateral distance (x-axis)
        lateral_distance = abs(projected_intersection.x - stump_position.x)
        if lateral_distance > self.STUMP_WIDTH / 2:
            return False
        
        # Height (y-axis)
        if projected_intersection.y < 0 or projected_intersection.y > self.STUMP_HEIGHT:
            return False
        
        return True
    
    def is_lbw_out(self, lbw_analysis: LBWAnalysis) -> bool:
        """
        Determine if batsman is out LBW based on analysis.
        
        LBW conditions:
        1. Ball pitched in line with stumps (or outside off stump)
        2. Impact in line with stumps
        3. Ball would have hit stumps
        4. Ball did not contact bat first
        
        Args:
            lbw_analysis: Complete LBW analysis
            
        Returns:
            True if out LBW, False otherwise
        """
        if not isinstance(lbw_analysis, LBWAnalysis):
            raise TypeError("lbw_analysis must be an LBWAnalysis instance")
        
        # Check bat-first exclusion
        if lbw_analysis.bat_first:
            return False
        
        # Check all LBW conditions
        # Note: We're simplifying the "pitched outside off stump" rule
        # In full implementation, this would check if ball pitched outside off stump
        # and batsman was not offering a shot
        
        return (
            lbw_analysis.pitched_in_line and
            lbw_analysis.impact_in_line and
            lbw_analysis.would_hit_stumps
        )
    
    def generate_trajectory_visualization(
        self,
        trajectory: Trajectory,
        pad_contact: PadContact,
        projected_intersection: Optional[Position3D]
    ) -> List[Position3D]:
        """
        Generate trajectory visualization showing ball path to stumps.
        
        Args:
            trajectory: Ball trajectory
            pad_contact: Pad contact information
            projected_intersection: Projected intersection with stumps
            
        Returns:
            List of positions for visualization
        """
        visualization = []
        
        # Add actual trajectory positions up to impact
        visualization.extend(trajectory.positions)
        
        # Add projected path from impact to stumps
        if projected_intersection is not None:
            # Create intermediate points for smooth visualization
            start = pad_contact.contact_position
            end = projected_intersection
            
            num_points = 10
            for i in range(1, num_points + 1):
                t = i / num_points
                x = start.x + t * (end.x - start.x)
                y = start.y + t * (end.y - start.y)
                z = start.z + t * (end.z - start.z)
                visualization
                visualization.append(Position3D(x=x, y=y, z=z))
        
        return visualization
    
    def _check_bat_first_contact(
        self,
        trajectory: Trajectory,
        detections: List[Detection]
    ) -> bool:
        """
        Check if ball contacted bat before pad.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections
            
        Returns:
            True if bat contacted first, False otherwise
        """
        # Find batsman detection
        batsman_detections = [
            d for d in detections
            if d.class_id == DetectionClass.BATSMAN.value
        ]
        
        if not batsman_detections:
            # No batsman detected, assume no bat contact
            return False
        
        # Check trajectory for sudden direction change (indicates bat contact)
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
    
    def _get_stump_position(self, calibration: CalibrationData) -> Position3D:
        """
        Get stump center position from calibration.
        
        Args:
            calibration: Pitch calibration data
            
        Returns:
            Stump center position
        """
        if calibration and calibration.stump_positions and "batting" in calibration.stump_positions:
            # Use calibrated stump position
            stump_pos = calibration.stump_positions["batting"]
            # Assume stump_pos is a Point2D with x, y coordinates
            # Convert to 3D position
            return Position3D(
                x=float(stump_pos.x),
                y=self.STUMP_HEIGHT / 2,  # Middle of stumps
                z=0.0  # At batting crease
            )
        
        # Default: stumps at origin (batting crease)
        return Position3D(x=0.0, y=self.STUMP_HEIGHT / 2, z=0.0)
    
    def _calculate_confidence(
        self,
        trajectory: Trajectory,
        detections: List[Detection],
        lbw_analysis: LBWAnalysis
    ) -> float:
        """
        Calculate confidence score for LBW decision.
        
        Factors:
        - Ball detection confidence at contact moment
        - Batsman detection confidence
        - Trajectory quality and prediction uncertainty
        - Pitching and impact point determination confidence
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections
            lbw_analysis: LBW analysis result
            
        Returns:
            Confidence score [0.0, 1.0]
        """
        confidences = []
        
        # Ball detection confidence
        confidences.append(lbw_analysis.pad_contact.ball_detection.confidence)
        
        # Batsman detection confidence
        confidences.append(lbw_analysis.pad_contact.batsman_detection.confidence)
        
        # Trajectory quality (based on number of positions)
        if trajectory.positions:
            trajectory_confidence = min(1.0, len(trajectory.positions) / 15.0)
            confidences.append(trajectory_confidence)
        
        # Projection confidence (lower if projection failed)
        if lbw_analysis.projected_stump_intersection is not None:
            projection_confidence = 0.9
        else:
            projection_confidence = 0.5
        confidences.append(projection_confidence)
        
        # Pitching point confidence (higher if ball bounced)
        pitching_height = lbw_analysis.pitching_point.y
        if pitching_height < 0.2:  # Ball bounced close to ground
            pitching_confidence = 0.95
        elif pitching_height < 0.5:  # Ball bounced
            pitching_confidence = 0.85
        else:  # Full toss (no bounce)
            pitching_confidence = 0.75
        confidences.append(pitching_confidence)
        
        # Impact point confidence (based on contact detection)
        impact_confidence = 0.85  # Moderate confidence for pad contact detection
        confidences.append(impact_confidence)
        
        # Average all confidence factors
        if confidences:
            return sum(confidences) / len(confidences)
        else:
            return 0.5
    
    def _create_video_references(
        self,
        trajectory: Trajectory,
        pad_contact: PadContact
    ) -> List[VideoReference]:
        """
        Create video references for decision.
        
        Args:
            trajectory: Ball trajectory
            pad_contact: Pad contact information
            
        Returns:
            List of video references
        """
        # Create reference for the moment of pad contact
        return [
            VideoReference(
                camera_id="cam1",
                frame_number=int(pad_contact.contact_timestamp * 30),  # Assume 30 FPS
                timestamp=pad_contact.contact_timestamp
            )
        ]
    
    def _create_reasoning(self, lbw_analysis: LBWAnalysis) -> str:
        """
        Create human-readable reasoning for decision.
        
        Args:
            lbw_analysis: LBW analysis result
            
        Returns:
            Reasoning string
        """
        impact = lbw_analysis.impact_point
        pitching = lbw_analysis.pitching_point
        
        reasoning_parts = []
        
        # Pitching point
        if lbw_analysis.pitched_in_line:
            reasoning_parts.append(
                f"Ball pitched in line with stumps at ({pitching.x:.2f}m, {pitching.z:.2f}m)."
            )
        else:
            reasoning_parts.append(
                f"Ball pitched outside line at ({pitching.x:.2f}m, {pitching.z:.2f}m)."
            )
        
        # Impact point
        if lbw_analysis.impact_in_line:
            reasoning_parts.append(
                f"Impact in line with stumps at ({impact.x:.2f}m, {impact.y:.2f}m, {impact.z:.2f}m)."
            )
        else:
            reasoning_parts.append(
                f"Impact outside line at ({impact.x:.2f}m, {impact.y:.2f}m, {impact.z:.2f}m)."
            )
        
        # Trajectory projection
        if lbw_analysis.would_hit_stumps:
            if lbw_analysis.projected_stump_intersection:
                proj = lbw_analysis.projected_stump_intersection
                reasoning_parts.append(
                    f"Projected trajectory would hit stumps at ({proj.x:.2f}m, {proj.y:.2f}m, {proj.z:.2f}m)."
                )
            else:
                reasoning_parts.append("Projected trajectory would hit stumps.")
        else:
            reasoning_parts.append("Projected trajectory would miss stumps.")
        
        # Bat-first check
        if lbw_analysis.bat_first:
            reasoning_parts.append("Ball contacted bat before pad - not out.")
        
        # Final decision
        if self.is_lbw_out(lbw_analysis):
            reasoning_parts.append("LBW decision: OUT - all conditions satisfied.")
        else:
            reasoning_parts.append("LBW decision: NOT OUT - conditions not satisfied.")
        
        return " ".join(reasoning_parts)
