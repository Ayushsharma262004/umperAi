"""
Ball tracking component using Extended Kalman Filter (EKF).

This module provides the BallTracker class which tracks ball position across frames
and predicts trajectory during occlusion using an Extended Kalman Filter with a
9-dimensional state vector (position, velocity, acceleration).
"""

import time
from typing import List, Optional, Tuple
import numpy as np
from dataclasses import dataclass

from umpirai.models.data_models import (
    Detection,
    Position3D,
    Vector3D,
    TrackState,
    Trajectory,
)


# Physical constants
GRAVITY = 9.81  # m/s² (gravitational acceleration)
DRAG_COEFFICIENT = 0.98  # Air resistance damping factor per frame


@dataclass
class BallDetection:
    """Ball detection with 2D pixel coordinates and optional 3D position."""
    detection: Detection
    timestamp: float
    pixel_coords: Tuple[float, float]  # (u, v) in pixels
    position_3d: Optional[Position3D] = None


class BallTracker:
    """
    Ball tracker using Extended Kalman Filter for trajectory estimation.
    
    State Vector (9 dimensions):
    - Position: (x, y, z) in meters relative to pitch center
    - Velocity: (vx, vy, vz) in m/s
    - Acceleration: (ax, ay, az) in m/s² (models gravity and air resistance)
    
    Process Model:
    - x(t+1) = x(t) + vx(t)*dt + 0.5*ax(t)*dt²
    - y(t+1) = y(t) + vy(t)*dt + 0.5*ay(t)*dt²
    - z(t+1) = z(t) + vz(t)*dt + 0.5*az(t)*dt² - 0.5*g*dt²  (gravity)
    - vx(t+1) = vx(t) + ax(t)*dt
    - vy(t+1) = vy(t) + ay(t)*dt
    - vz(t+1) = vz(t) + az(t)*dt - g*dt
    - ax(t+1) = ax(t) * drag_coefficient
    - ay(t+1) = ay(t) * drag_coefficient
    - az(t+1) = az(t) * drag_coefficient
    
    Measurement Model:
    - Observations: 2D pixel coordinates (u, v) from camera(s)
    - Convert to 3D using camera calibration and ground plane assumption
    - Measurement noise: σ = 5 pixels
    
    Occlusion Handling:
    - Track occlusion duration (frame count without detection)
    - If occluded ≤10 frames (~333ms at 30 FPS): use EKF prediction
    - If occluded >10 frames: flag decision as uncertain
    - Resume tracking when ball reappears
    """
    
    def __init__(
        self,
        dt: float = 1.0 / 30.0,  # Time step (30 FPS)
        measurement_noise: float = 5.0,  # pixels
        process_noise: float = 0.1,
        camera_calibration: Optional[dict] = None
    ):
        """
        Initialize ball tracker with EKF parameters.
        
        Args:
            dt: Time step between frames in seconds (default: 1/30 for 30 FPS)
            measurement_noise: Measurement noise standard deviation in pixels
            process_noise: Process noise standard deviation
            camera_calibration: Camera calibration data for 2D to 3D conversion
        """
        self.dt = dt
        self.measurement_noise = measurement_noise
        self.process_noise = process_noise
        self.camera_calibration = camera_calibration or {}
        
        # State vector: [x, y, z, vx, vy, vz, ax, ay, az]
        self.state = np.zeros(9)
        
        # Covariance matrix (9x9)
        self.covariance = np.eye(9) * 10.0  # Initial uncertainty
        
        # Tracking state
        self.track_id = "ball_track_0"
        self.last_seen = 0.0
        self.occlusion_duration = 0  # frames without detection
        self.confidence = 0.0
        self.is_initialized = False
        
        # Trajectory history (store last 30 positions = 1 second at 30 FPS)
        self.max_history = 30
        self.position_history: List[Position3D] = []
        self.velocity_history: List[Vector3D] = []
        self.timestamp_history: List[float] = []
        
        # Occlusion threshold
        self.max_occlusion_frames = 10
    
    def update(self, detection: BallDetection, timestamp: float) -> TrackState:
        """
        Update tracker with new ball detection.
        
        Performs EKF update step:
        1. Predict state forward to current timestamp
        2. Compute Kalman gain
        3. Update state with measurement
        4. Update covariance
        
        Args:
            detection: Ball detection with pixel coordinates
            timestamp: Detection timestamp in seconds
            
        Returns:
            Updated track state
        """
        # Convert detection to 3D position
        # Prefer position_3d from detection if available
        if detection.position_3d is not None:
            measured_position = detection.position_3d
        elif detection.detection.position_3d is not None:
            measured_position = detection.detection.position_3d
        else:
            # Convert 2D pixel coordinates to 3D using camera calibration
            measured_position = self._pixel_to_3d(
                detection.pixel_coords,
                detection.detection.confidence
            )
        
        # Initialize state if this is first detection
        if not self.is_initialized:
            self._initialize_state(measured_position, timestamp)
            self.is_initialized = True
            self.occlusion_duration = 0
        else:
            # Predict state forward
            dt = timestamp - self.last_seen
            self._predict(dt)
            
            # Update with measurement
            self._update_measurement(measured_position, detection.detection.confidence)
            
            # Reset occlusion counter
            self.occlusion_duration = 0
        
        # Update tracking metadata
        self.last_seen = timestamp
        self.confidence = detection.detection.confidence
        
        # Update trajectory history
        self._update_history(timestamp)
        
        # Return current track state
        return self._get_track_state()
    
    def predict(self, timestamp: float) -> Position3D:
        """
        Predict ball position at given timestamp during occlusion.
        
        Uses EKF prediction without measurement update.
        Increments occlusion duration counter.
        
        Args:
            timestamp: Target timestamp for prediction
            
        Returns:
            Predicted 3D position
        """
        if not self.is_initialized:
            raise RuntimeError("Tracker not initialized. Call update() with first detection.")
        
        # Predict state forward
        dt = timestamp - self.last_seen
        self._predict(dt)
        
        # Increment occlusion counter
        self.occlusion_duration += 1
        
        # Update timestamp
        self.last_seen = timestamp
        
        # Update history with predicted position
        self._update_history(timestamp)
        
        # Return predicted position
        return Position3D(
            x=float(self.state[0]),
            y=float(self.state[1]),
            z=float(self.state[2])
        )
    
    def get_trajectory(self) -> List[Position3D]:
        """
        Get ball trajectory history.
        
        Returns last 30 positions (1 second of history at 30 FPS).
        
        Returns:
            List of 3D positions in chronological order
        """
        return self.position_history.copy()
    
    def get_velocity(self) -> Vector3D:
        """
        Get current ball velocity.
        
        Returns:
            3D velocity vector in m/s
        """
        return Vector3D(
            vx=float(self.state[3]),
            vy=float(self.state[4]),
            vz=float(self.state[5])
        )
    
    def is_occluded(self) -> bool:
        """
        Check if ball is currently occluded.
        
        Returns:
            True if occlusion duration > 0 frames
        """
        return self.occlusion_duration > 0
    
    def is_long_occlusion(self) -> bool:
        """
        Check if occlusion exceeds threshold.
        
        Returns:
            True if occlusion duration > 10 frames
        """
        return self.occlusion_duration > self.max_occlusion_frames
    
    def get_occlusion_duration(self) -> int:
        """
        Get current occlusion duration in frames.
        
        Returns:
            Number of frames without detection
        """
        return self.occlusion_duration
    
    def reset(self) -> None:
        """
        Reset tracker for new delivery tracking.
        
        Clears state, covariance, and trajectory history.
        """
        self.state = np.zeros(9)
        self.covariance = np.eye(9) * 10.0
        self.last_seen = 0.0
        self.occlusion_duration = 0
        self.confidence = 0.0
        self.is_initialized = False
        self.position_history.clear()
        self.velocity_history.clear()
        self.timestamp_history.clear()
    
    def get_trajectory_object(self) -> Trajectory:
        """
        Get complete trajectory object with positions, velocities, and speed metrics.
        
        Returns:
            Trajectory object with all trajectory data
        """
        if not self.position_history:
            # Return empty trajectory
            return Trajectory(
                positions=[],
                timestamps=[],
                velocities=[],
                start_position=Position3D(x=0.0, y=0.0, z=0.0),
                end_position=None,
                speed_max=0.0,
                speed_avg=0.0
            )
        
        # Calculate speed metrics
        speeds = [v.magnitude() for v in self.velocity_history]
        speed_max = max(speeds) if speeds else 0.0
        speed_avg = sum(speeds) / len(speeds) if speeds else 0.0
        
        return Trajectory(
            positions=self.position_history.copy(),
            timestamps=self.timestamp_history.copy(),
            velocities=self.velocity_history.copy(),
            start_position=self.position_history[0],
            end_position=self.position_history[-1] if self.position_history else None,
            speed_max=speed_max,
            speed_avg=speed_avg
        )
    
    def _initialize_state(self, position: Position3D, timestamp: float) -> None:
        """
        Initialize state vector with first detection.
        
        Args:
            position: Initial 3D position
            timestamp: Initial timestamp
        """
        # Set position
        self.state[0] = position.x
        self.state[1] = position.y
        self.state[2] = position.z
        
        # Initialize velocity to zero (will be estimated from subsequent detections)
        self.state[3:6] = 0.0
        
        # Initialize acceleration to zero
        self.state[6:9] = 0.0
        
        # Set initial covariance
        self.covariance = np.eye(9)
        self.covariance[0:3, 0:3] *= 1.0  # Position uncertainty: 1m
        self.covariance[3:6, 3:6] *= 10.0  # Velocity uncertainty: 10 m/s
        self.covariance[6:9, 6:9] *= 5.0  # Acceleration uncertainty: 5 m/s²
        
        self.last_seen = timestamp
    
    def _predict(self, dt: float) -> None:
        """
        EKF prediction step: predict state forward using process model.
        
        Process model with gravity and air resistance:
        - x(t+1) = x(t) + vx(t)*dt + 0.5*ax(t)*dt²
        - y(t+1) = y(t) + vy(t)*dt + 0.5*ay(t)*dt²
        - z(t+1) = z(t) + vz(t)*dt + 0.5*az(t)*dt² - 0.5*g*dt²
        - vx(t+1) = vx(t) + ax(t)*dt
        - vy(t+1) = vy(t) + ay(t)*dt
        - vz(t+1) = vz(t) + az(t)*dt - g*dt
        - ax(t+1) = ax(t) * drag_coefficient
        - ay(t+1) = ay(t) * drag_coefficient
        - az(t+1) = az(t) * drag_coefficient
        
        Args:
            dt: Time step in seconds
        """
        # Extract current state
        x, y, z = self.state[0:3]
        vx, vy, vz = self.state[3:6]
        ax, ay, az = self.state[6:9]
        
        # Predict position
        self.state[0] = x + vx * dt + 0.5 * ax * dt**2
        self.state[1] = y + vy * dt + 0.5 * ay * dt**2
        self.state[2] = z + vz * dt + 0.5 * az * dt**2 - 0.5 * GRAVITY * dt**2
        
        # Predict velocity (with gravity)
        self.state[3] = vx + ax * dt
        self.state[4] = vy + ay * dt
        self.state[5] = vz + az * dt - GRAVITY * dt
        
        # Predict acceleration (with drag)
        self.state[6] = ax * DRAG_COEFFICIENT
        self.state[7] = ay * DRAG_COEFFICIENT
        self.state[8] = az * DRAG_COEFFICIENT
        
        # Compute Jacobian of process model
        F = self._compute_process_jacobian(dt)
        
        # Predict covariance: P = F * P * F^T + Q
        Q = np.eye(9) * self.process_noise**2  # Process noise covariance
        self.covariance = F @ self.covariance @ F.T + Q
    
    def _update_measurement(self, measured_position: Position3D, confidence: float) -> None:
        """
        EKF update step: update state with measurement.
        
        Args:
            measured_position: Measured 3D position
            confidence: Detection confidence [0, 1]
        """
        # Measurement vector (only position is measured)
        z = np.array([measured_position.x, measured_position.y, measured_position.z])
        
        # Predicted measurement (position part of state)
        h = self.state[0:3]
        
        # Measurement residual
        y = z - h
        
        # Measurement Jacobian (H maps state to measurement)
        H = np.zeros((3, 9))
        H[0:3, 0:3] = np.eye(3)  # Measure position only
        
        # Measurement noise covariance (scaled by confidence)
        R = np.eye(3) * (self.measurement_noise**2 / confidence)
        
        # Innovation covariance
        S = H @ self.covariance @ H.T + R
        
        # Kalman gain
        K = self.covariance @ H.T @ np.linalg.inv(S)
        
        # Update state
        self.state = self.state + K @ y
        
        # Update covariance
        I = np.eye(9)
        self.covariance = (I - K @ H) @ self.covariance
    
    def _compute_process_jacobian(self, dt: float) -> np.ndarray:
        """
        Compute Jacobian of process model for EKF prediction.
        
        Args:
            dt: Time step in seconds
            
        Returns:
            9x9 Jacobian matrix
        """
        F = np.eye(9)
        
        # Position depends on velocity and acceleration
        F[0, 3] = dt  # dx/dvx
        F[1, 4] = dt  # dy/dvy
        F[2, 5] = dt  # dz/dvz
        F[0, 6] = 0.5 * dt**2  # dx/dax
        F[1, 7] = 0.5 * dt**2  # dy/day
        F[2, 8] = 0.5 * dt**2  # dz/daz
        
        # Velocity depends on acceleration
        F[3, 6] = dt  # dvx/dax
        F[4, 7] = dt  # dvy/day
        F[5, 8] = dt  # dvz/daz
        
        # Acceleration depends on previous acceleration (drag)
        F[6, 6] = DRAG_COEFFICIENT  # dax/dax
        F[7, 7] = DRAG_COEFFICIENT  # day/day
        F[8, 8] = DRAG_COEFFICIENT  # daz/daz
        
        return F
    
    def _pixel_to_3d(
        self,
        pixel_coords: Tuple[float, float],
        confidence: float
    ) -> Position3D:
        """
        Convert 2D pixel coordinates to 3D position using camera calibration.
        
        Uses ground plane assumption and camera calibration matrix.
        If calibration not available, uses simple heuristic conversion.
        
        Args:
            pixel_coords: (u, v) pixel coordinates
            confidence: Detection confidence
            
        Returns:
            3D position in meters
        """
        u, v = pixel_coords
        
        # Check if camera calibration available
        if "camera_matrix" in self.camera_calibration:
            # Use camera calibration for proper 3D conversion
            # This would involve homography or triangulation
            # For now, use simplified conversion
            pass
        
        # Simplified conversion (heuristic)
        # Assume: 1280x720 image, pitch is ~20m x 10m
        # Center of image is pitch center
        x = (u - 640) / 64.0  # Rough conversion: 64 pixels per meter
        z = (v - 360) / 36.0  # Rough conversion: 36 pixels per meter
        y = 1.0  # Assume ball is at typical height (1m)
        
        return Position3D(x=x, y=y, z=z)
    
    def _update_history(self, timestamp: float) -> None:
        """
        Update trajectory history with current state.
        
        Maintains last 30 positions (1 second at 30 FPS).
        
        Args:
            timestamp: Current timestamp
        """
        # Add current position
        position = Position3D(
            x=float(self.state[0]),
            y=float(self.state[1]),
            z=float(self.state[2])
        )
        self.position_history.append(position)
        
        # Add current velocity
        velocity = Vector3D(
            vx=float(self.state[3]),
            vy=float(self.state[4]),
            vz=float(self.state[5])
        )
        self.velocity_history.append(velocity)
        
        # Add timestamp
        self.timestamp_history.append(timestamp)
        
        # Trim history to max length
        if len(self.position_history) > self.max_history:
            self.position_history.pop(0)
            self.velocity_history.pop(0)
            self.timestamp_history.pop(0)
    
    def _get_track_state(self) -> TrackState:
        """
        Get current track state.
        
        Returns:
            TrackState object with current tracking information
        """
        return TrackState(
            track_id=self.track_id,
            position=Position3D(
                x=float(self.state[0]),
                y=float(self.state[1]),
                z=float(self.state[2])
            ),
            velocity=Vector3D(
                vx=float(self.state[3]),
                vy=float(self.state[4]),
                vz=float(self.state[5])
            ),
            acceleration=Vector3D(
                vx=float(self.state[6]),
                vy=float(self.state[7]),
                vz=float(self.state[8])
            ),
            covariance=self.covariance.copy(),
            last_seen=self.last_seen,
            occlusion_duration=self.occlusion_duration,
            confidence=self.confidence
        )
