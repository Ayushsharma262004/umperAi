"""
Core data models for the UmpirAI system.

This module defines the fundamental data structures used throughout the system
for representing video frames, detections, tracking state, trajectories, and decisions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import numpy as np


# ============================================================================
# Utility Classes
# ============================================================================

@dataclass
class Position3D:
    """3D position in meters relative to pitch center."""
    x: float  # meters
    y: float  # meters
    z: float  # meters
    
    def __post_init__(self):
        """Validate position values."""
        if not all(isinstance(v, (int, float)) for v in [self.x, self.y, self.z]):
            raise TypeError("Position coordinates must be numeric")
        if not all(np.isfinite(v) for v in [self.x, self.y, self.z]):
            raise ValueError("Position coordinates must be finite")


@dataclass
class Vector3D:
    """3D vector for velocity or acceleration."""
    vx: float  # m/s or m/s²
    vy: float  # m/s or m/s²
    vz: float  # m/s or m/s²
    
    def __post_init__(self):
        """Validate vector values."""
        if not all(isinstance(v, (int, float)) for v in [self.vx, self.vy, self.vz]):
            raise TypeError("Vector components must be numeric")
        if not all(np.isfinite(v) for v in [self.vx, self.vy, self.vz]):
            raise ValueError("Vector components must be finite")
    
    def magnitude(self) -> float:
        """Calculate the magnitude of the vector."""
        return float(np.sqrt(self.vx**2 + self.vy**2 + self.vz**2))


@dataclass
class BoundingBox:
    """Bounding box for object detection."""
    x: float  # top-left x coordinate (pixels)
    y: float  # top-left y coordinate (pixels)
    width: float  # box width (pixels)
    height: float  # box height (pixels)
    
    def __post_init__(self):
        """Validate bounding box values."""
        if not all(isinstance(v, (int, float)) for v in [self.x, self.y, self.width, self.height]):
            raise TypeError("Bounding box coordinates must be numeric")
        if self.width < 0 or self.height < 0:
            raise ValueError("Bounding box width and height must be non-negative")
        if not all(np.isfinite(v) for v in [self.x, self.y, self.width, self.height]):
            raise ValueError("Bounding box coordinates must be finite")
    
    def center(self) -> tuple[float, float]:
        """Calculate the center point of the bounding box."""
        return (self.x + self.width / 2, self.y + self.height / 2)
    
    def area(self) -> float:
        """Calculate the area of the bounding box."""
        return self.width * self.height
    
    def intersects(self, other: 'BoundingBox') -> bool:
        """Check if this bounding box intersects with another."""
        return not (self.x + self.width <= other.x or
                   other.x + other.width <= self.x or
                   self.y + self.height <= other.y or
                   other.y + other.height <= self.y)


# ============================================================================
# Enumerations
# ============================================================================

class EventType(Enum):
    """Types of match events that can be detected."""
    WIDE = "wide"
    NO_BALL = "no_ball"
    BOWLED = "bowled"
    CAUGHT = "caught"
    LBW = "lbw"
    LEGAL = "legal"
    OVER_COMPLETE = "over_complete"


class DetectionClass(Enum):
    """Object classes for detection."""
    BALL = 0
    STUMPS = 1
    CREASE = 2
    BATSMAN = 3
    BOWLER = 4
    FIELDER = 5
    PITCH_BOUNDARY = 6
    WIDE_GUIDELINE = 7


# ============================================================================
# Core Data Models
# ============================================================================

@dataclass
class Frame:
    """Video frame with metadata."""
    camera_id: str
    frame_number: int
    timestamp: float  # seconds since epoch
    image: np.ndarray  # HxWx3 RGB
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate frame data."""
        if not isinstance(self.camera_id, str) or not self.camera_id:
            raise ValueError("camera_id must be a non-empty string")
        if not isinstance(self.frame_number, int) or self.frame_number < 0:
            raise ValueError("frame_number must be a non-negative integer")
        if not isinstance(self.timestamp, (int, float)) or self.timestamp < 0:
            raise ValueError("timestamp must be a non-negative number")
        if not isinstance(self.image, np.ndarray):
            raise TypeError("image must be a numpy array")
        if self.image.ndim != 3 or self.image.shape[2] != 3:
            raise ValueError("image must be HxWx3 RGB array")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary")


