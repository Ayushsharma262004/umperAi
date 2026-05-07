"""
Unit tests for ObjectDetector component.

Tests specific examples, edge cases, and error conditions for object detection.
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch

from umpirai.detection import ObjectDetector, MultiViewDetectionResult
from umpirai.models.data_models import (
    Frame,
    Detection,
    BoundingBox,
    Position3D,
    DetectionResult,
)


class TestObjectDetectorInitialization:
    """Test ObjectDetector initialization."""
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_initialization_with_default_model(self, mock_yolo):
        """Test initialization with default YOLOv8m model."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        detector = ObjectDetector()
        
        assert detector.model_path == "yolov8m.pt"
        assert detector.device == "cpu"
        mock_yolo.assert_called_once_with("yolov8m.pt")
        mock_model.to.assert_called_once_with("cpu")
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_initialization_with_custom_model(self, mock_yolo):
        """Test initialization with custom model path."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        detector = ObjectDetector(model_path="custom_model.pt", device="cuda")
        
        assert detector.model_path == "custom_model.pt"
        assert detector.device == "cuda"
        mock_yolo.assert_called_once_with("custom_model.pt")
        mock_model.to.assert_called_once_with("cuda")
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', False)
    def test_initialization_without_yolo_raises_error(self):
        """Test that initialization fails when YOLOv8 is not installed."""
        with pytest.raises(RuntimeError, match="YOLOv8.*not installed"):
            ObjectDetector()
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_initialization_with_invalid_model_raises_error(self, mock_yolo):
        """Test that initialization fails with invalid model path."""
        mock_yolo.side_effect = Exception("Model not found")
        
        with pytest.raises(RuntimeError, match="Failed to load YOLOv8 model"):
            ObjectDetector(model_path="nonexistent.pt")


class TestObjectDetectorDetection:
    """Test single-frame detection."""
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_detect_returns_detection_result(self, mock_yolo):
        """Test that detect returns a valid DetectionResult."""
        # Setup mock model
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        # Mock detection results
        mock_result = MagicMock()
        mock_boxes = MagicMock()
        
        # Mock single detection: ball at (100, 100, 150, 150) with confidence 0.95
        mock_boxes.xyxy = [np.array([100, 100, 150, 150])]
        mock_boxes.conf = [np.array(0.95)]
        mock_boxes.cls = [np.array(0)]  # class 0 = ball
        mock_boxes.__len__ = lambda self: 1
        
        mock_result.boxes = mock_boxes
        mock_model.return_value = [mock_result]
        
        detector = ObjectDetector()
        
        # Create test frame
        frame = Frame(
            camera_id="test_cam",
            frame_number=1,
            timestamp=1.0,
            image=np.zeros((720, 1280, 3), dtype=np.uint8),
            metadata={}
        )
        
        # Detect
        result = detector.detect(frame)
        
        # Assert
        assert isinstance(result, DetectionResult)
        assert result.frame == frame
        assert len(result.detections) == 1
        assert result.processing_time_ms >= 0
        
        # Check detection details
        detection = result.detections[0]
        assert detection.class_id == 0
        assert detection.class_name == "ball"
        assert detection.confidence == 0.95
        assert detection.bounding_box.x == 100
        assert detection.bounding_box.y == 100
        assert detection.bounding_box.width == 50
        assert detection.bounding_box.height == 50
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_detect_with_no_detections(self, mock_yolo):
        """Test detection when no objects are found."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        # Mock empty detection results
        mock_result = MagicMock()
        mock_boxes = MagicMock()
        mock_boxes.__len__ = lambda self: 0
        mock_result.boxes = mock_boxes
        mock_model.return_value = [mock_result]
        
        detector = ObjectDetector()
        
        frame = Frame(
            camera_id="test_cam",
            frame_number=1,
            timestamp=1.0,
            image=np.zeros((720, 1280, 3), dtype=np.uint8),
            metadata={}
        )
        
        result = detector.detect(frame)
        
        assert isinstance(result, DetectionResult)
        assert len(result.detections) == 0
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_detect_with_multiple_objects(self, mock_yolo):
        """Test detection with multiple objects of different classes."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        # Mock multiple detections
        mock_result = MagicMock()
        mock_boxes = MagicMock()
        
        # Ball, stumps, batsman
        mock_boxes.xyxy = [
            np.array([100, 100, 150, 150]),  # ball
            np.array([200, 200, 250, 300]),  # stumps
            np.array([300, 100, 400, 400]),  # batsman
        ]
        mock_boxes.conf = [np.array(0.95), np.array(0.98), np.array(0.87)]
        mock_boxes.cls = [np.array(0), np.array(1), np.array(3)]
        mock_boxes.__len__ = lambda self: 3
        
        mock_result.boxes = mock_boxes
        mock_model.return_value = [mock_result]
        
        detector = ObjectDetector()
        
        frame = Frame(
            camera_id="test_cam",
            frame_number=1,
            timestamp=1.0,
            image=np.zeros((720, 1280, 3), dtype=np.uint8),
            metadata={}
        )
        
        result = detector.detect(frame)
        
        assert len(result.detections) == 3
        assert result.detections[0].class_name == "ball"
        assert result.detections[1].class_name == "stumps"
        assert result.detections[2].class_name == "batsman"


class TestObjectDetectorConfidenceEvaluation:
    """Test confidence threshold evaluation."""
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_high_confidence_classification(self, mock_yolo):
        """Test classification of high confidence detections (≥90%)."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        detector = ObjectDetector()
        
        detection = Detection(
            class_id=0,
            class_name="ball",
            bounding_box=BoundingBox(x=100, y=100, width=50, height=50),
            confidence=0.95,
            position_3d=None
        )
        
        level = detector.evaluate_confidence(detection)
        assert level == "high"
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_medium_confidence_classification(self, mock_yolo):
        """Test classification of medium confidence detections (70-90%)."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        detector = ObjectDetector()
        
        detection = Detection(
            class_id=0,
            class_name="ball",
            bounding_box=BoundingBox(x=100, y=100, width=50, height=50),
            confidence=0.80,
            position_3d=None
        )
        
        level = detector.evaluate_confidence(detection)
        assert level == "medium"
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_low_confidence_classification(self, mock_yolo):
        """Test classification of low confidence detections (<70%)."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        detector = ObjectDetector()
        
        detection = Detection(
            class_id=0,
            class_name="ball",
            bounding_box=BoundingBox(x=100, y=100, width=50, height=50),
            confidence=0.65,
            position_3d=None
        )
        
        level = detector.evaluate_confidence(detection)
        assert level == "low"
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_boundary_confidence_90_percent(self, mock_yolo):
        """Test boundary case: exactly 90% confidence."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        detector = ObjectDetector()
        
        detection = Detection(
            class_id=0,
            class_name="ball",
            bounding_box=BoundingBox(x=100, y=100, width=50, height=50),
            confidence=0.90,
            position_3d=None
        )
        
        level = detector.evaluate_confidence(detection)
        assert level == "high"
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_boundary_confidence_70_percent(self, mock_yolo):
        """Test boundary case: exactly 70% confidence."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        detector = ObjectDetector()
        
        detection = Detection(
            class_id=0,
            class_name="ball",
            bounding_box=BoundingBox(x=100, y=100, width=50, height=50),
            confidence=0.70,
            position_3d=None
        )
        
        level = detector.evaluate_confidence(detection)
        assert level == "medium"


