"""
Calibration Manager for the UmpirAI system.

This module provides functionality for managing pitch calibration including:
- Defining pitch boundaries, crease lines, wide guidelines, and stump positions
- Computing camera calibration (homography matrices)
- Validating calibration data
- Saving and loading calibration configurations to/from JSON files
"""

import json
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import cv2


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Point2D:
    """2D point in image coordinates (pixels)."""
    x: float
    y: float
    
    def __post_init__(self):
        """Validate point values."""
        if not isinstance(self.x, (int, float)):
            raise TypeError("x coordinate must be numeric")
        if not isinstance(self.y, (int, float)):
            raise TypeError("y coordinate must be numeric")
        if not all(np.isfinite(v) for v in [self.x, self.y]):
            raise ValueError("Point coordinates must be finite")
    
    def to_tuple(self) -> Tuple[float, float]:
        """Convert to tuple format."""
        return (self.x, self.y)
    
    def to_list(self) -> List[float]:
        """Convert to list format."""
        return [self.x, self.y]


@dataclass
class CameraIntrinsics:
    """Camera intrinsic parameters."""
    focal_length_x: float
    focal_length_y: float
    principal_point_x: float
    principal_point_y: float
    distortion_coeffs: List[float] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate camera intrinsics."""
        if not all(isinstance(v, (int, float)) for v in [
            self.focal_length_x, self.focal_length_y,
            self.principal_point_x, self.principal_point_y
        ]):
            raise TypeError("Camera intrinsic parameters must be numeric")
        if not isinstance(self.distortion_coeffs, list):
            raise TypeError("distortion_coeffs must be a list")


@dataclass
class CameraCalibration:
    """Camera calibration data including homography and intrinsics."""
    camera_id: str
    homography: np.ndarray  # 3x3 matrix from pitch plane to image plane
    intrinsics: Optional[CameraIntrinsics] = None
    
    def __post_init__(self):
        """Validate camera calibration."""
        if not isinstance(self.camera_id, str) or not self.camera_id:
            raise ValueError("camera_id must be a non-empty string")
        if not isinstance(self.homography, np.ndarray):
            raise TypeError("homography must be a numpy array")
        if self.homography.shape != (3, 3):
            raise ValueError("homography must be a 3x3 matrix")
        if self.intrinsics is not None and not isinstance(self.intrinsics, CameraIntrinsics):
            raise TypeError("intrinsics must be a CameraIntrinsics instance or None")


@dataclass
class CalibrationData:
    """Complete calibration data for a cricket pitch."""
    calibration_name: str
    created_at: str
    pitch_boundary: List[Point2D]  # 4 corners
    crease_lines: Dict[str, List[Point2D]]  # bowling and batting crease (2 points each)
    wide_guidelines: Dict[str, float]  # left and right offsets in meters
    stump_positions: Dict[str, Point2D]  # bowling and batting stump centers
    camera_calibrations: Dict[str, CameraCalibration]
    
    def __post_init__(self):
        """Validate calibration data."""
        if not isinstance(self.calibration_name, str) or not self.calibration_name:
            raise ValueError("calibration_name must be a non-empty string")
        if not isinstance(self.created_at, str):
            raise TypeError("created_at must be a string")
        if not isinstance(self.pitch_boundary, list) or len(self.pitch_boundary) != 4:
            raise ValueError("pitch_boundary must be a list of 4 Point2D objects")
        if not all(isinstance(p, Point2D) for p in self.pitch_boundary):
            raise TypeError("all pitch_boundary points must be Point2D instances")
        if not isinstance(self.crease_lines, dict):
            raise TypeError("crease_lines must be a dictionary")
        if not isinstance(self.wide_guidelines, dict):
            raise TypeError("wide_guidelines must be a dictionary")
        if not isinstance(self.stump_positions, dict):
            raise TypeError("stump_positions must be a dictionary")
        if not isinstance(self.camera_calibrations, dict):
            raise TypeError("camera_calibrations must be a dictionary")


@dataclass
class CalibrationStatus:
    """Status of calibration validation."""
    is_valid: bool
    missing_elements: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate calibration status."""
        if not isinstance(self.is_valid, bool):
            raise TypeError("is_valid must be a boolean")
        if not isinstance(self.missing_elements, list):
            raise TypeError("missing_elements must be a list")
        if not isinstance(self.warnings, list):
            raise TypeError("warnings must be a list")