@dataclass
class Detection:
    """Single object detection result."""
    class_id: int
    class_name: str
    bounding_box: BoundingBox
    confidence: float
    position_3d: Optional[Position3D] = None
    
    def __post_init__(self):
        """Validate detection data."""
        if not isinstance(self.class_id, int) or self.class_id < 0:
            raise ValueError("class_id must be a non-negative integer")
        if not isinstance(self.class_name, str) or not self.class_name:
            raise ValueError("class_name must be a non-empty string")
        if not isinstance(self.bounding_box, BoundingBox):
            raise TypeError("bounding_box must be a BoundingBox instance")
        if not isinstance(self.confidence, (int, float)):
            raise TypeError("confidence must be numeric")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be in range [0.0, 1.0]")
        if self.position_3d is not None and not isinstance(self.position_3d, Position3D):
            raise TypeError("position_3d must be a Position3D instance or None")
    
    def is_uncertain(self) -> bool:
        """Check if detection confidence is below uncertainty threshold."""
        return self.confidence < 0.70


@dataclass
class DetectionResult:
    """Complete detection result for a frame."""
    frame: Frame
    detections: List[Detection]
    processing_time_ms: float
    
    def __post_init__(self):
        """Validate detection result."""
        if not isinstance(self.frame, Frame):
            raise TypeError("frame must be a Frame instance")
        if not isinstance(self.detections, list):
            raise TypeError("detections must be a list")
        if not all(isinstance(d, Detection) for d in self.detections):
            raise TypeError("all detections must be Detection instances")
        if not isinstance(self.processing_time_ms, (int, float)) or self.processing_time_ms < 0:
            raise ValueError("processing_time_ms must be a non-negative number")
    
    def get_detections_by_class(self, class_id: int) -> List[Detection]:
        """Get all detections of a specific class."""
        return [d for d in self.detections if d.class_id == class_id]
    
    def has_uncertain_detections(self) -> bool:
        """Check if any detections have low confidence."""
        return any(d.is_uncertain() for d in self.detections)


@dataclass
class TrackState:
    """Ball tracking state from Extended Kalman Filter."""
    track_id: str
    position: Position3D
    velocity: Vector3D
    acceleration: Vector3D
    covariance: np.ndarray  # 9x9 uncertainty matrix
    last_seen: float  # timestamp
    occlusion_duration: int  # frames
    confidence: float
    
    def __post_init__(self):
        """Validate track state."""
        if not isinstance(self.track_id, str) or not self.track_id:
            raise ValueError("track_id must be a non-empty string")
        if not isinstance(self.position, Position3D):
            raise TypeError("position must be a Position3D instance")
        if not isinstance(self.velocity, Vector3D):
            raise TypeError("velocity must be a Vector3D instance")
        if not isinstance(self.acceleration, Vector3D):
            raise TypeError("acceleration must be a Vector3D instance")
        if not isinstance(self.covariance, np.ndarray):
            raise TypeError("covariance must be a numpy array")
        if self.covariance.shape != (9, 9):
            raise ValueError("covariance must be a 9x9 matrix")
        if not isinstance(self.last_seen, (int, float)) or self.last_seen < 0:
            raise ValueError("last_seen must be a non-negative number")
        if not isinstance(self.occlusion_duration, int) or self.occlusion_duration < 0:
            raise ValueError("occlusion_duration must be a non-negative integer")
        if not isinstance(self.confidence, (int, float)):
            raise TypeError("confidence must be numeric")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be in range [0.0, 1.0]")
    
    def is_occluded(self) -> bool:
        """Check if ball is currently occluded."""
        return self.occlusion_duration > 0
    
    def is_long_occlusion(self) -> bool:
        """Check if occlusion exceeds threshold (>10 frames)."""
        return self.occlusion_duration > 10


