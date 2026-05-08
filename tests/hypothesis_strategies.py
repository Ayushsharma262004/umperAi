"""
Custom Hypothesis strategies for property-based testing of the UmpirAI system.

This module provides specialized generators for cricket-specific data structures
with realistic physics constraints and cricket rule compliance.
"""

import numpy as np
from hypothesis import strategies as st
from hypothesis.strategies import composite

from umpirai.models.data_models import (
    Position3D,
    Vector3D,
    BoundingBox,
    Frame,
    Detection,
    DetectionResult,
    TrackState,
    Trajectory,
    Decision,
    EventType,
    DetectionClass,
    VideoReference,
    MatchContext,
)
from umpirai.calibration.calibration_manager import CalibrationData, Point2D


# ============================================================================
# Physics Constants for Cricket Ball Trajectories
# ============================================================================

GRAVITY = 9.81  # m/s²
AIR_RESISTANCE_COEFFICIENT = 0.47  # Drag coefficient for sphere
BALL_MASS = 0.156  # kg (cricket ball)
BALL_RADIUS = 0.036  # m (cricket ball)

# Typical cricket ball speeds
MIN_BALL_SPEED = 20.0  # m/s (~72 km/h, slow spin bowling)
MAX_BALL_SPEED = 45.0  # m/s (~162 km/h, fast bowling)

# Pitch dimensions (standard cricket pitch)
PITCH_LENGTH = 20.12  # m (22 yards)
PITCH_WIDTH = 3.05  # m (10 feet)
CREASE_DISTANCE = 1.22  # m (4 feet from stumps)


# ============================================================================
# Basic Building Blocks
# ============================================================================

@composite
def position_3d_strategy(draw, 
                        x_range=(-10.0, 10.0),
                        y_range=(0.0, 3.0),
                        z_range=(-5.0, 25.0)):
    """
    Generate valid 3D positions.
    
    Default ranges represent typical cricket pitch coordinates:
    - x: lateral position across pitch width
    - y: height above ground
    - z: distance along pitch length
    """
    x = draw(st.floats(min_value=x_range[0], max_value=x_range[1], 
                      allow_nan=False, allow_infinity=False))
    y = draw(st.floats(min_value=y_range[0], max_value=y_range[1],
                      allow_nan=False, allow_infinity=False))
    z = draw(st.floats(min_value=z_range[0], max_value=z_range[1],
                      allow_nan=False, allow_infinity=False))
    return Position3D(x=x, y=y, z=z)


@composite
def vector_3d_strategy(draw,
                      vx_range=(-10.0, 10.0),
                      vy_range=(-20.0, 20.0),
                      vz_range=(-50.0, 50.0)):
    """
    Generate valid 3D vectors.
    
    Default ranges represent typical cricket ball velocities in m/s.
    """
    vx = draw(st.floats(min_value=vx_range[0], max_value=vx_range[1],
                       allow_nan=False, allow_infinity=False))
    vy = draw(st.floats(min_value=vy_range[0], max_value=vy_range[1],
                       allow_nan=False, allow_infinity=False))
    vz = draw(st.floats(min_value=vz_range[0], max_value=vz_range[1],
                       allow_nan=False, allow_infinity=False))
    return Vector3D(vx=vx, vy=vy, vz=vz)


@composite
def bounding_box_strategy(draw,
                         x_range=(0, 1280),
                         y_range=(0, 720),
                         width_range=(10, 200),
                         height_range=(10, 200)):
    """Generate valid bounding boxes within image dimensions."""
    x = draw(st.integers(min_value=x_range[0], max_value=x_range[1] - width_range[0]))
    y = draw(st.integers(min_value=y_range[0], max_value=y_range[1] - height_range[0]))
    width = draw(st.integers(min_value=width_range[0], max_value=min(width_range[1], x_range[1] - x)))
    height = draw(st.integers(min_value=height_range[0], max_value=min(height_range[1], y_range[1] - y)))
    return BoundingBox(x=x, y=y, width=width, height=height)


# ============================================================================
# Cricket-Specific Strategies
# ============================================================================

