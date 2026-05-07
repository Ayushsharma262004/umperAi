"""
Property-based tests for ObjectDetector component.

Tests verify that object detection properties hold across
all valid inputs using Hypothesis framework.
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck
from unittest.mock import Mock, MagicMock, patch

from umpirai.detection import ObjectDetector, MultiViewDetectionResult
from umpirai.models.data_models import (
    Frame,
    Detection,
    BoundingBox,
    Position3D,
    DetectionResult,
)


# ============================================================================
# Custom Strategies
# ============================================================================

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
def detection_strategy(draw):
    """Generate valid detection with random confidence."""
    class_id = draw(st.integers(min_value=0, max_value=7))
    class_names = ["ball", "stumps", "crease", "batsman", "bowler", "fielder", "pitch_boundary", "wide_guideline"]
    
    # Generate bounding box
    x = draw(st.floats(min_value=0, max_value=1000))
    y = draw(st.floats(min_value=0, max_value=500))
    width = draw(st.floats(min_value=10, max_value=200))
    height = draw(st.floats(min_value=10, max_value=200))
    
    bbox = BoundingBox(x=x, y=y, width=width, height=height)
    
    # Generate confidence in valid range [0.0, 1.0]
    confidence = draw(st.floats(min_value=0.0, max_value=1.0))
    
    return Detection(
        class_id=class_id,
        class_name=class_names[class_id],
        bounding_box=bbox,
        confidence=confidence,
        position_3d=None
    )


@st.composite
def detection_result_strategy(draw):
    """Generate valid detection result."""
    frame = draw(frame_strategy())
    
    # Generate list of detections
    num_detections = draw(st.integers(min_value=0, max_value=10))
    detections = [draw(detection_strategy()) for _ in range(num_detections)]
    
    processing_time_ms = draw(st.floats(min_value=0.0, max_value=1000.0))
    
    return DetectionResult(
        frame=frame,
        detections=detections,
        processing_time_ms=processing_time_ms
    )


@st.composite
def multi_camera_detections_strategy(draw):
    """Generate detections from multiple cameras."""
    num_cameras = draw(st.integers(min_value=2, max_value=4))
    camera_ids = [f"cam{i}" for i in range(num_cameras)]
    
    # Generate detections for each camera
    detections_by_camera = {}
    for camera_id in camera_ids:
        num_detections = draw(st.integers(min_value=1, max_value=5))
        detections = [draw(detection_strategy()) for _ in range(num_detections)]
        detections_by_camera[camera_id] = detections
    
    return detections_by_camera


# ============================================================================
# Property Tests
# ============================================================================

class TestObjectDetectorProperties:
    """Property-based tests for ObjectDetector."""
    
    @given(detection=detection_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_1_detection_confidence_bounds(self, detection):
        """
        **Validates: Requirements 2.6, 2.7**
        
        Feature: ai-auto-umpiring-system, Property 1: Detection Confidence Bounds
        
        For any detection result produced by the Object Detector, the confidence
        score SHALL be in the range [0.0, 1.0] and all detections with confidence
        below 0.70 SHALL be flagged as uncertain.
        """
        # Assert: Confidence is in valid range [0.0, 1.0]
        assert 0.0 <= detection.confidence <= 1.0, \
            f"Confidence {detection.confidence} is outside valid range [0.0, 1.0]"
        
        # Assert: Low confidence detections are flagged as uncertain
        if detection.confidence < 0.70:
            assert detection.is_uncertain(), \
                f"Detection with confidence {detection.confidence} should be flagged as uncertain"
        else:
            assert not detection.is_uncertain(), \
                f"Detection with confidence {detection.confidence} should not be flagged as uncertain"
    
    @given(detection_result=detection_result_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_1_all_detections_have_valid_confidence(self, detection_result):
        """
        Property: For any detection result, all detections SHALL have
        confidence scores in the range [0.0, 1.0].
        """
        for detection in detection_result.detections:
            assert 0.0 <= detection.confidence <= 1.0, \
                f"Detection confidence {detection.confidence} is outside valid range"
    
    @given(detection_result=detection_result_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_1_uncertain_detections_flagged(self, detection_result):
        """
        Property: For any detection result, all detections with confidence
        below 0.70 SHALL be flagged as uncertain.
        """
        for detection in detection_result.detections:
            if detection.confidence < 0.70:
                assert detection.is_uncertain(), \
                    f"Detection with confidence {detection.confidence} should be uncertain"
    
    @given(
        detections=st.lists(detection_strategy(), min_size=1, max_size=10)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_confidence_evaluation_consistency(self, detections):
        """
        Property: For any detection, confidence evaluation SHALL be consistent
        with defined thresholds (high ≥90%, medium 70-90%, low <70%).
        """
        # Create a mock detector to test confidence evaluation
        # We don't need a real model for this property test
        with patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True):
            with patch('umpirai.detection.object_detector.YOLO'):
                detector = ObjectDetector.__new__(ObjectDetector)
                detector.CONFIDENCE_HIGH = 0.90
                detector.CONFIDENCE_MEDIUM = 0.70
                detector.CONFIDENCE_LOW = 0.70
                
                for detection in detections:
                    level = detector.evaluate_confidence(detection)
                    
                    if detection.confidence >= 0.90:
                        assert level == "high", \
                            f"Confidence {detection.confidence} should be 'high', got '{level}'"
                    elif detection.confidence >= 0.70:
                        assert level == "medium", \
                            f"Confidence {detection.confidence} should be 'medium', got '{level}'"
                    else:
                        assert level == "low", \
                            f"Confidence {detection.confidence} should be 'low', got '{level}'"
    
    @given(
        num_detections=st.integers(min_value=0, max_value=20)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_detection_result_preserves_count(self, num_detections):
        """
        Property: For any number of detections, the detection result SHALL
        preserve the exact count of detections.
        """
        # Create mock detections
        detections = []
        for i in range(num_detections):
            detection = Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=100, width=50, height=50),
                confidence=0.85,
                position_3d=None
            )
            detections.append(detection)
        
        # Create detection result
        frame = Frame(
            camera_id="test",
            frame_number=0,
            timestamp=0.0,
            image=np.zeros((720, 1280, 3), dtype=np.uint8),
            metadata={}
        )
        
        result = DetectionResult(
            frame=frame,
            detections=detections,
            processing_time_ms=10.0
        )
        
        # Assert: Count preserved
        assert len(result.detections) == num_detections
    
    @given(
        class_id=st.integers(min_value=0, max_value=7)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_detection_class_filtering(self, class_id):
        """
        Property: For any detection result, filtering by class ID SHALL
        return only detections of that class.
        """
        # Create detections with various classes
        detections = []
        expected_count = 0
        
        for i in range(10):
            det_class_id = i % 8  # Cycle through classes 0-7
            if det_class_id == class_id:
                expected_count += 1
            
            detection = Detection(
                class_id=det_class_id,
                class_name=f"class_{det_class_id}",
                bounding_box=BoundingBox(x=100, y=100, width=50, height=50),
                confidence=0.85,
                position_3d=None
            )
            detections.append(detection)
        
        # Create detection result
        frame = Frame(
            camera_id="test",
            frame_number=0,
            timestamp=0.0,
            image=np.zeros((720, 1280, 3), dtype=np.uint8),
            metadata={}
        )
        
        result = DetectionResult(
            frame=frame,
            detections=detections,
            processing_time_ms=10.0
        )
        
        # Filter by class
        filtered = result.get_detections_by_class(class_id)
        
        # Assert: All filtered detections have correct class
        assert len(filtered) == expected_count
        assert all(d.class_id == class_id for d in filtered)
    
    @given(
        detections=st.lists(detection_strategy(), min_size=0, max_size=10)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_uncertain_detection_identification(self, detections):
        """
        Property: For any detection result, has_uncertain_detections SHALL
        return True if and only if at least one detection has confidence < 0.70.
        """
        frame = Frame(
            camera_id="test",
            frame_number=0,
            timestamp=0.0,
            image=np.zeros((720, 1280, 3), dtype=np.uint8),
            metadata={}
        )
        
        result = DetectionResult(
            frame=frame,
            detections=detections,
            processing_time_ms=10.0
        )
        
        # Check if any detection is uncertain
        has_uncertain = any(d.confidence < 0.70 for d in detections)
        
        # Assert: Method returns correct value
        assert result.has_uncertain_detections() == has_uncertain
    
    @given(
        processing_time=st.floats(min_value=0.0, max_value=10000.0)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_processing_time_non_negative(self, processing_time):
        """
        Property: For any detection result, processing time SHALL be non-negative.
        """
        frame = Frame(
            camera_id="test",
            frame_number=0,
            timestamp=0.0,
            image=np.zeros((720, 1280, 3), dtype=np.uint8),
            metadata={}
        )
        
        result = DetectionResult(
            frame=frame,
            detections=[],
            processing_time_ms=processing_time
        )
        
        assert result.processing_time_ms >= 0.0
    
    @given(
        num_cameras=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_25_multi_camera_detection_fusion(self, num_cameras):
        """
        **Validates: Requirements 12.2, 12.3**
        
        Feature: ai-auto-umpiring-system, Property 25: Multi-Camera Detection Fusion
        
        For any set of detections from multiple cameras observing the same object,
        the Decision Engine SHALL combine the detections, using the detection with
        highest confidence when conflicts occur.
        """
        # Create mock detector
        with patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True):
            with patch('umpirai.detection.object_detector.YOLO') as mock_yolo:
                # Create mock model
                mock_model = MagicMock()
                mock_yolo.return_value = mock_model
                
                detector = ObjectDetector()
                
                # Create frames from multiple cameras
                frames = {}
                camera_ids = [f"cam{i}" for i in range(num_cameras)]
                
                for camera_id in camera_ids:
                    frame = Frame(
                        camera_id=camera_id,
                        frame_number=0,
                        timestamp=0.0,
                        image=np.zeros((720, 1280, 3), dtype=np.uint8),
                        metadata={}
                    )
                    frames[camera_id] = frame
                
                # Mock detection results for each camera
                # Create detections of the same object (ball) with different confidences
                view_detections = {}
                confidences = [0.85, 0.92, 0.78, 0.88][:num_cameras]
                
                for i, camera_id in enumerate(camera_ids):
                    detection = Detection(
                        class_id=0,  # ball
                        class_name="ball",
                        bounding_box=BoundingBox(
                            x=100 + i * 5,  # Slightly different positions
                            y=100 + i * 5,
                            width=50,
                            height=50
                        ),
                        confidence=confidences[i],
                        position_3d=None
                    )
                    view_detections[camera_id] = [detection]
                
                # Fuse detections
                fused = detector._fuse_multi_view_detections(view_detections, frames)
                
                # Assert: Fusion produces detections
                assert len(fused) > 0, "Fusion should produce at least one detection"
                
                # Assert: Fused detection has valid confidence
                for detection in fused:
                    assert 0.0 <= detection.confidence <= 1.0, \
                        f"Fused detection confidence {detection.confidence} is outside valid range"
                
                # Assert: When views are similar, fusion should combine them
                # The fused confidence should be influenced by all views
                ball_detections = [d for d in fused if d.class_id == 0]
                if ball_detections:
                    fused_ball = ball_detections[0]
                    # Fused confidence should be within range of input confidences
                    min_conf = min(confidences)
                    max_conf = max(confidences)
                    assert min_conf <= fused_ball.confidence <= max_conf, \
                        f"Fused confidence {fused_ball.confidence} should be between {min_conf} and {max_conf}"
    
    @given(
        num_cameras=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=50, deadline=None)
    def test_property_multi_view_highest_confidence_on_conflict(self, num_cameras):
        """
        Property: For any set of conflicting detections (significantly different
        positions), the system SHALL use the detection with highest confidence.
        """
        # Create mock detector
        with patch('umpirai.detection.object_detector.YOLO_AVAILABLE', True):
            with patch('umpirai.detection.object_detector.YOLO') as mock_yolo:
                mock_model = MagicMock()
                mock_yolo.return_value = mock_model
                
                detector = ObjectDetector()
                
                # Create conflicting detections (very different positions)
                detections = []
                confidences = [0.75, 0.92, 0.68, 0.85][:num_cameras]
                
                for i in range(num_cameras):
                    detection = Detection(
                        class_id=0,
                        class_name="ball",
                        bounding_box=BoundingBox(
                            x=100 + i * 200,  # Very different positions (conflict)
                            y=100 + i * 200,
                            width=50,
                            height=50
                        ),
                        confidence=confidences[i],
                        position_3d=None
                    )
                    detections.append((f"cam{i}", detection))
                
                # Check for conflict
                has_conflict = detector._has_significant_conflict(detections)
                
                if has_conflict:
                    # Fuse detections
                    frames = {f"cam{i}": Frame(
                        camera_id=f"cam{i}",
                        frame_number=0,
                        timestamp=0.0,
                        image=np.zeros((720, 1280, 3), dtype=np.uint8),
                        metadata={}
                    ) for i in range(num_cameras)}
                    
                    fused = detector._fuse_detections_for_class(0, detections, frames)
                    
                    # Assert: Fused detection should use highest confidence
                    max_confidence = max(confidences)
                    assert fused is not None
                    # The fused detection should have the highest confidence
                    # (when conflict detected, we use the best detection)
                    assert fused.confidence == max_confidence, \
                        f"On conflict, should use highest confidence {max_confidence}, got {fused.confidence}"
    
    @given(
        num_cameras=st.integers(min_value=1, max_value=4)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_multi_view_result_structure(self, num_cameras):
        """
        Property: For any multi-view detection result, the result SHALL contain
        all required fields with valid types and values.
        """
        camera_ids = [f"cam{i}" for i in range(num_cameras)]
        
        # Create detections
        detections = [
            Detection(
                class_id=0,
                class_name="ball",
                bounding_box=BoundingBox(x=100, y=100, width=50, height=50),
                confidence=0.85,
                position_3d=None
            )
        ]
        
        # Create multi-view result
        result = MultiViewDetectionResult(
            detections=detections,
            processing_time_ms=50.0,
            camera_ids=camera_ids,
            fusion_method="weighted_average"
        )
        
        # Assert: All fields present and valid
        assert isinstance(result.detections, list)
        assert all(isinstance(d, Detection) for d in result.detections)
        assert isinstance(result.processing_time_ms, (int, float))
        assert result.processing_time_ms >= 0.0
        assert isinstance(result.camera_ids, list)
        assert len(result.camera_ids) == num_cameras
        assert isinstance(result.fusion_method, str)
