"""
Caught Dismissal Detector for the UmpirAI system.

This module provides the CaughtDetector class which detects caught dismissals
based on ball-bat contact, ball-to-fielder tracking, fielder control verification,
and ground contact verification.
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


@dataclass
class BatContact:
    """Information about ball-bat contact."""
    contact_position: Position3D
    contact_timestamp: float
    contact_frame_index: int
    ball_detection: Detection
    batsman_detection: Detection
    velocity_before: Vector3D
    velocity_after: Vector3D
    
    def __post_init__(self):
        """Validate bat contact."""
        if not isinstance(self.contact_position, Position3D):
            raise TypeError("contact_position must be a Position3D instance")
        if not isinstance(self.contact_timestamp, (int, float)):
            raise TypeError("contact_timestamp must be numeric")
        if not isinstance(self.contact_frame_index, int) or self.contact_frame_index < 0:
            raise ValueError("contact_frame_index must be a non-negative integer")
        if not isinstance(self.ball_detection, Detection):
            raise TypeError("ball_detection must be a Detection instance")
        if not isinstance(self.batsman_detection, Detection):
            raise TypeError("batsman_detection must be a Detection instance")
        if not isinstance(self.velocity_before, Vector3D):
            raise TypeError("velocity_before must be a Vector3D instance")
        if not isinstance(self.velocity_after, Vector3D):
            raise TypeError("velocity_after must be a Vector3D instance")
        if not np.isfinite(self.contact_timestamp):
            raise ValueError("contact_timestamp must be finite")


@dataclass
class FielderCatch:
    """Information about fielder catching the ball."""
    fielder_detection: Detection
    catch_position: Position3D
    catch_timestamp: float
    control_frames: int  # Number of frames ball remained in fielder box
    ball_detections: List[Detection]  # Ball detections during catch
    
    def __post_init__(self):
        """Validate fielder catch."""
        if not isinstance(self.fielder_detection, Detection):
            raise TypeError("fielder_detection must be a Detection instance")
        if not isinstance(self.catch_position, Position3D):
            raise TypeError("catch_position must be a Position3D instance")
        if not isinstance(self.catch_timestamp, (int, float)):
            raise TypeError("catch_timestamp must be numeric")
        if not isinstance(self.control_frames, int) or self.control_frames < 0:
            raise ValueError("control_frames must be a non-negative integer")
        if not isinstance(self.ball_detections, list):
            raise TypeError("ball_detections must be a list")
        if not all(isinstance(d, Detection) for d in self.ball_detections):
            raise TypeError("all ball_detections must be Detection instances")
        if not np.isfinite(self.catch_timestamp):
            raise ValueError("catch_timestamp must be finite")


@dataclass
class CaughtAnalysis:
    """Complete caught dismissal analysis result."""
    bat_contact: BatContact
    fielder_catch: FielderCatch
    ground_contact_detected: bool
    min_ball_height: float  # Minimum height during flight to fielder (meters)
    flight_duration: float  # Time from bat contact to catch (seconds)
    
    def __post_init__(self):
        """Validate caught analysis."""
        if not isinstance(self.bat_contact, BatContact):
            raise TypeError("bat_contact must be a BatContact instance")
        if not isinstance(self.fielder_catch, FielderCatch):
            raise TypeError("fielder_catch must be a FielderCatch instance")
        if not isinstance(self.ground_contact_detected, bool):
            raise TypeError("ground_contact_detected must be a boolean")
        if not isinstance(self.min_ball_height, (int, float)):
            raise TypeError("min_ball_height must be numeric")
        if not isinstance(self.flight_duration, (int, float)) or self.flight_duration < 0:
            raise ValueError("flight_duration must be a non-negative number")
        if not np.isfinite(self.min_ball_height):
            raise ValueError("min_ball_height must be finite")


class CaughtDetector:
    """
    Detects caught dismissals based on ball-bat contact and fielder control.
    
    Logic:
    1. Detect ball-bat contact: trajectory direction change near bat
    2. Track ball to fielder: ball enters fielder bounding box
    3. Verify fielder control: ball remains in fielder box for ≥3 frames
    4. Verify no ground contact: ball height >0.1m throughout flight
    5. Classify as caught if all conditions met
    
    Confidence Factors:
    - Ball detection confidence during flight
    - Bat contact detection confidence
    - Fielder detection confidence
    - Ground contact verification confidence
    """
    
    # Minimum confidence threshold for reliable detection
    MIN_CONFIDENCE = 0.70
    
    # Minimum angle change to detect bat contact (radians)
    # 30 degrees = π/6 radians
    MIN_BAT_CONTACT_ANGLE = np.pi / 6
    
    # Minimum control frames for valid catch
    MIN_CONTROL_FRAMES = 3
    
    # Minimum ball height to avoid ground contact (meters)
    MIN_BALL_HEIGHT = 0.1
    
    # Maximum distance from batsman to detect bat contact (meters)
    MAX_BAT_CONTACT_DISTANCE = 2.0
    
    def __init__(self):
        """Initialize caught detector."""
        # Track last analysis for debugging
        self._last_analysis: Optional[CaughtAnalysis] = None
    
    def detect(
        self,
        trajectory: Trajectory,
        detections: List[Detection]
    ) -> Optional[Decision]:
        """
        Detect caught dismissal from trajectory and detections.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections (including ball, batsman, fielder)
            
        Returns:
            Decision object if caught dismissal detected, None otherwise
        """
        # Detect ball-bat contact
        bat_contact = self.detect_ball_bat_contact(trajectory, detections)
        if bat_contact is None:
            # No bat contact detected
            return None
        
        # Track ball to fielder
        fielder_catch = self.detect_fielder_catch(trajectory, detections, bat_contact)
        if fielder_catch is None:
            # Ball not caught by fielder
            return None
        
        # Verify fielder control (≥3 frames)
        if fielder_catch.control_frames < self.MIN_CONTROL_FRAMES:
            # Insufficient control
            return None
        
        # Verify no ground contact
        ground_contact, min_height = self.detect_ground_contact(trajectory, bat_contact, fielder_catch)
        if ground_contact:
            # Ball touched ground before catch
            return None
        
        # Calculate flight duration
        flight_duration = fielder_catch.catch_timestamp - bat_contact.contact_timestamp
        
        # Create analysis
        caught_analysis = CaughtAnalysis(
            bat_contact=bat_contact,
            fielder_catch=fielder_catch,
            ground_contact_detected=ground_contact,
            min_ball_height=min_height,
            flight_duration=flight_duration
        )
        
        # Store analysis
        self._last_analysis = caught_analysis
        
        # Calculate confidence
        confidence = self._calculate_confidence(trajectory, detections, caught_analysis)
        
        # Create decision
        decision_id = f"caught_{int(fielder_catch.catch_timestamp * 1000)}"
        
        # Get video references
        video_refs = self._create_video_references(bat_contact, fielder_catch)
        
        # Create reasoning
        reasoning = self._create_reasoning(caught_analysis)
        
        return Decision(
            decision_id=decision_id,
            event_type=EventType.CAUGHT,
            confidence=confidence,
            timestamp=fielder_catch.catch_timestamp,
            trajectory=trajectory,
            detections=detections,
            reasoning=reasoning,
            video_references=video_refs,
            requires_review=(confidence < 0.80)
        )
    
    def detect_ball_bat_contact(
        self,
        trajectory: Trajectory,
        detections: List[Detection]
    ) -> Optional[BatContact]:
        """
        Detect ball-bat contact by checking for trajectory direction change near bat.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections
            
        Returns:
            BatContact if contact detected, None otherwise
        """
        # Find batsman detection
        batsman_detections = [
            d for d in detections
            if d.class_id == DetectionClass.BATSMAN.value
        ]
        
        if not batsman_detections:
            # No batsman detected
            return None
        
        # Use highest confidence batsman detection
        batsman_det = max(batsman_detections, key=lambda d: d.confidence)
        
        # Check trajectory for sudden direction change (indicates bat contact)
        if len(trajectory.velocities) < 2 or len(trajectory.positions) < 2:
            return None
        
        # Look for significant velocity direction change
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
                
                # If angle change is significant, likely bat contact
                if angle_change > self.MIN_BAT_CONTACT_ANGLE:
                    # Verify contact occurred near batsman
                    contact_position = trajectory.positions[i]
                    
                    # Check distance from batsman
                    if batsman_det.position_3d is not None:
                        batsman_pos = batsman_det.position_3d
                        distance = np.sqrt(
                            (contact_position.x - batsman_pos.x)**2 +
                            (contact_position.y - batsman_pos.y)**2 +
                            (contact_position.z - batsman_pos.z)**2
                        )
                        
                        if distance > self.MAX_BAT_CONTACT_DISTANCE:
                            # Too far from batsman
                            continue
                    
                    # Get ball detection at contact moment
                    # Find ball detection closest to contact position
                    ball_detections = [
                        d for d in detections
                        if d.class_id == DetectionClass.BALL.value
                    ]
                    
                    if not ball_detections:
                        continue
                    
                    ball_det = max(ball_detections, key=lambda d: d.confidence)
                    
                    # Get timestamp
                    if i < len(trajectory.timestamps):
                        contact_timestamp = trajectory.timestamps[i]
                    else:
                        contact_timestamp = 0.0
                    
                    return BatContact(
                        contact_position=contact_position,
                        contact_timestamp=contact_timestamp,
                        contact_frame_index=i,
                        ball_detection=ball_det,
                        batsman_detection=batsman_det,
                        velocity_before=v1,
                        velocity_after=v2
                    )
        
        return None
    
    def detect_fielder_catch(
        self,
        trajectory: Trajectory,
        detections: List[Detection],
        bat_contact: BatContact
    ) -> Optional[FielderCatch]:
        """
        Detect fielder catching the ball.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections
            bat_contact: Bat contact information
            
        Returns:
            FielderCatch if catch detected, None otherwise
        """
        # Find fielder detections
        fielder_detections = [
            d for d in detections
            if d.class_id == DetectionClass.FIELDER.value
        ]
        
        if not fielder_detections:
            # No fielder detected
            return None
        
        # Find ball detections
        ball_detections = [
            d for d in detections
            if d.class_id == DetectionClass.BALL.value
        ]
        
        if not ball_detections:
            return None
        
        # Check if ball is in any fielder's bounding box
        # and count consecutive frames of control
        for fielder_det in fielder_detections:
            control_frames = 0
            catch_ball_detections = []
            catch_position = None
            catch_timestamp = None
            
            # Look through trajectory positions after bat contact
            start_index = bat_contact.contact_frame_index + 1
            
            for i in range(start_index, len(trajectory.positions)):
                pos = trajectory.positions[i]
                
                # Convert 3D position to 2D bounding box center (rough approximation)
                # In real implementation, this would use camera calibration
                ball_2d_x = 640 + pos.x * 64.0  # Rough conversion
                ball_2d_y = 720 - pos.y * 360.0
                
                # Check if ball is in fielder bounding box
                if (fielder_det.bounding_box.x <= ball_2d_x <= fielder_det.bounding_box.x + fielder_det.bounding_box.width and
                    fielder_det.bounding_box.y <= ball_2d_y <= fielder_det.bounding_box.y + fielder_det.bounding_box.height):
                    
                    control_frames += 1
                    
                    # Find corresponding ball detection
                    if i < len(ball_detections):
                        catch_ball_detections.append(ball_detections[min(i, len(ball_detections) - 1)])
                    
                    if catch_position is None:
                        catch_position = pos
                        if i < len(trajectory.timestamps):
                            catch_timestamp = trajectory.timestamps[i]
                        else:
                            catch_timestamp = 0.0
                else:
                    # Ball left fielder box
                    if control_frames >= self.MIN_CONTROL_FRAMES:
                        # Valid catch detected
                        break
                    else:
                        # Reset counter
                        control_frames = 0
                        catch_ball_detections = []
                        catch_position = None
                        catch_timestamp = None
            
            # Check if we found a valid catch
            if control_frames >= self.MIN_CONTROL_FRAMES and catch_position is not None:
                return FielderCatch(
                    fielder_detection=fielder_det,
                    catch_position=catch_position,
                    catch_timestamp=catch_timestamp if catch_timestamp is not None else 0.0,
                    control_frames=control_frames,
                    ball_detections=catch_ball_detections
                )
        
        return None
    
    def detect_ground_contact(
        self,
        trajectory: Trajectory,
        bat_contact: BatContact,
        fielder_catch: FielderCatch
    ) -> Tuple[bool, float]:
        """
        Detect if ball contacted ground between bat and fielder.
        
        Args:
            trajectory: Ball trajectory
            bat_contact: Bat contact information
            fielder_catch: Fielder catch information
            
        Returns:
            Tuple of (ground_contact_detected, min_ball_height)
        """
        # Check ball height throughout flight from bat to fielder
        start_index = bat_contact.contact_frame_index
        
        # Find end index (when ball reached fielder)
        end_index = len(trajectory.positions)
        for i in range(start_index, len(trajectory.positions)):
            if i < len(trajectory.timestamps):
                if trajectory.timestamps[i] >= fielder_catch.catch_timestamp:
                    end_index = i
                    break
        
        # Check minimum height during flight
        min_height = float('inf')
        ground_contact = False
        
        for i in range(start_index, min(end_index + 1, len(trajectory.positions))):
            pos = trajectory.positions[i]
            
            if pos.y < min_height:
                min_height = pos.y
            
            # Check if ball went below minimum height threshold
            if pos.y < self.MIN_BALL_HEIGHT:
                ground_contact = True
        
        # If no positions checked, use safe defaults
        if min_height == float('inf'):
            min_height = 0.0
            ground_contact = True
        
        return ground_contact, min_height
    
    def _calculate_confidence(
        self,
        trajectory: Trajectory,
        detections: List[Detection],
        caught_analysis: CaughtAnalysis
    ) -> float:
        """
        Calculate confidence score for caught dismissal decision.
        
        Factors:
        - Ball detection confidence during flight
        - Bat contact detection confidence
        - Fielder detection confidence
        - Ground contact verification confidence
        - Control duration (more frames = higher confidence)
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections
            caught_analysis: Caught analysis result
            
        Returns:
            Confidence score [0.0, 1.0]
        """
        confidences = []
        
        # Ball detection confidence
        confidences.append(caught_analysis.bat_contact.ball_detection.confidence)
        
        # Batsman detection confidence
        confidences.append(caught_analysis.bat_contact.batsman_detection.confidence)
        
        # Fielder detection confidence
        confidences.append(caught_analysis.fielder_catch.fielder_detection.confidence)
        
        # Bat contact confidence (based on velocity change magnitude)
        v_before_mag = caught_analysis.bat_contact.velocity_before.magnitude()
        v_after_mag = caught_analysis.bat_contact.velocity_after.magnitude()
        if v_before_mag > 0:
            velocity_change_ratio = abs(v_after_mag - v_before_mag) / v_before_mag
            bat_contact_confidence = min(1.0, velocity_change_ratio)
            confidences.append(bat_contact_confidence)
        
        # Control duration confidence (more frames = higher confidence)
        control_confidence = min(1.0, caught_analysis.fielder_catch.control_frames / 5.0)
        confidences.append(control_confidence)
        
        # Ground contact verification confidence
        if not caught_analysis.ground_contact_detected:
            # No ground contact detected - high confidence
            if caught_analysis.min_ball_height > self.MIN_BALL_HEIGHT * 2:
                ground_confidence = 0.95
            else:
                ground_confidence = 0.85
        else:
            # Ground contact detected - low confidence in catch
            ground_confidence = 0.3
        confidences.append(ground_confidence)
        
        # Trajectory quality (based on number of positions)
        if trajectory.positions:
            trajectory_confidence = min(1.0, len(trajectory.positions) / 20.0)
            confidences.append(trajectory_confidence)
        
        # Average all confidence factors
        if confidences:
            return sum(confidences) / len(confidences)
        else:
            return 0.5
    
    def _create_video_references(
        self,
        bat_contact: BatContact,
        fielder_catch: FielderCatch
    ) -> List[VideoReference]:
        """
        Create video references for decision.
        
        Args:
            bat_contact: Bat contact information
            fielder_catch: Fielder catch information
            
        Returns:
            List of video references
        """
        return [
            # Bat contact moment
            VideoReference(
                camera_id="cam1",
                frame_number=int(bat_contact.contact_timestamp * 30),  # Assume 30 FPS
                timestamp=bat_contact.contact_timestamp
            ),
            # Catch moment
            VideoReference(
                camera_id="cam1",
                frame_number=int(fielder_catch.catch_timestamp * 30),  # Assume 30 FPS
                timestamp=fielder_catch.catch_timestamp
            )
        ]
    
    def _create_reasoning(self, caught_analysis: CaughtAnalysis) -> str:
        """
        Create human-readable reasoning for decision.
        
        Args:
            caught_analysis: Caught analysis result
            
        Returns:
            Reasoning string
        """
        reasoning_parts = []
        
        # Bat contact
        bat_pos = caught_analysis.bat_contact.contact_position
        reasoning_parts.append(
            f"Ball contacted bat at ({bat_pos.x:.2f}m, {bat_pos.y:.2f}m, {bat_pos.z:.2f}m) "
            f"at t={caught_analysis.bat_contact.contact_timestamp:.3f}s."
        )
        
        # Flight to fielder
        catch_pos = caught_analysis.fielder_catch.catch_position
        reasoning_parts.append(
            f"Ball traveled to fielder at ({catch_pos.x:.2f}m, {catch_pos.y:.2f}m, {catch_pos.z:.2f}m) "
            f"in {caught_analysis.flight_duration:.3f}s."
        )
        
        # Fielder control
        reasoning_parts.append(
            f"Fielder maintained control for {caught_analysis.fielder_catch.control_frames} frames."
        )
        
        # Ground contact
        if caught_analysis.ground_contact_detected:
            reasoning_parts.append(
                f"Ball contacted ground (min height: {caught_analysis.min_ball_height:.2f}m) - NOT OUT."
            )
        else:
            reasoning_parts.append(
                f"No ground contact detected (min height: {caught_analysis.min_ball_height:.2f}m)."
            )
        
        # Final decision
        if not caught_analysis.ground_contact_detected and caught_analysis.fielder_catch.control_frames >= self.MIN_CONTROL_FRAMES:
            reasoning_parts.append("Caught dismissal: OUT - all conditions satisfied.")
        else:
            reasoning_parts.append("Caught dismissal: NOT OUT - conditions not satisfied.")
        
        return " ".join(reasoning_parts)