class TestObjectDetectorMultiView:
    """Test multi-camera detection and fusion."""
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_detect_multi_view_with_two_cameras(self, mock_yolo):
        """Test multi-view detection with two cameras."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        # Mock detection results for both cameras
        def mock_detect_side_effect(image, verbose=False):
            mock_result = MagicMock()
            mock_boxes = MagicMock()
            
            # Return ball detection
            mock_boxes.xyxy = [np.array([100, 100, 150, 150])]
            mock_boxes.conf = [np.array(0.90)]
            mock_boxes.cls = [np.array(0)]
            mock_boxes.__len__ = lambda self: 1
            
            mock_result.boxes = mock_boxes
            return [mock_result]
        
        mock_model.side_effect = mock_detect_side_effect
        
        detector = ObjectDetector()
        
        # Create frames from two cameras
        frames = {
            "cam1": Frame(
                camera_id="cam1",
                frame_number=1,
                timestamp=1.0,
                image=np.zeros((720, 1280, 3), dtype=np.uint8),
                metadata={}
            ),
            "cam2": Frame(
                camera_id="cam2",
                frame_number=1,
                timestamp=1.0,
                image=np.zeros((720, 1280, 3), dtype=np.uint8),
                metadata={}
            )
        }
        
        result = detector.detect_multi_view(frames)
        
        assert isinstance(result, MultiViewDetectionResult)
        assert len(result.camera_ids) == 2
        assert "cam1" in result.camera_ids
        assert "cam2" in result.camera_ids
        assert result.processing_time_ms >= 0
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_detect_multi_view_with_empty_frames_raises_error(self, mock_yolo):
        """Test that multi-view detection fails with empty frames dict."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        detector = ObjectDetector()
        
        with pytest.raises(ValueError, match="frames dictionary cannot be empty"):
            detector.detect_multi_view({})
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_multi_view_fusion_weighted_average(self, mock_yolo):
        """Test that multi-view fusion uses weighted average for similar detections."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        detector = ObjectDetector()
        
        # Create detections from two cameras with similar positions
        detections_cam1 = [
            Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=100, width=50, height=50),
                confidence=0.90,
                position_3d=None
            )
        ]
        
        detections_cam2 = [
            Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=105, y=105, width=50, height=50),
                confidence=0.85,
                position_3d=None
            )
        ]
        
        view_detections = {
            "cam1": detections_cam1,
            "cam2": detections_cam2
        }
        
        frames = {
            "cam1": Frame(
                camera_id="cam1",
                frame_number=1,
                timestamp=1.0,
                image=np.zeros((720, 1280, 3), dtype=np.uint8),
                metadata={}
            ),
            "cam2": Frame(
                camera_id="cam2",
                frame_number=1,
                timestamp=1.0,
                image=np.zeros((720, 1280, 3), dtype=np.uint8),
                metadata={}
            )
        }
        
        fused = detector._fuse_multi_view_detections(view_detections, frames)
        
        # Should have one fused detection
        assert len(fused) == 1
        
        # Fused detection should have weighted average position
        fused_detection = fused[0]
        assert fused_detection.class_id == 0
        
        # Weighted average: (100*0.9 + 105*0.85) / (0.9 + 0.85) ≈ 102.43
        expected_x = (100 * 0.90 + 105 * 0.85) / (0.90 + 0.85)
        assert abs(fused_detection.bounding_box.x - expected_x) < 0.1
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_multi_view_fusion_highest_confidence_on_conflict(self, mock_yolo):
        """Test that multi-view fusion uses highest confidence when views conflict."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        detector = ObjectDetector()
        
        # Create conflicting detections (very different positions)
        detections = [
            ("cam1", Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=100, width=50, height=50),
                confidence=0.85,
                position_3d=None
            )),
            ("cam2", Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=500, y=500, width=50, height=50),  # Far away
                confidence=0.92,
                position_3d=None
            ))
        ]
        
        frames = {
            "cam1": Frame(
                camera_id="cam1",
                frame_number=1,
                timestamp=1.0,
                image=np.zeros((720, 1280, 3), dtype=np.uint8),
                metadata={}
            ),
            "cam2": Frame(
                camera_id="cam2",
                frame_number=1,
                timestamp=1.0,
                image=np.zeros((720, 1280, 3), dtype=np.uint8),
                metadata={}
            )
        }
        
        # Check for conflict
        has_conflict = detector._has_significant_conflict(detections)
        assert has_conflict, "Should detect significant conflict"
        
        # Fuse detections
        fused = detector._fuse_detections_for_class(0, detections, frames)
        
        # Should use highest confidence detection
        assert fused.confidence == 0.92


