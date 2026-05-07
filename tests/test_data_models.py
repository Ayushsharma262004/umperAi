"""
Unit tests for core data models.

Tests data class initialization, validation, edge cases, and boundary conditions.
"""

import pytest
import numpy as np
from umpirai.models.data_models import (
    Position3D, Vector3D, BoundingBox,
    Frame, Detection, DetectionResult, TrackState, Trajectory,
    Decision, MatchContext, VideoReference,
    EventType, DetectionClass
)


# ============================================================================
# Utility Classes Tests
# ============================================================================

class TestPosition3D:
    """Tests for Position3D class."""
    
    def test_valid_position(self):
        """Test creating a valid position."""
        pos = Position3D(x=1.0, y=2.0, z=3.0)
        assert pos.x == 1.0
        assert pos.y == 2.0
        assert pos.z == 3.0
    
    def test_zero_position(self):
        """Test position at origin."""
        pos = Position3D(x=0.0, y=0.0, z=0.0)
        assert pos.x == 0.0
        assert pos.y == 0.0
        assert pos.z == 0.0
    
    def test_negative_coordinates(self):
        """Test position with negative coordinates."""
        pos = Position3D(x=-5.0, y=-10.0, z=-2.5)
        assert pos.x == -5.0
        assert pos.y == -10.0
        assert pos.z == -2.5
    
    def test_integer_coordinates(self):
        """Test position with integer coordinates."""
        pos = Position3D(x=1, y=2, z=3)
        assert pos.x == 1
        assert pos.y == 2
        assert pos.z == 3
    
    def test_invalid_type(self):
        """Test position with invalid type raises TypeError."""
        with pytest.raises(TypeError):
            Position3D(x="1.0", y=2.0, z=3.0)
    
    def test_infinite_value(self):
        """Test position with infinite value raises ValueError."""
        with pytest.raises(ValueError):
            Position3D(x=float('inf'), y=2.0, z=3.0)
    
    def test_nan_value(self):
        """Test position with NaN value raises ValueError."""
        with pytest.raises(ValueError):
            Position3D(x=float('nan'), y=2.0, z=3.0)


class TestVector3D:
    """Tests for Vector3D class."""
    
    def test_valid_vector(self):
        """Test creating a valid vector."""
        vec = Vector3D(vx=1.0, vy=2.0, vz=3.0)
        assert vec.vx == 1.0
        assert vec.vy == 2.0
        assert vec.vz == 3.0
    
    def test_zero_vector(self):
        """Test zero vector."""
        vec = Vector3D(vx=0.0, vy=0.0, vz=0.0)
        assert vec.magnitude() == 0.0
    
    def test_magnitude_calculation(self):
        """Test vector magnitude calculation."""
        vec = Vector3D(vx=3.0, vy=4.0, vz=0.0)
        assert vec.magnitude() == 5.0
    
    def test_negative_components(self):
        """Test vector with negative components."""
        vec = Vector3D(vx=-1.0, vy=-2.0, vz=-3.0)
        assert vec.vx == -1.0
        assert vec.vy == -2.0
        assert vec.vz == -3.0
    
    def test_invalid_type(self):
        """Test vector with invalid type raises TypeError."""
        with pytest.raises(TypeError):
            Vector3D(vx="1.0", vy=2.0, vz=3.0)
    
    def test_infinite_value(self):
        """Test vector with infinite value raises ValueError."""
        with pytest.raises(ValueError):
            Vector3D(vx=float('inf'), vy=2.0, vz=3.0)


class TestBoundingBox:
    """Tests for BoundingBox class."""
    
    def test_valid_bounding_box(self):
        """Test creating a valid bounding box."""
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        assert bbox.x == 10.0
        assert bbox.y == 20.0
        assert bbox.width == 100.0
        assert bbox.height == 50.0
    
    def test_center_calculation(self):
        """Test bounding box center calculation."""
        bbox = BoundingBox(x=0.0, y=0.0, width=100.0, height=50.0)
        center = bbox.center()
        assert center == (50.0, 25.0)
    
    def test_area_calculation(self):
        """Test bounding box area calculation."""
        bbox = BoundingBox(x=0.0, y=0.0, width=100.0, height=50.0)
        assert bbox.area() == 5000.0
    
    def test_zero_area(self):
        """Test bounding box with zero area."""
        bbox = BoundingBox(x=0.0, y=0.0, width=0.0, height=0.0)
        assert bbox.area() == 0.0
    
    def test_intersection_true(self):
        """Test bounding box intersection detection (overlapping)."""
        bbox1 = BoundingBox(x=0.0, y=0.0, width=100.0, height=100.0)
        bbox2 = BoundingBox(x=50.0, y=50.0, width=100.0, height=100.0)
        assert bbox1.intersects(bbox2)
        assert bbox2.intersects(bbox1)
    
    def test_intersection_false(self):
        """Test bounding box intersection detection (non-overlapping)."""
        bbox1 = BoundingBox(x=0.0, y=0.0, width=50.0, height=50.0)
        bbox2 = BoundingBox(x=100.0, y=100.0, width=50.0, height=50.0)
        assert not bbox1.intersects(bbox2)
        assert not bbox2.intersects(bbox1)
    
    def test_negative_width(self):
        """Test bounding box with negative width raises ValueError."""
        with pytest.raises(ValueError):
            BoundingBox(x=0.0, y=0.0, width=-10.0, height=50.0)
    
    def test_negative_height(self):
        """Test bounding box with negative height raises ValueError."""
        with pytest.raises(ValueError):
            BoundingBox(x=0.0, y=0.0, width=100.0, height=-50.0)
    
    def test_invalid_type(self):
        """Test bounding box with invalid type raises TypeError."""
        with pytest.raises(TypeError):
            BoundingBox(x="0", y=0.0, width=100.0, height=50.0)


