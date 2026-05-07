"""
Unit tests for CalibrationManager.

Tests cover:
- Calibration data storage and retrieval
- Pitch boundary, crease line, wide guideline, and stump position definition
- Homography matrix computation
- Calibration validation logic
- Save/load calibration to/from JSON files
"""

import pytest
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from umpirai.calibration import (
    CalibrationManager,
    Point2D,
    CameraIntrinsics,
    CameraCalibration,
    CalibrationData,
    CalibrationStatus
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def calibration_manager():
    """Create a fresh CalibrationManager instance."""
    return CalibrationManager()


@pytest.fixture
def sample_pitch_boundary():
    """Sample pitch boundary points (4 corners)."""
    return [
        Point2D(x=100.0, y=100.0),  # top-left
        Point2D(x=500.0, y=100.0),  # top-right
        Point2D(x=500.0, y=400.0),  # bottom-right
        Point2D(x=100.0, y=400.0)   # bottom-left
    ]


@pytest.fixture
def sample_crease_lines():
    """Sample crease line points."""
    return {
        "bowling": [Point2D(x=150.0, y=200.0), Point2D(x=450.0, y=200.0)],
        "batting": [Point2D(x=150.0, y=300.0), Point2D(x=450.0, y=300.0)]
    }


@pytest.fixture
def sample_stump_positions():
    """Sample stump positions."""
    return {
        "bowling": Point2D(x=300.0, y=200.0),
        "batting": Point2D(x=300.0, y=300.0)
    }


@pytest.fixture
def sample_wide_guidelines():
    """Sample wide guideline offsets."""
    return {"left": -1.0, "right": 1.0}


@pytest.fixture
def sample_camera_intrinsics():
    """Sample camera intrinsic parameters."""
    return CameraIntrinsics(
        focal_length_x=800.0,
        focal_length_y=800.0,
        principal_point_x=640.0,
        principal_point_y=360.0,
        distortion_coeffs=[0.1, -0.05, 0.0, 0.0, 0.0]
    )


@pytest.fixture
def complete_calibration(
    calibration_manager,
    sample_pitch_boundary,
    sample_crease_lines,
    sample_wide_guidelines,
    sample_stump_positions
):
    """Create a complete calibration setup."""
    manager = calibration_manager
    manager.start_calibration_mode()
    manager.define_pitch_boundary(sample_pitch_boundary)
    manager.define_crease_line("bowling", sample_crease_lines["bowling"])
    manager.define_crease_line("batting", sample_crease_lines["batting"])
    manager.define_wide_guideline(
        sample_wide_guidelines["left"],
        sample_wide_guidelines["right"]
    )
    manager.define_stump_positions(
        sample_stump_positions["bowling"],
        sample_stump_positions["batting"]
    )
    
    # Add a camera calibration
    image_points = sample_pitch_boundary
    world_points = [(0, 0), (20, 0), (20, 10), (0, 10)]
    manager.compute_homography("cam1", image_points, world_points)
    
    return manager


# ============================================================================
# Test Point2D
# ============================================================================

class TestPoint2D:
    """Tests for Point2D data model."""
    
    def test_point2d_creation(self):
        """Test creating a valid Point2D."""
        point = Point2D(x=10.5, y=20.3)
        assert point.x == 10.5
        assert point.y == 20.3
    
    def test_point2d_to_tuple(self):
        """Test converting Point2D to tuple."""
        point = Point2D(x=10.5, y=20.3)
        assert point.to_tuple() == (10.5, 20.3)
    
    def test_point2d_to_list(self):
        """Test converting Point2D to list."""
        point = Point2D(x=10.5, y=20.3)
        assert point.to_list() == [10.5, 20.3]
    
    def test_point2d_invalid_type(self):
        """Test Point2D with invalid coordinate types."""
        with pytest.raises(TypeError):
            Point2D(x="invalid", y=20.0)
    
    def test_point2d_infinite_values(self):
        """Test Point2D with infinite values."""
        with pytest.raises(ValueError):
            Point2D(x=float('inf'), y=20.0)


# ============================================================================
# Test CameraIntrinsics
# ============================================================================

class TestCameraIntrinsics:
    """Tests for CameraIntrinsics data model."""
    
    def test_camera_intrinsics_creation(self):
        """Test creating valid CameraIntrinsics."""
        intrinsics = CameraIntrinsics(
            focal_length_x=800.0,
            focal_length_y=800.0,
            principal_point_x=640.0,
            principal_point_y=360.0,
            distortion_coeffs=[0.1, -0.05]
        )
        assert intrinsics.focal_length_x == 800.0
        assert len(intrinsics.distortion_coeffs) == 2
    
    def test_camera_intrinsics_invalid_type(self):
        """Test CameraIntrinsics with invalid types."""
        with pytest.raises(TypeError):
            CameraIntrinsics(
                focal_length_x="invalid",
                focal_length_y=800.0,
                principal_point_x=640.0,
                principal_point_y=360.0
            )


# ============================================================================
# Test CalibrationManager - Basic Operations
# ============================================================================

class TestCalibrationManagerBasics:
    """Tests for basic CalibrationManager operations."""
    
    def test_initialization(self, calibration_manager):
        """Test CalibrationManager initialization."""
        assert not calibration_manager.is_calibration_mode()
        assert calibration_manager.get_current_calibration() is None
    
    def test_start_calibration_mode(self, calibration_manager):
        """Test starting calibration mode."""
        calibration_manager.start_calibration_mode()
        assert calibration_manager.is_calibration_mode()
    
    def test_stop_calibration_mode(self, calibration_manager):
        """Test stopping calibration mode."""
        calibration_manager.start_calibration_mode()
        calibration_manager.stop_calibration_mode()
        assert not calibration_manager.is_calibration_mode()
    
    def test_start_calibration_clears_data(self, calibration_manager, sample_pitch_boundary):
        """Test that starting calibration mode clears existing data."""
        calibration_manager.start_calibration_mode()
        calibration_manager.define_pitch_boundary(sample_pitch_boundary)
        
        # Start again - should clear previous data
        calibration_manager.start_calibration_mode()
        assert len(calibration_manager.get_pitch_boundary()) == 0


# ============================================================================
# Test Pitch Boundary Definition
# ============================================================================

class TestPitchBoundary:
    """Tests for pitch boundary definition."""
    
    def test_define_pitch_boundary_valid(self, calibration_manager, sample_pitch_boundary):
        """Test defining a valid pitch boundary."""
        calibration_manager.define_pitch_boundary(sample_pitch_boundary)
        boundary = calibration_manager.get_pitch_boundary()
        assert len(boundary) == 4
        assert boundary[0].x == 100.0
        assert boundary[0].y == 100.0
    
    def test_define_pitch_boundary_wrong_count(self, calibration_manager):
        """Test defining pitch boundary with wrong number of points."""
        with pytest.raises(ValueError, match="exactly 4 points"):
            calibration_manager.define_pitch_boundary([
                Point2D(x=0, y=0),
                Point2D(x=1, y=1)
            ])
    
    def test_define_pitch_boundary_invalid_type(self, calibration_manager):
        """Test defining pitch boundary with invalid point types."""
        with pytest.raises(TypeError, match="Point2D"):
            calibration_manager.define_pitch_boundary([
                (0, 0), (1, 1), (2, 2), (3, 3)
            ])
    
    def test_define_pitch_boundary_not_list(self, calibration_manager):
        """Test defining pitch boundary with non-list input."""
        with pytest.raises(TypeError, match="must be a list"):
            calibration_manager.define_pitch_boundary("invalid")


# ============================================================================
# Test Crease Line Definition
# ============================================================================

class TestCreaseLine:
    """Tests for crease line definition."""
    
    def test_define_crease_line_bowling(self, calibration_manager, sample_crease_lines):
        """Test defining bowling crease line."""
        calibration_manager.define_crease_line("bowling", sample_crease_lines["bowling"])
        crease_lines = calibration_manager.get_crease_lines()
        assert "bowling" in crease_lines
        assert len(crease_lines["bowling"]) == 2
    
    def test_define_crease_line_batting(self, calibration_manager, sample_crease_lines):
        """Test defining batting crease line."""
        calibration_manager.define_crease_line("batting", sample_crease_lines["batting"])
        crease_lines = calibration_manager.get_crease_lines()
        assert "batting" in crease_lines
        assert len(crease_lines["batting"]) == 2
    
    def test_define_crease_line_invalid_type(self, calibration_manager):
        """Test defining crease line with invalid type."""
        with pytest.raises(ValueError, match="bowling.*batting"):
            calibration_manager.define_crease_line("invalid", [
                Point2D(x=0, y=0),
                Point2D(x=1, y=1)
            ])
    
    def test_define_crease_line_wrong_count(self, calibration_manager):
        """Test defining crease line with wrong number of points."""
        with pytest.raises(ValueError, match="exactly 2 points"):
            calibration_manager.define_crease_line("bowling", [
                Point2D(x=0, y=0)
            ])
    
    def test_define_crease_line_invalid_points(self, calibration_manager):
        """Test defining crease line with invalid point types."""
        with pytest.raises(TypeError, match="Point2D"):
            calibration_manager.define_crease_line("bowling", [(0, 0), (1, 1)])


# ============================================================================
# Test Wide Guideline Definition
# ============================================================================

class TestWideGuideline:
    """Tests for wide guideline definition."""
    
    def test_define_wide_guideline_valid(self, calibration_manager):
        """Test defining valid wide guidelines."""
        calibration_manager.define_wide_guideline(-1.0, 1.0)
        guidelines = calibration_manager.get_wide_guidelines()
        assert guidelines["left"] == -1.0
        assert guidelines["right"] == 1.0
    
    def test_define_wide_guideline_asymmetric(self, calibration_manager):
        """Test defining asymmetric wide guidelines."""
        calibration_manager.define_wide_guideline(-1.2, 0.8)
        guidelines = calibration_manager.get_wide_guidelines()
        assert guidelines["left"] == -1.2
        assert guidelines["right"] == 0.8
    
    def test_define_wide_guideline_invalid_type(self, calibration_manager):
        """Test defining wide guidelines with invalid types."""
        with pytest.raises(TypeError, match="numeric"):
            calibration_manager.define_wide_guideline("invalid", 1.0)
    
    def test_define_wide_guideline_infinite(self, calibration_manager):
        """Test defining wide guidelines with infinite values."""
        with pytest.raises(ValueError, match="finite"):
            calibration_manager.define_wide_guideline(float('inf'), 1.0)


# ============================================================================
# Test Stump Position Definition
# ============================================================================

class TestStumpPositions:
    """Tests for stump position definition."""
    
    def test_define_stump_positions_valid(self, calibration_manager, sample_stump_positions):
        """Test defining valid stump positions."""
        calibration_manager.define_stump_positions(
            sample_stump_positions["bowling"],
            sample_stump_positions["batting"]
        )
        positions = calibration_manager.get_stump_positions()
        assert "bowling" in positions
        assert "batting" in positions
        assert positions["bowling"].x == 300.0
    
    def test_define_stump_positions_invalid_type(self, calibration_manager):
        """Test defining stump positions with invalid types."""
        with pytest.raises(TypeError, match="Point2D"):
            calibration_manager.define_stump_positions(
                (300.0, 200.0),
                Point2D(x=300.0, y=300.0)
            )


# ============================================================================
# Test Homography Computation
# ============================================================================

class TestHomographyComputation:
    """Tests for homography matrix computation."""
    
    def test_compute_homography_valid(self, calibration_manager, sample_pitch_boundary):
        """Test computing homography with valid points."""
        image_points = sample_pitch_boundary
        world_points = [(0, 0), (20, 0), (20, 10), (0, 10)]
        
        calibration = calibration_manager.compute_homography(
            "cam1", image_points, world_points
        )
        
        assert calibration.camera_id == "cam1"
        assert calibration.homography.shape == (3, 3)
        assert isinstance(calibration.homography, np.ndarray)
    
    def test_compute_homography_with_intrinsics(
        self, calibration_manager, sample_pitch_boundary, sample_camera_intrinsics
    ):
        """Test computing homography with camera intrinsics."""
        image_points = sample_pitch_boundary
        world_points = [(0, 0), (20, 0), (20, 10), (0, 10)]
        
        calibration = calibration_manager.compute_homography(
            "cam1", image_points, world_points, sample_camera_intrinsics
        )
        
        assert calibration.intrinsics is not None
        assert calibration.intrinsics.focal_length_x == 800.0
    
    def test_compute_homography_insufficient_points(self, calibration_manager):
        """Test computing homography with insufficient points."""
        image_points = [Point2D(x=0, y=0), Point2D(x=1, y=1)]
        world_points = [(0, 0), (1, 1)]
        
        with pytest.raises(ValueError, match="at least 4"):
            calibration_manager.compute_homography("cam1", image_points, world_points)
    
    def test_compute_homography_mismatched_lengths(self, calibration_manager, sample_pitch_boundary):
        """Test computing homography with mismatched point counts."""
        image_points = sample_pitch_boundary  # 4 points
        world_points = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)]  # 5 points
        
        with pytest.raises(ValueError, match="same length"):
            calibration_manager.compute_homography("cam1", image_points, world_points)
    
    def test_compute_homography_empty_camera_id(self, calibration_manager, sample_pitch_boundary):
        """Test computing homography with empty camera ID."""
        image_points = sample_pitch_boundary
        world_points = [(0, 0), (20, 0), (20, 10), (0, 10)]
        
        with pytest.raises(ValueError, match="non-empty string"):
            calibration_manager.compute_homography("", image_points, world_points)
    
    def test_get_camera_calibration(self, calibration_manager, sample_pitch_boundary):
        """Test retrieving camera calibration."""
        image_points = sample_pitch_boundary
        world_points = [(0, 0), (20, 0), (20, 10), (0, 10)]
        
        calibration_manager.compute_homography("cam1", image_points, world_points)
        
        retrieved = calibration_manager.get_camera_calibration("cam1")
        assert retrieved is not None
        assert retrieved.camera_id == "cam1"
    
    def test_get_camera_calibration_not_found(self, calibration_manager):
        """Test retrieving non-existent camera calibration."""
        retrieved = calibration_manager.get_camera_calibration("nonexistent")
        assert retrieved is None


