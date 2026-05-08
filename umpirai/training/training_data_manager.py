"""
Training Data Manager for the UmpirAI system.

This module provides functionality for managing training data for the Object Detector,
including exporting video frames with detections, importing annotations in COCO format,
tracking model and dataset versions, and supporting model retraining workflows.
"""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import cv2

from umpirai.models.data_models import Frame, Detection, DetectionResult


@dataclass
class DatasetVersion:
    """Dataset version information."""
    version_id: str
    created_at: str  # ISO 8601 timestamp
    num_frames: int
    num_annotations: int
    description: str
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        """Validate dataset version data."""
        if not isinstance(self.version_id, str) or not self.version_id:
            raise ValueError("version_id must be a non-empty string")
        if not isinstance(self.created_at, str) or not self.created_at:
            raise ValueError("created_at must be a non-empty string")
        if not isinstance(self.num_frames, int) or self.num_frames < 0:
            raise ValueError("num_frames must be a non-negative integer")
        if not isinstance(self.num_annotations, int) or self.num_annotations < 0:
            raise ValueError("num_annotations must be a non-negative integer")
        if not isinstance(self.description, str):
            raise TypeError("description must be a string")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary")


@dataclass
class ModelVersion:
    """Model version information."""
    version_id: str
    created_at: str  # ISO 8601 timestamp
    training_dataset_version: str
    model_architecture: str
    performance_metrics: Dict[str, float]
    model_path: str
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        """Validate model version data."""
        if not isinstance(self.version_id, str) or not self.version_id:
            raise ValueError("version_id must be a non-empty string")
        if not isinstance(self.created_at, str) or not self.created_at:
            raise ValueError("created_at must be a non-empty string")
        if not isinstance(self.training_dataset_version, str) or not self.training_dataset_version:
            raise ValueError("training_dataset_version must be a non-empty string")
        if not isinstance(self.model_architecture, str) or not self.model_architecture:
            raise ValueError("model_architecture must be a non-empty string")
        if not isinstance(self.performance_metrics, dict):
            raise TypeError("performance_metrics must be a dictionary")
        if not isinstance(self.model_path, str) or not self.model_path:
            raise ValueError("model_path must be a non-empty string")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary")


@dataclass
class MatchDatasetInfo:
    """Information about model and dataset versions used for a match."""
    match_id: str
    timestamp: str  # ISO 8601 timestamp
    model_version: str
    dataset_version: str
    
    def __post_init__(self):
        """Validate match dataset info."""
        if not isinstance(self.match_id, str) or not self.match_id:
            raise ValueError("match_id must be a non-empty string")
        if not isinstance(self.timestamp, str) or not self.timestamp:
            raise ValueError("timestamp must be a non-empty string")
        if not isinstance(self.model_version, str) or not self.model_version:
            raise ValueError("model_version must be a non-empty string")
        if not isinstance(self.dataset_version, str) or not self.dataset_version:
            raise ValueError("dataset_version must be a non-empty string")


