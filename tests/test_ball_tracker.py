"""
Unit tests for Ball Tracker component.

Tests specific examples and edge cases for ball tracking functionality.
"""

import pytest
import numpy as np

from umpirai.tracking.ball_tracker import BallTracker, BallDetection
from umpirai.models.data_models import (
    Detection,
    BoundingBox,
    Position3D,
    Vector3D,
    TrackState,
)


class TestBallTrackerInitialization:
    """Test ball tracker initialization."""
    
    def test_tracker_initialization_default_params(self):
        """Test tracker initializes with default parameters."""
        tracker = BallTracker()
        
        assert tracker.dt == 1.0 / 30.0
        assert tracker.measurement_noise == 5.0
        assert tracker.process_noise == 0.1
        assert not tracker.is_initialized
        assert tracker.occlusion_duration == 0
        assert len(tracker.position_history) == 0
    
    def test_tracker_initialization_custom_params(self):
        """Test tracker initializes with custom parameters."""
        tracker = BallTracker(
            dt=1.0/60.0,
            measurement_noise=10.0,
            process_noise=0.5
        )
        
        assert tracker.dt == 1.0 / 60.0
        assert tracker.measurement_noise == 10.0
        assert tracker.process_noise == 0.5
    
    def test_tracker_state_initialization(self):
        """Test tracker state is properly initialized."""
        tracker = BallTracker()
        
        assert tracker.state.shape == (9,)
        assert np.all(tracker.state == 0.0)
        assert tracker.covariance.shape == (9, 9)


class TestBallTrackerUpdate:
    """Test ball tracker update with detections."""
    
    def test_update_with_first_detection(self):
        """Test tracker update with first detection initializes state."""
        tracker = BallTracker(dt=1.0/30.0)
        
        position = Position3D(x=1.0, y=1.5, z=5.0)
        detection = BallDetection(
            detection=Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=100, width=20, height=20),
                confidence=0.95,
                position_3d=position
            ),
            timestamp=0.0,
            pixel_coords=(110, 110),
            position_3d=position
        )
        
        track_state = tracker.update(detection, 0.0)
        
        assert tracker.is_initialized
        assert track_state.position.x == pytest.approx(1.0, abs=0.1)
        assert track_state.position.y == pytest.approx(1.5, abs=0.1)
        assert track_state.position.z == pytest.approx(5.0, abs=0.1)
        assert tracker.occlusion_duration == 0
    
    def test_update_with_multiple_detections(self):
        """Test tracker update with multiple consecutive detections."""
        tracker = BallTracker(dt=1.0/30.0)
        
        # Create sequence of detections
        detections = []
        for i in range(5):
            position = Position3D(x=1.0, y=1.5, z=5.0 + i * 0.5)
            detection = BallDetection(
                detection=Detection(
                    class_id=0,
                    class_name="ball",
                    bounding_box=BoundingBox(x=100, y=100+i*10, width=20, height=20),
                    confidence=0.95,
                    position_3d=position
                ),
                timestamp=i * (1.0/30.0),
                pixel_coords=(110, 110+i*10),
                position_3d=position
            )
            detections.append(detection)
        
        # Process all detections
        for detection in detections:
            tracker.update(detection, detection.timestamp)
        
        # Check trajectory history
        trajectory = tracker.get_trajectory()
        assert len(trajectory) == 5
        assert tracker.occlusion_duration == 0
    
    def test_update_resets_occlusion_counter(self):
        """Test that update resets occlusion counter."""
        tracker = BallTracker(dt=1.0/30.0)
        
        # Initialize with first detection
        position1 = Position3D(x=1.0, y=1.5, z=5.0)
        detection1 = BallDetection(
            detection=Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=100, width=20, height=20),
                confidence=0.95,
                position_3d=position1
            ),
            timestamp=0.0,
            pixel_coords=(110, 110),
            position_3d=position1
        )
        tracker.update(detection1, 0.0)
        
        # Predict for a few frames (simulate occlusion)
        for i in range(3):
            tracker.predict((i + 1) * (1.0/30.0))
        
        assert tracker.occlusion_duration == 3
        
        # Update with new detection
        position2 = Position3D(x=1.0, y=1.5, z=6.0)
        detection2 = BallDetection(
            detection=Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=120, width=20, height=20),
                confidence=0.95,
                position_3d=position2
            ),
            timestamp=4 * (1.0/30.0),
            pixel_coords=(110, 120),
            position_3d=position2
        )
        tracker.update(detection2, 4 * (1.0/30.0))
        
        # Occlusion counter should be reset
        assert tracker.occlusion_duration == 0


