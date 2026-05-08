"""
Hybrid Detector: YOLOv8 for players + Cricket Ball Detector for balls

This combines the best of both approaches:
- YOLOv8 for detecting players, umpires, fielders
- Custom cricket ball detector for detecting cricket balls
"""

import time
import logging
from typing import List, Optional
import numpy as np

from umpirai.models.data_models import Frame, Detection, DetectionResult, BoundingBox
from umpirai.detection.object_detector import ObjectDetector
from umpirai.detection.cricket_ball_detector import CricketBallDetector

logger = logging.getLogger(__name__)


class HybridDetector:
    """
    Hybrid detector combining YOLOv8 and cricket ball detection.
    
    Uses:
    - YOLOv8 for: players, umpires, fielders (person class)
    - Cricket ball detector for: red and white cricket balls
    
    This gives us the best of both worlds:
    - Robust player detection from YOLOv8
    - Accurate cricket ball detection from color/shape analysis
    """
    
    def __init__(self, model_path: Optional[str] = None, device: str = "cpu"):
        """
        Initialize hybrid detector
        
        Args:
            model_path: Path to YOLOv8 model
            device: Device for YOLOv8 inference
        """
        # Initialize YOLOv8 for player detection
        try:
            self.yolo_detector = ObjectDetector(model_path=model_path, device=device)
            self.yolo_available = True
            logger.info("YOLOv8 detector initialized for player detection")
        except Exception as e:
            logger.warning(f"YOLOv8 initialization failed: {e}. Using cricket ball detector only.")
            self.yolo_detector = None
            self.yolo_available = False
        
        # Initialize cricket ball detector
        self.ball_detector = CricketBallDetector()
        logger.info("Cricket ball detector initialized")
        
        self.device = device
    
    def detect(self, frame: Frame) -> DetectionResult:
        """
        Detect objects in frame using hybrid approach
        
        Args:
            frame: Video frame
            
        Returns:
            DetectionResult with all detections
        """
        start_time = time.time()
        detections = []
        
        # Stage 1: YOLOv8 detection for players
        if self.yolo_available:
            try:
                yolo_result = self.yolo_detector.detect(frame)
                
                # Keep only person detections from YOLOv8
                for det in yolo_result.detections:
                    if det.class_name == "person":
                        detections.append(det)
                
            except Exception as e:
                logger.error(f"YOLOv8 detection error: {e}")
        
        # Stage 2: Cricket ball detection
        try:
            ball_candidates = self.ball_detector.detect(frame.image)
            
            # Convert ball candidates to Detection objects
            for candidate in ball_candidates:
                # Only use high-confidence detections (stricter threshold)
                if candidate.confidence > 0.7:  # Increased from 0.4 to reduce false positives
                    x, y = candidate.center
                    r = candidate.radius
                    
                    ball_detection = Detection(
                        class_id=32,  # sports ball class ID
                        class_name="ball",
                        bounding_box=BoundingBox(
                            x=float(x - r),
                            y=float(y - r),
                            width=float(2 * r),
                            height=float(2 * r)
                        ),
                        confidence=candidate.confidence,
                        position_3d=None
                    )
                    
                    detections.append(ball_detection)
                    break  # Only take the best ball detection per frame
        
        except Exception as e:
            logger.error(f"Cricket ball detection error: {e}")
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        return DetectionResult(
            frame=frame,
            detections=detections,
            processing_time_ms=processing_time_ms
        )
    
    def reset(self):
        """Reset detector state"""
        self.ball_detector.reset()
    
    def is_using_gpu(self) -> bool:
        """Check if using GPU"""
        if self.yolo_available:
            return self.yolo_detector.is_using_gpu()
        return False
    
    def get_model_version(self) -> str:
        """Get model version"""
        if self.yolo_available:
            return f"Hybrid (YOLOv8 + Cricket Ball Detector)"
        return "Cricket Ball Detector Only"