# ============================================================================
# Test Calibration Validation
# ============================================================================

class TestCalibrationValidation:
    """Tests for calibration validation logic."""
    
    def test_validate_complete_calibration(self, complete_calibration):
        """Test validating a complete calibration."""
        status = complete_calibration.validate_calibration()
        assert status.is_valid
        assert len(status.missing_elements) == 0
    
    def test_validate_missing_pitch_boundary(self, calibration_manager):
        """Test validation with missing pitch boundary."""
        calibration_manager.start_calibration_mode()
        status = calibration_manager.validate_calibration()
        
        assert not status.is_valid
        assert any("pitch_boundary" in elem for elem in status.missing_elements)
    
    def test_validate_missing_crease_lines(
        self, calibration_manager, sample_pitch_boundary
    ):
        """Test validation with missing crease lines."""
        calibration_manager.start_calibration_mode()
        calibration_manager.define_pitch_boundary(sample_pitch_boundary)
        
        status = calibration_manager.validate_calibration()
        assert not status.is_valid
        assert any("bowling crease" in elem for elem in status.missing_elements)
        assert any("batting crease" in elem for elem in status.missing_elements)
    
    def test_validate_missing_wide_guidelines(
        self, calibration_manager, sample_pitch_boundary, sample_crease_lines
    ):
        """Test validation with missing wide guidelines."""
        calibration_manager.start_calibration_mode()
        calibration_manager.define_pitch_boundary(sample_pitch_boundary)
        calibration_manager.define_crease_line("bowling", sample_crease_lines["bowling"])
        calibration_manager.define_crease_line("batting", sample_crease_lines["batting"])
        
        status = calibration_manager.validate_calibration()
        assert not status.is_valid
        assert any("wide guidelines" in elem for elem in status.missing_elements)
    
    def test_validate_missing_stump_positions(
        self, calibration_manager, sample_pitch_boundary, sample_crease_lines,
        sample_wide_guidelines
    ):
        """Test validation with missing stump positions."""
        calibration_manager.start_calibration_mode()
        calibration_manager.define_pitch_boundary(sample_pitch_boundary)
        calibration_manager.define_crease_line("bowling", sample_crease_lines["bowling"])
        calibration_manager.define_crease_line("batting", sample_crease_lines["batting"])
        calibration_manager.define_wide_guideline(
            sample_wide_guidelines["left"],
            sample_wide_guidelines["right"]
        )
        
        status = calibration_manager.validate_calibration()
        assert not status.is_valid
        assert any("stump positions" in elem for elem in status.missing_elements)
    
    def test_validate_missing_camera_calibration(
        self, calibration_manager, sample_pitch_boundary, sample_crease_lines,
        sample_wide_guidelines, sample_stump_positions
    ):
        """Test validation with missing camera calibration."""
        calibration_manager.start_calibration_mode()
        calibration_manager.define_pitch_boundary(sample_pitch_boundary)
        calibration_manager.define_crease_line("bowling", sample_crease_lines["bowling"])
        calibration_manager.define_crease_line("batting", sample_crease_lines["batting"])
        calibration_manager.define_wide_guideline(
            sample_wide_guidelines["left"],
            sample_wide_guidelines["right"]
        )
        calibration_manager.define_stump_positions(
            sample_stump_positions["bowling"],
            sample_stump_positions["batting"]
        )
        
        status = calibration_manager.validate_calibration()
        assert not status.is_valid
        assert any("camera calibration" in elem for elem in status.missing_elements)


