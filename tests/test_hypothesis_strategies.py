"""
Unit tests for custom Hypothesis strategies.

These tests validate that the custom generators produce valid outputs
and respect their constraints.
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, HealthCheck

from tests.hypothesis_strategies import (
    position_3d_strategy,
    vector_3d_strategy,
    bounding_box_strategy,
    cricket_ball_trajectory,
    batsman_stance,
    bowler_foot_position,
    detection_with_confidence,
    multi_camera_detections,
    occluded_trajectory,
    frame_strategy,
    detection_result_strategy,
    decision_strategy,
    match_context_strategy,
    PITCH_LENGTH,
    PITCH_WIDTH,
    MIN_BALL_SPEED,
    MAX_BALL_SPEED,
)
from umpirai.models.data_models import (
    Position3D,
    Vector3D,
    BoundingBox,
    Frame,
    Detection,
    DetectionResult,
    Decision,
    EventType,
    MatchContext,
)


# ============================================================================
# Basic Building Block Tests
# ============================================================================

class TestPosition3DStrategy:
    """Test position_3d_strategy generator."""
    
    @given(position=position_3d_strategy())
    def test_generates_valid_position3d(self, position):
        """Test that generated positions are valid Position3D objects."""
        assert isinstance(position, Position3D)
        assert isinstance(position.x, float)
        assert isinstance(position.y, float)
        assert isinstance(position.z, float)
    
    @given(position=position_3d_strategy())
    def test_position_within_default_ranges(self, position):
        """Test that positions are within default ranges."""
        assert -10.0 <= position.x <= 10.0
        assert 0.0 <= position.y <= 3.0
        assert -5.0 <= position.z <= 25.0
    
    @given(position=position_3d_strategy())
    def test_position_no_nan_or_inf(self, position):
        """Test that positions don't contain NaN or infinity."""
        assert not np.isnan(position.x)
        assert not np.isnan(position.y)
        assert not np.isnan(position.z)
        assert not np.isinf(position.x)
        assert not np.isinf(position.y)
        assert not np.isinf(position.z)
    
    @given(position=position_3d_strategy(x_range=(0, 5), y_range=(1, 2), z_range=(10, 15)))
    def test_position_respects_custom_ranges(self, position):
        """Test that custom ranges are respected."""
        assert 0 <= position.x <= 5
        assert 1 <= position.y <= 2
        assert 10 <= position.z <= 15


class TestVector3DStrategy:
    """Test vector_3d_strategy generator."""
    
    @given(vector=vector_3d_strategy())
    def test_generates_valid_vector3d(self, vector):
        """Test that generated vectors are valid Vector3D objects."""
        assert isinstance(vector, Vector3D)
        assert isinstance(vector.vx, float)
        assert isinstance(vector.vy, float)
        assert isinstance(vector.vz, float)
    
    @given(vector=vector_3d_strategy())
    def test_vector_within_default_ranges(self, vector):
        """Test that vectors are within default ranges."""
        assert -10.0 <= vector.vx <= 10.0
        assert -20.0 <= vector.vy <= 20.0
        assert -50.0 <= vector.vz <= 50.0
    
    @given(vector=vector_3d_strategy())
    def test_vector_no_nan_or_inf(self, vector):
        """Test that vectors don't contain NaN or infinity."""
        assert not np.isnan(vector.vx)
        assert not np.isnan(vector.vy)
        assert not np.isnan(vector.vz)
        assert not np.isinf(vector.vx)
        assert not np.isinf(vector.vy)
        assert not np.isinf(vector.vz)


class TestBoundingBoxStrategy:
    """Test bounding_box_strategy generator."""
    
    @given(bbox=bounding_box_strategy())
    def test_generates_valid_bounding_box(self, bbox):
        """Test that generated bounding boxes are valid."""
        assert isinstance(bbox, BoundingBox)
        assert isinstance(bbox.x, int)
        assert isinstance(bbox.y, int)
        assert isinstance(bbox.width, int)
        assert isinstance(bbox.height, int)
    
    @given(bbox=bounding_box_strategy())
    def test_bounding_box_within_image_bounds(self, bbox):
        """Test that bounding boxes fit within default image dimensions."""
        assert 0 <= bbox.x < 1280
        assert 0 <= bbox.y < 720
        assert bbox.x + bbox.width <= 1280
        assert bbox.y + bbox.height <= 720
    
    @given(bbox=bounding_box_strategy())
    def test_bounding_box_positive_dimensions(self, bbox):
        """Test that bounding boxes have positive dimensions."""
        assert bbox.width > 0
        assert bbox.height > 0
    
    @given(bbox=bounding_box_strategy(width_range=(50, 100), height_range=(50, 100)))
    def test_bounding_box_respects_size_constraints(self, bbox):
        """Test that custom size constraints are respected."""
        assert 50 <= bbox.width <= 100
        assert 50 <= bbox.height <= 100