@composite
def cricket_ball_trajectory(draw, 
                           release_height_range=(1.8, 2.5),
                           release_speed_range=(MIN_BALL_SPEED, MAX_BALL_SPEED),
                           release_angle_range=(-15, 15),  # degrees from horizontal
                           num_points_range=(10, 30)):
    """
    Generate realistic cricket ball trajectories with physics.
    
    This strategy creates trajectories that follow realistic physics including:
    - Gravity
    - Air resistance
    - Typical cricket ball release parameters
    
    Returns a Trajectory object with positions, velocities, and timestamps.
    """
    # Release parameters
    release_height = draw(st.floats(min_value=release_height_range[0], 
                                    max_value=release_height_range[1]))
    release_speed = draw(st.floats(min_value=release_speed_range[0],
                                   max_value=release_speed_range[1]))
    release_angle = draw(st.floats(min_value=release_angle_range[0],
                                   max_value=release_angle_range[1]))
    
    # Lateral deviation (for spin/swing)
    lateral_velocity = draw(st.floats(min_value=-3.0, max_value=3.0))
    
    # Convert angle to radians
    angle_rad = np.deg2rad(release_angle)
    
    # Initial velocity components
    vz_initial = release_speed * np.cos(angle_rad)  # Forward velocity
    vy_initial = release_speed * np.sin(angle_rad)  # Vertical velocity
    vx_initial = lateral_velocity  # Lateral velocity
    
    # Initial position (bowler's release point)
    x0 = draw(st.floats(min_value=-0.5, max_value=0.5))  # Slight lateral offset
    y0 = release_height
    z0 = 0.0  # Release at bowler's end
    
    # Simulate trajectory
    num_points = draw(st.integers(min_value=num_points_range[0], 
                                  max_value=num_points_range[1]))
    dt = 0.033  # ~30 FPS
    
    positions = []
    velocities = []
    timestamps = []
    
    x, y, z = x0, y0, z0
    vx, vy, vz = vx_initial, vy_initial, vz_initial
    t = 0.0
    
    for i in range(num_points):
        # Store current state
        positions.append(Position3D(x=x, y=y, z=z))
        velocities.append(Vector3D(vx=vx, vy=vy, vz=vz))
        timestamps.append(t)
        
        # Stop if ball hits ground or goes past pitch
        if y <= 0.0 or z > PITCH_LENGTH + 5.0:
            break
        
        # Calculate air resistance
        speed = np.sqrt(vx**2 + vy**2 + vz**2)
        if speed > 0:
            drag_force = 0.5 * AIR_RESISTANCE_COEFFICIENT * speed**2
            drag_accel = drag_force / BALL_MASS
            
            # Drag acceleration components (opposite to velocity)
            ax = -drag_accel * (vx / speed) if speed > 0 else 0
            ay = -GRAVITY - drag_accel * (vy / speed) if speed > 0 else -GRAVITY
            az = -drag_accel * (vz / speed) if speed > 0 else 0
        else:
            ax, ay, az = 0, -GRAVITY, 0
        
        # Update velocity
        vx += ax * dt
        vy += ay * dt
        vz += az * dt
        
        # Update position
        x += vx * dt
        y += vy * dt
        z += vz * dt
        
        t += dt
    
    # Calculate speed metrics
    speeds = [np.sqrt(v.vx**2 + v.vy**2 + v.vz**2) for v in velocities]
    speed_max = max(speeds) if speeds else 0.0
    speed_avg = sum(speeds) / len(speeds) if speeds else 0.0
    
    # Determine end position (where ball lands or last tracked point)
    end_position = positions[-1] if positions else None
    
    return Trajectory(
        positions=positions,
        timestamps=timestamps,
        velocities=velocities,
        start_position=positions[0] if positions else Position3D(x=x0, y=y0, z=z0),
        end_position=end_position,
        speed_max=speed_max,
        speed_avg=speed_avg
    )


@composite
def batsman_stance(draw,
                  z_position_range=(PITCH_LENGTH * 0.7, PITCH_LENGTH * 0.9),
                  lateral_range=(-1.5, 1.5)):
    """
    Generate valid batsman stance positions.
    
    Batsman typically stands near the batting crease (around 18-19m from bowler).
    Lateral position varies based on stance and shot selection.
    """
    x = draw(st.floats(min_value=lateral_range[0], max_value=lateral_range[1]))
    y = draw(st.floats(min_value=0.0, max_value=0.1))  # Feet on ground
    z = draw(st.floats(min_value=z_position_range[0], max_value=z_position_range[1]))
    
    return Position3D(x=x, y=y, z=z)


@composite
def bowler_foot_position(draw,
                        crease_z=CREASE_DISTANCE,
                        behind_range=(0.0, 0.5),  # Behind crease (legal)
                        over_range=(0.01, 0.3)):   # Over crease (no ball) - minimum 0.01 to ensure > crease
    """
    Generate bowler foot positions relative to crease line.
    
    Args:
        crease_z: Z-coordinate of the bowling crease
        behind_range: Range for legal deliveries (foot behind crease)
        over_range: Range for no balls (foot over crease)
    
    Returns a tuple of (position, is_legal) where is_legal indicates
    if the foot position would result in a legal delivery.
    """
    is_legal = draw(st.booleans())
    
    x = draw(st.floats(min_value=-0.5, max_value=0.5))  # Lateral position
    y = 0.0  # Foot on ground
    
    if is_legal:
        # Foot behind crease
        distance_behind = draw(st.floats(min_value=behind_range[0], 
                                        max_value=behind_range[1]))
        z = crease_z - distance_behind
    else:
        # Foot over crease (no ball)
        distance_over = draw(st.floats(min_value=over_range[0],
                                      max_value=over_range[1]))
        z = crease_z + distance_over
    
    position = Position3D(x=x, y=y, z=z)
    return position, is_legal