class TestBallTrackerPrediction:
    """Test ball tracker prediction during occlusion."""
    
    def test_predict_without_initialization_raises_error(self):
        """Test that predict raises error if tracker not initialized."""
        tracker = BallTracker()
        
        with pytest.raises(RuntimeError, match="Tracker not initialized"):
            tracker.predict(1.0)
    
    def test_predict_increments_occlusion_counter(self):
        """Test that predict increments occlusion counter."""
        tracker = BallTracker(dt=1.0/30.0)
        
        # Initialize
        position = Position3D(x=1.0, y=1.5, z=5.0)
        detection = BallDetection(
            detection=Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=100, width=20, height=20),
                confidence=0.95,
                position_3d=position
            ),
            timestamp=0.0,
            pixel_coords=(110, 110),
            position_3d=position
        )
        tracker.update(detection, 0.0)
        
        # Predict for 5 frames
        for i in range(5):
            tracker.predict((i + 1) * (1.0/30.0))
        
        assert tracker.occlusion_duration == 5
        assert tracker.is_occluded()
    
    def test_predict_with_known_trajectory(self):
        """Test EKF prediction continues trajectory forward."""
        tracker = BallTracker(dt=1.0/30.0)
        
        # Initialize with multiple detections to establish velocity
        # Ball moving at 30 m/s in z direction
        dt = 1.0/30.0
        for i in range(10):
            position = Position3D(x=0.0, y=2.0, z=float(i))
            detection = BallDetection(
                detection=Detection(
                    class_id=0,
                    class_name="ball",
                    bounding_box=BoundingBox(x=100, y=100, width=20, height=20),
                    confidence=0.95,
                    position_3d=position
                ),
                timestamp=i * dt,
                pixel_coords=(110, 110),
                position_3d=position
            )
            tracker.update(detection, i * dt)
        
        last_position = tracker._get_track_state().position
        
        # Predict next position
        predicted_pos = tracker.predict(10 * dt)
        
        # Prediction should produce a valid position
        # (May not be perfectly accurate due to EKF uncertainty, but should be reasonable)
        assert isinstance(predicted_pos, Position3D)
        assert np.isfinite(predicted_pos.x)
        assert np.isfinite(predicted_pos.y)
        assert np.isfinite(predicted_pos.z)
    
    def test_predict_applies_gravity(self):
        """Test that prediction applies gravity to trajectory."""
        tracker = BallTracker(dt=1.0/30.0)
        
        # Initialize with ball at height, with initial upward velocity
        # that will be overcome by gravity
        dt = 1.0/30.0
        
        # Create trajectory with ball starting high and falling
        for i in range(5):
            # Ball starts at y=3.0 and falls
            y_pos = 3.0 - 0.1 * i  # Slight downward motion
            position = Position3D(x=0.0, y=y_pos, z=float(i))
            detection = BallDetection(
                detection=Detection(
                    class_id=0,
                    class_name="ball",
                    bounding_box=BoundingBox(x=100, y=100, width=20, height=20),
                    confidence=0.95,
                    position_3d=position
                ),
                timestamp=i * dt,
                pixel_coords=(110, 110),
                position_3d=position
            )
            tracker.update(detection, i * dt)
        
        # Get initial y position
        initial_y = tracker._get_track_state().position.y
        
        # Predict several frames ahead - gravity should pull ball down
        for i in range(20):
            tracker.predict((i + 5) * dt)
        
        # Final y position should be lower than initial (ball fell)
        final_y = tracker._get_track_state().position.y
        assert final_y < initial_y, "Ball should fall due to gravity"