class TestObjectDetectorModelManagement:
    """Test model version and update functionality."""
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_get_model_version(self, mock_yolo):
        """Test getting model version."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        detector = ObjectDetector()
        version = detector.get_model_version()
        
        assert isinstance(version, str)
        assert len(version) > 0
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_update_model_success(self, mock_yolo):
        """Test successful model update."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        detector = ObjectDetector()
        old_version = detector.get_model_version()
        
        # Update model
        detector.update_model("new_model.pt")
        
        assert detector.model_path == "new_model.pt"
        mock_yolo.assert_called_with("new_model.pt")
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_update_model_failure(self, mock_yolo):
        """Test model update failure handling."""
        mock_model = MagicMock()
        # First call succeeds (initialization), second call fails (update)
        mock_yolo.side_effect = [mock_model, Exception("Model load failed")]
        
        detector = ObjectDetector()
        
        # Now the second call to YOLO should fail
        with pytest.raises(RuntimeError, match="Failed to update model"):
            detector.update_model("invalid_model.pt")


class TestObjectDetectorCameraCalibration:
    """Test camera calibration management."""
    
    @patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True)
    @patch('umpirai.detection.object_detector.YOLO')
    def test_add_camera_calibration(self, mock_yolo):
        """Test adding camera calibration data."""
        mock_model = MagicMock()
        mock_yolo.return_value = mock_model
        
        detector = ObjectDetector()
        
        calibration = {
            "camera_matrix": np.eye(3),
            "distortion_coeffs": np.zeros(5)
        }
        
        detector.add_camera_calibration("cam1", calibration)
        
        assert "cam1" in detector.camera_calibrations
        assert detector.camera_calibrations["cam1"] == calibration