# ============================================================================
# Calibration Manager
# ============================================================================

class CalibrationManager:
    """
    Manages pitch calibration and camera configuration for the UmpirAI system.
    
    Provides functionality to:
    - Define pitch boundaries, crease lines, wide guidelines, and stump positions
    - Compute homography matrices for camera calibration
    - Validate calibration completeness
    - Save and load calibration data to/from JSON files
    """
    
    def __init__(self):
        """Initialize the calibration manager."""
        self._calibration_mode: bool = False
        self._current_calibration: Optional[CalibrationData] = None
        self._pitch_boundary: List[Point2D] = []
        self._crease_lines: Dict[str, List[Point2D]] = {}
        self._wide_guidelines: Dict[str, float] = {}
        self._stump_positions: Dict[str, Point2D] = {}
        self._camera_calibrations: Dict[str, CameraCalibration] = {}
    
    def start_calibration_mode(self) -> None:
        """
        Start calibration mode and reset current calibration data.
        
        This clears any existing calibration in progress and prepares
        the manager to accept new calibration inputs.
        """
        self._calibration_mode = True
        self._pitch_boundary = []
        self._crease_lines = {}
        self._wide_guidelines = {}
        self._stump_positions = {}
        self._camera_calibrations = {}
        self._current_calibration = None
    
    def stop_calibration_mode(self) -> None:
        """Stop calibration mode."""
        self._calibration_mode = False
    
    def is_calibration_mode(self) -> bool:
        """Check if currently in calibration mode."""
        return self._calibration_mode
    
    def define_pitch_boundary(self, points: List[Point2D]) -> None:
        """
        Define the pitch boundary using 4 corner points.
        
        Args:
            points: List of 4 Point2D objects representing the pitch corners
                   (typically in order: top-left, top-right, bottom-right, bottom-left)
        
        Raises:
            ValueError: If not exactly 4 points are provided
            TypeError: If points are not Point2D instances
        """
        if not isinstance(points, list):
            raise TypeError("points must be a list")
        if len(points) != 4:
            raise ValueError("pitch_boundary requires exactly 4 points")
        if not all(isinstance(p, Point2D) for p in points):
            raise TypeError("all points must be Point2D instances")
        
        self._pitch_boundary = points.copy()
    
    def define_crease_line(self, crease_type: str, points: List[Point2D]) -> None:
        """
        Define a crease line using 2 points.
        
        Args:
            crease_type: Type of crease line ("bowling" or "batting")
            points: List of 2 Point2D objects representing the crease line endpoints
        
        Raises:
            ValueError: If not exactly 2 points are provided or invalid crease_type
            TypeError: If points are not Point2D instances
        """
        if not isinstance(crease_type, str):
            raise TypeError("crease_type must be a string")
        if crease_type not in ["bowling", "batting"]:
            raise ValueError("crease_type must be 'bowling' or 'batting'")
        if not isinstance(points, list):
            raise TypeError("points must be a list")
        if len(points) != 2:
            raise ValueError("crease_line requires exactly 2 points")
        if not all(isinstance(p, Point2D) for p in points):
            raise TypeError("all points must be Point2D instances")
        
        self._crease_lines[crease_type] = points.copy()
    
    def define_wide_guideline(self, left_offset: float, right_offset: float) -> None:
        """
        Define wide guidelines as offsets from pitch center.
        
        Args:
            left_offset: Distance in meters for left wide guideline (typically negative)
            right_offset: Distance in meters for right wide guideline (typically positive)
        
        Raises:
            TypeError: If offsets are not numeric
            ValueError: If offsets are not finite
        """
        if not isinstance(left_offset, (int, float)):
            raise TypeError("left_offset must be numeric")
        if not isinstance(right_offset, (int, float)):
            raise TypeError("right_offset must be numeric")
        if not np.isfinite(left_offset) or not np.isfinite(right_offset):
            raise ValueError("offsets must be finite values")
        
        self._wide_guidelines = {
            "left": float(left_offset),
            "right": float(right_offset)
        }
    
    def define_stump_positions(self, bowling_stump: Point2D, batting_stump: Point2D) -> None:
        """
        Define stump positions for both ends of the pitch.
        
        Args:
            bowling_stump: Center point of the bowling end stumps
            batting_stump: Center point of the batting end stumps
        
        Raises:
            TypeError: If positions are not Point2D instances
        """
        if not isinstance(bowling_stump, Point2D):
            raise TypeError("bowling_stump must be a Point2D instance")
        if not isinstance(batting_stump, Point2D):
            raise TypeError("batting_stump must be a Point2D instance")
        
        self._stump_positions = {
            "bowling": bowling_stump,
            "batting": batting_stump
        }
    
    def compute_homography(
        self,
        camera_id: str,
        image_points: List[Point2D],
        world_points: List[Tuple[float, float]],
        intrinsics: Optional[CameraIntrinsics] = None
    ) -> CameraCalibration:
        """
        Compute homography matrix from pitch plane to image plane.
        
        This uses OpenCV's findHomography to compute the transformation matrix
        that maps world coordinates (on the pitch plane) to image coordinates.
        
        Args:
            camera_id: Identifier for the camera
            image_points: List of points in image coordinates (pixels)
            world_points: Corresponding points in world coordinates (meters on pitch plane)
            intrinsics: Optional camera intrinsic parameters
        
        Returns:
            CameraCalibration object containing the homography matrix
        
        Raises:
            ValueError: If insufficient points or homography computation fails
            TypeError: If input types are incorrect
        """
        if not isinstance(camera_id, str) or not camera_id:
            raise ValueError("camera_id must be a non-empty string")
        if not isinstance(image_points, list) or len(image_points) < 4:
            raise ValueError("at least 4 image points required for homography")
        if not isinstance(world_points, list) or len(world_points) < 4:
            raise ValueError("at least 4 world points required for homography")
        if len(image_points) != len(world_points):
            raise ValueError("image_points and world_points must have same length")
        if not all(isinstance(p, Point2D) for p in image_points):
            raise TypeError("all image_points must be Point2D instances")
        
        # Convert points to numpy arrays for OpenCV
        src_points = np.array([p.to_tuple() for p in image_points], dtype=np.float32)
        dst_points = np.array(world_points, dtype=np.float32)
        
        # Compute homography using RANSAC for robustness
        homography, mask = cv2.findHomography(dst_points, src_points, cv2.RANSAC, 5.0)
        
        if homography is None:
            raise ValueError("Failed to compute homography matrix")
        
        # Create camera calibration object
        camera_calibration = CameraCalibration(
            camera_id=camera_id,
            homography=homography,
            intrinsics=intrinsics
        )
        
        # Store in camera calibrations
        self._camera_calibrations[camera_id] = camera_calibration
        
        return camera_calibration
    
    def validate_calibration(self) -> CalibrationStatus:
        """
        Validate that all required calibration elements are defined.
        
        Checks for:
        - Pitch boundary (4 points)
        - Both crease lines (bowling and batting)
        - Wide guidelines (left and right)
        - Stump positions (bowling and batting)
        - At least one camera calibration
        
        Returns:
            CalibrationStatus object indicating validation result
        """
        missing_elements = []
        warnings = []
        
        # Check pitch boundary
        if len(self._pitch_boundary) != 4:
            missing_elements.append("pitch_boundary (requires 4 points)")
        
        # Check crease lines
        if "bowling" not in self._crease_lines:
            missing_elements.append("bowling crease line")
        elif len(self._crease_lines["bowling"]) != 2:
            warnings.append("bowling crease line should have exactly 2 points")
        
        if "batting" not in self._crease_lines:
            missing_elements.append("batting crease line")
        elif len(self._crease_lines["batting"]) != 2:
            warnings.append("batting crease line should have exactly 2 points")
        
        # Check wide guidelines
        if not self._wide_guidelines:
            missing_elements.append("wide guidelines")
        elif "left" not in self._wide_guidelines or "right" not in self._wide_guidelines:
            missing_elements.append("wide guidelines (both left and right required)")
        
        # Check stump positions
        if not self._stump_positions:
            missing_elements.append("stump positions")
        elif "bowling" not in self._stump_positions or "batting" not in self._stump_positions:
            missing_elements.append("stump positions (both bowling and batting required)")
        
        # Check camera calibrations
        if not self._camera_calibrations:
            missing_elements.append("camera calibration (at least one camera required)")
        
        is_valid = len(missing_elements) == 0
        
        return CalibrationStatus(
            is_valid=is_valid,
            missing_elements=missing_elements,
            warnings=warnings
        )
    
    def save_calibration(self, name: str, filepath: Optional[Path] = None) -> Path:
        """
        Save current calibration to a JSON file.
        
        Args:
            name: Name for this calibration configuration
            filepath: Optional custom file path; if None, uses default location
        
        Returns:
            Path to the saved calibration file
        
        Raises:
            ValueError: If calibration is invalid or name is empty
            IOError: If file cannot be written
        """
        if not isinstance(name, str) or not name:
            raise ValueError("calibration name must be a non-empty string")
        
        # Validate calibration before saving
        status = self.validate_calibration()
        if not status.is_valid:
            raise ValueError(
                f"Cannot save invalid calibration. Missing: {', '.join(status.missing_elements)}"
            )
        
        # Create calibration data object
        calibration_data = CalibrationData(
            calibration_name=name,
            created_at=datetime.utcnow().isoformat(),
            pitch_boundary=self._pitch_boundary,
            crease_lines=self._crease_lines,
            wide_guidelines=self._wide_guidelines,
            stump_positions=self._stump_positions,
            camera_calibrations=self._camera_calibrations
        )
        
        # Determine file path
        if filepath is None:
            filepath = Path(f"calibrations/{name}.json")
        else:
            filepath = Path(filepath)
        
        # Create directory if it doesn't exist
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to JSON-serializable format
        data_dict = self._calibration_to_dict(calibration_data)
        
        # Write to file
        try:
            with open(filepath, 'w') as f:
                json.dump(data_dict, f, indent=2)
        except Exception as e:
            raise IOError(f"Failed to save calibration to {filepath}: {e}")
        
        # Store as current calibration
        self._current_calibration = calibration_data
        
        return filepath
    
    def load_calibration(self, filepath: Path) -> CalibrationData:
        """
        Load calibration from a JSON file.
        
        Args:
            filepath: Path to the calibration JSON file
        
        Returns:
            CalibrationData object with loaded configuration
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
            IOError: If file cannot be read
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Calibration file not found: {filepath}")
        
        # Read file
        try:
            with open(filepath, 'r') as f:
                data_dict = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {filepath}: {e}")
        except Exception as e:
            raise IOError(f"Failed to read calibration from {filepath}: {e}")
        
        # Convert from dictionary to CalibrationData
        calibration_data = self._dict_to_calibration(data_dict)
        
        # Load into current state
        self._pitch_boundary = calibration_data.pitch_boundary
        self._crease_lines = calibration_data.crease_lines
        self._wide_guidelines = calibration_data.wide_guidelines
        self._stump_positions = calibration_data.stump_positions
        self._camera_calibrations = calibration_data.camera_calibrations
        self._current_calibration = calibration_data
        
        return calibration_data
    
    def get_current_calibration(self) -> Optional[CalibrationData]:
        """
        Get the current calibration data.
        
        Returns:
            Current CalibrationData object or None if no calibration loaded
        """
        return self._current_calibration
    
    def get_pitch_boundary(self) -> List[Point2D]:
        """Get the current pitch boundary points."""
        return self._pitch_boundary.copy()
    
    def get_crease_lines(self) -> Dict[str, List[Point2D]]:
        """Get the current crease line definitions."""
        return {k: v.copy() for k, v in self._crease_lines.items()}
    
    def get_wide_guidelines(self) -> Dict[str, float]:
        """Get the current wide guideline offsets."""
        return self._wide_guidelines.copy()
    
    def get_stump_positions(self) -> Dict[str, Point2D]:
        """Get the current stump positions."""
        return self._stump_positions.copy()
    
    def get_camera_calibration(self, camera_id: str) -> Optional[CameraCalibration]:
        """
        Get calibration for a specific camera.
        
        Args:
            camera_id: Identifier for the camera
        
        Returns:
            CameraCalibration object or None if not found
        """
        return self._camera_calibrations.get(camera_id)
    
    def get_all_camera_calibrations(self) -> Dict[str, CameraCalibration]:
        """Get all camera calibrations."""
        return self._camera_calibrations.copy()
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _calibration_to_dict(self, calibration: CalibrationData) -> Dict[str, Any]:
        """Convert CalibrationData to JSON-serializable dictionary."""
        return {
            "calibration_name": calibration.calibration_name,
            "created_at": calibration.created_at,
            "pitch_boundary": [p.to_list() for p in calibration.pitch_boundary],
            "crease_lines": {
                k: [p.to_list() for p in v]
                for k, v in calibration.crease_lines.items()
            },
            "wide_guidelines": calibration.wide_guidelines,
            "stump_positions": {
                k: v.to_list() for k, v in calibration.stump_positions.items()
            },
            "camera_calibrations": {
                cam_id: {
                    "camera_id": cal.camera_id,
                    "homography": cal.homography.tolist(),
                    "intrinsics": {
                        "focal_length_x": cal.intrinsics.focal_length_x,
                        "focal_length_y": cal.intrinsics.focal_length_y,
                        "principal_point_x": cal.intrinsics.principal_point_x,
                        "principal_point_y": cal.intrinsics.principal_point_y,
                        "distortion_coeffs": cal.intrinsics.distortion_coeffs
                    } if cal.intrinsics else None
                }
                for cam_id, cal in calibration.camera_calibrations.items()
            }
        }
    
    def _dict_to_calibration(self, data: Dict[str, Any]) -> CalibrationData:
        """Convert dictionary to CalibrationData object."""
        # Convert pitch boundary
        pitch_boundary = [Point2D(x=p[0], y=p[1]) for p in data["pitch_boundary"]]
        
        # Convert crease lines
        crease_lines = {
            k: [Point2D(x=p[0], y=p[1]) for p in v]
            for k, v in data["crease_lines"].items()
        }
        
        # Convert stump positions
        stump_positions = {
            k: Point2D(x=v[0], y=v[1])
            for k, v in data["stump_positions"].items()
        }
        
        # Convert camera calibrations
        camera_calibrations = {}
        for cam_id, cal_data in data["camera_calibrations"].items():
            intrinsics = None
            if cal_data["intrinsics"]:
                intrinsics = CameraIntrinsics(
                    focal_length_x=cal_data["intrinsics"]["focal_length_x"],
                    focal_length_y=cal_data["intrinsics"]["focal_length_y"],
                    principal_point_x=cal_data["intrinsics"]["principal_point_x"],
                    principal_point_y=cal_data["intrinsics"]["principal_point_y"],
                    distortion_coeffs=cal_data["intrinsics"]["distortion_coeffs"]
                )
            
            camera_calibrations[cam_id] = CameraCalibration(
                camera_id=cal_data["camera_id"],
                homography=np.array(cal_data["homography"]),
                intrinsics=intrinsics
            )
        
        return CalibrationData(
            calibration_name=data["calibration_name"],
            created_at=data["created_at"],
            pitch_boundary=pitch_boundary,
            crease_lines=crease_lines,
            wide_guidelines=data["wide_guidelines"],
            stump_positions=stump_positions,
            camera_calibrations=camera_calibrations
        )