# ============================================================================
# Core Data Models Tests
# ============================================================================

class TestFrame:
    """Tests for Frame class."""
    
    def test_valid_frame(self):
        """Test creating a valid frame."""
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame = Frame(
            camera_id="cam1",
            frame_number=100,
            timestamp=1234567890.5,
            image=image
        )
        assert frame.camera_id == "cam1"
        assert frame.frame_number == 100
        assert frame.timestamp == 1234567890.5
        assert frame.image.shape == (720, 1280, 3)
    
    def test_frame_with_metadata(self):
        """Test frame with metadata."""
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        metadata = {"exposure": 0.5, "gain": 1.2}
        frame = Frame(
            camera_id="cam1",
            frame_number=100,
            timestamp=1234567890.5,
            image=image,
            metadata=metadata
        )
        assert frame.metadata == metadata
    
    def test_empty_camera_id(self):
        """Test frame with empty camera_id raises ValueError."""
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        with pytest.raises(ValueError):
            Frame(camera_id="", frame_number=100, timestamp=1234567890.5, image=image)
    
    def test_negative_frame_number(self):
        """Test frame with negative frame_number raises ValueError."""
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        with pytest.raises(ValueError):
            Frame(camera_id="cam1", frame_number=-1, timestamp=1234567890.5, image=image)
    
    def test_negative_timestamp(self):
        """Test frame with negative timestamp raises ValueError."""
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        with pytest.raises(ValueError):
            Frame(camera_id="cam1", frame_number=100, timestamp=-1.0, image=image)
    
    def test_invalid_image_shape(self):
        """Test frame with invalid image shape raises ValueError."""
        image = np.zeros((720, 1280), dtype=np.uint8)  # Missing color channel
        with pytest.raises(ValueError):
            Frame(camera_id="cam1", frame_number=100, timestamp=1234567890.5, image=image)
    
    def test_invalid_image_type(self):
        """Test frame with invalid image type raises TypeError."""
        with pytest.raises(TypeError):
            Frame(camera_id="cam1", frame_number=100, timestamp=1234567890.5, image="not_an_array")


class TestDetection:
    """Tests for Detection class."""
    
    def test_valid_detection(self):
        """Test creating a valid detection."""
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        detection = Detection(
            class_id=0,
            class_name="ball",
            bounding_box=bbox,
            confidence=0.95
        )
        assert detection.class_id == 0
        assert detection.class_name == "ball"
        assert detection.confidence == 0.95
        assert not detection.is_uncertain()
    
    def test_detection_with_3d_position(self):
        """Test detection with 3D position."""
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        pos = Position3D(x=1.0, y=2.0, z=3.0)
        detection = Detection(
            class_id=0,
            class_name="ball",
            bounding_box=bbox,
            confidence=0.95,
            position_3d=pos
        )
        assert detection.position_3d == pos
    
    def test_uncertain_detection(self):
        """Test detection with low confidence is flagged as uncertain."""
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        detection = Detection(
            class_id=0,
            class_name="ball",
            bounding_box=bbox,
            confidence=0.65
        )
        assert detection.is_uncertain()
    
    def test_confidence_boundary_low(self):
        """Test detection at low confidence boundary."""
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        detection = Detection(
            class_id=0,
            class_name="ball",
            bounding_box=bbox,
            confidence=0.70
        )
        assert not detection.is_uncertain()
    
    def test_confidence_out_of_range_high(self):
        """Test detection with confidence > 1.0 raises ValueError."""
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        with pytest.raises(ValueError):
            Detection(class_id=0, class_name="ball", bounding_box=bbox, confidence=1.5)
    
    def test_confidence_out_of_range_low(self):
        """Test detection with confidence < 0.0 raises ValueError."""
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        with pytest.raises(ValueError):
            Detection(class_id=0, class_name="ball", bounding_box=bbox, confidence=-0.1)
    
    def test_negative_class_id(self):
        """Test detection with negative class_id raises ValueError."""
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        with pytest.raises(ValueError):
            Detection(class_id=-1, class_name="ball", bounding_box=bbox, confidence=0.95)


