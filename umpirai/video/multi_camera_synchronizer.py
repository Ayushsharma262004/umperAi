"""
Multi-camera synchronization component for temporal alignment of video frames.

This module provides the MultiCameraSynchronizer class which aligns frames from
multiple cameras to the same temporal reference using cross-view object motion alignment.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy.optimize import minimize

from umpirai.models.data_models import Frame, Detection, Position3D, BoundingBox


@dataclass
class CameraIntrinsics:
    """Camera intrinsic parameters for 3D reconstruction."""
    camera_matrix: np.ndarray  # 3x3 camera matrix [fx, 0, cx; 0, fy, cy; 0, 0, 1]
    distortion_coeffs: np.ndarray  # Distortion coefficients [k1, k2, p1, p2, k3]
    rotation_matrix: Optional[np.ndarray] = None  # 3x3 rotation matrix (camera pose)
    translation_vector: Optional[np.ndarray] = None  # 3x1 translation vector (camera position)
    
    def __post_init__(self):
        """Validate camera intrinsics."""
        if not isinstance(self.camera_matrix, np.ndarray):
            raise TypeError("camera_matrix must be a numpy array")
        if self.camera_matrix.shape != (3, 3):
            raise ValueError("camera_matrix must be 3x3")
        if not isinstance(self.distortion_coeffs, np.ndarray):
            raise TypeError("distortion_coeffs must be a numpy array")
        if self.rotation_matrix is not None:
            if not isinstance(self.rotation_matrix, np.ndarray):
                raise TypeError("rotation_matrix must be a numpy array")
            if self.rotation_matrix.shape != (3, 3):
                raise ValueError("rotation_matrix must be 3x3")
        if self.translation_vector is not None:
            if not isinstance(self.translation_vector, np.ndarray):
                raise TypeError("translation_vector must be a numpy array")
            if self.translation_vector.shape not in [(3,), (3, 1)]:
                raise ValueError("translation_vector must be 3x1 or (3,)")


@dataclass
class SynchronizedFrameSet:
    """Set of synchronized frames from multiple cameras."""
    frames: Dict[str, Frame]  # camera_id -> frame
    reference_timestamp: float  # Common temporal reference
    temporal_offsets: Dict[str, float]  # camera_id -> offset in seconds
    sync_quality: float  # Quality metric [0, 1]
    
    def __post_init__(self):
        """Validate synchronized frame set."""
        if not isinstance(self.frames, dict):
            raise TypeError("frames must be a dictionary")
        if not all(isinstance(k, str) for k in self.frames.keys()):
            raise TypeError("frame keys must be strings")
        if not all(isinstance(v, Frame) for v in self.frames.values()):
            raise TypeError("frame values must be Frame instances")
        if not isinstance(self.reference_timestamp, (int, float)):
            raise TypeError("reference_timestamp must be numeric")
        if not isinstance(self.temporal_offsets, dict):
            raise TypeError("temporal_offsets must be a dictionary")
        if not isinstance(self.sync_quality, (int, float)):
            raise TypeError("sync_quality must be numeric")
        if not (0.0 <= self.sync_quality <= 1.0):
            raise ValueError("sync_quality must be in range [0.0, 1.0]")


@dataclass
class BallDetectionSequence:
    """Sequence of ball detections from a single camera."""
    camera_id: str
    detections: List[Detection]
    timestamps: List[float]
    positions_2d: List[Tuple[float, float]]  # (x, y) pixel coordinates
    
    def __post_init__(self):
        """Validate ball detection sequence."""
        if not isinstance(self.camera_id, str):
            raise TypeError("camera_id must be a string")
        if not isinstance(self.detections, list):
            raise TypeError("detections must be a list")
        if not isinstance(self.timestamps, list):
            raise TypeError("timestamps must be a list")
        if not isinstance(self.positions_2d, list):
            raise TypeError("positions_2d must be a list")
        if len(self.detections) != len(self.timestamps):
            raise ValueError("detections and timestamps must have same length")
        if len(self.detections) != len(self.positions_2d):
            raise ValueError("detections and positions_2d must have same length")


class MultiCameraSynchronizer:
    """
    Multi-camera synchronizer for temporal alignment of video frames.
    
    Uses cross-view object motion alignment (based on VisualSync approach) to
    synchronize frames from multiple cameras to millisecond accuracy.
    
    Algorithm:
    1. Detect ball position in each camera view
    2. Compute epipolar constraints for ball motion across views
    3. Optimize temporal offsets to minimize epipolar constraint violations
    4. Apply offsets to align frame timestamps
    5. Interpolate frames if necessary to achieve exact alignment
    
    Supports up to 4 cameras simultaneously with target synchronization
    accuracy of <50ms offset.
    """
    
    def __init__(self, max_cameras: int = 4, target_sync_ms: float = 50.0):
        """
        Initialize multi-camera synchronizer.
        
        Args:
            max_cameras: Maximum number of cameras supported (default: 4)
            target_sync_ms: Target synchronization accuracy in milliseconds (default: 50.0)
        """
        self.max_cameras = max_cameras
        self.target_sync_ms = target_sync_ms
        
        # Camera intrinsics storage
        self.camera_intrinsics: Dict[str, CameraIntrinsics] = {}
        
        # Temporal offset estimates (relative to first camera)
        self.temporal_offsets: Dict[str, float] = {}
        
        # Reference camera (first camera added)
        self.reference_camera_id: Optional[str] = None
        
        # Ball detection history for offset estimation
        self.ball_detection_history: Dict[str, BallDetectionSequence] = {}
        
        # Sync quality tracking
        self.last_sync_quality: float = 0.0
    
    def add_camera(self, camera_id: str, intrinsics: CameraIntrinsics) -> None:
        """
        Add a camera with its intrinsic parameters.
        
        Args:
            camera_id: Unique identifier for the camera
            intrinsics: Camera intrinsic parameters
            
        Raises:
            ValueError: If camera already exists or max cameras exceeded
        """
        if camera_id in self.camera_intrinsics:
            raise ValueError(f"Camera '{camera_id}' already exists")
        
        if len(self.camera_intrinsics) >= self.max_cameras:
            raise ValueError(f"Maximum number of cameras ({self.max_cameras}) exceeded")
        
        self.camera_intrinsics[camera_id] = intrinsics
        
        # Set reference camera if this is the first camera
        if self.reference_camera_id is None:
            self.reference_camera_id = camera_id
            self.temporal_offsets[camera_id] = 0.0  # Reference has zero offset
        else:
            # Initialize offset to zero (will be estimated later)
            self.temporal_offsets[camera_id] = 0.0
    
    def synchronize_frames(self, frames: Dict[str, Frame]) -> SynchronizedFrameSet:
        """
        Synchronize frames from multiple cameras using cross-view object motion alignment.
        
        Args:
            frames: Dictionary mapping camera_id to Frame
            
        Returns:
            SynchronizedFrameSet with aligned frames and temporal offsets
            
        Raises:
            ValueError: If frames dict is empty or contains unknown cameras
        """
        if not frames:
            raise ValueError("frames dictionary cannot be empty")
        
        # Validate all cameras are known
        for camera_id in frames.keys():
            if camera_id not in self.camera_intrinsics:
                raise ValueError(f"Unknown camera '{camera_id}'. Use add_camera() first.")
        
        # If only one camera, no synchronization needed
        if len(frames) == 1:
            camera_id = list(frames.keys())[0]
            return SynchronizedFrameSet(
                frames=frames,
                reference_timestamp=frames[camera_id].timestamp,
                temporal_offsets={camera_id: 0.0},
                sync_quality=1.0
            )
        
        # Use reference camera timestamp as common reference
        if self.reference_camera_id not in frames:
            # Reference camera not in current frame set, use first available
            reference_camera_id = list(frames.keys())[0]
            reference_timestamp = frames[reference_camera_id].timestamp
        else:
            reference_camera_id = self.reference_camera_id
            reference_timestamp = frames[reference_camera_id].timestamp
        
        # Apply temporal offsets to align frames
        aligned_frames = {}
        for camera_id, frame in frames.items():
            # Adjust timestamp using estimated offset
            offset = self.temporal_offsets.get(camera_id, 0.0)
            
            # Create aligned frame (shallow copy with adjusted timestamp)
            aligned_frame = Frame(
                camera_id=frame.camera_id,
                frame_number=frame.frame_number,
                timestamp=frame.timestamp - offset,  # Apply offset
                image=frame.image,
                metadata={**frame.metadata, "temporal_offset": offset}
            )
            aligned_frames[camera_id] = aligned_frame
        
        # Calculate sync quality based on timestamp alignment
        sync_quality = self._calculate_sync_quality(aligned_frames, reference_timestamp)
        self.last_sync_quality = sync_quality
        
        return SynchronizedFrameSet(
            frames=aligned_frames,
            reference_timestamp=reference_timestamp,
            temporal_offsets=self.temporal_offsets.copy(),
            sync_quality=sync_quality
        )
    
    def estimate_temporal_offset(
        self,
        cam1_id: str,
        cam2_id: str,
        ball_detections_cam1: Optional[List[Tuple[Detection, float]]] = None,
        ball_detections_cam2: Optional[List[Tuple[Detection, float]]] = None
    ) -> float:
        """
        Estimate temporal offset between two cameras using ball motion as reference.
        
        Uses epipolar constraint optimization to find the temporal offset that
        minimizes epipolar violations across ball trajectories.
        
        Args:
            cam1_id: First camera identifier
            cam2_id: Second camera identifier
            ball_detections_cam1: Optional list of (detection, timestamp) tuples for cam1
            ball_detections_cam2: Optional list of (detection, timestamp) tuples for cam2
            
        Returns:
            Temporal offset in seconds (cam2 relative to cam1)
            
        Raises:
            ValueError: If cameras are unknown or insufficient detections
        """
        if cam1_id not in self.camera_intrinsics:
            raise ValueError(f"Unknown camera '{cam1_id}'")
        if cam2_id not in self.camera_intrinsics:
            raise ValueError(f"Unknown camera '{cam2_id}'")
        
        # If ball detections provided, use them; otherwise use history
        if ball_detections_cam1 is not None and ball_detections_cam2 is not None:
            if len(ball_detections_cam1) < 2 or len(ball_detections_cam2) < 2:
                raise ValueError("Need at least 2 ball detections per camera for offset estimation")
            
            # Extract positions and timestamps
            positions_cam1 = [self._get_ball_center(det) for det, _ in ball_detections_cam1]
            timestamps_cam1 = [ts for _, ts in ball_detections_cam1]
            positions_cam2 = [self._get_ball_center(det) for det, _ in ball_detections_cam2]
            timestamps_cam2 = [ts for _, ts in ball_detections_cam2]
        else:
            # Use detection history
            if cam1_id not in self.ball_detection_history or cam2_id not in self.ball_detection_history:
                # No history available, return current offset or zero
                return self.temporal_offsets.get(cam2_id, 0.0) - self.temporal_offsets.get(cam1_id, 0.0)
            
            seq1 = self.ball_detection_history[cam1_id]
            seq2 = self.ball_detection_history[cam2_id]
            
            if len(seq1.positions_2d) < 2 or len(seq2.positions_2d) < 2:
                return self.temporal_offsets.get(cam2_id, 0.0) - self.temporal_offsets.get(cam1_id, 0.0)
            
            positions_cam1 = seq1.positions_2d
            timestamps_cam1 = seq1.timestamps
            positions_cam2 = seq2.positions_2d
            timestamps_cam2 = seq2.timestamps
        
        # Optimize temporal offset to minimize epipolar constraint violations
        offset = self._optimize_temporal_offset(
            positions_cam1, timestamps_cam1,
            positions_cam2, timestamps_cam2,
            self.camera_intrinsics[cam1_id],
            self.camera_intrinsics[cam2_id]
        )
        
        # Update stored offset (relative to reference camera)
        if cam1_id == self.reference_camera_id:
            self.temporal_offsets[cam2_id] = offset
        elif cam2_id == self.reference_camera_id:
            self.temporal_offsets[cam1_id] = -offset
        else:
            # Both cameras are non-reference, update cam2 relative to cam1
            offset1 = self.temporal_offsets.get(cam1_id, 0.0)
            self.temporal_offsets[cam2_id] = offset1 + offset
        
        return offset
    
    def get_sync_quality(self) -> float:
        """
        Get the synchronization quality metric.
        
        Returns:
            Sync quality in range [0.0, 1.0], where 1.0 is perfect synchronization
        """
        return self.last_sync_quality
    
    def _get_ball_center(self, detection: Detection) -> Tuple[float, float]:
        """
        Extract ball center position from detection.
        
        Args:
            detection: Ball detection
            
        Returns:
            (x, y) pixel coordinates of ball center
        """
        bbox = detection.bounding_box
        center_x, center_y = bbox.center()
        return (center_x, center_y)
    
    def _calculate_epipolar_constraint(
        self,
        point1: Tuple[float, float],
        point2: Tuple[float, float],
        intrinsics1: CameraIntrinsics,
        intrinsics2: CameraIntrinsics
    ) -> float:
        """
        Calculate epipolar constraint violation for a point correspondence.
        
        The epipolar constraint states that corresponding points in two views
        must satisfy: x2^T * F * x1 = 0, where F is the fundamental matrix.
        
        Args:
            point1: (x, y) in camera 1
            point2: (x, y) in camera 2
            intrinsics1: Camera 1 intrinsics
            intrinsics2: Camera 2 intrinsics
            
        Returns:
            Epipolar constraint violation (lower is better)
        """
        # Convert points to homogeneous coordinates
        x1 = np.array([point1[0], point1[1], 1.0])
        x2 = np.array([point2[0], point2[1], 1.0])
        
        # Compute fundamental matrix from camera intrinsics
        # F = K2^-T * [t]_x * R * K1^-1
        # For simplicity, if rotation/translation not available, use simplified constraint
        if intrinsics1.rotation_matrix is None or intrinsics2.rotation_matrix is None:
            # Simplified constraint: use normalized coordinates
            K1_inv = np.linalg.inv(intrinsics1.camera_matrix)
            K2_inv = np.linalg.inv(intrinsics2.camera_matrix)
            
            x1_norm = K1_inv @ x1
            x2_norm = K2_inv @ x2
            
            # Simplified epipolar constraint (assumes parallel cameras)
            # Violation is the difference in normalized y-coordinates
            violation = abs(x2_norm[1] - x1_norm[1])
        else:
            # Full epipolar constraint with fundamental matrix
            R = intrinsics2.rotation_matrix @ intrinsics1.rotation_matrix.T
            t = intrinsics2.translation_vector - R @ intrinsics1.translation_vector
            
            # Skew-symmetric matrix for cross product
            t_x = np.array([
                [0, -t[2], t[1]],
                [t[2], 0, -t[0]],
                [-t[1], t[0], 0]
            ])
            
            # Essential matrix
            E = t_x @ R
            
            # Fundamental matrix
            K1_inv = np.linalg.inv(intrinsics1.camera_matrix)
            K2_inv = np.linalg.inv(intrinsics2.camera_matrix)
            F = K2_inv.T @ E @ K1_inv
            
            # Epipolar constraint: x2^T * F * x1 = 0
            violation = abs(x2.T @ F @ x1)
        
        return violation
    
    def _optimize_temporal_offset(
        self,
        positions_cam1: List[Tuple[float, float]],
        timestamps_cam1: List[float],
        positions_cam2: List[Tuple[float, float]],
        timestamps_cam2: List[float],
        intrinsics1: CameraIntrinsics,
        intrinsics2: CameraIntrinsics
    ) -> float:
        """
        Optimize temporal offset to minimize epipolar constraint violations.
        
        Args:
            positions_cam1: Ball positions in camera 1
            timestamps_cam1: Timestamps for camera 1 positions
            positions_cam2: Ball positions in camera 2
            timestamps_cam2: Timestamps for camera 2 positions
            intrinsics1: Camera 1 intrinsics
            intrinsics2: Camera 2 intrinsics
            
        Returns:
            Optimal temporal offset (seconds)
        """
        def objective(offset: np.ndarray) -> float:
            """
            Objective function: sum of epipolar constraint violations.
            
            Args:
                offset: Temporal offset to test (1D array)
                
            Returns:
                Total epipolar violation
            """
            offset_val = offset[0]
            
            # Adjust timestamps for cam2 by offset
            adjusted_timestamps_cam2 = [ts - offset_val for ts in timestamps_cam2]
            
            # Find corresponding points using nearest timestamp matching
            total_violation = 0.0
            num_correspondences = 0
            
            for i, ts1 in enumerate(timestamps_cam1):
                # Find closest timestamp in adjusted cam2
                time_diffs = [abs(ts2 - ts1) for ts2 in adjusted_timestamps_cam2]
                if not time_diffs:
                    continue
                
                min_diff_idx = np.argmin(time_diffs)
                min_diff = time_diffs[min_diff_idx]
                
                # Only use correspondences within 100ms
                if min_diff < 0.1:
                    point1 = positions_cam1[i]
                    point2 = positions_cam2[min_diff_idx]
                    
                    violation = self._calculate_epipolar_constraint(
                        point1, point2, intrinsics1, intrinsics2
                    )
                    total_violation += violation
                    num_correspondences += 1
            
            # Return average violation (or large value if no correspondences)
            if num_correspondences == 0:
                return 1e6
            
            return total_violation / num_correspondences
        
        # Initial guess: zero offset
        initial_offset = np.array([0.0])
        
        # Bounds: search within ±1 second
        bounds = [(-1.0, 1.0)]
        
        # Optimize using scipy
        result = minimize(
            objective,
            initial_offset,
            method='L-BFGS-B',
            bounds=bounds
        )
        
        return result.x[0]
    
    def _calculate_sync_quality(
        self,
        frames: Dict[str, Frame],
        reference_timestamp: float
    ) -> float:
        """
        Calculate synchronization quality metric.
        
        Quality is based on how well timestamps align after offset correction.
        
        Args:
            frames: Aligned frames
            reference_timestamp: Reference timestamp
            
        Returns:
            Sync quality in range [0.0, 1.0]
        """
        if len(frames) <= 1:
            return 1.0
        
        # Calculate maximum timestamp deviation from reference
        max_deviation = 0.0
        for frame in frames.values():
            deviation = abs(frame.timestamp - reference_timestamp)
            max_deviation = max(max_deviation, deviation)
        
        # Convert to quality metric
        # Target: <50ms deviation = quality 1.0
        # 100ms deviation = quality 0.5
        # >200ms deviation = quality 0.0
        target_ms = self.target_sync_ms / 1000.0  # Convert to seconds
        
        if max_deviation <= target_ms:
            quality = 1.0
        elif max_deviation >= 4 * target_ms:
            quality = 0.0
        else:
            # Linear interpolation
            quality = 1.0 - (max_deviation - target_ms) / (3 * target_ms)
        
        return max(0.0, min(1.0, quality))
    
    def _interpolate_frame(
        self,
        frame1: Frame,
        frame2: Frame,
        target_timestamp: float
    ) -> Frame:
        """
        Interpolate between two frames to achieve exact temporal alignment.
        
        Uses linear interpolation of pixel values.
        
        Args:
            frame1: Earlier frame
            frame2: Later frame
            target_timestamp: Desired timestamp
            
        Returns:
            Interpolated frame
        """
        # Calculate interpolation weight
        dt = frame2.timestamp - frame1.timestamp
        if dt == 0:
            return frame1
        
        alpha = (target_timestamp - frame1.timestamp) / dt
        alpha = max(0.0, min(1.0, alpha))  # Clamp to [0, 1]
        
        # Interpolate images
        interpolated_image = (
            (1 - alpha) * frame1.image.astype(np.float32) +
            alpha * frame2.image.astype(np.float32)
        ).astype(np.uint8)
        
        # Create interpolated frame
        interpolated_frame = Frame(
            camera_id=frame1.camera_id,
            frame_number=frame1.frame_number,
            timestamp=target_timestamp,
            image=interpolated_image,
            metadata={
                **frame1.metadata,
                "interpolated": True,
                "interpolation_alpha": alpha,
                "source_frames": [frame1.frame_number, frame2.frame_number]
            }
        )
        
        return interpolated_frame
