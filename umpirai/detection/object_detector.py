"""
Object detection component using YOLOv8 for cricket element identification.

This module provides the ObjectDetector class which uses YOLOv8m to detect
cricket elements (ball, stumps, players, crease lines, etc.) in video frames.
"""

import time
from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    YOLO = None

from umpirai.models.data_models import (
    Frame,
    Detection,
    DetectionResult,
    BoundingBox,
    Position3D,
    DetectionClass,
)


@dataclass
class MultiViewDetectionResult:
    """Detection result from multiple camera views with fusion."""
    detections: List[Detection]
    processing_time_ms: float
    camera_ids: List[str]
    fusion_method: str  # "weighted_average", "highest_confidence", "triangulation"
    
    def __post_init__(self):
        """Validate multi-view detection result."""
        if not isinstance(self.detections, list):
            raise TypeError("detections must be a list")
        if not all(isinstance(d, Detection) for d in self.detections):
            raise TypeError("all detections must be Detection instances")
        if not isinstance(self.processing_time_ms, (int, float)) or self.processing_time_ms < 0:
            raise ValueError("processing_time_ms must be a non-negative number")
        if not isinstance(self.camera_ids, list):
            raise TypeError("camera_ids must be a list")
        if not all(isinstance(cid, str) for cid in self.camera_ids):
            raise TypeError("all camera_ids must be strings")
        if not isinstance(self.fusion_method, str):
            raise TypeError("fusion_method must be a string")


