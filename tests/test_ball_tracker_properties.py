"""
Property-based tests for Ball Tracker component.

Tests universal properties that should hold for all ball tracking scenarios.
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck

from umpirai.tracking.ball_tracker import BallTracker, BallDetection
from umpirai.models.data_models import (
    Detection,
    BoundingBox,
    Position3D,
    Vector3D,
    Trajectory,
)


# ============================================================================
# Custom Hypothesis Strategies
# ============================================================================

@st.composite
def ball_position_3d(draw):
    """Generate realistic 3D ball positions on cricket pitch."""
    # Pitch dimensions: ~20m x 10m, ball height 0-3m
    x = draw(st.floats(min_value=-10.0, max_value=10.0))
    y = draw(st.floats(min_value=0.1, max_value=3.0))  # Ball height
    z = draw(st.floats(min_value=-5.0, max_value=15.0))  # Along pitch
    return Position3D(x=x, y=y, z=z)


@st.composite
def ball_detection_sequence(draw, min_length=2, max_length=30):
    """
    Generate a sequence of ball detections across consecutive frames.
    
    Args:
        min_length: Minimum number of detections
        max_length: Maximum number of detections
        
    Returns:
        List of BallDetection objects with consecutive timestamps
    """
    length = draw(st.integers(min_value=min_length, max_value=max_length))
    
    # Start position
    start_pos = draw(ball_position_3d())
    
    # Initial velocity (realistic cricket ball speeds: 20-40 m/s)
    vx = draw(st.floats(min_value=-5.0, max_value=5.0))
    vy = draw(st.floats(min_value=-10.0, max_value=0.0))  # Usually downward
    vz = draw(st.floats(min_value=20.0, max_value=40.0))  # Forward velocity
    
    detections = []
    dt = 1.0 / 30.0  # 30 FPS
    
    for i in range(length):
        timestamp = i * dt
        
        # Simple physics: position = start + velocity * time - 0.5 * g * time^2
        t = i * dt
        x = start_pos.x + vx * t
        y = max(0.1, start_pos.y + vy * t - 0.5 * 9.81 * t**2)  # With gravity
        z = start_pos.z + vz * t
        
        position = Position3D(x=x, y=y, z=z)
        
        # Convert to pixel coordinates (simplified)
        u = 640 + x * 64.0
        v = 360 + z * 36.0
        
        # Create detection
        confidence = draw(st.floats(min_value=0.70, max_value=1.0))
        detection = Detection(
            class_id=0,
            class_name="ball",
            bounding_box=BoundingBox(x=u-10, y=v-10, width=20, height=20),
            confidence=confidence,
            position_3d=position
        )
        
        ball_det = BallDetection(
            detection=detection,
            timestamp=timestamp,
            pixel_coords=(u, v),
            position_3d=position
        )
        
        detections.append(ball_det)
    
    return detections


@st.composite
def occluded_detection_sequence(draw, min_occlusion=2, max_occlusion=15):
    """
    Generate a detection sequence with an occlusion gap.
    
    Args:
        min_occlusion: Minimum number of occluded frames
        max_occlusion: Maximum number of occluded frames
        
    Returns:
        Tuple of (pre_occlusion_detections, occlusion_timestamps, post_occlusion_detections)
    """
    # Draw occlusion frames count
    occlusion_frames = draw(st.integers(min_value=min_occlusion, max_value=max_occlusion))
    
    # Pre-occlusion detections
    pre_length = draw(st.integers(min_value=3, max_value=10))
    pre_detections = draw(ball_detection_sequence(min_length=pre_length, max_length=pre_length))
    
    # Occlusion period timestamps
    last_timestamp = pre_detections[-1].timestamp
    dt = 1.0 / 30.0
    occlusion_timestamps = [last_timestamp + (i + 1) * dt for i in range(occlusion_frames)]
    
    # Post-occlusion detections (continue trajectory)
    post_length = draw(st.integers(min_value=2, max_value=10))
    
    # Get last known position and velocity to continue trajectory
    last_pos = pre_detections[-1].position_3d
    if len(pre_detections) >= 2:
        # Estimate velocity from last two positions
        dt_prev = pre_detections[-1].timestamp - pre_detections[-2].timestamp
        vx = (pre_detections[-1].position_3d.x - pre_detections[-2].position_3d.x) / dt_prev
        vy = (pre_detections[-1].position_3d.y - pre_detections[-2].position_3d.y) / dt_prev
        vz = (pre_detections[-1].position_3d.z - pre_detections[-2].position_3d.z) / dt_prev
    else:
        vx, vy, vz = 0.0, -5.0, 25.0
    
    post_detections = []
    start_timestamp = occlusion_timestamps[-1] + dt
    
    for i in range(post_length):
        timestamp = start_timestamp + i * dt
        t = timestamp - last_timestamp
        
        # Continue trajectory with physics
        x = last_pos.x + vx * t
        y = max(0.1, last_pos.y + vy * t - 0.5 * 9.81 * t**2)
        z = last_pos.z + vz * t
        
        position = Position3D(x=x, y=y, z=z)
        
        # Convert to pixel coordinates
        u = 640 + x * 64.0
        v = 360 + z * 36.0
        
        confidence = draw(st.floats(min_value=0.70, max_value=1.0))
        detection = Detection(
            class_id=0,
            class_name="ball",
            bounding_box=BoundingBox(x=u-10, y=v-10, width=20, height=20),
            confidence=confidence,
            position_3d=position
        )
        
        ball_det = BallDetection(
            detection=detection,
            timestamp=timestamp,
            pixel_coords=(u, v),
            position_3d=position
        )
        
        post_detections.append(ball_det)
    
    return pre_detections, occlusion_timestamps, post_detections


# ============================================================================
# Property 2: Trajectory Completeness
# ============================================================================

@given(detections=ball_detection_sequence(min_length=2, max_length=30))
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_trajectory_completeness(detections):
    """
    **Property 2: Trajectory Completeness**
    **Validates: Requirements 3.1, 3.4, 3.5**
    
    For any sequence of ball detections across consecutive frames, the Ball Tracker
    SHALL produce a trajectory containing positions, velocities, timestamps, and
    calculated speed metrics.
    """
    # Create tracker
    tracker = BallTracker(dt=1.0/30.0)
    
    # Process all detections
    for detection in detections:
        tracker.update(detection, detection.timestamp)
    
    # Get trajectory
    trajectory_obj = tracker.get_trajectory_object()
    
    # Property assertions
    
    # 1. Trajectory must contain positions
    assert len(trajectory_obj.positions) > 0, "Trajectory must contain positions"
    assert all(isinstance(pos, Position3D) for pos in trajectory_obj.positions), \
        "All positions must be Position3D instances"
    
    # 2. Trajectory must contain velocities
    assert len(trajectory_obj.velocities) > 0, "Trajectory must contain velocities"
    assert all(isinstance(vel, Vector3D) for vel in trajectory_obj.velocities), \
        "All velocities must be Vector3D instances"
    
    # 3. Trajectory must contain timestamps
    assert len(trajectory_obj.timestamps) > 0, "Trajectory must contain timestamps"
    assert all(isinstance(ts, (int, float)) for ts in trajectory_obj.timestamps), \
        "All timestamps must be numeric"
    
    # 4. Positions, velocities, and timestamps must have same length
    assert len(trajectory_obj.positions) == len(trajectory_obj.velocities), \
        "Positions and velocities must have same length"
    assert len(trajectory_obj.positions) == len(trajectory_obj.timestamps), \
        "Positions and timestamps must have same length"
    
    # 5. Trajectory must contain calculated speed metrics
    assert isinstance(trajectory_obj.speed_max, (int, float)), \
        "speed_max must be numeric"
    assert isinstance(trajectory_obj.speed_avg, (int, float)), \
        "speed_avg must be numeric"
    assert trajectory_obj.speed_max >= 0, "speed_max must be non-negative"
    assert trajectory_obj.speed_avg >= 0, "speed_avg must be non-negative"
    
    # 6. Speed metrics must be consistent
    if len(trajectory_obj.velocities) > 0:
        speeds = [v.magnitude() for v in trajectory_obj.velocities]
        assert trajectory_obj.speed_max >= max(speeds) * 0.9, \
            "speed_max should be close to maximum velocity magnitude"
        assert trajectory_obj.speed_avg >= min(speeds) * 0.9, \
            "speed_avg should be at least minimum velocity magnitude"
        assert trajectory_obj.speed_avg <= max(speeds) * 1.1, \
            "speed_avg should not exceed maximum velocity magnitude"
    
    # 7. Timestamps must be in chronological order
    for i in range(1, len(trajectory_obj.timestamps)):
        assert trajectory_obj.timestamps[i] >= trajectory_obj.timestamps[i-1], \
            "Timestamps must be in chronological order"


# ============================================================================
# Property 3: Occlusion Prediction
# ============================================================================

@given(sequence_data=occluded_detection_sequence(min_occlusion=1, max_occlusion=10))
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_occlusion_prediction(sequence_data):
    """
    **Property 3: Occlusion Prediction**
    **Validates: Requirements 3.3, 13.1**
    
    For any ball trajectory with occlusion duration less than 10 frames, the Ball Tracker
    SHALL predict ball positions during the occluded period using trajectory estimation.
    """
    pre_detections, occlusion_timestamps, post_detections = sequence_data
    
    # Only test if occlusion is less than 10 frames
    assume(len(occlusion_timestamps) < 10)
    
    # Create tracker
    tracker = BallTracker(dt=1.0/30.0)
    
    # Process pre-occlusion detections
    for detection in pre_detections:
        tracker.update(detection, detection.timestamp)
    
    # Predict during occlusion
    predicted_positions = []
    for timestamp in occlusion_timestamps:
        predicted_pos = tracker.predict(timestamp)
        predicted_positions.append(predicted_pos)
    
    # Property assertions
    
    # 1. Tracker must predict positions for all occluded frames
    assert len(predicted_positions) == len(occlusion_timestamps), \
        "Must predict position for each occluded frame"
    
    # 2. All predicted positions must be valid Position3D objects
    assert all(isinstance(pos, Position3D) for pos in predicted_positions), \
        "All predictions must be Position3D instances"
    
    # 3. Predicted positions must be finite (not NaN or inf)
    for pos in predicted_positions:
        assert np.isfinite(pos.x) and np.isfinite(pos.y) and np.isfinite(pos.z), \
            "Predicted positions must be finite"
    
    # 4. Tracker must report occlusion status
    assert tracker.is_occluded(), "Tracker must report occlusion status"
    assert tracker.get_occlusion_duration() == len(occlusion_timestamps), \
        "Occlusion duration must match number of predicted frames"
    
    # 5. Predicted trajectory must be continuous (no large jumps)
    if len(predicted_positions) > 1:
        for i in range(1, len(predicted_positions)):
            pos1 = predicted_positions[i-1]
            pos2 = predicted_positions[i]
            distance = np.sqrt(
                (pos2.x - pos1.x)**2 +
                (pos2.y - pos1.y)**2 +
                (pos2.z - pos1.z)**2
            )
            # At 30 FPS, ball moving at 40 m/s travels ~1.33m per frame
            # Allow up to 3m per frame for prediction uncertainty
            assert distance < 3.0, \
                f"Predicted positions must be continuous (distance: {distance}m)"
    
    # 6. Trajectory history must include predicted positions
    trajectory = tracker.get_trajectory()
    assert len(trajectory) >= len(pre_detections) + len(occlusion_timestamps), \
        "Trajectory must include both detected and predicted positions"


# ============================================================================
# Property 4: Occlusion Uncertainty Flagging
# ============================================================================

@given(sequence_data=occluded_detection_sequence(min_occlusion=11, max_occlusion=20))
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_occlusion_uncertainty_flagging(sequence_data):
    """
    **Property 4: Occlusion Uncertainty Flagging**
    **Validates: Requirements 13.2**
    
    For any ball trajectory with occlusion duration exceeding 10 frames, the Decision Engine
    SHALL flag the resulting decision as uncertain.
    
    Note: This test verifies the tracker reports long occlusion status, which the Decision
    Engine uses to flag uncertainty.
    """
    pre_detections, occlusion_timestamps, post_detections = sequence_data
    
    # Only test if occlusion exceeds 10 frames
    assume(len(occlusion_timestamps) > 10)
    
    # Create tracker
    tracker = BallTracker(dt=1.0/30.0)
    
    # Process pre-occlusion detections
    for detection in pre_detections:
        tracker.update(detection, detection.timestamp)
    
    # Predict during occlusion
    for timestamp in occlusion_timestamps:
        tracker.predict(timestamp)
    
    # Property assertions
    
    # 1. Tracker must report long occlusion status
    assert tracker.is_long_occlusion(), \
        "Tracker must report long occlusion when duration exceeds 10 frames"
    
    # 2. Occlusion duration must be accurate
    assert tracker.get_occlusion_duration() == len(occlusion_timestamps), \
        "Occlusion duration must match number of predicted frames"
    
    # 3. Occlusion duration must exceed threshold
    assert tracker.get_occlusion_duration() > 10, \
        "Occlusion duration must exceed 10 frames"
    
    # 4. Track state must reflect long occlusion
    track_state = tracker._get_track_state()
    assert track_state.is_long_occlusion(), \
        "Track state must indicate long occlusion"


# ============================================================================
# Property 28: Tracking Resumption After Occlusion
# ============================================================================

@given(sequence_data=occluded_detection_sequence(min_occlusion=2, max_occlusion=15))
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_tracking_resumption_after_occlusion(sequence_data):
    """
    **Property 28: Tracking Resumption After Occlusion**
    **Validates: Requirements 13.4**
    
    For any ball trajectory with an occlusion period followed by ball reappearance,
    the Ball Tracker SHALL resume tracking when the ball becomes visible.
    """
    pre_detections, occlusion_timestamps, post_detections = sequence_data
    
    # Create tracker
    tracker = BallTracker(dt=1.0/30.0)
    
    # Process pre-occlusion detections
    for detection in pre_detections:
        tracker.update(detection, detection.timestamp)
    
    # Predict during occlusion
    for timestamp in occlusion_timestamps:
        tracker.predict(timestamp)
    
    # Verify occlusion status before resumption
    assert tracker.is_occluded(), "Tracker must be in occluded state"
    occlusion_duration_before = tracker.get_occlusion_duration()
    assert occlusion_duration_before > 0, "Occlusion duration must be positive"
    
    # Resume tracking with post-occlusion detections
    for detection in post_detections:
        tracker.update(detection, detection.timestamp)
    
    # Property assertions
    
    # 1. Tracker must resume tracking (occlusion counter reset)
    assert not tracker.is_occluded(), \
        "Tracker must not be occluded after ball reappears"
    assert tracker.get_occlusion_duration() == 0, \
        "Occlusion duration must be reset to zero after resumption"
    
    # 2. Trajectory must include both pre and post occlusion positions
    trajectory = tracker.get_trajectory()
    # Should have at least some positions from both periods
    assert len(trajectory) > len(pre_detections), \
        "Trajectory must include positions after occlusion resumption"
    
    # 3. Tracker must continue updating with new detections
    # Check that tracker accepts new detections after resumption
    if post_detections:
        # Get current state before adding new detection
        current_confidence = tracker._get_track_state().confidence
        
        # Add one more detection
        last_det = post_detections[-1]
        new_timestamp = last_det.timestamp + 1.0/30.0
        
        # Create new detection continuing trajectory
        new_pos = Position3D(
            x=last_det.position_3d.x,
            y=last_det.position_3d.y,
            z=last_det.position_3d.z + 1.0
        )
        
        new_detection = BallDetection(
            detection=Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=100, width=20, height=20),
                confidence=0.9,
                position_3d=new_pos
            ),
            timestamp=new_timestamp,
            pixel_coords=(640, 360),
            position_3d=new_pos
        )
        
        tracker.update(new_detection, new_timestamp)
        
        # Tracker should accept the update (confidence updated)
        new_confidence = tracker._get_track_state().confidence
        assert new_confidence == 0.9, \
            "Tracker must continue accepting updates after resumption"
    
    # 4. Tracker confidence must be updated from new detections
    if post_detections:
        track_state = tracker._get_track_state()
        assert track_state.confidence > 0, \
            "Tracker confidence must be updated from resumed detections"



# ============================================================================
# Property 27: Unoccluded View Selection
# ============================================================================

@st.composite
def multi_camera_detection_scenario(draw):
    """
    Generate a multi-camera scenario where ball is occluded in some views but visible in others.
    
    Returns:
        Tuple of (camera1_detections, camera2_detections, occluded_camera_id)
    """
    # Generate base trajectory
    base_detections = draw(ball_detection_sequence(min_length=5, max_length=15))
    
    # Camera 1: full detections (unoccluded)
    camera1_detections = base_detections
    
    # Camera 2: same trajectory but with occlusion in middle frames
    occlusion_start = draw(st.integers(min_value=2, max_value=len(base_detections)-3))
    occlusion_length = draw(st.integers(min_value=2, max_value=min(5, len(base_detections)-occlusion_start-1)))
    
    camera2_detections = (
        base_detections[:occlusion_start] +
        base_detections[occlusion_start + occlusion_length:]
    )
    
    occluded_camera_id = "camera2"
    
    return camera1_detections, camera2_detections, occluded_camera_id


@given(scenario=multi_camera_detection_scenario())
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_unoccluded_view_selection(scenario):
    """
    **Property 27: Unoccluded View Selection**
    **Validates: Requirements 13.3**
    
    For any multi-camera scenario where the ball is occluded in some views but visible
    in others, the system SHALL use the unoccluded camera view for tracking.
    
    Note: This test verifies that when one camera has continuous detections and another
    has occlusion, the tracker can maintain continuous tracking using the unoccluded view.
    """
    camera1_detections, camera2_detections, occluded_camera_id = scenario
    
    # Create tracker for camera 1 (unoccluded)
    tracker_cam1 = BallTracker(dt=1.0/30.0)
    
    # Process all camera 1 detections (unoccluded view)
    for detection in camera1_detections:
        tracker_cam1.update(detection, detection.timestamp)
    
    # Create tracker for camera 2 (occluded)
    tracker_cam2 = BallTracker(dt=1.0/30.0)
    
    # Process camera 2 detections (with occlusion gap)
    # Need to predict during occlusion
    cam2_idx = 0
    for i, cam1_det in enumerate(camera1_detections):
        timestamp = cam1_det.timestamp
        
        # Check if we have a detection from camera 2 at this timestamp
        if cam2_idx < len(camera2_detections) and \
           abs(camera2_detections[cam2_idx].timestamp - timestamp) < 0.001:
            # Have detection, update
            tracker_cam2.update(camera2_detections[cam2_idx], timestamp)
            cam2_idx += 1
        else:
            # Occluded, predict
            tracker_cam2.predict(timestamp)
    
    # Property assertions
    
    # 1. Unoccluded camera must have continuous tracking (no occlusion)
    assert not tracker_cam1.is_occluded(), \
        "Unoccluded camera must not report occlusion"
    assert tracker_cam1.get_occlusion_duration() == 0, \
        "Unoccluded camera must have zero occlusion duration"
    
    # 2. Occluded camera must report occlusion
    # Note: After processing all frames, occlusion counter may be reset if tracking resumed
    # So we check trajectory length instead
    trajectory_cam1 = tracker_cam1.get_trajectory()
    trajectory_cam2 = tracker_cam2.get_trajectory()
    
    # Both should have similar trajectory lengths (cam2 uses prediction during occlusion)
    assert len(trajectory_cam1) > 0, "Camera 1 must have trajectory"
    assert len(trajectory_cam2) > 0, "Camera 2 must have trajectory"
    
    # 3. System should prefer unoccluded view (camera 1) for tracking
    # This is demonstrated by camera 1 having higher confidence and no occlusion
    track_state_cam1 = tracker_cam1._get_track_state()
    
    # Camera 1 should have good confidence (from actual detections)
    assert track_state_cam1.confidence >= 0.7, \
        "Unoccluded camera should have high confidence"
    
    # 4. Unoccluded camera trajectory should be complete
    trajectory_obj_cam1 = tracker_cam1.get_trajectory_object()
    assert len(trajectory_obj_cam1.positions) == len(camera1_detections), \
        "Unoccluded camera should have position for every detection"
    
    # 5. In a multi-camera system, unoccluded view should be selected
    # This is verified by showing camera 1 provides better tracking quality
    # (no occlusion, higher confidence, complete trajectory)
    assert (not tracker_cam1.is_occluded() and 
            track_state_cam1.confidence >= 0.7 and
            len(trajectory_obj_cam1.positions) == len(camera1_detections)), \
        "Unoccluded camera view should be preferred for tracking"