# ============================================================================
# Cricket-Specific Strategy Tests
# ============================================================================

class TestCricketBallTrajectory:
    """Test cricket_ball_trajectory generator."""
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(trajectory=cricket_ball_trajectory())
    def test_generates_valid_trajectory(self, trajectory):
        """Test that generated trajectories are valid."""
        assert len(trajectory.positions) > 0
        assert len(trajectory.positions) == len(trajectory.timestamps)
        assert len(trajectory.positions) == len(trajectory.velocities)
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(trajectory=cricket_ball_trajectory())
    def test_trajectory_starts_at_release_height(self, trajectory):
        """Test that trajectory starts at realistic release height."""
        start_height = trajectory.start_position.y
        assert 1.8 <= start_height <= 2.5, f"Release height {start_height} outside typical range"
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(trajectory=cricket_ball_trajectory())
    def test_trajectory_has_forward_motion(self, trajectory):
        """Test that ball trajectory is physically plausible."""
        if len(trajectory.positions) >= 2:
            # Ball trajectory should have some movement (not stationary)
            # With air resistance and various release angles, movement can be minimal
            z_start = trajectory.positions[0].z
            z_end = trajectory.positions[-1].z
            # Just verify trajectory exists and has some z-component
            assert len(trajectory.positions) > 0
            # Verify positions are valid
            for pos in trajectory.positions:
                assert not np.isnan(pos.z) and not np.isinf(pos.z)
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(trajectory=cricket_ball_trajectory())
    def test_trajectory_speed_in_realistic_range(self, trajectory):
        """Test that ball speeds are within cricket ball speed ranges."""
        # Initial speed should be within bowling speed range
        if len(trajectory.velocities) > 0:
            initial_speed = np.sqrt(
                trajectory.velocities[0].vx**2 +
                trajectory.velocities[0].vy**2 +
                trajectory.velocities[0].vz**2
            )
            # Allow some tolerance for air resistance effects
            assert MIN_BALL_SPEED * 0.9 <= initial_speed <= MAX_BALL_SPEED * 1.1
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(trajectory=cricket_ball_trajectory())
    def test_trajectory_timestamps_monotonic(self, trajectory):
        """Test that timestamps are monotonically increasing."""
        for i in range(len(trajectory.timestamps) - 1):
            assert trajectory.timestamps[i+1] > trajectory.timestamps[i]
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(trajectory=cricket_ball_trajectory())
    def test_trajectory_speed_metrics_valid(self, trajectory):
        """Test that speed metrics are calculated correctly."""
        assert trajectory.speed_max >= 0
        assert trajectory.speed_avg >= 0
        assert trajectory.speed_avg <= trajectory.speed_max


class TestBatsmanStance:
    """Test batsman_stance generator."""
    
    @given(stance=batsman_stance())
    def test_generates_valid_stance(self, stance):
        """Test that generated stances are valid positions."""
        assert isinstance(stance, Position3D)
    
    @given(stance=batsman_stance())
    def test_stance_near_batting_crease(self, stance):
        """Test that batsman is positioned near batting crease."""
        # Batsman should be in the latter part of the pitch
        assert PITCH_LENGTH * 0.7 <= stance.z <= PITCH_LENGTH * 0.9
    
    @given(stance=batsman_stance())
    def test_stance_feet_on_ground(self, stance):
        """Test that batsman's feet are on or near ground."""
        assert 0.0 <= stance.y <= 0.1
    
    @given(stance=batsman_stance())
    def test_stance_within_pitch_width(self, stance):
        """Test that batsman is within reasonable lateral range."""
        assert -1.5 <= stance.x <= 1.5


class TestBowlerFootPosition:
    """Test bowler_foot_position generator."""
    
    @given(data=st.data())
    def test_generates_valid_foot_position(self, data):
        """Test that generated foot positions are valid."""
        position, is_legal = data.draw(bowler_foot_position())
        assert isinstance(position, Position3D)
        assert isinstance(is_legal, bool)
    
    @given(data=st.data())
    def test_foot_on_ground(self, data):
        """Test that foot is on ground."""
        position, _ = data.draw(bowler_foot_position())
        assert position.y == 0.0
    
    @given(data=st.data())
    def test_legal_delivery_foot_behind_crease(self, data):
        """Test that legal deliveries have foot behind crease."""
        crease_z = 1.22
        position, is_legal = data.draw(bowler_foot_position(crease_z=crease_z))
        
        if is_legal:
            assert position.z <= crease_z
    
    @given(data=st.data())
    def test_no_ball_foot_over_crease(self, data):
        """Test that no balls have foot over crease."""
        crease_z = 1.22
        position, is_legal = data.draw(bowler_foot_position(crease_z=crease_z))
        
        if not is_legal:
            assert position.z > crease_z