class ObjectDetector:
    """
    Object detector for identifying cricket elements using YOLOv8.
    
    Detects 8 classes:
    - Ball (class 0)
    - Stumps (class 1)
    - Crease line (class 2)
    - Batsman (class 3)
    - Bowler (class 4)
    - Fielder (class 5)
    - Pitch boundary (class 6)
    - Wide guideline (class 7)
    
    Model: YOLOv8m (medium variant)
    Input: 1280x720 RGB frames
    Output: Bounding boxes + confidence scores + class labels
    
    Confidence Thresholds:
    - High confidence: ≥90% (use directly)
    - Medium confidence: 70-90% (use with caution, flag for review)
    - Low confidence: <70% (flag as uncertain)
    """
    
    # Class names mapping
    CLASS_NAMES = {
        0: "ball",
        1: "stumps",
        2: "crease",
        3: "batsman",
        4: "bowler",
        5: "fielder",
        6: "pitch_boundary",
        7: "wide_guideline"
    }
    
    # Confidence thresholds
    CONFIDENCE_HIGH = 0.90
    CONFIDENCE_MEDIUM = 0.70
    CONFIDENCE_LOW = 0.70  # Below this is uncertain
    
    def __init__(self, model_path: Optional[str] = None, device: str = "cpu"):
        """
        Initialize object detector with YOLOv8 model.
        
        Args:
            model_path: Path to YOLOv8 model weights. If None, uses default YOLOv8m.
            device: Device for inference ("cpu", "cuda", "mps")
            
        Raises:
            RuntimeError: If YOLOv8 (ultralytics) is not installed
            RuntimeError: If model fails to load
        """
        if not YOLO_AVAILABLE:
            raise RuntimeError(
                "YOLOv8 (ultralytics) is not installed. "
                "Install with: pip install ultralytics"
            )
        
        self.device = device
        self.model_path = model_path or "yolov8m.pt"  # Default to YOLOv8m
        
        try:
            # Load YOLOv8 model
            self.model = YOLO(self.model_path)
            self.model.to(device)
            
            # Store model version
            self._model_version = self._extract_model_version()
            
        except Exception as e:
            raise RuntimeError(f"Failed to load YOLOv8 model from {self.model_path}: {e}")
        
        # Camera calibration data for 3D triangulation
        self.camera_calibrations: Dict[str, Dict] = {}
    
    def detect(self, frame: Frame) -> DetectionResult:
        """
        Detect cricket elements in a single frame.
        
        Args:
            frame: Video frame to process
            
        Returns:
            DetectionResult with detected objects
        """
        start_time = time.time()
        
        # Run YOLOv8 inference
        results = self.model(frame.image, verbose=False)
        
        # Extract detections
        detections = []
        for result in results:
            boxes = result.boxes
            
            for i in range(len(boxes)):
                # Extract box data
                box_data = boxes.xyxy[i]
                # Handle both tensor and numpy array
                if hasattr(box_data, 'cpu'):
                    box = box_data.cpu().numpy()  # [x1, y1, x2, y2]
                else:
                    box = np.array(box_data)
                
                conf_data = boxes.conf[i]
                if hasattr(conf_data, 'cpu'):
                    confidence = float(conf_data.cpu().numpy())
                else:
                    confidence = float(conf_data)
                
                cls_data = boxes.cls[i]
                if hasattr(cls_data, 'cpu'):
                    class_id = int(cls_data.cpu().numpy())
                else:
                    class_id = int(cls_data)
                
                # Convert to BoundingBox format (x, y, width, height)
                x1, y1, x2, y2 = box
                bounding_box = BoundingBox(
                    x=float(x1),
                    y=float(y1),
                    width=float(x2 - x1),
                    height=float(y2 - y1)
                )
                
                # Get class name
                class_name = self.CLASS_NAMES.get(class_id, f"unknown_{class_id}")
                
                # Create detection
                detection = Detection(
                    class_id=class_id,
                    class_name=class_name,
                    bounding_box=bounding_box,
                    confidence=confidence,
                    position_3d=None  # Will be set by triangulation if available
                )
                
                detections.append(detection)
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        return DetectionResult(
            frame=frame,
            detections=detections,
            processing_time_ms=processing_time_ms
        )
    
    def detect_multi_view(self, frames: Dict[str, Frame]) -> MultiViewDetectionResult:
        """
        Detect cricket elements across multiple camera views and fuse results.
        
        Multi-view fusion strategy:
        1. Detect objects in each camera view independently
        2. Match detections across views (same object class, similar timestamp)
        3. For matched detections:
           - Average bounding boxes weighted by confidence
           - Triangulate 3D position for ball detections
           - Use highest confidence when views conflict significantly
        
        Args:
            frames: Dictionary mapping camera_id to Frame
            
        Returns:
            MultiViewDetectionResult with fused detections
        """
        start_time = time.time()
        
        if not frames:
            raise ValueError("frames dictionary cannot be empty")
        
        # Detect in each view
        view_detections: Dict[str, List[Detection]] = {}
        for camera_id, frame in frames.items():
            result = self.detect(frame)
            view_detections[camera_id] = result.detections
        
        # Fuse detections across views
        fused_detections = self._fuse_multi_view_detections(view_detections, frames)
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        return MultiViewDetectionResult(
            detections=fused_detections,
            processing_time_ms=processing_time_ms,
            camera_ids=list(frames.keys()),
            fusion_method="weighted_average"
        )
    
    def _fuse_multi_view_detections(
        self,
        view_detections: Dict[str, List[Detection]],
        frames: Dict[str, Frame]
    ) -> List[Detection]:
        """
        Fuse detections from multiple camera views.
        
        Strategy:
        1. Group detections by class
        2. For each class, match detections across views
        3. Fuse matched detections using weighted average
        4. Triangulate 3D position for ball detections
        
        Args:
            view_detections: Detections per camera view
            frames: Original frames (for triangulation)
            
        Returns:
            List of fused detections
        """
        if len(view_detections) == 1:
            # Single view, no fusion needed
            return list(view_detections.values())[0]
        
        # Group detections by class
        detections_by_class: Dict[int, List[tuple[str, Detection]]] = {}
        for camera_id, detections in view_detections.items():
            for detection in detections:
                if detection.class_id not in detections_by_class:
                    detections_by_class[detection.class_id] = []
                detections_by_class[detection.class_id].append((camera_id, detection))
        
        # Fuse detections for each class
        fused_detections = []
        for class_id, class_detections in detections_by_class.items():
            if len(class_detections) == 1:
                # Only one view detected this class, use it directly
                _, detection = class_detections[0]
                fused_detections.append(detection)
            else:
                # Multiple views detected this class, fuse them
                fused = self._fuse_detections_for_class(class_id, class_detections, frames)
                if fused:
                    fused_detections.append(fused)
        
        return fused_detections
    
    def _fuse_detections_for_class(
        self,
        class_id: int,
        detections: List[tuple[str, Detection]],
        frames: Dict[str, Frame]
    ) -> Optional[Detection]:
        """
        Fuse multiple detections of the same class from different views.
        
        Uses weighted average of bounding boxes, weighted by confidence.
        For ball detections, attempts 3D triangulation if calibration available.
        
        Args:
            class_id: Object class ID
            detections: List of (camera_id, detection) tuples
            frames: Original frames
            
        Returns:
            Fused detection, or None if fusion fails
        """
        if not detections:
            return None
        
        # Check for significant conflicts (very different bounding boxes)
        # If conflict detected, use highest confidence detection
        if self._has_significant_conflict(detections):
            # Use detection with highest confidence
            _, best_detection = max(detections, key=lambda x: x[1].confidence)
            return best_detection
        
        # Weighted average of bounding boxes
        total_weight = sum(det.confidence for _, det in detections)
        
        weighted_x = sum(det.bounding_box.x * det.confidence for _, det in detections) / total_weight
        weighted_y = sum(det.bounding_box.y * det.confidence for _, det in detections) / total_weight
        weighted_width = sum(det.bounding_box.width * det.confidence for _, det in detections) / total_weight
        weighted_height = sum(det.bounding_box.height * det.confidence for _, det in detections) / total_weight
        
        fused_bbox = BoundingBox(
            x=weighted_x,
            y=weighted_y,
            width=weighted_width,
            height=weighted_height
        )
        
        # Average confidence
        avg_confidence = total_weight / len(detections)
        
        # Get class name
        class_name = self.CLASS_NAMES.get(class_id, f"unknown_{class_id}")
        
        # Triangulate 3D position for ball
        position_3d = None
        if class_id == DetectionClass.BALL.value and len(detections) >= 2:
            position_3d = self._triangulate_ball_position(detections, frames)
        
        return Detection(
            class_id=class_id,
            class_name=class_name,
            bounding_box=fused_bbox,
            confidence=avg_confidence,
            position_3d=position_3d
        )
    
    def _has_significant_conflict(self, detections: List[tuple[str, Detection]]) -> bool:
        """
        Check if detections have significant conflicts (very different positions).
        
        Conflict is significant if bounding box centers differ by more than
        50% of the average box size.
        
        Args:
            detections: List of (camera_id, detection) tuples
            
        Returns:
            True if significant conflict detected
        """
        if len(detections) < 2:
            return False
        
        # Get bounding box centers
        centers = [det.bounding_box.center() for _, det in detections]
        
        # Calculate average box size
        avg_size = sum(
            (det.bounding_box.width + det.bounding_box.height) / 2
            for _, det in detections
        ) / len(detections)
        
        # Check pairwise distances
        for i in range(len(centers)):
            for j in range(i + 1, len(centers)):
                cx1, cy1 = centers[i]
                cx2, cy2 = centers[j]
                distance = np.sqrt((cx2 - cx1)**2 + (cy2 - cy1)**2)
                
                # Conflict if distance > 50% of average size
                if distance > 0.5 * avg_size:
                    return True
        
        return False
    
    def _triangulate_ball_position(
        self,
        detections: List[tuple[str, Detection]],
        frames: Dict[str, Frame]
    ) -> Optional[Position3D]:
        """
        Triangulate 3D ball position from multiple camera views.
        
        Requires camera calibration data (intrinsics and extrinsics).
        Uses DLT (Direct Linear Transform) for triangulation.
        
        Args:
            detections: List of (camera_id, detection) tuples
            frames: Original frames
            
        Returns:
            3D position, or None if triangulation fails or calibration unavailable
        """
        if len(detections) < 2:
            return None
        
        # Check if we have calibration for at least 2 cameras
        calibrated_detections = [
            (camera_id, det) for camera_id, det in detections
            if camera_id in self.camera_calibrations
        ]
        
        if len(calibrated_detections) < 2:
            # Not enough calibrated cameras for triangulation
            return None
        
        # For now, return a placeholder
        # Full triangulation implementation would require camera matrices
        # and would use cv2.triangulatePoints or similar
        
        # Simple approximation: use average of 2D positions as placeholder
        # In production, this would be replaced with proper triangulation
        avg_x = sum(det.bounding_box.center()[0] for _, det in calibrated_detections) / len(calibrated_detections)
        avg_y = sum(det.bounding_box.center()[1] for _, det in calibrated_detections) / len(calibrated_detections)
        
        # Placeholder 3D position (would be computed from camera geometry)
        return Position3D(
            x=avg_x / 100.0,  # Rough conversion from pixels to meters
            y=1.0,  # Assume ball is at typical height
            z=avg_y / 100.0
        )
    
    def add_camera_calibration(self, camera_id: str, calibration: Dict) -> None:
        """
        Add camera calibration data for 3D triangulation.
        
        Args:
            camera_id: Camera identifier
            calibration: Calibration data including camera matrix, distortion, etc.
        """
        self.camera_calibrations[camera_id] = calibration
    
    def get_model_version(self) -> str:
        """
        Get the current model version.
        
        Returns:
            Model version string
        """
        return self._model_version
    
    def update_model(self, model_path: str) -> None:
        """
        Update the detection model with a new model file.
        
        Args:
            model_path: Path to new YOLOv8 model weights
            
        Raises:
            RuntimeError: If model fails to load
        """
        try:
            # Load new model
            new_model = YOLO(model_path)
            new_model.to(self.device)
            
            # Update model and path
            self.model = new_model
            self.model_path = model_path
            self._model_version = self._extract_model_version()
            
        except Exception as e:
            raise RuntimeError(f"Failed to update model from {model_path}: {e}")
    
    def _extract_model_version(self) -> str:
        """
        Extract model version from model metadata.
        
        Returns:
            Model version string
        """
        # Try to get version from model metadata
        try:
            if hasattr(self.model, 'ckpt') and self.model.ckpt:
                version = self.model.ckpt.get('version', 'unknown')
                return str(version)
        except:
            pass
        
        # Fallback: use model path as version
        return f"yolov8m_{self.model_path}"
    
    def evaluate_confidence(self, detection: Detection) -> str:
        """
        Evaluate detection confidence level.
        
        Args:
            detection: Detection to evaluate
            
        Returns:
            Confidence level: "high", "medium", or "low"
        """
        if detection.confidence >= self.CONFIDENCE_HIGH:
            return "high"
        elif detection.confidence >= self.CONFIDENCE_MEDIUM:
            return "medium"
        else:
            return "low"
