"""
Unit tests for TrainingDataManager.

Tests cover:
- Frame export functionality
- Annotation import (COCO format)
- Version tracking (dataset and model)
- Match usage tracking
- Retraining candidate identification
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
import numpy as np

from umpirai.training.training_data_manager import (
    TrainingDataManager,
    DatasetVersion,
    ModelVersion,
    MatchDatasetInfo
)
from umpirai.models.data_models import (
    Frame,
    Detection,
    DetectionResult,
    BoundingBox,
    Position3D
)


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def training_manager(temp_data_dir):
    """Create a TrainingDataManager instance with temporary directory."""
    return TrainingDataManager(data_dir=temp_data_dir)


@pytest.fixture
def sample_frame():
    """Create a sample frame for testing."""
    image = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    return Frame(
        camera_id="cam1",
        frame_number=100,
        timestamp=1234567890.0,
        image=image,
        metadata={"test": "data"}
    )


@pytest.fixture
def sample_detection():
    """Create a sample detection for testing."""
    return Detection(
        class_id=0,
        class_name="ball",
        bounding_box=BoundingBox(x=100, y=200, width=50, height=50),
        confidence=0.95,
        position_3d=Position3D(x=1.0, y=2.0, z=0.5)
    )


@pytest.fixture
def sample_detection_result(sample_frame, sample_detection):
    """Create a sample detection result for testing."""
    return DetectionResult(
        frame=sample_frame,
        detections=[sample_detection],
        processing_time_ms=50.0
    )


class TestDatasetVersion:
    """Tests for DatasetVersion dataclass."""
    
    def test_valid_dataset_version(self):
        """Test creating a valid dataset version."""
        version = DatasetVersion(
            version_id="v1.0",
            created_at="2024-01-01T00:00:00",
            num_frames=100,
            num_annotations=500,
            description="Test dataset",
            metadata={"source": "test"}
        )
        assert version.version_id == "v1.0"
        assert version.num_frames == 100
        assert version.num_annotations == 500
    
    def test_invalid_version_id(self):
        """Test that empty version_id raises ValueError."""
        with pytest.raises(ValueError, match="version_id must be a non-empty string"):
            DatasetVersion(
                version_id="",
                created_at="2024-01-01T00:00:00",
                num_frames=100,
                num_annotations=500,
                description="Test",
                metadata={}
            )
    
    def test_negative_num_frames(self):
        """Test that negative num_frames raises ValueError."""
        with pytest.raises(ValueError, match="num_frames must be a non-negative integer"):
            DatasetVersion(
                version_id="v1.0",
                created_at="2024-01-01T00:00:00",
                num_frames=-1,
                num_annotations=500,
                description="Test",
                metadata={}
            )


class TestModelVersion:
    """Tests for ModelVersion dataclass."""
    
    def test_valid_model_version(self):
        """Test creating a valid model version."""
        version = ModelVersion(
            version_id="model_v1.0",
            created_at="2024-01-01T00:00:00",
            training_dataset_version="dataset_v1.0",
            model_architecture="YOLOv8m",
            performance_metrics={"mAP50": 0.95},
            model_path="/path/to/model.pt",
            metadata={"epochs": 100}
        )
        assert version.version_id == "model_v1.0"
        assert version.model_architecture == "YOLOv8m"
        assert version.performance_metrics["mAP50"] == 0.95
    
    def test_invalid_model_path(self):
        """Test that empty model_path raises ValueError."""
        with pytest.raises(ValueError, match="model_path must be a non-empty string"):
            ModelVersion(
                version_id="model_v1.0",
                created_at="2024-01-01T00:00:00",
                training_dataset_version="dataset_v1.0",
                model_architecture="YOLOv8m",
                performance_metrics={},
                model_path="",
                metadata={}
            )


class TestMatchDatasetInfo:
    """Tests for MatchDatasetInfo dataclass."""
    
    def test_valid_match_info(self):
        """Test creating valid match dataset info."""
        info = MatchDatasetInfo(
            match_id="match_001",
            timestamp="2024-01-01T00:00:00",
            model_version="model_v1.0",
            dataset_version="dataset_v1.0"
        )
        assert info.match_id == "match_001"
        assert info.model_version == "model_v1.0"
    
    def test_invalid_match_id(self):
        """Test that empty match_id raises ValueError."""
        with pytest.raises(ValueError, match="match_id must be a non-empty string"):
            MatchDatasetInfo(
                match_id="",
                timestamp="2024-01-01T00:00:00",
                model_version="model_v1.0",
                dataset_version="dataset_v1.0"
            )


class TestTrainingDataManagerInit:
    """Tests for TrainingDataManager initialization."""
    
    def test_initialization_creates_directories(self, temp_data_dir):
        """Test that initialization creates required directories."""
        manager = TrainingDataManager(data_dir=temp_data_dir)
        
        assert manager.frames_dir.exists()
        assert manager.annotations_dir.exists()
        assert manager.versions_dir.exists()
        assert manager.models_dir.exists()
        assert manager.match_info_dir.exists()
    
    def test_initialization_loads_existing_versions(self, temp_data_dir):
        """Test that initialization loads existing version files."""
        # Create a dataset version file
        versions_dir = Path(temp_data_dir) / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)
        
        version_data = {
            "version_id": "v1.0",
            "created_at": "2024-01-01T00:00:00",
            "num_frames": 100,
            "num_annotations": 500,
            "description": "Test",
            "metadata": {}
        }
        
        with open(versions_dir / "dataset_v1.0.json", 'w') as f:
            json.dump(version_data, f)
        
        manager = TrainingDataManager(data_dir=temp_data_dir)
        assert "v1.0" in manager.dataset_versions
        assert manager.dataset_versions["v1.0"].num_frames == 100


class TestExportFrames:
    """Tests for export_frames functionality."""
    
    def test_export_single_frame(self, training_manager, sample_detection_result):
        """Test exporting a single frame with detections."""
        dataset_version = training_manager.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="test_v1",
            description="Test export"
        )
        
        assert dataset_version.version_id == "test_v1"
        assert dataset_version.num_frames == 1
        assert dataset_version.num_annotations == 1
        assert dataset_version.description == "Test export"
        
        # Check that frame was saved
        version_dir = training_manager.frames_dir / "test_v1"
        assert version_dir.exists()
        
        # Check that image file exists
        frame_files = list(version_dir.glob("*.jpg"))
        assert len(frame_files) == 1
        
        # Check that metadata file exists
        metadata_files = list(version_dir.glob("*.json"))
        assert len(metadata_files) == 1
    
    def test_export_multiple_frames(self, training_manager, sample_frame, sample_detection):
        """Test exporting multiple frames."""
        detection_results = []
        for i in range(5):
            frame = Frame(
                camera_id="cam1",
                frame_number=100 + i,
                timestamp=1234567890.0 + i,
                image=np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8),
                metadata={}
            )
            result = DetectionResult(
                frame=frame,
                detections=[sample_detection],
                processing_time_ms=50.0
            )
            detection_results.append(result)
        
        dataset_version = training_manager.export_frames(
            detection_results=detection_results,
            dataset_version_id="test_v2",
            description="Multiple frames"
        )
        
        assert dataset_version.num_frames == 5
        assert dataset_version.num_annotations == 5
    
    def test_export_duplicate_version_raises_error(self, training_manager, sample_detection_result):
        """Test that exporting with duplicate version_id raises ValueError."""
        training_manager.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="test_v1",
            description="First export"
        )
        
        with pytest.raises(ValueError, match="Dataset version test_v1 already exists"):
            training_manager.export_frames(
                detection_results=[sample_detection_result],
                dataset_version_id="test_v1",
                description="Duplicate export"
            )
    
    def test_export_with_metadata(self, training_manager, sample_detection_result):
        """Test exporting frames with custom metadata."""
        metadata = {"source": "test_match", "camera_type": "smartphone"}
        
        dataset_version = training_manager.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="test_v3",
            description="With metadata",
            metadata=metadata
        )
        
        assert dataset_version.metadata["source"] == "test_match"
        assert dataset_version.metadata["camera_type"] == "smartphone"
    
    def test_export_frame_metadata_structure(self, training_manager, sample_detection_result):
        """Test that exported frame metadata has correct structure."""
        training_manager.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="test_v4",
            description="Metadata structure test"
        )
        
        version_dir = training_manager.frames_dir / "test_v4"
        metadata_file = list(version_dir.glob("*.json"))[0]
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        assert "frame_filename" in metadata
        assert "camera_id" in metadata
        assert "frame_number" in metadata
        assert "timestamp" in metadata
        assert "detections" in metadata
        assert len(metadata["detections"]) == 1
        
        detection = metadata["detections"][0]
        assert "class_id" in detection
        assert "class_name" in detection
        assert "bounding_box" in detection
        assert "confidence" in detection


class TestImportAnnotations:
    """Tests for import_annotations functionality."""
    
    def test_import_valid_coco_annotations(self, training_manager, sample_detection_result, temp_data_dir):
        """Test importing valid COCO format annotations."""
        # First export frames to create dataset version
        training_manager.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="test_v1",
            description="Test"
        )
        
        # Create COCO format annotations
        coco_data = {
            "images": [
                {
                    "id": 1,
                    "file_name": "cam1_00000100.jpg",
                    "width": 1280,
                    "height": 720
                }
            ],
            "annotations": [
                {
                    "id": 1,
                    "image_id": 1,
                    "category_id": 0,
                    "bbox": [100, 200, 50, 50],
                    "area": 2500,
                    "iscrowd": 0
                }
            ],
            "categories": [
                {
                    "id": 0,
                    "name": "ball",
                    "supercategory": "object"
                }
            ]
        }
        
        coco_file = Path(temp_data_dir) / "annotations.json"
        with open(coco_file, 'w') as f:
            json.dump(coco_data, f)
        
        num_annotations = training_manager.import_annotations(
            coco_file_path=str(coco_file),
            dataset_version_id="test_v1"
        )
        
        assert num_annotations == 1
        
        # Check that annotations were saved
        annotations_dir = training_manager.annotations_dir / "test_v1"
        assert annotations_dir.exists()
        assert (annotations_dir / "annotations_coco.json").exists()
    
    def test_import_nonexistent_dataset_raises_error(self, training_manager, temp_data_dir):
        """Test that importing to nonexistent dataset raises ValueError."""
        coco_data = {
            "images": [],
            "annotations": [],
            "categories": []
        }
        
        coco_file = Path(temp_data_dir) / "annotations.json"
        with open(coco_file, 'w') as f:
            json.dump(coco_data, f)
        
        with pytest.raises(ValueError, match="Dataset version nonexistent does not exist"):
            training_manager.import_annotations(
                coco_file_path=str(coco_file),
                dataset_version_id="nonexistent"
            )
    
    def test_import_invalid_coco_format_raises_error(self, training_manager, sample_detection_result, temp_data_dir):
        """Test that invalid COCO format raises ValueError."""
        # First export frames
        training_manager.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="test_v1",
            description="Test"
        )
        
        # Create invalid COCO data (missing required keys)
        invalid_coco = {"images": []}
        
        coco_file = Path(temp_data_dir) / "invalid_annotations.json"
        with open(coco_file, 'w') as f:
            json.dump(invalid_coco, f)
        
        with pytest.raises(ValueError, match="Invalid COCO format"):
            training_manager.import_annotations(
                coco_file_path=str(coco_file),
                dataset_version_id="test_v1"
            )
    
    def test_import_updates_dataset_version(self, training_manager, sample_detection_result, temp_data_dir):
        """Test that importing annotations updates dataset version."""
        # Export frames
        training_manager.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="test_v1",
            description="Test"
        )
        
        # Create COCO annotations
        coco_data = {
            "images": [{"id": 1, "file_name": "test.jpg"}],
            "annotations": [
                {"id": 1, "image_id": 1, "category_id": 0, "bbox": [0, 0, 10, 10]},
                {"id": 2, "image_id": 1, "category_id": 1, "bbox": [10, 10, 20, 20]}
            ],
            "categories": [{"id": 0, "name": "ball"}]
        }
        
        coco_file = Path(temp_data_dir) / "annotations.json"
        with open(coco_file, 'w') as f:
            json.dump(coco_data, f)
        
        training_manager.import_annotations(
            coco_file_path=str(coco_file),
            dataset_version_id="test_v1"
        )
        
        dataset_version = training_manager.get_dataset_version("test_v1")
        assert dataset_version.num_annotations == 2
        assert "coco_annotations_path" in dataset_version.metadata


class TestModelVersionTracking:
    """Tests for model version tracking."""
    
    def test_register_model_version(self, training_manager, sample_detection_result):
        """Test registering a new model version."""
        # First create a dataset version
        training_manager.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="dataset_v1",
            description="Training data"
        )
        
        model_version = training_manager.register_model_version(
            version_id="model_v1",
            training_dataset_version="dataset_v1",
            model_architecture="YOLOv8m",
            performance_metrics={"mAP50": 0.95, "mAP50-95": 0.85},
            model_path="/path/to/model.pt",
            metadata={"epochs": 100, "batch_size": 16}
        )
        
        assert model_version.version_id == "model_v1"
        assert model_version.training_dataset_version == "dataset_v1"
        assert model_version.model_architecture == "YOLOv8m"
        assert model_version.performance_metrics["mAP50"] == 0.95
        assert model_version.metadata["epochs"] == 100
    
    def test_register_duplicate_model_raises_error(self, training_manager, sample_detection_result):
        """Test that registering duplicate model version raises ValueError."""
        training_manager.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="dataset_v1",
            description="Training data"
        )
        
        training_manager.register_model_version(
            version_id="model_v1",
            training_dataset_version="dataset_v1",
            model_architecture="YOLOv8m",
            performance_metrics={},
            model_path="/path/to/model.pt"
        )
        
        with pytest.raises(ValueError, match="Model version model_v1 already exists"):
            training_manager.register_model_version(
                version_id="model_v1",
                training_dataset_version="dataset_v1",
                model_architecture="YOLOv8m",
                performance_metrics={},
                model_path="/path/to/model2.pt"
            )
    
    def test_register_model_with_nonexistent_dataset_raises_error(self, training_manager):
        """Test that registering model with nonexistent dataset raises ValueError."""
        with pytest.raises(ValueError, match="Dataset version nonexistent does not exist"):
            training_manager.register_model_version(
                version_id="model_v1",
                training_dataset_version="nonexistent",
                model_architecture="YOLOv8m",
                performance_metrics={},
                model_path="/path/to/model.pt"
            )
    
    def test_get_model_version(self, training_manager, sample_detection_result):
        """Test retrieving model version by ID."""
        training_manager.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="dataset_v1",
            description="Training data"
        )
        
        training_manager.register_model_version(
            version_id="model_v1",
            training_dataset_version="dataset_v1",
            model_architecture="YOLOv8m",
            performance_metrics={"mAP50": 0.95},
            model_path="/path/to/model.pt"
        )
        
        model_version = training_manager.get_model_version("model_v1")
        assert model_version is not None
        assert model_version.version_id == "model_v1"
        
        nonexistent = training_manager.get_model_version("nonexistent")
        assert nonexistent is None


class TestMatchUsageTracking:
    """Tests for match usage tracking."""
    
    def test_track_match_usage(self, training_manager, sample_detection_result):
        """Test tracking model and dataset versions used for a match."""
        # Create dataset and model versions
        training_manager.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="dataset_v1",
            description="Training data"
        )
        
        training_manager.register_model_version(
            version_id="model_v1",
            training_dataset_version="dataset_v1",
            model_architecture="YOLOv8m",
            performance_metrics={},
            model_path="/path/to/model.pt"
        )
        
        match_info = training_manager.track_match_usage(
            match_id="match_001",
            model_version="model_v1",
            dataset_version="dataset_v1"
        )
        
        assert match_info.match_id == "match_001"
        assert match_info.model_version == "model_v1"
        assert match_info.dataset_version == "dataset_v1"
    
    def test_track_match_with_nonexistent_model_raises_error(self, training_manager, sample_detection_result):
        """Test that tracking match with nonexistent model raises ValueError."""
        training_manager.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="dataset_v1",
            description="Training data"
        )
        
        with pytest.raises(ValueError, match="Model version nonexistent does not exist"):
            training_manager.track_match_usage(
                match_id="match_001",
                model_version="nonexistent",
                dataset_version="dataset_v1"
            )
    
    def test_get_match_info(self, training_manager, sample_detection_result):
        """Test retrieving match info by match ID."""
        training_manager.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="dataset_v1",
            description="Training data"
        )
        
        training_manager.register_model_version(
            version_id="model_v1",
            training_dataset_version="dataset_v1",
            model_architecture="YOLOv8m",
            performance_metrics={},
            model_path="/path/to/model.pt"
        )
        
        training_manager.track_match_usage(
            match_id="match_001",
            model_version="model_v1",
            dataset_version="dataset_v1"
        )
        
        match_info = training_manager.get_match_info("match_001")
        assert match_info is not None
        assert match_info.match_id == "match_001"
        
        nonexistent = training_manager.get_match_info("nonexistent")
        assert nonexistent is None


class TestVersionListing:
    """Tests for listing versions."""
    
    def test_list_dataset_versions(self, training_manager, sample_detection_result):
        """Test listing all dataset versions."""
        # Create multiple dataset versions
        for i in range(3):
            frame = Frame(
                camera_id="cam1",
                frame_number=100 + i,
                timestamp=1234567890.0 + i,
                image=np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8),
                metadata={}
            )
            result = DetectionResult(
                frame=frame,
                detections=[],
                processing_time_ms=50.0
            )
            training_manager.export_frames(
                detection_results=[result],
                dataset_version_id=f"dataset_v{i}",
                description=f"Dataset {i}"
            )
        
        versions = training_manager.list_dataset_versions()
        assert len(versions) == 3
        assert all(isinstance(v, DatasetVersion) for v in versions)
    
    def test_list_model_versions(self, training_manager, sample_detection_result):
        """Test listing all model versions."""
        training_manager.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="dataset_v1",
            description="Training data"
        )
        
        # Create multiple model versions
        for i in range(2):
            training_manager.register_model_version(
                version_id=f"model_v{i}",
                training_dataset_version="dataset_v1",
                model_architecture="YOLOv8m",
                performance_metrics={},
                model_path=f"/path/to/model{i}.pt"
            )
        
        versions = training_manager.list_model_versions()
        assert len(versions) == 2
        assert all(isinstance(v, ModelVersion) for v in versions)


class TestRetrainingCandidates:
    """Tests for identifying retraining candidates."""
    
    def test_get_retraining_candidates(self, training_manager):
        """Test identifying dataset versions suitable for retraining."""
        # Create dataset versions with different frame counts
        for i in range(3):
            num_frames = 50 + i * 100  # 50, 150, 250 frames
            detection_results = []
            for j in range(num_frames):
                frame = Frame(
                    camera_id="cam1",
                    frame_number=j,
                    timestamp=float(j),
                    image=np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8),
                    metadata={}
                )
                result = DetectionResult(
                    frame=frame,
                    detections=[],
                    processing_time_ms=50.0
                )
                detection_results.append(result)
            
            training_manager.export_frames(
                detection_results=detection_results,
                dataset_version_id=f"dataset_v{i}",
                description=f"Dataset {i}"
            )
        
        # Get candidates with min 100 frames
        candidates = training_manager.get_retraining_candidates(min_new_frames=100)
        
        # Should return datasets with ≥100 frames that haven't been used for training
        assert len(candidates) == 2  # dataset_v1 (150 frames) and dataset_v2 (250 frames)
        assert all(c.num_frames >= 100 for c in candidates)
    
    def test_retraining_candidates_excludes_used_datasets(self, training_manager):
        """Test that datasets used for training are excluded from candidates."""
        # Create dataset
        frame = Frame(
            camera_id="cam1",
            frame_number=0,
            timestamp=0.0,
            image=np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8),
            metadata={}
        )
        detection_results = [DetectionResult(frame=frame, detections=[], processing_time_ms=50.0)] * 150
        
        training_manager.export_frames(
            detection_results=detection_results,
            dataset_version_id="dataset_v1",
            description="Training data"
        )
        
        # Register model using this dataset
        training_manager.register_model_version(
            version_id="model_v1",
            training_dataset_version="dataset_v1",
            model_architecture="YOLOv8m",
            performance_metrics={},
            model_path="/path/to/model.pt"
        )
        
        # Should not return dataset_v1 as it's been used for training
        candidates = training_manager.get_retraining_candidates(min_new_frames=100)
        assert len(candidates) == 0


class TestPersistence:
    """Tests for data persistence across manager instances."""
    
    def test_dataset_version_persists(self, temp_data_dir, sample_detection_result):
        """Test that dataset versions persist across manager instances."""
        # Create first manager and export frames
        manager1 = TrainingDataManager(data_dir=temp_data_dir)
        manager1.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="dataset_v1",
            description="Persistent dataset"
        )
        
        # Create second manager instance
        manager2 = TrainingDataManager(data_dir=temp_data_dir)
        
        # Should load existing dataset version
        assert "dataset_v1" in manager2.dataset_versions
        assert manager2.dataset_versions["dataset_v1"].description == "Persistent dataset"
    
    def test_model_version_persists(self, temp_data_dir, sample_detection_result):
        """Test that model versions persist across manager instances."""
        manager1 = TrainingDataManager(data_dir=temp_data_dir)
        manager1.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="dataset_v1",
            description="Training data"
        )
        manager1.register_model_version(
            version_id="model_v1",
            training_dataset_version="dataset_v1",
            model_architecture="YOLOv8m",
            performance_metrics={"mAP50": 0.95},
            model_path="/path/to/model.pt"
        )
        
        manager2 = TrainingDataManager(data_dir=temp_data_dir)
        
        assert "model_v1" in manager2.model_versions
        assert manager2.model_versions["model_v1"].performance_metrics["mAP50"] == 0.95
    
    def test_match_info_persists(self, temp_data_dir, sample_detection_result):
        """Test that match info persists across manager instances."""
        manager1 = TrainingDataManager(data_dir=temp_data_dir)
        manager1.export_frames(
            detection_results=[sample_detection_result],
            dataset_version_id="dataset_v1",
            description="Training data"
        )
        manager1.register_model_version(
            version_id="model_v1",
            training_dataset_version="dataset_v1",
            model_architecture="YOLOv8m",
            performance_metrics={},
            model_path="/path/to/model.pt"
        )
        manager1.track_match_usage(
            match_id="match_001",
            model_version="model_v1",
            dataset_version="dataset_v1"
        )
        
        manager2 = TrainingDataManager(data_dir=temp_data_dir)
        
        assert "match_001" in manager2.match_info
        assert manager2.match_info["match_001"].model_version == "model_v1"