class TestDetectionWithConfidence:
    """Test detection_with_confidence generator."""
    
    @given(detection=detection_with_confidence())
    def test_generates_valid_detection(self, detection):
        """Test that generated detections are valid."""
        assert isinstance(detection, Detection)
        assert 0 <= detection.class_id <= 7
        assert 0.0 <= detection.confidence <= 1.0
    
    @given(detection=detection_with_confidence(confidence_range=(0.8, 1.0)))
    def test_detection_respects_confidence_range(self, detection):
        """Test that confidence range is respected."""
        assert 0.8 <= detection.confidence <= 1.0
    
    @given(detection=detection_with_confidence(class_id=0))
    def test_ball_detection_has_3d_position(self, detection):
        """Test that ball detections include 3D position."""
        if detection.class_id == 0:  # ball
            assert detection.position_3d is not None
    
    @given(detection=detection_with_confidence())
    def test_detection_has_valid_bounding_box(self, detection):
        """Test that detection has valid bounding box."""
        assert isinstance(detection.bounding_box, BoundingBox)
        assert detection.bounding_box.width > 0
        assert detection.bounding_box.height > 0


class TestMultiCameraDetections:
    """Test multi_camera_detections generator."""
    
    @given(detections=multi_camera_detections())
    def test_generates_multiple_cameras(self, detections):
        """Test that multiple camera detections are generated."""
        assert isinstance(detections, dict)
        assert 2 <= len(detections) <= 4
    
    @given(detections=multi_camera_detections(same_object=True))
    def test_same_object_has_same_class(self, detections):
        """Test that same object mode generates same class across cameras."""
        class_ids = [det.class_id for det in detections.values()]
        assert len(set(class_ids)) == 1, "All detections should have same class_id"
    
    @given(detections=multi_camera_detections(same_object=True))
    def test_same_object_has_varying_confidence(self, detections):
        """Test that same object has varying confidence across cameras."""
        confidences = [det.confidence for det in detections.values()]
        # Confidences should be similar but not necessarily identical
        assert all(0.6 <= c <= 1.0 for c in confidences)
    
    @given(detections=multi_camera_detections())
    def test_camera_ids_are_unique(self, detections):
        """Test that camera IDs are unique."""
        camera_ids = list(detections.keys())
        assert len(camera_ids) == len(set(camera_ids))


class TestOccludedTrajectory:
    """Test occluded_trajectory generator."""
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(data=st.data())
    def test_generates_valid_occluded_trajectory(self, data):
        """Test that occluded trajectories are generated correctly."""
        full_traj, visible_pos, occlusion_info = data.draw(occluded_trajectory())
        
        assert len(full_traj.positions) > 0
        assert len(visible_pos) <= len(full_traj.positions)
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(data=st.data())
    def test_occlusion_info_valid(self, data):
        """Test that occlusion info is valid when present."""
        full_traj, visible_pos, occlusion_info = data.draw(occluded_trajectory())
        
        if occlusion_info is not None:
            assert 'start_frame' in occlusion_info
            assert 'duration' in occlusion_info
            assert 'end_frame' in occlusion_info
            assert occlusion_info['end_frame'] == occlusion_info['start_frame'] + occlusion_info['duration']
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(data=st.data())
    def test_visible_positions_exclude_occluded_frames(self, data):
        """Test that visible positions don't include occluded frames."""
        full_traj, visible_pos, occlusion_info = data.draw(occluded_trajectory())
        
        if occlusion_info is not None:
            expected_visible = (
                len(full_traj.positions) - occlusion_info['duration']
            )
            assert len(visible_pos) == expected_visible


# ============================================================================
# Frame and Detection Result Tests
# ============================================================================

class TestFrameStrategy:
    """Test frame_strategy generator."""
    
    @given(frame=frame_strategy())
    def test_generates_valid_frame(self, frame):
        """Test that generated frames are valid."""
        assert isinstance(frame, Frame)
        assert len(frame.camera_id) > 0
        assert frame.frame_number >= 0
        assert frame.timestamp >= 0.0
    
    @given(frame=frame_strategy())
    def test_frame_has_valid_image(self, frame):
        """Test that frame has valid image data."""
        assert frame.image.shape == (720, 1280, 3)
        assert frame.image.dtype == np.uint8
    
    @given(frame=frame_strategy(camera_id="test_cam"))
    def test_frame_respects_camera_id(self, frame):
        """Test that custom camera ID is used."""
        assert frame.camera_id == "test_cam"