class TestDetectionResult:
    """Tests for DetectionResult class."""
    
    def test_valid_detection_result(self):
        """Test creating a valid detection result."""
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame = Frame(camera_id="cam1", frame_number=100, timestamp=1234567890.5, image=image)
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        detection = Detection(class_id=0, class_name="ball", bounding_box=bbox, confidence=0.95)
        
        result = DetectionResult(
            frame=frame,
            detections=[detection],
            processing_time_ms=45.5
        )
        assert result.frame == frame
        assert len(result.detections) == 1
        assert result.processing_time_ms == 45.5
    
    def test_empty_detections(self):
        """Test detection result with empty detections list."""
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame = Frame(camera_id="cam1", frame_number=100, timestamp=1234567890.5, image=image)
        
        result = DetectionResult(frame=frame, detections=[], processing_time_ms=45.5)
        assert len(result.detections) == 0
        assert not result.has_uncertain_detections()
    
    def test_get_detections_by_class(self):
        """Test filtering detections by class."""
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame = Frame(camera_id="cam1", frame_number=100, timestamp=1234567890.5, image=image)
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        
        detections = [
            Detection(class_id=0, class_name="ball", bounding_box=bbox, confidence=0.95),
            Detection(class_id=1, class_name="stumps", bounding_box=bbox, confidence=0.98),
            Detection(class_id=0, class_name="ball", bounding_box=bbox, confidence=0.92)
        ]
        
        result = DetectionResult(frame=frame, detections=detections, processing_time_ms=45.5)
        ball_detections = result.get_detections_by_class(0)
        assert len(ball_detections) == 2
        assert all(d.class_id == 0 for d in ball_detections)
    
    def test_has_uncertain_detections(self):
        """Test detection of uncertain detections."""
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame = Frame(camera_id="cam1", frame_number=100, timestamp=1234567890.5, image=image)
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        
        detections = [
            Detection(class_id=0, class_name="ball", bounding_box=bbox, confidence=0.95),
            Detection(class_id=1, class_name="stumps", bounding_box=bbox, confidence=0.65)
        ]
        
        result = DetectionResult(frame=frame, detections=detections, processing_time_ms=45.5)
        assert result.has_uncertain_detections()
    
    def test_negative_processing_time(self):
        """Test detection result with negative processing time raises ValueError."""
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame = Frame(camera_id="cam1", frame_number=100, timestamp=1234567890.5, image=image)
        
        with pytest.raises(ValueError):
            DetectionResult(frame=frame, detections=[], processing_time_ms=-10.0)


class TestTrackState:
    """Tests for TrackState class."""
    
    def test_valid_track_state(self):
        """Test creating a valid track state."""
        pos = Position3D(x=1.0, y=2.0, z=3.0)
        vel = Vector3D(vx=10.0, vy=5.0, vz=-2.0)
        acc = Vector3D(vx=0.0, vy=0.0, vz=-9.81)
        cov = np.eye(9)
        
        track = TrackState(
            track_id="track_001",
            position=pos,
            velocity=vel,
            acceleration=acc,
            covariance=cov,
            last_seen=1234567890.5,
            occlusion_duration=0,
            confidence=0.95
        )
        assert track.track_id == "track_001"
        assert not track.is_occluded()
        assert not track.is_long_occlusion()
    
    def test_occluded_track(self):
        """Test track state with occlusion."""
        pos = Position3D(x=1.0, y=2.0, z=3.0)
        vel = Vector3D(vx=10.0, vy=5.0, vz=-2.0)
        acc = Vector3D(vx=0.0, vy=0.0, vz=-9.81)
        cov = np.eye(9)
        
        track = TrackState(
            track_id="track_001",
            position=pos,
            velocity=vel,
            acceleration=acc,
            covariance=cov,
            last_seen=1234567890.5,
            occlusion_duration=5,
            confidence=0.85
        )
        assert track.is_occluded()
        assert not track.is_long_occlusion()
    
    def test_long_occlusion(self):
        """Test track state with long occlusion."""
        pos = Position3D(x=1.0, y=2.0, z=3.0)
        vel = Vector3D(vx=10.0, vy=5.0, vz=-2.0)
        acc = Vector3D(vx=0.0, vy=0.0, vz=-9.81)
        cov = np.eye(9)
        
        track = TrackState(
            track_id="track_001",
            position=pos,
            velocity=vel,
            acceleration=acc,
            covariance=cov,
            last_seen=1234567890.5,
            occlusion_duration=15,
            confidence=0.70
        )
        assert track.is_occluded()
        assert track.is_long_occlusion()
    
    def test_invalid_covariance_shape(self):
        """Test track state with invalid covariance shape raises ValueError."""
        pos = Position3D(x=1.0, y=2.0, z=3.0)
        vel = Vector3D(vx=10.0, vy=5.0, vz=-2.0)
        acc = Vector3D(vx=0.0, vy=0.0, vz=-9.81)
        cov = np.eye(3)  # Wrong shape
        
        with pytest.raises(ValueError):
            TrackState(
                track_id="track_001",
                position=pos,
                velocity=vel,
                acceleration=acc,
                covariance=cov,
                last_seen=1234567890.5,
                occlusion_duration=0,
                confidence=0.95
            )