# ============================================================================
# Test Save/Load Calibration
# ============================================================================

class TestSaveLoadCalibration:
    """Tests for saving and loading calibration to/from JSON files."""
    
    def test_save_calibration_valid(self, complete_calibration, tmp_path):
        """Test saving a valid calibration."""
        filepath = tmp_path / "test_calibration.json"
        saved_path = complete_calibration.save_calibration("test_cal", filepath)
        
        assert saved_path.exists()
        assert saved_path == filepath
    
    def test_save_calibration_creates_directory(self, complete_calibration, tmp_path):
        """Test that save creates parent directories."""
        filepath = tmp_path / "subdir" / "test_calibration.json"
        saved_path = complete_calibration.save_calibration("test_cal", filepath)
        
        assert saved_path.exists()
        assert saved_path.parent.exists()
    
    def test_save_calibration_invalid(self, calibration_manager, tmp_path):
        """Test saving an invalid calibration."""
        calibration_manager.start_calibration_mode()
        filepath = tmp_path / "test_calibration.json"
        
        with pytest.raises(ValueError, match="invalid calibration"):
            calibration_manager.save_calibration("test_cal", filepath)
    
    def test_save_calibration_empty_name(self, complete_calibration, tmp_path):
        """Test saving with empty name."""
        filepath = tmp_path / "test_calibration.json"
        
        with pytest.raises(ValueError, match="non-empty string"):
            complete_calibration.save_calibration("", filepath)
    
    def test_save_calibration_json_format(self, complete_calibration, tmp_path):
        """Test that saved calibration is valid JSON."""
        filepath = tmp_path / "test_calibration.json"
        complete_calibration.save_calibration("test_cal", filepath)
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        assert data["calibration_name"] == "test_cal"
        assert "created_at" in data
        assert "pitch_boundary" in data
        assert "crease_lines" in data
        assert "wide_guidelines" in data
        assert "stump_positions" in data
        assert "camera_calibrations" in data
    
    def test_load_calibration_valid(self, complete_calibration, tmp_path):
        """Test loading a valid calibration."""
        filepath = tmp_path / "test_calibration.json"
        complete_calibration.save_calibration("test_cal", filepath)
        
        # Create new manager and load
        new_manager = CalibrationManager()
        loaded_data = new_manager.load_calibration(filepath)
        
        assert loaded_data.calibration_name == "test_cal"
        assert len(loaded_data.pitch_boundary) == 4
        assert "bowling" in loaded_data.crease_lines
        assert "batting" in loaded_data.crease_lines
    
    def test_load_calibration_file_not_found(self, calibration_manager, tmp_path):
        """Test loading from non-existent file."""
        filepath = tmp_path / "nonexistent.json"
        
        with pytest.raises(FileNotFoundError):
            calibration_manager.load_calibration(filepath)
    
    def test_load_calibration_invalid_json(self, calibration_manager, tmp_path):
        """Test loading invalid JSON file."""
        filepath = tmp_path / "invalid.json"
        with open(filepath, 'w') as f:
            f.write("invalid json content {")
        
        with pytest.raises(ValueError, match="Invalid JSON"):
            calibration_manager.load_calibration(filepath)
    
    def test_save_load_roundtrip(self, complete_calibration, tmp_path):
        """Test that save/load preserves all data."""
        filepath = tmp_path / "test_calibration.json"
        complete_calibration.save_calibration("test_cal", filepath)
        
        # Load into new manager
        new_manager = CalibrationManager()
        loaded_data = new_manager.load_calibration(filepath)
        
        # Verify all data preserved
        assert loaded_data.calibration_name == "test_cal"
        assert len(loaded_data.pitch_boundary) == 4
        assert loaded_data.pitch_boundary[0].x == 100.0
        assert loaded_data.wide_guidelines["left"] == -1.0
        assert loaded_data.wide_guidelines["right"] == 1.0
        assert "cam1" in loaded_data.camera_calibrations
        
        # Verify homography matrix preserved
        cam_cal = loaded_data.camera_calibrations["cam1"]
        assert cam_cal.homography.shape == (3, 3)
    
    def test_get_current_calibration_after_load(self, complete_calibration, tmp_path):
        """Test that current calibration is set after loading."""
        filepath = tmp_path / "test_calibration.json"
        complete_calibration.save_calibration("test_cal", filepath)
        
        new_manager = CalibrationManager()
        new_manager.load_calibration(filepath)
        
        current = new_manager.get_current_calibration()
        assert current is not None
        assert current.calibration_name == "test_cal"


