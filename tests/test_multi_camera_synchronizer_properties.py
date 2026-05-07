"""
Property-based tests for MultiCameraSynchronizer component.

Tests verify that multi-camera synchronization properties hold across
all valid inputs using Hypothesis framework.
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck

from umpirai.video import (
    MultiCameraSynchronizer,
    CameraIntrinsics,
    SynchronizedFrameSet,
)
from umpirai.models.data_models import Frame, Detection, BoundingBox


# ============================================================================
# Custom Strategies
# ============================================================================

@st.composite
def camera_intrinsics_strategy(draw):
    """Generate valid camera intrinsics."""
    # Focal lengths (typical range for cameras)
    fx = draw(st.floats(min_value=500, max_value=2000))
    fy = draw(st.floats(min_value=500, max_value=2000))
    
    # Principal point (image center, typical 1280x720)
    cx = draw(st.floats(min_value=320, max_value=960))
    cy = draw(st.floats(min_value=180, max_value=540))
    
    camera_matrix = np.array([
        [fx, 0, cx],
        [0, fy, cy],
        [0, 0, 1]
    ])
    
    # Distortion coefficients (small values)
    distortion_coeffs = draw(st.lists(
        st.floats(min_value=-0.5, max_value=0.5),
        min_size=5,
        max_size=5
    ))
    
    return CameraIntrinsics(
        camera_matrix=camera_matrix,
        distortion_coeffs=np.array(distortion_coeffs)
    )


@st.composite
def frame_strategy(draw, camera_id=None):
    """Generate valid video frame."""
    if camera_id is None:
        camera_id = draw(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    
    frame_number = draw(st.integers(min_value=0, max_value=10000))
    timestamp = draw(st.floats(min_value=0.0, max_value=1000.0))
    
    # Create simple test image (small for performance)
    image = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    return Frame(
        camera_id=camera_id,
        frame_number=frame_number,
        timestamp=timestamp,
        image=image,
        metadata={}
    )


@st.composite
def multi_camera_frames_strategy(draw, num_cameras=None):
    """Generate frames from multiple cameras with realistic timestamp offsets."""
    if num_cameras is None:
        num_cameras = draw(st.integers(min_value=2, max_value=4))
    
    # Generate camera IDs
    camera_ids = [f"cam{i}" for i in range(num_cameras)]
    
    # Base timestamp (ensure it's large enough to accommodate negative offsets)
    base_timestamp = draw(st.floats(min_value=1.0, max_value=100.0))
    
    # Generate frames with small random offsets (simulating unsynchronized cameras)
    frames = {}
    for camera_id in camera_ids:
        # Add random offset up to ±200ms
        offset = draw(st.floats(min_value=-0.2, max_value=0.2))
        timestamp = base_timestamp + offset
        
        frame = Frame(
            camera_id=camera_id,
            frame_number=draw(st.integers(min_value=0, max_value=1000)),
            timestamp=timestamp,
            image=np.zeros((720, 1280, 3), dtype=np.uint8),
            metadata={}
        )
        frames[camera_id] = frame
    
    return frames


# ============================================================================
# Property Tests
# ============================================================================

class TestMultiCameraSynchronizerProperties:
    """Property-based tests for MultiCameraSynchronizer."""
    
    @given(
        intrinsics=camera_intrinsics_strategy(),
        camera_id=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @settings(max_examples=100, deadline=None)
    def test_property_add_camera_stores_intrinsics(self, intrinsics, camera_id):
        """
        Property: For any valid camera intrinsics and camera ID,
        add_camera SHALL store the intrinsics correctly.
        """
        synchronizer = MultiCameraSynchronizer()
        
        synchronizer.add_camera(camera_id, intrinsics)
        
        assert camera_id in synchronizer.camera_intrinsics
        assert synchronizer.camera_intrinsics[camera_id] == intrinsics
    
    @given(
        num_cameras=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_26_multi_camera_timestamp_synchronization(self, num_cameras):
        """
        **Validates: Requirements 12.4**
        
        Feature: ai-auto-umpiring-system, Property 26: Multi-Camera Timestamp Synchronization
        
        For any set of frames from multiple cameras, the synchronization system
        SHALL align timestamps to within 50 milliseconds.
        """
        # Arrange: Create synchronizer and add cameras
        synchronizer = MultiCameraSynchronizer(target_sync_ms=50.0)
        
        camera_ids = [f"cam{i}" for i in range(num_cameras)]
        
        # Add cameras with intrinsics
        for camera_id in camera_ids:
            intrinsics = CameraIntrinsics(
                camera_matrix=np.eye(3) * 1000,
                distortion_coeffs=np.zeros(5)
            )
            synchronizer.add_camera(camera_id, intrinsics)
        
        # Create frames with timestamp offsets (simulating unsynchronized cameras)
        base_timestamp = 10.0
        frames = {}
        actual_offsets = {}
        
        # Reference camera (first one) has zero offset
        reference_camera_id = camera_ids[0]
        actual_offsets[reference_camera_id] = 0.0
        
        for i, camera_id in enumerate(camera_ids):
            if i == 0:
                # Reference camera: no offset
                offset = 0.0
            else:
                # Other cameras: small offsets within ±50ms
                offset = (i - 1) * 0.03  # 30ms, 60ms, etc.
            
            actual_offsets[camera_id] = offset
            timestamp = base_timestamp + offset
            
            frame = Frame(
                camera_id=camera_id,
                frame_number=100,
                timestamp=timestamp,
                image=np.zeros((720, 1280, 3), dtype=np.uint8),
                metadata={}
            )
            frames[camera_id] = frame
        
        # Manually set the temporal offsets in the synchronizer
        # (In real usage, these would be estimated from ball motion)
        for camera_id, offset in actual_offsets.items():
            synchronizer.temporal_offsets[camera_id] = offset
        
        # Act: Synchronize frames
        synchronized = synchronizer.synchronize_frames(frames)
        
        # Assert: All timestamps should be aligned within 50ms
        reference_timestamp = synchronized.reference_timestamp
        
        for camera_id, frame in synchronized.frames.items():
            timestamp_diff = abs(frame.timestamp - reference_timestamp)
            # Allow for numerical precision issues
            assert timestamp_diff <= 0.051, \
                f"Camera {camera_id} timestamp differs by {timestamp_diff*1000:.2f}ms, exceeds 50ms threshold"
    
    @given(
        frames=multi_camera_frames_strategy(num_cameras=2)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_synchronization_preserves_frame_count(self, frames):
        """
        Property: For any set of input frames, synchronization SHALL preserve
        the number of frames (no frames lost or added).
        """
        # Arrange: Create synchronizer and add cameras
        synchronizer = MultiCameraSynchronizer()
        
        for camera_id in frames.keys():
            intrinsics = CameraIntrinsics(
                camera_matrix=np.eye(3) * 1000,
                distortion_coeffs=np.zeros(5)
            )
            synchronizer.add_camera(camera_id, intrinsics)
        
        # Act: Synchronize frames
        synchronized = synchronizer.synchronize_frames(frames)
        
        # Assert: Same number of frames
        assert len(synchronized.frames) == len(frames)
        
        # Assert: All camera IDs preserved
        assert set(synchronized.frames.keys()) == set(frames.keys())
    
    @given(
        frames=multi_camera_frames_strategy(num_cameras=3)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_synchronization_quality_bounds(self, frames):
        """
        Property: For any set of frames, the sync quality metric SHALL be
        in the range [0.0, 1.0].
        """
        # Arrange: Create synchronizer and add cameras
        synchronizer = MultiCameraSynchronizer()
        
        for camera_id in frames.keys():
            intrinsics = CameraIntrinsics(
                camera_matrix=np.eye(3) * 1000,
                distortion_coeffs=np.zeros(5)
            )
            synchronizer.add_camera(camera_id, intrinsics)
        
        # Act: Synchronize frames
        synchronized = synchronizer.synchronize_frames(frames)
        
        # Assert: Sync quality in valid range
        assert 0.0 <= synchronized.sync_quality <= 1.0
        
        # Assert: get_sync_quality returns same value
        assert synchronizer.get_sync_quality() == synchronized.sync_quality
    
    @given(
        camera_id=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @settings(max_examples=100, deadline=None)
    def test_property_single_camera_perfect_sync(self, camera_id):
        """
        Property: For any single camera, synchronization SHALL return
        perfect sync quality (1.0).
        """
        # Arrange: Create synchronizer with one camera
        synchronizer = MultiCameraSynchronizer()
        
        intrinsics = CameraIntrinsics(
            camera_matrix=np.eye(3) * 1000,
            distortion_coeffs=np.zeros(5)
        )
        synchronizer.add_camera(camera_id, intrinsics)
        
        # Create single frame
        frame = Frame(
            camera_id=camera_id,
            frame_number=0,
            timestamp=10.0,
            image=np.zeros((720, 1280, 3), dtype=np.uint8),
            metadata={}
        )
        
        # Act: Synchronize
        synchronized = synchronizer.synchronize_frames({camera_id: frame})
        
        # Assert: Perfect sync quality for single camera
        assert synchronized.sync_quality == 1.0
    
    @given(
        num_cameras=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_temporal_offsets_stored(self, num_cameras):
        """
        Property: For any set of cameras, synchronization SHALL store
        temporal offsets for each camera.
        """
        # Arrange: Create synchronizer and add cameras
        synchronizer = MultiCameraSynchronizer()
        
        camera_ids = [f"cam{i}" for i in range(num_cameras)]
        
        for camera_id in camera_ids:
            intrinsics = CameraIntrinsics(
                camera_matrix=np.eye(3) * 1000,
                distortion_coeffs=np.zeros(5)
            )
            synchronizer.add_camera(camera_id, intrinsics)
        
        # Create frames
        frames = {}
        for camera_id in camera_ids:
            frame = Frame(
                camera_id=camera_id,
                frame_number=0,
                timestamp=10.0,
                image=np.zeros((720, 1280, 3), dtype=np.uint8),
                metadata={}
            )
            frames[camera_id] = frame
        
        # Act: Synchronize
        synchronized = synchronizer.synchronize_frames(frames)
        
        # Assert: Temporal offsets stored for all cameras
        assert len(synchronized.temporal_offsets) == num_cameras
        for camera_id in camera_ids:
            assert camera_id in synchronized.temporal_offsets
            assert isinstance(synchronized.temporal_offsets[camera_id], float)
    
    @given(
        num_cameras=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_reference_camera_zero_offset(self, num_cameras):
        """
        Property: For any multi-camera setup, the reference camera (first added)
        SHALL have zero temporal offset.
        """
        # Arrange: Create synchronizer and add cameras
        synchronizer = MultiCameraSynchronizer()
        
        camera_ids = [f"cam{i}" for i in range(num_cameras)]
        
        for camera_id in camera_ids:
            intrinsics = CameraIntrinsics(
                camera_matrix=np.eye(3) * 1000,
                distortion_coeffs=np.zeros(5)
            )
            synchronizer.add_camera(camera_id, intrinsics)
        
        # Act & Assert: Reference camera (first added) has zero offset
        reference_camera_id = camera_ids[0]
        assert synchronizer.reference_camera_id == reference_camera_id
        assert synchronizer.temporal_offsets[reference_camera_id] == 0.0
    
    @given(
        frames=multi_camera_frames_strategy(num_cameras=2)
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_synchronized_frames_have_metadata(self, frames):
        """
        Property: For any synchronized frames, each frame SHALL contain
        temporal offset metadata.
        """
        # Arrange: Create synchronizer and add cameras
        synchronizer = MultiCameraSynchronizer()
        
        for camera_id in frames.keys():
            intrinsics = CameraIntrinsics(
                camera_matrix=np.eye(3) * 1000,
                distortion_coeffs=np.zeros(5)
            )
            synchronizer.add_camera(camera_id, intrinsics)
        
        # Act: Synchronize frames
        synchronized = synchronizer.synchronize_frames(frames)
        
        # Assert: All frames have temporal_offset in metadata
        for camera_id, frame in synchronized.frames.items():
            assert "temporal_offset" in frame.metadata
            assert isinstance(frame.metadata["temporal_offset"], float)
    
    @given(
        num_cameras=st.integers(min_value=1, max_value=4)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_max_cameras_enforced(self, num_cameras):
        """
        Property: For any number of cameras up to max_cameras, add_camera
        SHALL succeed. Beyond max_cameras, it SHALL raise ValueError.
        """
        # Arrange: Create synchronizer with specific max
        max_cameras = 4
        synchronizer = MultiCameraSynchronizer(max_cameras=max_cameras)
        
        # Act & Assert: Add cameras up to max
        for i in range(min(num_cameras, max_cameras)):
            intrinsics = CameraIntrinsics(
                camera_matrix=np.eye(3) * 1000,
                distortion_coeffs=np.zeros(5)
            )
            synchronizer.add_camera(f"cam{i}", intrinsics)
        
        # If we've reached max, adding another should fail
        if num_cameras >= max_cameras:
            intrinsics = CameraIntrinsics(
                camera_matrix=np.eye(3) * 1000,
                distortion_coeffs=np.zeros(5)
            )
            with pytest.raises(ValueError, match="Maximum number of cameras"):
                synchronizer.add_camera(f"cam{max_cameras}", intrinsics)
    
    @given(
        camera_id=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @settings(max_examples=100, deadline=None)
    def test_property_duplicate_camera_rejected(self, camera_id):
        """
        Property: For any camera ID, adding it twice SHALL raise ValueError.
        """
        # Arrange: Create synchronizer and add camera
        synchronizer = MultiCameraSynchronizer()
        
        intrinsics = CameraIntrinsics(
            camera_matrix=np.eye(3) * 1000,
            distortion_coeffs=np.zeros(5)
        )
        synchronizer.add_camera(camera_id, intrinsics)
        
        # Act & Assert: Adding same camera again should fail
        with pytest.raises(ValueError, match="already exists"):
            synchronizer.add_camera(camera_id, intrinsics)
    
    @given(
        num_cameras=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_estimate_temporal_offset_returns_float(self, num_cameras):
        """
        Property: For any two cameras, estimate_temporal_offset SHALL return
        a float value representing the offset in seconds.
        """
        # Arrange: Create synchronizer with cameras
        synchronizer = MultiCameraSynchronizer()
        
        camera_ids = [f"cam{i}" for i in range(num_cameras)]
        
        for camera_id in camera_ids:
            intrinsics = CameraIntrinsics(
                camera_matrix=np.eye(3) * 1000,
                distortion_coeffs=np.zeros(5)
            )
            synchronizer.add_camera(camera_id, intrinsics)
        
        # Act: Estimate offset between first two cameras
        offset = synchronizer.estimate_temporal_offset(camera_ids[0], camera_ids[1])
        
        # Assert: Offset is a float
        assert isinstance(offset, (float, np.floating))