@composite
def detection_with_confidence(draw,
                              class_id=None,
                              confidence_range=(0.0, 1.0),
                              include_3d=True):
    """
    Generate Detection objects with specified confidence ranges.
    
    Useful for testing confidence threshold logic and uncertain detection handling.
    """
    if class_id is None:
        class_id = draw(st.integers(min_value=0, max_value=7))
    
    class_names = ["ball", "stumps", "crease", "batsman", "bowler", 
                   "fielder", "pitch_boundary", "wide_guideline"]
    class_name = class_names[class_id]
    
    bbox = draw(bounding_box_strategy())
    confidence = draw(st.floats(min_value=confidence_range[0],
                                max_value=confidence_range[1]))
    
    position_3d = None
    if include_3d:
        # Only ball detections typically have 3D positions
        if class_id == 0:  # ball
            position_3d = draw(position_3d_strategy())
    
    return Detection(
        class_id=class_id,
        class_name=class_name,
        bounding_box=bbox,
        confidence=confidence,
        position_3d=position_3d
    )


@composite
def multi_camera_detections(draw,
                            num_cameras_range=(2, 4),
                            same_object=True):
    """
    Generate synchronized multi-camera detections.
    
    Args:
        num_cameras_range: Range for number of cameras
        same_object: If True, all cameras detect the same object (for fusion testing)
    
    Returns a dictionary mapping camera_id to Detection.
    """
    num_cameras = draw(st.integers(min_value=num_cameras_range[0],
                                   max_value=num_cameras_range[1]))
    
    detections = {}
    
    if same_object:
        # All cameras detect the same object with varying confidence
        class_id = draw(st.integers(min_value=0, max_value=7))
        base_confidence = draw(st.floats(min_value=0.7, max_value=0.95))
        
        for i in range(num_cameras):
            camera_id = f"cam{i+1}"
            # Add noise to confidence
            confidence = base_confidence + draw(st.floats(min_value=-0.1, max_value=0.1))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
            
            detection = draw(detection_with_confidence(
                class_id=class_id,
                confidence_range=(confidence, confidence)
            ))
            detections[camera_id] = detection
    else:
        # Each camera may detect different objects
        for i in range(num_cameras):
            camera_id = f"cam{i+1}"
            detection = draw(detection_with_confidence())
            detections[camera_id] = detection
    
    return detections


@composite
def occluded_trajectory(draw,
                       occlusion_start_range=(5, 15),
                       occlusion_duration_range=(1, 20),
                       total_length_range=(20, 40)):
    """
    Generate ball trajectories with occlusion gaps.
    
    Returns a tuple of (full_trajectory, visible_positions, occlusion_info)
    where occlusion_info contains start_frame and duration.
    """
    # Generate full trajectory
    full_trajectory = draw(cricket_ball_trajectory(num_points_range=total_length_range))
    
    if len(full_trajectory.positions) < 10:
        # Trajectory too short for occlusion
        return full_trajectory, full_trajectory.positions, None
    
    # Determine occlusion period
    occlusion_start = draw(st.integers(
        min_value=occlusion_start_range[0],
        max_value=min(occlusion_start_range[1], len(full_trajectory.positions) - 5)
    ))
    
    max_duration = min(occlusion_duration_range[1], 
                      len(full_trajectory.positions) - occlusion_start - 1)
    occlusion_duration = draw(st.integers(
        min_value=occlusion_duration_range[0],
        max_value=max_duration
    ))
    
    occlusion_end = occlusion_start + occlusion_duration
    
    # Create visible positions (excluding occluded frames)
    visible_positions = (
        full_trajectory.positions[:occlusion_start] +
        full_trajectory.positions[occlusion_end:]
    )
    
    occlusion_info = {
        'start_frame': occlusion_start,
        'duration': occlusion_duration,
        'end_frame': occlusion_end
    }
    
    return full_trajectory, visible_positions, occlusion_info


# ============================================================================
# Frame and Detection Strategies
# ============================================================================