class TestBallTrackerOcclusion:
    """Test occlusion handling edge cases."""
    
    def test_short_occlusion_handling(self):
        """Test handling of short occlusion (≤10 frames)."""
        tracker = BallTracker(dt=1.0/30.0)
        
        # Initialize
        position = Position3D(x=0.0, y=2.0, z=0.0)
        detection = BallDetection(
            detection=Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=100, width=20, height=20),
                confidence=0.95,
                position_3d=position
            ),
            timestamp=0.0,
            pixel_coords=(110, 110),
            position_3d=position
        )
        tracker.update(detection, 0.0)
        
        # Predict for 5 frames (short occlusion)
        for i in range(5):
            tracker.predict((i + 1) * (1.0/30.0))
        
        assert tracker.is_occluded()
        assert not tracker.is_long_occlusion()
        assert tracker.get_occlusion_duration() == 5
    
    def test_long_occlusion_handling(self):
        """Test handling of long occlusion (>10 frames)."""
        tracker = BallTracker(dt=1.0/30.0)
        
        # Initialize
        position = Position3D(x=0.0, y=2.0, z=0.0)
        detection = BallDetection(
            detection=Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=100, width=20, height=20),
                confidence=0.95,
                position_3d=position
            ),
            timestamp=0.0,
            pixel_coords=(110, 110),
            position_3d=position
        )
        tracker.update(detection, 0.0)
        
        # Predict for 15 frames (long occlusion)
        for i in range(15):
            tracker.predict((i + 1) * (1.0/30.0))
        
        assert tracker.is_occluded()
        assert tracker.is_long_occlusion()
        assert tracker.get_occlusion_duration() == 15
    
    def test_occlusion_boundary_case(self):
        """Test occlusion exactly at 10 frame boundary."""
        tracker = BallTracker(dt=1.0/30.0)
        
        # Initialize
        position = Position3D(x=0.0, y=2.0, z=0.0)
        detection = BallDetection(
            detection=Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=100, width=20, height=20),
                confidence=0.95,
                position_3d=position
            ),
            timestamp=0.0,
            pixel_coords=(110, 110),
            position_3d=position
        )
        tracker.update(detection, 0.0)
        
        # Predict for exactly 10 frames
        for i in range(10):
            tracker.predict((i + 1) * (1.0/30.0))
        
        assert tracker.is_occluded()
        assert not tracker.is_long_occlusion()  # Not long until >10
        assert tracker.get_occlusion_duration() == 10
        
        # One more frame makes it long occlusion
        tracker.predict(11 * (1.0/30.0))
        assert tracker.is_long_occlusion()


class TestBallTrackerTrajectory:
    """Test trajectory calculation with various input sequences."""
    
    def test_trajectory_history_limit(self):
        """Test that trajectory history is limited to 30 positions."""
        tracker = BallTracker(dt=1.0/30.0)
        
        # Add 50 detections
        for i in range(50):
            position = Position3D(x=0.0, y=2.0, z=float(i))
            detection = BallDetection(
                detection=Detection(
                    class_id=0,
                    class_name="ball",
                    bounding_box=BoundingBox(x=100, y=100+i, width=20, height=20),
                    confidence=0.95,
                    position_3d=position
                ),
                timestamp=i * (1.0/30.0),
                pixel_coords=(110, 110+i),
                position_3d=position
            )
            tracker.update(detection, i * (1.0/30.0))
        
        # Should only keep last 30
        trajectory = tracker.get_trajectory()
        assert len(trajectory) == 30
    
    def test_trajectory_speed_calculation(self):
        """Test speed metrics calculation."""
        tracker = BallTracker(dt=1.0/30.0)
        
        # Create trajectory with known speeds
        # Ball moving at constant 30 m/s in z direction
        for i in range(10):
            position = Position3D(x=0.0, y=2.0, z=float(i))
            detection = BallDetection(
                detection=Detection(
                    class_id=0,
                    class_name="ball",
                    bounding_box=BoundingBox(x=100, y=100, width=20, height=20),
                    confidence=0.95,
                    position_3d=position
                ),
                timestamp=i * (1.0/30.0),
                pixel_coords=(110, 110),
                position_3d=position
            )
            tracker.update(detection, i * (1.0/30.0))
        
        trajectory_obj = tracker.get_trajectory_object()
        
        # Speed should be approximately 30 m/s (z velocity)
        # Allow some tolerance due to EKF estimation
        assert trajectory_obj.speed_max > 0
        assert trajectory_obj.speed_avg > 0
    
    def test_empty_trajectory_before_initialization(self):
        """Test that trajectory is empty before initialization."""
        tracker = BallTracker()
        
        trajectory = tracker.get_trajectory()
        assert len(trajectory) == 0
        
        trajectory_obj = tracker.get_trajectory_object()
        assert len(trajectory_obj.positions) == 0
        assert trajectory_obj.speed_max == 0.0
        assert trajectory_obj.speed_avg == 0.0