@dataclass
class Trajectory:
    """Ball trajectory over time."""
    positions: List[Position3D]
    timestamps: List[float]
    velocities: List[Vector3D]
    start_position: Position3D
    end_position: Optional[Position3D] = None
    speed_max: float = 0.0  # m/s
    speed_avg: float = 0.0  # m/s
    
    def __post_init__(self):
        """Validate trajectory data."""
        if not isinstance(self.positions, list):
            raise TypeError("positions must be a list")
        if not all(isinstance(p, Position3D) for p in self.positions):
            raise TypeError("all positions must be Position3D instances")
        if not isinstance(self.timestamps, list):
            raise TypeError("timestamps must be a list")
        if not all(isinstance(t, (int, float)) for t in self.timestamps):
            raise TypeError("all timestamps must be numeric")
        if len(self.positions) != len(self.timestamps):
            raise ValueError("positions and timestamps must have same length")
        if not isinstance(self.velocities, list):
            raise TypeError("velocities must be a list")
        if not all(isinstance(v, Vector3D) for v in self.velocities):
            raise TypeError("all velocities must be Vector3D instances")
        if not isinstance(self.start_position, Position3D):
            raise TypeError("start_position must be a Position3D instance")
        if self.end_position is not None and not isinstance(self.end_position, Position3D):
            raise TypeError("end_position must be a Position3D instance or None")
        if not isinstance(self.speed_max, (int, float)) or self.speed_max < 0:
            raise ValueError("speed_max must be a non-negative number")
        if not isinstance(self.speed_avg, (int, float)) or self.speed_avg < 0:
            raise ValueError("speed_avg must be a non-negative number")
    
    def duration(self) -> float:
        """Calculate trajectory duration in seconds."""
        if len(self.timestamps) < 2:
            return 0.0
        return self.timestamps[-1] - self.timestamps[0]
    
    def length(self) -> int:
        """Get number of positions in trajectory."""
        return len(self.positions)


@dataclass
class VideoReference:
    """Reference to a specific video frame."""
    camera_id: str
    frame_number: int
    timestamp: float
    
    def __post_init__(self):
        """Validate video reference."""
        if not isinstance(self.camera_id, str) or not self.camera_id:
            raise ValueError("camera_id must be a non-empty string")
        if not isinstance(self.frame_number, int) or self.frame_number < 0:
            raise ValueError("frame_number must be a non-negative integer")
        if not isinstance(self.timestamp, (int, float)) or self.timestamp < 0:
            raise ValueError("timestamp must be a non-negative number")


@dataclass
class Decision:
    """Umpiring decision result."""
    decision_id: str
    event_type: EventType
    confidence: float
    timestamp: float
    trajectory: Trajectory
    detections: List[Detection]
    reasoning: str
    video_references: List[VideoReference]
    requires_review: bool = False
    
    def __post_init__(self):
        """Validate decision data."""
        if not isinstance(self.decision_id, str) or not self.decision_id:
            raise ValueError("decision_id must be a non-empty string")
        if not isinstance(self.event_type, EventType):
            raise TypeError("event_type must be an EventType enum")
        if not isinstance(self.confidence, (int, float)):
            raise TypeError("confidence must be numeric")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be in range [0.0, 1.0]")
        if not isinstance(self.timestamp, (int, float)) or self.timestamp < 0:
            raise ValueError("timestamp must be a non-negative number")
        if not isinstance(self.trajectory, Trajectory):
            raise TypeError("trajectory must be a Trajectory instance")
        if not isinstance(self.detections, list):
            raise TypeError("detections must be a list")
        if not all(isinstance(d, Detection) for d in self.detections):
            raise TypeError("all detections must be Detection instances")
        if not isinstance(self.reasoning, str):
            raise TypeError("reasoning must be a string")
        if not isinstance(self.video_references, list):
            raise TypeError("video_references must be a list")
        if not all(isinstance(v, VideoReference) for v in self.video_references):
            raise TypeError("all video_references must be VideoReference instances")
        if not isinstance(self.requires_review, bool):
            raise TypeError("requires_review must be a boolean")
        
        # Auto-flag for review if confidence is low
        if self.confidence < 0.80:
            self.requires_review = True


@dataclass
class MatchContext:
    """Current match state context."""
    over_number: int
    ball_number: int  # within over (1-6)
    legal_deliveries: int  # count in current over
    batsman_stance: Position3D
    calibration: Dict[str, Any]  # CalibrationData will be defined in calibration module
    
    def __post_init__(self):
        """Validate match context."""
        if not isinstance(self.over_number, int) or self.over_number < 0:
            raise ValueError("over_number must be a non-negative integer")
        if not isinstance(self.ball_number, int) or not (1 <= self.ball_number <= 6):
            raise ValueError("ball_number must be in range [1, 6]")
        if not isinstance(self.legal_deliveries, int) or not (0 <= self.legal_deliveries <= 6):
            raise ValueError("legal_deliveries must be in range [0, 6]")
        if not isinstance(self.batsman_stance, Position3D):
            raise TypeError("batsman_stance must be a Position3D instance")
        if not isinstance(self.calibration, dict):
            raise TypeError("calibration must be a dictionary")
    
    def is_over_complete(self) -> bool:
        """Check if current over is complete."""
        return self.legal_deliveries >= 6