# ============================================================================
# Test Getter Methods
# ============================================================================

class TestGetterMethods:
    """Tests for calibration data getter methods."""
    
    def test_get_all_camera_calibrations(self, complete_calibration):
        """Test getting all camera calibrations."""
        calibrations = complete_calibration.get_all_camera_calibrations()
        assert "cam1" in calibrations
        assert len(calibrations) == 1
    
    def test_getters_return_copies(self, complete_calibration):
        """Test that getters return copies, not references."""
        boundary1 = complete_calibration.get_pitch_boundary()
        boundary2 = complete_calibration.get_pitch_boundary()
        
        # Modify one copy
        boundary1[0] = Point2D(x=999, y=999)
        
        # Original should be unchanged
        boundary2 = complete_calibration.get_pitch_boundary()
        assert boundary2[0].x == 100.0


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_multiple_camera_calibrations(self, calibration_manager, sample_pitch_boundary):
        """Test adding multiple camera calibrations."""
        image_points = sample_pitch_boundary
        world_points = [(0, 0), (20, 0), (20, 10), (0, 10)]
        
        calibration_manager.compute_homography("cam1", image_points, world_points)
        calibration_manager.compute_homography("cam2", image_points, world_points)
        
        calibrations = calibration_manager.get_all_camera_calibrations()
        assert len(calibrations) == 2
        assert "cam1" in calibrations
        assert "cam2" in calibrations
    
    def test_overwrite_camera_calibration(self, calibration_manager, sample_pitch_boundary):
        """Test overwriting an existing camera calibration."""
        image_points = sample_pitch_boundary
        world_points = [(0, 0), (20, 0), (20, 10), (0, 10)]
        
        cal1 = calibration_manager.compute_homography("cam1", image_points, world_points)
        cal2 = calibration_manager.compute_homography("cam1", image_points, world_points)
        
        # Should have only one calibration for cam1
        calibrations = calibration_manager.get_all_camera_calibrations()
        assert len(calibrations) == 1
    
    def test_negative_wide_guidelines(self, calibration_manager):
        """Test wide guidelines with both negative values."""
        calibration_manager.define_wide_guideline(-2.0, -0.5)
        guidelines = calibration_manager.get_wide_guidelines()
        assert guidelines["left"] == -2.0
        assert guidelines["right"] == -0.5
    
    def test_zero_wide_guidelines(self, calibration_manager):
        """Test wide guidelines with zero values."""
        calibration_manager.define_wide_guideline(0.0, 0.0)
        guidelines = calibration_manager.get_wide_guidelines()
        assert guidelines["left"] == 0.0
        assert guidelines["right"] == 0.0