class TrainingDataManager:
    """
    Manages training data for the Object Detector model.
    
    Provides functionality to:
    - Export video frames with detected elements for annotation
    - Import annotated training data in COCO format
    - Track model version and training data version used for each match
    - Support model retraining workflows
    - Manage dataset versioning
    """
    
    def __init__(self, data_dir: str = "./training_data"):
        """
        Initialize the TrainingDataManager.
        
        Args:
            data_dir: Base directory for storing training data
        """
        self.data_dir = Path(data_dir)
        self.frames_dir = self.data_dir / "frames"
        self.annotations_dir = self.data_dir / "annotations"
        self.versions_dir = self.data_dir / "versions"
        self.models_dir = self.data_dir / "models"
        self.match_info_dir = self.data_dir / "match_info"
        
        # Create directories if they don't exist
        for directory in [self.frames_dir, self.annotations_dir, 
                         self.versions_dir, self.models_dir, self.match_info_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Load existing versions
        self.dataset_versions: Dict[str, DatasetVersion] = self._load_dataset_versions()
        self.model_versions: Dict[str, ModelVersion] = self._load_model_versions()
        self.match_info: Dict[str, MatchDatasetInfo] = self._load_match_info()
    
    def export_frames(
        self,
        detection_results: List[DetectionResult],
        dataset_version_id: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> DatasetVersion:
        """
        Export video frames with detected elements for annotation.
        
        Args:
            detection_results: List of detection results to export
            dataset_version_id: Unique identifier for this dataset version
            description: Human-readable description of the dataset
            metadata: Additional metadata for the dataset
        
        Returns:
            DatasetVersion object with information about the exported dataset
        
        Raises:
            ValueError: If dataset_version_id already exists
            IOError: If frame export fails
        """
        if dataset_version_id in self.dataset_versions:
            raise ValueError(f"Dataset version {dataset_version_id} already exists")
        
        if metadata is None:
            metadata = {}
        
        # Create version-specific directory
        version_dir = self.frames_dir / dataset_version_id
        version_dir.mkdir(parents=True, exist_ok=True)
        
        exported_frames = 0
        total_annotations = 0
        
        # Export each frame with its detections
        for result in detection_results:
            frame = result.frame
            frame_filename = f"{frame.camera_id}_{frame.frame_number:08d}.jpg"
            frame_path = version_dir / frame_filename
            
            try:
                # Save frame image
                # Convert RGB to BGR for OpenCV
                bgr_image = cv2.cvtColor(frame.image, cv2.COLOR_RGB2BGR)
                cv2.imwrite(str(frame_path), bgr_image)
                
                # Save detection metadata
                detection_data = {
                    "frame_filename": frame_filename,
                    "camera_id": frame.camera_id,
                    "frame_number": frame.frame_number,
                    "timestamp": frame.timestamp,
                    "detections": [
                        {
                            "class_id": det.class_id,
                            "class_name": det.class_name,
                            "bounding_box": {
                                "x": det.bounding_box.x,
                                "y": det.bounding_box.y,
                                "width": det.bounding_box.width,
                                "height": det.bounding_box.height
                            },
                            "confidence": det.confidence,
                            "position_3d": {
                                "x": det.position_3d.x,
                                "y": det.position_3d.y,
                                "z": det.position_3d.z
                            } if det.position_3d else None
                        }
                        for det in result.detections
                    ]
                }
                
                # Save detection metadata as JSON
                metadata_path = version_dir / f"{frame_filename}.json"
                with open(metadata_path, 'w') as f:
                    json.dump(detection_data, f, indent=2)
                
                exported_frames += 1
                total_annotations += len(result.detections)
                
            except Exception as e:
                raise IOError(f"Failed to export frame {frame_filename}: {str(e)}")
        
        # Create dataset version
        dataset_version = DatasetVersion(
            version_id=dataset_version_id,
            created_at=datetime.utcnow().isoformat(),
            num_frames=exported_frames,
            num_annotations=total_annotations,
            description=description,
            metadata=metadata
        )
        
        # Save dataset version info
        self._save_dataset_version(dataset_version)
        self.dataset_versions[dataset_version_id] = dataset_version
        
        return dataset_version
    
    def import_annotations(
        self,
        coco_file_path: str,
        dataset_version_id: str
    ) -> int:
        """
        Import annotated training data in COCO format.
        
        Args:
            coco_file_path: Path to COCO format JSON file
            dataset_version_id: Dataset version to associate annotations with
        
        Returns:
            Number of annotations imported
        
        Raises:
            ValueError: If dataset version doesn't exist or COCO file is invalid
            IOError: If file cannot be read
        """
        if dataset_version_id not in self.dataset_versions:
            raise ValueError(f"Dataset version {dataset_version_id} does not exist")
        
        try:
            with open(coco_file_path, 'r') as f:
                coco_data = json.load(f)
        except Exception as e:
            raise IOError(f"Failed to read COCO file: {str(e)}")
        
        # Validate COCO format
        required_keys = ['images', 'annotations', 'categories']
        if not all(key in coco_data for key in required_keys):
            raise ValueError(f"Invalid COCO format: missing required keys {required_keys}")
        
        # Save COCO annotations to dataset version directory
        version_dir = self.annotations_dir / dataset_version_id
        version_dir.mkdir(parents=True, exist_ok=True)
        
        annotations_path = version_dir / "annotations_coco.json"
        with open(annotations_path, 'w') as f:
            json.dump(coco_data, f, indent=2)
        
        num_annotations = len(coco_data['annotations'])
        
        # Update dataset version with annotation count
        dataset_version = self.dataset_versions[dataset_version_id]
        dataset_version.num_annotations = num_annotations
        dataset_version.metadata['coco_annotations_path'] = str(annotations_path)
        self._save_dataset_version(dataset_version)
        
        return num_annotations
    
    def register_model_version(
        self,
        version_id: str,
        training_dataset_version: str,
        model_architecture: str,
        performance_metrics: Dict[str, float],
        model_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ModelVersion:
        """
        Register a new model version.
        
        Args:
            version_id: Unique identifier for this model version
            training_dataset_version: Dataset version used for training
            model_architecture: Model architecture name (e.g., "YOLOv8m")
            performance_metrics: Performance metrics (e.g., {"mAP50": 0.95})
            model_path: Path to the trained model file
            metadata: Additional metadata for the model
        
        Returns:
            ModelVersion object
        
        Raises:
            ValueError: If model version already exists or dataset version doesn't exist
        """
        if version_id in self.model_versions:
            raise ValueError(f"Model version {version_id} already exists")
        
        if training_dataset_version not in self.dataset_versions:
            raise ValueError(f"Dataset version {training_dataset_version} does not exist")
        
        if metadata is None:
            metadata = {}
        
        model_version = ModelVersion(
            version_id=version_id,
            created_at=datetime.utcnow().isoformat(),
            training_dataset_version=training_dataset_version,
            model_architecture=model_architecture,
            performance_metrics=performance_metrics,
            model_path=model_path,
            metadata=metadata
        )
        
        # Save model version info
        self._save_model_version(model_version)
        self.model_versions[version_id] = model_version
        
        return model_version
    
    def track_match_usage(
        self,
        match_id: str,
        model_version: str,
        dataset_version: str
    ) -> MatchDatasetInfo:
        """
        Track model version and training data version used for a match.
        
        Args:
            match_id: Unique identifier for the match
            model_version: Model version used for the match
            dataset_version: Dataset version the model was trained on
        
        Returns:
            MatchDatasetInfo object
        
        Raises:
            ValueError: If model or dataset version doesn't exist
        """
        if model_version not in self.model_versions:
            raise ValueError(f"Model version {model_version} does not exist")
        
        if dataset_version not in self.dataset_versions:
            raise ValueError(f"Dataset version {dataset_version} does not exist")
        
        match_info = MatchDatasetInfo(
            match_id=match_id,
            timestamp=datetime.utcnow().isoformat(),
            model_version=model_version,
            dataset_version=dataset_version
        )
        
        # Save match info
        self._save_match_info(match_info)
        self.match_info[match_id] = match_info
        
        return match_info
    
    def get_dataset_version(self, version_id: str) -> Optional[DatasetVersion]:
        """Get dataset version by ID."""
        return self.dataset_versions.get(version_id)
    
    def get_model_version(self, version_id: str) -> Optional[ModelVersion]:
        """Get model version by ID."""
        return self.model_versions.get(version_id)
    
    def get_match_info(self, match_id: str) -> Optional[MatchDatasetInfo]:
        """Get match dataset info by match ID."""
        return self.match_info.get(match_id)
    
    def list_dataset_versions(self) -> List[DatasetVersion]:
        """List all dataset versions."""
        return list(self.dataset_versions.values())
    
    def list_model_versions(self) -> List[ModelVersion]:
        """List all model versions."""
        return list(self.model_versions.values())
    
    def get_retraining_candidates(
        self,
        min_new_frames: int = 100
    ) -> List[DatasetVersion]:
        """
        Get dataset versions that are candidates for model retraining.
        
        Args:
            min_new_frames: Minimum number of new frames to consider for retraining
        
        Returns:
            List of dataset versions suitable for retraining
        """
        candidates = []
        for dataset_version in self.dataset_versions.values():
            if dataset_version.num_frames >= min_new_frames:
                # Check if this dataset has been used for training
                used_for_training = any(
                    model.training_dataset_version == dataset_version.version_id
                    for model in self.model_versions.values()
                )
                if not used_for_training:
                    candidates.append(dataset_version)
        
        return candidates
    
    def _save_dataset_version(self, dataset_version: DatasetVersion) -> None:
        """Save dataset version to disk."""
        version_file = self.versions_dir / f"dataset_{dataset_version.version_id}.json"
        with open(version_file, 'w') as f:
            json.dump(asdict(dataset_version), f, indent=2)
    
    def _save_model_version(self, model_version: ModelVersion) -> None:
        """Save model version to disk."""
        version_file = self.models_dir / f"model_{model_version.version_id}.json"
        with open(version_file, 'w') as f:
            json.dump(asdict(model_version), f, indent=2)
    
    def _save_match_info(self, match_info: MatchDatasetInfo) -> None:
        """Save match info to disk."""
        info_file = self.match_info_dir / f"match_{match_info.match_id}.json"
        with open(info_file, 'w') as f:
            json.dump(asdict(match_info), f, indent=2)
    
    def _load_dataset_versions(self) -> Dict[str, DatasetVersion]:
        """Load all dataset versions from disk."""
        versions = {}
        if not self.versions_dir.exists():
            return versions
        
        for version_file in self.versions_dir.glob("dataset_*.json"):
            try:
                with open(version_file, 'r') as f:
                    data = json.load(f)
                    dataset_version = DatasetVersion(**data)
                    versions[dataset_version.version_id] = dataset_version
            except Exception:
                # Skip invalid version files
                continue
        
        return versions
    
    def _load_model_versions(self) -> Dict[str, ModelVersion]:
        """Load all model versions from disk."""
        versions = {}
        if not self.models_dir.exists():
            return versions
        
        for version_file in self.models_dir.glob("model_*.json"):
            try:
                with open(version_file, 'r') as f:
                    data = json.load(f)
                    model_version = ModelVersion(**data)
                    versions[model_version.version_id] = model_version
            except Exception:
                # Skip invalid version files
                continue
        
        return versions
    
    def _load_match_info(self) -> Dict[str, MatchDatasetInfo]:
        """Load all match info from disk."""
        info = {}
        if not self.match_info_dir.exists():
            return info
        
        for info_file in self.match_info_dir.glob("match_*.json"):
            try:
                with open(info_file, 'r') as f:
                    data = json.load(f)
                    match_info = MatchDatasetInfo(**data)
                    info[match_info.match_id] = match_info
            except Exception:
                # Skip invalid info files
                continue
        
        return info