@composite
def frame_strategy(draw, camera_id=None):
    """Generate valid video frames."""
    if camera_id is None:
        camera_id = draw(st.text(min_size=1, max_size=10, 
                                alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    
    frame_number = draw(st.integers(min_value=0, max_value=100000))
    timestamp = draw(st.floats(min_value=0.0, max_value=10000.0))
    
    # Generate realistic image
    image = np.random.randint(0, 256, (720, 1280, 3), dtype=np.uint8)
    
    metadata = draw(st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(st.integers(), st.floats(), st.text()),
        max_size=5
    ))
    
    return Frame(
        camera_id=camera_id,
        frame_number=frame_number,
        timestamp=timestamp,
        image=image,
        metadata=metadata
    )


@composite
def detection_result_strategy(draw, num_detections_range=(0, 10)):
    """Generate DetectionResult with multiple detections."""
    frame = draw(frame_strategy())
    
    num_detections = draw(st.integers(min_value=num_detections_range[0],
                                     max_value=num_detections_range[1]))
    
    detections = [draw(detection_with_confidence()) for _ in range(num_detections)]
    
    processing_time = draw(st.floats(min_value=0.001, max_value=1.0))
    
    return DetectionResult(
        frame=frame,
        detections=detections,
        processing_time_ms=processing_time * 1000
    )


# ============================================================================
# Decision and Match Context Strategies
# ============================================================================

@composite
def decision_strategy(draw, event_type=None, confidence=None):
    """Generate Decision objects."""
    if event_type is None:
        event_type = draw(st.sampled_from(list(EventType)))
    
    if confidence is None:
        confidence = draw(st.floats(min_value=0.0, max_value=1.0))
    
    decision_id = draw(st.text(min_size=1, max_size=20,
                              alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    
    timestamp = draw(st.floats(min_value=0.0, max_value=10000.0))
    trajectory = draw(cricket_ball_trajectory())
    
    # Generate some detections
    num_detections = draw(st.integers(min_value=1, max_value=5))
    detections = [draw(detection_with_confidence()) for _ in range(num_detections)]
    
    reasoning = f"Decision based on {event_type.value} detection"
    
    # Generate video references
    num_refs = draw(st.integers(min_value=1, max_value=3))
    video_references = []
    for i in range(num_refs):
        ref_timestamp = timestamp + draw(st.floats(min_value=0.0, max_value=0.1))  # Ensure non-negative
        video_references.append(VideoReference(
            camera_id=f"cam{i+1}",
            frame_number=draw(st.integers(min_value=0, max_value=10000)),
            timestamp=ref_timestamp
        ))
    
    requires_review = confidence < 0.8
    
    return Decision(
        decision_id=decision_id,
        event_type=event_type,
        confidence=confidence,
        timestamp=timestamp,
        trajectory=trajectory,
        detections=detections,
        reasoning=reasoning,
        video_references=video_references,
        requires_review=requires_review
    )


@composite
def match_context_strategy(draw):
    """Generate MatchContext objects."""
    over_number = draw(st.integers(min_value=1, max_value=50))
    ball_number = draw(st.integers(min_value=1, max_value=6))
    legal_deliveries = draw(st.integers(min_value=0, max_value=6))
    
    batsman_stance_pos = draw(batsman_stance())
    
    # Generate calibration data as dictionary (as expected by MatchContext)
    calibration = {
        'calibration_name': "test_calibration",
        'created_at': "2024-01-01T00:00:00Z",
        'pitch_boundary': [
            (100.0, 100.0),
            (1180.0, 100.0),
            (1180.0, 620.0),
            (100.0, 620.0)
        ],
        'crease_lines': {
            'bowling': [(100.0, 200.0), (1180.0, 200.0)],
            'batting': [(100.0, 520.0), (1180.0, 520.0)]
        },
        'wide_guidelines': {'left': -1.0, 'right': 1.0},
        'stump_positions': {
            'bowling': (640.0, 200.0),
            'batting': (640.0, 520.0)
        },
        'camera_calibrations': {}
    }
    
    return MatchContext(
        over_number=over_number,
        ball_number=ball_number,
        legal_deliveries=legal_deliveries,
        batsman_stance=batsman_stance_pos,
        calibration=calibration
    )


# ============================================================================
# Exported Strategy Collections
# ============================================================================

# Export commonly used strategies for easy import
__all__ = [
    'position_3d_strategy',
    'vector_3d_strategy',
    'bounding_box_strategy',
    'cricket_ball_trajectory',
    'batsman_stance',
    'bowler_foot_position',
    'detection_with_confidence',
    'multi_camera_detections',
    'occluded_trajectory',
    'frame_strategy',
    'detection_result_strategy',
    'decision_strategy',
    'match_context_strategy',
]