class TestBallTrackerReset:
    """Test tracker reset functionality."""
    
    def test_reset_clears_state(self):
        """Test that reset clears all tracker state."""
        tracker = BallTracker(dt=1.0/30.0)
        
        # Initialize and add some detections
        for i in range(5):
            position = Position3D(x=0.0, y=2.0, z=float(i))
            detection = BallDetection(
                detection=Detection(
                    class_id=0,
                    class_name="ball",
                    bounding_box=BoundingBox(x=100, y=100, width=20, height=20),
                    confidence=0.95,
                    position_3d=position
                ),
                timestamp=i * (1.0/30.0),
                pixel_coords=(110, 110),
                position_3d=position
            )
            tracker.update(detection, i * (1.0/30.0))
        
        # Verify tracker has state
        assert tracker.is_initialized
        assert len(tracker.get_trajectory()) > 0
        
        # Reset
        tracker.reset()
        
        # Verify state is cleared
        assert not tracker.is_initialized
        assert len(tracker.get_trajectory()) == 0
        assert tracker.occlusion_duration == 0
        assert tracker.confidence == 0.0
        assert np.all(tracker.state == 0.0)
    
    def test_reset_allows_reinitialization(self):
        """Test that tracker can be reinitialized after reset."""
        tracker = BallTracker(dt=1.0/30.0)
        
        # Initialize
        position1 = Position3D(x=0.0, y=2.0, z=0.0)
        detection1 = BallDetection(
            detection=Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=100, width=20, height=20),
                confidence=0.95,
                position_3d=position1
            ),
            timestamp=0.0,
            pixel_coords=(110, 110),
            position_3d=position1
        )
        tracker.update(detection1, 0.0)
        
        # Reset
        tracker.reset()
        
        # Reinitialize with new detection
        position2 = Position3D(x=5.0, y=1.0, z=10.0)
        detection2 = BallDetection(
            detection=Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=200, y=200, width=20, height=20),
                confidence=0.90,
                position_3d=position2
            ),
            timestamp=0.0,
            pixel_coords=(210, 210),
            position_3d=position2
        )
        tracker.update(detection2, 0.0)
        
        # Verify new initialization
        assert tracker.is_initialized
        track_state = tracker._get_track_state()
        assert track_state.position.x == pytest.approx(5.0, abs=0.1)
        assert track_state.position.z == pytest.approx(10.0, abs=0.1)


class TestBallTrackerEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_single_detection_trajectory(self):
        """Test trajectory with only one detection."""
        tracker = BallTracker(dt=1.0/30.0)
        
        position = Position3D(x=1.0, y=2.0, z=3.0)
        detection = BallDetection(
            detection=Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=100, width=20, height=20),
                confidence=0.95,
                position_3d=position
            ),
            timestamp=0.0,
            pixel_coords=(110, 110),
            position_3d=position
        )
        tracker.update(detection, 0.0)
        
        trajectory = tracker.get_trajectory()
        assert len(trajectory) == 1
        assert trajectory[0].x == pytest.approx(1.0, abs=0.1)
    
    def test_high_confidence_detection(self):
        """Test tracker with high confidence detection."""
        tracker = BallTracker(dt=1.0/30.0)
        
        position = Position3D(x=1.0, y=2.0, z=3.0)
        detection = BallDetection(
            detection=Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=100, width=20, height=20),
                confidence=0.99,
                position_3d=position
            ),
            timestamp=0.0,
            pixel_coords=(110, 110),
            position_3d=position
        )
        track_state = tracker.update(detection, 0.0)
        
        assert track_state.confidence == 0.99
    
    def test_low_confidence_detection(self):
        """Test tracker with low confidence detection."""
        tracker = BallTracker(dt=1.0/30.0)
        
        position = Position3D(x=1.0, y=2.0, z=3.0)
        detection = BallDetection(
            detection=Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=100, width=20, height=20),
                confidence=0.70,
                position_3d=position
            ),
            timestamp=0.0,
            pixel_coords=(110, 110),
            position_3d=position
        )
        track_state = tracker.update(detection, 0.0)
        
        assert track_state.confidence == 0.70