class TestTrajectory:
    """Tests for Trajectory class."""
    
    def test_valid_trajectory(self):
        """Test creating a valid trajectory."""
        positions = [Position3D(x=i, y=i*2, z=i*3) for i in range(5)]
        timestamps = [float(i) for i in range(5)]
        velocities = [Vector3D(vx=1.0, vy=2.0, vz=3.0) for _ in range(5)]
        start_pos = Position3D(x=0.0, y=0.0, z=0.0)
        
        traj = Trajectory(
            positions=positions,
            timestamps=timestamps,
            velocities=velocities,
            start_position=start_pos,
            speed_max=15.0,
            speed_avg=12.0
        )
        assert traj.length() == 5
        assert traj.duration() == 4.0
    
    def test_empty_trajectory(self):
        """Test trajectory with empty lists."""
        start_pos = Position3D(x=0.0, y=0.0, z=0.0)
        
        traj = Trajectory(
            positions=[],
            timestamps=[],
            velocities=[],
            start_position=start_pos
        )
        assert traj.length() == 0
        assert traj.duration() == 0.0
    
    def test_single_position_trajectory(self):
        """Test trajectory with single position."""
        positions = [Position3D(x=1.0, y=2.0, z=3.0)]
        timestamps = [1234567890.5]
        velocities = [Vector3D(vx=0.0, vy=0.0, vz=0.0)]
        start_pos = Position3D(x=1.0, y=2.0, z=3.0)
        
        traj = Trajectory(
            positions=positions,
            timestamps=timestamps,
            velocities=velocities,
            start_position=start_pos
        )
        assert traj.length() == 1
        assert traj.duration() == 0.0
    
    def test_mismatched_lengths(self):
        """Test trajectory with mismatched positions and timestamps raises ValueError."""
        positions = [Position3D(x=i, y=i*2, z=i*3) for i in range(5)]
        timestamps = [float(i) for i in range(3)]  # Wrong length
        velocities = [Vector3D(vx=1.0, vy=2.0, vz=3.0) for _ in range(5)]
        start_pos = Position3D(x=0.0, y=0.0, z=0.0)
        
        with pytest.raises(ValueError):
            Trajectory(
                positions=positions,
                timestamps=timestamps,
                velocities=velocities,
                start_position=start_pos
            )
    
    def test_negative_speed(self):
        """Test trajectory with negative speed raises ValueError."""
        positions = [Position3D(x=i, y=i*2, z=i*3) for i in range(5)]
        timestamps = [float(i) for i in range(5)]
        velocities = [Vector3D(vx=1.0, vy=2.0, vz=3.0) for _ in range(5)]
        start_pos = Position3D(x=0.0, y=0.0, z=0.0)
        
        with pytest.raises(ValueError):
            Trajectory(
                positions=positions,
                timestamps=timestamps,
                velocities=velocities,
                start_position=start_pos,
                speed_max=-5.0
            )


