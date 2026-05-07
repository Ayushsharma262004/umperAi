"""Pytest configuration and shared fixtures."""

import pytest
import numpy as np
from umpirai.models.data_models import (
    Frame,
    Detection,
    BoundingBox,
    Position3D,
    Vector3D,
)


@pytest.fixture
def sample_frame():
    """Create a sample video frame for testing."""
    return Frame(
        camera_id="test_cam",
        frame_number=1,
        timestamp=1.0,
        image=np.zeros((720, 1280, 3), dtype=np.uint8),
        metadata={}
    )


@pytest.fixture
def sample_detection():
    """Create a sample detection for testing."""
    return Detection(
        class_id=0,
        class_name="ball",
        bounding_box=BoundingBox(x=100, y=100, width=50, height=50),
        confidence=0.95,
        position_3d=Position3D(x=0.0, y=1.0, z=0.0)
    )


@pytest.fixture
def sample_position():
    """Create a sample 3D position for testing."""
    return Position3D(x=1.0, y=2.0, z=3.0)


@pytest.fixture
def sample_vector():
    """Create a sample 3D vector for testing."""
    return Vector3D(vx=1.0, vy=2.0, vz=3.0)


@pytest.fixture
def sample_calibration():
    """Create a sample calibration data dictionary for testing."""
    return {
        "pitch_boundary": [(0, 0), (10, 0), (10, 20), (0, 20)],
        "crease_lines": {
            "bowling": [(0, 5), (10, 5)],
            "batting": [(0, 15), (10, 15)]
        },
        "wide_guidelines": {"left": -1.0, "right": 1.0},
        "stump_positions": {
            "bowling": (5, 5),
            "batting": (5, 15)
        },
        "camera_calibrations": {}
    }
