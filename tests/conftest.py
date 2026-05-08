"""
Pytest configuration and fixtures for UmpirAI tests.
"""

import pytest
import numpy as np
from hypothesis import settings, HealthCheck

# Configure Hypothesis for faster test runs
# Reduce max_examples from default 100 to 20 for faster execution
settings.register_profile("fast", max_examples=20, deadline=None)
settings.register_profile("ci", max_examples=50, deadline=None)
settings.register_profile("thorough", max_examples=100, deadline=None)

# Use fast profile by default
settings.load_profile("fast")


@pytest.fixture
def sample_frame():
    """Create a sample video frame for testing."""
    return np.zeros((720, 1280, 3), dtype=np.uint8)


@pytest.fixture
def sample_calibration():
    """Create sample calibration data for testing."""
    return {
        "pitch_boundary": [(0, 0), (20.12, 0), (20.12, 3.05), (0, 3.05)],
        "crease_lines": {
            "bowling": {"start": (0, 0), "end": (0, 3.05)},
            "popping": {"start": (1.22, 0), "end": (1.22, 3.05)},
        },
        "stump_positions": {
            "bowler": {"off": (0, 1.64), "middle": (0, 1.525), "leg": (0, 1.41)},
            "batsman": {"off": (20.12, 1.64), "middle": (20.12, 1.525), "leg": (20.12, 1.41)},
        },
        "wide_guidelines": {"left": 0.525, "right": 2.525},
        "cameras": {},
    }