class TestDecision:
    """Tests for Decision class."""
    
    def test_valid_decision(self):
        """Test creating a valid decision."""
        positions = [Position3D(x=i, y=i*2, z=i*3) for i in range(5)]
        timestamps = [float(i) for i in range(5)]
        velocities = [Vector3D(vx=1.0, vy=2.0, vz=3.0) for _ in range(5)]
        start_pos = Position3D(x=0.0, y=0.0, z=0.0)
        traj = Trajectory(
            positions=positions,
            timestamps=timestamps,
            velocities=velocities,
            start_position=start_pos
        )
        
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        detection = Detection(class_id=0, class_name="ball", bounding_box=bbox, confidence=0.95)
        
        video_ref = VideoReference(camera_id="cam1", frame_number=100, timestamp=1234567890.5)
        
        decision = Decision(
            decision_id="dec_001",
            event_type=EventType.WIDE,
            confidence=0.92,
            timestamp=1234567890.5,
            trajectory=traj,
            detections=[detection],
            reasoning="Ball crossed wide guideline",
            video_references=[video_ref]
        )
        assert decision.decision_id == "dec_001"
        assert decision.event_type == EventType.WIDE
        assert not decision.requires_review
    
    def test_low_confidence_auto_review(self):
        """Test decision with low confidence is auto-flagged for review."""
        positions = [Position3D(x=i, y=i*2, z=i*3) for i in range(5)]
        timestamps = [float(i) for i in range(5)]
        velocities = [Vector3D(vx=1.0, vy=2.0, vz=3.0) for _ in range(5)]
        start_pos = Position3D(x=0.0, y=0.0, z=0.0)
        traj = Trajectory(
            positions=positions,
            timestamps=timestamps,
            velocities=velocities,
            start_position=start_pos
        )
        
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        detection = Detection(class_id=0, class_name="ball", bounding_box=bbox, confidence=0.95)
        
        video_ref = VideoReference(camera_id="cam1", frame_number=100, timestamp=1234567890.5)
        
        decision = Decision(
            decision_id="dec_001",
            event_type=EventType.WIDE,
            confidence=0.75,  # Below 0.80 threshold
            timestamp=1234567890.5,
            trajectory=traj,
            detections=[detection],
            reasoning="Ball crossed wide guideline",
            video_references=[video_ref]
        )
        assert decision.requires_review
    
    def test_empty_detections(self):
        """Test decision with empty detections list."""
        positions = [Position3D(x=i, y=i*2, z=i*3) for i in range(5)]
        timestamps = [float(i) for i in range(5)]
        velocities = [Vector3D(vx=1.0, vy=2.0, vz=3.0) for _ in range(5)]
        start_pos = Position3D(x=0.0, y=0.0, z=0.0)
        traj = Trajectory(
            positions=positions,
            timestamps=timestamps,
            velocities=velocities,
            start_position=start_pos
        )
        
        video_ref = VideoReference(camera_id="cam1", frame_number=100, timestamp=1234567890.5)
        
        decision = Decision(
            decision_id="dec_001",
            event_type=EventType.LEGAL,
            confidence=0.95,
            timestamp=1234567890.5,
            trajectory=traj,
            detections=[],
            reasoning="Legal delivery",
            video_references=[video_ref]
        )
        assert len(decision.detections) == 0


class TestMatchContext:
    """Tests for MatchContext class."""
    
    def test_valid_match_context(self):
        """Test creating a valid match context."""
        stance = Position3D(x=0.0, y=0.0, z=0.0)
        calibration = {"pitch_width": 3.05, "pitch_length": 20.12}
        
        context = MatchContext(
            over_number=5,
            ball_number=3,
            legal_deliveries=2,
            batsman_stance=stance,
            calibration=calibration
        )
        assert context.over_number == 5
        assert context.ball_number == 3
        assert not context.is_over_complete()
    
    def test_over_complete(self):
        """Test match context with complete over."""
        stance = Position3D(x=0.0, y=0.0, z=0.0)
        calibration = {"pitch_width": 3.05, "pitch_length": 20.12}
        
        context = MatchContext(
            over_number=5,
            ball_number=6,
            legal_deliveries=6,
            batsman_stance=stance,
            calibration=calibration
        )
        assert context.is_over_complete()
    
    def test_invalid_ball_number(self):
        """Test match context with invalid ball_number raises ValueError."""
        stance = Position3D(x=0.0, y=0.0, z=0.0)
        calibration = {"pitch_width": 3.05, "pitch_length": 20.12}
        
        with pytest.raises(ValueError):
            MatchContext(
                over_number=5,
                ball_number=7,  # Invalid
                legal_deliveries=2,
                batsman_stance=stance,
                calibration=calibration
            )
    
    def test_invalid_legal_deliveries(self):
        """Test match context with invalid legal_deliveries raises ValueError."""
        stance = Position3D(x=0.0, y=0.0, z=0.0)
        calibration = {"pitch_width": 3.05, "pitch_length": 20.12}
        
        with pytest.raises(ValueError):
            MatchContext(
                over_number=5,
                ball_number=3,
                legal_deliveries=7,  # Invalid
                batsman_stance=stance,
                calibration=calibration
            )
    
    def test_negative_over_number(self):
        """Test match context with negative over_number raises ValueError."""
        stance = Position3D(x=0.0, y=0.0, z=0.0)
        calibration = {"pitch_width": 3.05, "pitch_length": 20.12}
        
        with pytest.raises(ValueError):
            MatchContext(
                over_number=-1,
                ball_number=3,
                legal_deliveries=2,
                batsman_stance=stance,
                calibration=calibration
            )
    
    def test_ball_number_zero(self):
        """Test match context with ball_number=0 raises ValueError."""
        stance = Position3D(x=0.0, y=0.0, z=0.0)
        calibration = {"pitch_width": 3.05, "pitch_length": 20.12}
        
        with pytest.raises(ValueError):
            MatchContext(
                over_number=5,
                ball_number=0,  # Invalid
                legal_deliveries=2,
                batsman_stance=stance,
                calibration=calibration
            )
    
    def test_negative_legal_deliveries(self):
        """Test match context with negative legal_deliveries raises ValueError."""
        stance = Position3D(x=0.0, y=0.0, z=0.0)
        calibration = {"pitch_width": 3.05, "pitch_length": 20.12}
        
        with pytest.raises(ValueError):
            MatchContext(
                over_number=5,
                ball_number=3,
                legal_deliveries=-1,  # Invalid
                batsman_stance=stance,
                calibration=calibration
            )
    
    def test_empty_calibration(self):
        """Test match context with empty calibration dictionary."""
        stance = Position3D(x=0.0, y=0.0, z=0.0)
        calibration = {}
        
        context = MatchContext(
            over_number=5,
            ball_number=3,
            legal_deliveries=2,
            batsman_stance=stance,
            calibration=calibration
        )
        assert context.calibration == {}
    
    def test_invalid_calibration_type(self):
        """Test match context with invalid calibration type raises TypeError."""
        stance = Position3D(x=0.0, y=0.0, z=0.0)
        
        with pytest.raises(TypeError):
            MatchContext(
                over_number=5,
                ball_number=3,
                legal_deliveries=2,
                batsman_stance=stance,
                calibration="not_a_dict"
            )