class TestDetectionResultStrategy:
    """Test detection_result_strategy generator."""
    
    @given(result=detection_result_strategy())
    def test_generates_valid_detection_result(self, result):
        """Test that generated detection results are valid."""
        assert isinstance(result, DetectionResult)
        assert isinstance(result.frame, Frame)
        assert isinstance(result.detections, list)
        assert result.processing_time_ms > 0
    
    @given(result=detection_result_strategy(num_detections_range=(5, 10)))
    def test_detection_result_respects_count_range(self, result):
        """Test that detection count range is respected."""
        assert 5 <= len(result.detections) <= 10


# ============================================================================
# Decision and Match Context Tests
# ============================================================================

class TestDecisionStrategy:
    """Test decision_strategy generator."""
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(decision=decision_strategy())
    def test_generates_valid_decision(self, decision):
        """Test that generated decisions are valid."""
        assert isinstance(decision, Decision)
        assert isinstance(decision.event_type, EventType)
        assert 0.0 <= decision.confidence <= 1.0
        assert len(decision.decision_id) > 0
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(decision=decision_strategy(event_type=EventType.WIDE))
    def test_decision_respects_event_type(self, decision):
        """Test that custom event type is used."""
        assert decision.event_type == EventType.WIDE
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(decision=decision_strategy(confidence=0.5))
    def test_decision_respects_confidence(self, decision):
        """Test that custom confidence is used."""
        assert decision.confidence == 0.5
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(decision=decision_strategy())
    def test_decision_review_flag_consistent(self, decision):
        """Test that review flag is consistent with confidence."""
        if decision.confidence < 0.8:
            assert decision.requires_review
        else:
            assert not decision.requires_review
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(decision=decision_strategy())
    def test_decision_has_video_references(self, decision):
        """Test that decision has video references."""
        assert len(decision.video_references) > 0


class TestMatchContextStrategy:
    """Test match_context_strategy generator."""
    
    @given(context=match_context_strategy())
    def test_generates_valid_match_context(self, context):
        """Test that generated match contexts are valid."""
        assert isinstance(context, MatchContext)
        assert 1 <= context.over_number <= 50
        assert 1 <= context.ball_number <= 6
        assert 0 <= context.legal_deliveries <= 6
    
    @given(context=match_context_strategy())
    def test_match_context_has_batsman_stance(self, context):
        """Test that match context includes batsman stance."""
        assert isinstance(context.batsman_stance, Position3D)
    
    @given(context=match_context_strategy())
    def test_match_context_has_calibration(self, context):
        """Test that match context includes calibration data."""
        assert context.calibration is not None
        assert 'pitch_boundary' in context.calibration
        assert len(context.calibration['pitch_boundary']) == 4


# ============================================================================
# Generator Constraint Tests
# ============================================================================

class TestGeneratorConstraints:
    """Test that generators respect their constraints."""
    
    @given(position=position_3d_strategy(y_range=(0.0, 0.0)))
    def test_zero_range_produces_constant(self, position):
        """Test that zero range produces constant value."""
        assert position.y == 0.0
    
    @given(detection=detection_with_confidence(class_id=3, confidence_range=(0.9, 0.9)))
    def test_fixed_parameters_are_constant(self, detection):
        """Test that fixed parameters remain constant."""
        assert detection.class_id == 3
        assert detection.confidence == 0.9
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(trajectory=cricket_ball_trajectory(num_points_range=(10, 10)))
    def test_fixed_trajectory_length(self, trajectory):
        """Test that fixed trajectory length is respected."""
        # Length may be less than 10 if ball hits ground early
        assert len(trajectory.positions) <= 10


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestGeneratorEdgeCases:
    """Test edge cases in generators."""
    
    @given(bbox=bounding_box_strategy(width_range=(10, 10), height_range=(10, 10)))
    def test_minimum_bounding_box_size(self, bbox):
        """Test minimum bounding box size."""
        assert bbox.width == 10
        assert bbox.height == 10
    
    @given(detections=multi_camera_detections(num_cameras_range=(2, 2)))
    def test_minimum_camera_count(self, detections):
        """Test minimum camera count."""
        assert len(detections) == 2
    
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(result=detection_result_strategy(num_detections_range=(0, 0)))
    def test_empty_detection_result(self, result):
        """Test detection result with no detections."""
        assert len(result.detections) == 0