# ============================================================================
# Enumeration Tests
# ============================================================================

class TestEventType:
    """Tests for EventType enumeration."""
    
    def test_event_type_values(self):
        """Test all EventType enum values exist."""
        assert EventType.WIDE.value == "wide"
        assert EventType.NO_BALL.value == "no_ball"
        assert EventType.BOWLED.value == "bowled"
        assert EventType.CAUGHT.value == "caught"
        assert EventType.LBW.value == "lbw"
        assert EventType.LEGAL.value == "legal"
        assert EventType.OVER_COMPLETE.value == "over_complete"
    
    def test_event_type_count(self):
        """Test EventType has exactly 7 values."""
        assert len(EventType) == 7
    
    def test_event_type_comparison(self):
        """Test EventType enum comparison."""
        assert EventType.WIDE == EventType.WIDE
        assert EventType.WIDE != EventType.NO_BALL


class TestDetectionClass:
    """Tests for DetectionClass enumeration."""
    
    def test_detection_class_values(self):
        """Test all DetectionClass enum values exist."""
        assert DetectionClass.BALL.value == 0
        assert DetectionClass.STUMPS.value == 1
        assert DetectionClass.CREASE.value == 2
        assert DetectionClass.BATSMAN.value == 3
        assert DetectionClass.BOWLER.value == 4
        assert DetectionClass.FIELDER.value == 5
        assert DetectionClass.PITCH_BOUNDARY.value == 6
        assert DetectionClass.WIDE_GUIDELINE.value == 7
    
    def test_detection_class_count(self):
        """Test DetectionClass has exactly 8 values."""
        assert len(DetectionClass) == 8
    
    def test_detection_class_comparison(self):
        """Test DetectionClass enum comparison."""
        assert DetectionClass.BALL == DetectionClass.BALL
        assert DetectionClass.BALL != DetectionClass.STUMPS


# ============================================================================
# VideoReference Tests
# ============================================================================

class TestVideoReference:
    """Tests for VideoReference class."""
    
    def test_valid_video_reference(self):
        """Test creating a valid video reference."""
        ref = VideoReference(
            camera_id="cam1",
            frame_number=100,
            timestamp=1234567890.5
        )
        assert ref.camera_id == "cam1"
        assert ref.frame_number == 100
        assert ref.timestamp == 1234567890.5
    
    def test_empty_camera_id(self):
        """Test video reference with empty camera_id raises ValueError."""
        with pytest.raises(ValueError):
            VideoReference(camera_id="", frame_number=100, timestamp=1234567890.5)
    
    def test_negative_frame_number(self):
        """Test video reference with negative frame_number raises ValueError."""
        with pytest.raises(ValueError):
            VideoReference(camera_id="cam1", frame_number=-1, timestamp=1234567890.5)
    
    def test_negative_timestamp(self):
        """Test video reference with negative timestamp raises ValueError."""
        with pytest.raises(ValueError):
            VideoReference(camera_id="cam1", frame_number=100, timestamp=-1.0)
    
    def test_zero_values(self):
        """Test video reference with zero frame_number and timestamp."""
        ref = VideoReference(camera_id="cam1", frame_number=0, timestamp=0.0)
        assert ref.frame_number == 0
        assert ref.timestamp == 0.0


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Additional edge case tests for data models."""
    
    def test_bounding_box_edge_touching(self):
        """Test bounding boxes that touch at edges."""
        bbox1 = BoundingBox(x=0.0, y=0.0, width=50.0, height=50.0)
        bbox2 = BoundingBox(x=50.0, y=0.0, width=50.0, height=50.0)
        # Boxes touching at edge should not intersect
        assert not bbox1.intersects(bbox2)
    
    def test_bounding_box_contained(self):
        """Test bounding box completely contained in another."""
        bbox1 = BoundingBox(x=0.0, y=0.0, width=100.0, height=100.0)
        bbox2 = BoundingBox(x=25.0, y=25.0, width=50.0, height=50.0)
        assert bbox1.intersects(bbox2)
        assert bbox2.intersects(bbox1)
    
    def test_vector_magnitude_large_values(self):
        """Test vector magnitude with large values."""
        vec = Vector3D(vx=1000.0, vy=2000.0, vz=3000.0)
        expected = np.sqrt(1000**2 + 2000**2 + 3000**2)
        assert abs(vec.magnitude() - expected) < 1e-6
    
    def test_trajectory_with_end_position(self):
        """Test trajectory with end position specified."""
        positions = [Position3D(x=i, y=i*2, z=i*3) for i in range(5)]
        timestamps = [float(i) for i in range(5)]
        velocities = [Vector3D(vx=1.0, vy=2.0, vz=3.0) for _ in range(5)]
        start_pos = Position3D(x=0.0, y=0.0, z=0.0)
        end_pos = Position3D(x=4.0, y=8.0, z=12.0)
        
        traj = Trajectory(
            positions=positions,
            timestamps=timestamps,
            velocities=velocities,
            start_position=start_pos,
            end_position=end_pos
        )
        assert traj.end_position == end_pos
    
    def test_detection_confidence_boundary_high(self):
        """Test detection at high confidence boundary (1.0)."""
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        detection = Detection(
            class_id=0,
            class_name="ball",
            bounding_box=bbox,
            confidence=1.0
        )
        assert detection.confidence == 1.0
        assert not detection.is_uncertain()
    
    def test_detection_confidence_boundary_zero(self):
        """Test detection at low confidence boundary (0.0)."""
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        detection = Detection(
            class_id=0,
            class_name="ball",
            bounding_box=bbox,
            confidence=0.0
        )
        assert detection.confidence == 0.0
        assert detection.is_uncertain()
    
    def test_detection_confidence_just_below_threshold(self):
        """Test detection just below uncertainty threshold."""
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        detection = Detection(
            class_id=0,
            class_name="ball",
            bounding_box=bbox,
            confidence=0.69
        )
        assert detection.is_uncertain()
    
    def test_decision_confidence_boundary_80(self):
        """Test decision at review threshold boundary (0.80)."""
        positions = [Position3D(x=i, y=i*2, z=i*3) for i in range(5)]
        timestamps = [float(i) for i in range(5)]
        velocities = [Vector3D(vx=1.0, vy=2.0, vz=3.0) for _ in range(5)]
        start_pos = Position3D(x=0.0, y=0.0, z=0.0)
        traj = Trajectory(
            positions=positions,
            timestamps=timestamps,
            velocities=velocities,
            start_position=start_pos
        )
        
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        detection = Detection(class_id=0, class_name="ball", bounding_box=bbox, confidence=0.95)
        video_ref = VideoReference(camera_id="cam1", frame_number=100, timestamp=1234567890.5)
        
        decision = Decision(
            decision_id="dec_001",
            event_type=EventType.WIDE,
            confidence=0.80,  # Exactly at threshold
            timestamp=1234567890.5,
            trajectory=traj,
            detections=[detection],
            reasoning="Ball crossed wide guideline",
            video_references=[video_ref]
        )
        # At exactly 0.80, should not require review
        assert not decision.requires_review
    
    def test_decision_confidence_just_below_threshold(self):
        """Test decision just below review threshold."""
        positions = [Position3D(x=i, y=i*2, z=i*3) for i in range(5)]
        timestamps = [float(i) for i in range(5)]
        velocities = [Vector3D(vx=1.0, vy=2.0, vz=3.0) for _ in range(5)]
        start_pos = Position3D(x=0.0, y=0.0, z=0.0)
        traj = Trajectory(
            positions=positions,
            timestamps=timestamps,
            velocities=velocities,
            start_position=start_pos
        )
        
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        detection = Detection(class_id=0, class_name="ball", bounding_box=bbox, confidence=0.95)
        video_ref = VideoReference(camera_id="cam1", frame_number=100, timestamp=1234567890.5)
        
        decision = Decision(
            decision_id="dec_001",
            event_type=EventType.WIDE,
            confidence=0.79,  # Just below threshold
            timestamp=1234567890.5,
            trajectory=traj,
            detections=[detection],
            reasoning="Ball crossed wide guideline",
            video_references=[video_ref]
        )
        assert decision.requires_review
    
    def test_track_state_occlusion_boundary(self):
        """Test track state at occlusion threshold boundary (10 frames)."""
        pos = Position3D(x=1.0, y=2.0, z=3.0)
        vel = Vector3D(vx=10.0, vy=5.0, vz=-2.0)
        acc = Vector3D(vx=0.0, vy=0.0, vz=-9.81)
        cov = np.eye(9)
        
        track = TrackState(
            track_id="track_001",
            position=pos,
            velocity=vel,
            acceleration=acc,
            covariance=cov,
            last_seen=1234567890.5,
            occlusion_duration=10,
            confidence=0.85
        )
        assert track.is_occluded()
        # At exactly 10 frames, should not be long occlusion
        assert not track.is_long_occlusion()
    
    def test_track_state_long_occlusion_boundary(self):
        """Test track state just over long occlusion threshold."""
        pos = Position3D(x=1.0, y=2.0, z=3.0)
        vel = Vector3D(vx=10.0, vy=5.0, vz=-2.0)
        acc = Vector3D(vx=0.0, vy=0.0, vz=-9.81)
        cov = np.eye(9)
        
        track = TrackState(
            track_id="track_001",
            position=pos,
            velocity=vel,
            acceleration=acc,
            covariance=cov,
            last_seen=1234567890.5,
            occlusion_duration=11,
            confidence=0.85
        )
        assert track.is_occluded()
        assert track.is_long_occlusion()
    
    def test_frame_with_different_image_sizes(self):
        """Test frame with various valid image sizes."""
        # Test different resolutions
        for height, width in [(480, 640), (720, 1280), (1080, 1920)]:
            image = np.zeros((height, width, 3), dtype=np.uint8)
            frame = Frame(
                camera_id="cam1",
                frame_number=100,
                timestamp=1234567890.5,
                image=image
            )
            assert frame.image.shape == (height, width, 3)
    
    def test_detection_result_multiple_classes(self):
        """Test detection result with multiple object classes."""
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame = Frame(camera_id="cam1", frame_number=100, timestamp=1234567890.5, image=image)
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        
        detections = [
            Detection(class_id=0, class_name="ball", bounding_box=bbox, confidence=0.95),
            Detection(class_id=1, class_name="stumps", bounding_box=bbox, confidence=0.98),
            Detection(class_id=2, class_name="crease", bounding_box=bbox, confidence=0.97),
            Detection(class_id=3, class_name="batsman", bounding_box=bbox, confidence=0.88)
        ]
        
        result = DetectionResult(frame=frame, detections=detections, processing_time_ms=45.5)
        assert len(result.get_detections_by_class(0)) == 1
        assert len(result.get_detections_by_class(1)) == 1
        assert len(result.get_detections_by_class(5)) == 0  # No fielder detections
    
    def test_decision_with_multiple_video_references(self):
        """Test decision with multiple camera video references."""
        positions = [Position3D(x=i, y=i*2, z=i*3) for i in range(5)]
        timestamps = [float(i) for i in range(5)]
        velocities = [Vector3D(vx=1.0, vy=2.0, vz=3.0) for _ in range(5)]
        start_pos = Position3D(x=0.0, y=0.0, z=0.0)
        traj = Trajectory(
            positions=positions,
            timestamps=timestamps,
            velocities=velocities,
            start_position=start_pos
        )
        
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        detection = Detection(class_id=0, class_name="ball", bounding_box=bbox, confidence=0.95)
        
        video_refs = [
            VideoReference(camera_id="cam1", frame_number=100, timestamp=1234567890.5),
            VideoReference(camera_id="cam2", frame_number=101, timestamp=1234567890.5),
            VideoReference(camera_id="cam3", frame_number=99, timestamp=1234567890.5)
        ]
        
        decision = Decision(
            decision_id="dec_001",
            event_type=EventType.BOWLED,
            confidence=0.95,
            timestamp=1234567890.5,
            trajectory=traj,
            detections=[detection],
            reasoning="Ball hit stumps",
            video_references=video_refs
        )
        assert len(decision.video_references) == 3
    
    def test_match_context_first_ball(self):
        """Test match context for first ball of over."""
        stance = Position3D(x=0.0, y=0.0, z=0.0)
        calibration = {"pitch_width": 3.05, "pitch_length": 20.12}
        
        context = MatchContext(
            over_number=1,
            ball_number=1,
            legal_deliveries=0,
            batsman_stance=stance,
            calibration=calibration
        )
        assert context.ball_number == 1
        assert context.legal_deliveries == 0
        assert not context.is_over_complete()
    
    def test_trajectory_non_uniform_timestamps(self):
        """Test trajectory with non-uniform timestamp intervals."""
        positions = [Position3D(x=i, y=i*2, z=i*3) for i in range(5)]
        timestamps = [0.0, 0.1, 0.25, 0.5, 1.0]  # Non-uniform intervals
        velocities = [Vector3D(vx=1.0, vy=2.0, vz=3.0) for _ in range(5)]
        start_pos = Position3D(x=0.0, y=0.0, z=0.0)
        
        traj = Trajectory(
            positions=positions,
            timestamps=timestamps,
            velocities=velocities,
            start_position=start_pos
        )
        assert traj.duration() == 1.0
        assert traj.length() == 5
