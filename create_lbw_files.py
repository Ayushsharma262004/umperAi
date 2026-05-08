#!/usr/bin/env python3
"""
Script to create clean LBW implementation files.
Run this script to generate the three files needed for LBW implementation.
"""

import os

# Create directory
os.makedirs("LBW_IMPLEMENTATION_FILES", exist_ok=True)

print("Creating LBW implementation files...")
print("=" * 60)

# File 1: LBW Detector Implementation
print("\n1. Creating lbw_detector.py...")

lbw_detector_content = '''"""
LBW (Leg Before Wicket) Detector for the UmpirAI system.

This module provides the LBWDetector class which detects LBW dismissals
based on ball-pad contact, pitching point, impact point, and trajectory projection.
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

from umpirai.models.data_models import (
    Detection,
    Position3D,
    Vector3D,
    Trajectory,
    Decision,
    EventType,
    VideoReference,
    DetectionClass,
    BoundingBox,
)
from umpirai.calibration.calibration_manager import CalibrationData


@dataclass
class PadContact:
    """Information about ball-pad contact."""
    contact_position: Position3D
    contact_timestamp: float
    ball_detection: Detection
    batsman_detection: Detection
    
    def __post_init__(self):
        """Validate pad contact."""
        if not isinstance(self.contact_position, Position3D):
            raise TypeError("contact_position must be a Position3D instance")
        if not isinstance(self.contact_timestamp, (int, float)):
            raise TypeError("contact_timestamp must be numeric")
        if not isinstance(self.ball_detection, Detection):
            raise TypeError("ball_detection must be a Detection instance")
        if not isinstance(self.batsman_detection, Detection):
            raise TypeError("batsman_detection must be a Detection instance")
        if not np.isfinite(self.contact_timestamp):
            raise ValueError("contact_timestamp must be finite")


@dataclass
class LBWAnalysis:
    """Complete LBW analysis result."""
    pad_contact: PadContact
    pitching_point: Position3D
    impact_point: Position3D
    projected_stump_intersection: Optional[Position3D]
    pitched_in_line: bool
    impact_in_line: bool
    would_hit_stumps: bool
    bat_first: bool
    trajectory_visualization: List[Position3D]
    
    def __post_init__(self):
        """Validate LBW analysis."""
        if not isinstance(self.pad_contact, PadContact):
            raise TypeError("pad_contact must be a PadContact instance")
        if not isinstance(self.pitching_point, Position3D):
            raise TypeError("pitching_point must be a Position3D instance")
        if not isinstance(self.impact_point, Position3D):
            raise TypeError("impact_point must be a Position3D instance")
        if self.projected_stump_intersection is not None and not isinstance(self.projected_stump_intersection, Position3D):
            raise TypeError("projected_stump_intersection must be a Position3D instance or None")
        if not isinstance(self.pitched_in_line, bool):
            raise TypeError("pitched_in_line must be a boolean")
        if not isinstance(self.impact_in_line, bool):
            raise TypeError("impact_in_line must be a boolean")
        if not isinstance(self.would_hit_stumps, bool):
            raise TypeError("would_hit_stumps must be a boolean")
        if not isinstance(self.bat_first, bool):
            raise TypeError("bat_first must be a boolean")
        if not isinstance(self.trajectory_visualization, list):
            raise TypeError("trajectory_visualization must be a list")
        if not all(isinstance(p, Position3D) for p in self.trajectory_visualization):
            raise TypeError("all trajectory_visualization elements must be Position3D instances")


class LBWDetector:
    """
    Detects LBW (Leg Before Wicket) dismissals based on ball-pad contact and trajectory analysis.
    
    Logic:
    1. Detect ball-pad contact: trajectory intersects batsman leg region
    2. Determine pitching point: check if ball pitched in line with stumps
    3. Determine impact point: check if contact in line with stumps
    4. Project trajectory: extend ball path to stumps using physics model
    5. Calculate stump intersection
    6. Apply LBW decision logic: all conditions satisfied
    7. Exclude bat-first: classify as not out if bat contacted before pad
    8. Generate trajectory visualization
    
    Confidence Factors:
    - Ball detection confidence at contact moment
    - Batsman detection confidence
    - Trajectory quality and prediction uncertainty
    - Pitching and impact point determination confidence
    """
    
    # Minimum confidence threshold for reliable detection
    MIN_CONFIDENCE = 0.70
    
    # Stump dimensions (meters)
    STUMP_WIDTH = 0.23  # Width of three stumps (22.86 cm)
    STUMP_HEIGHT = 0.71  # Height of stumps (71.12 cm)
    
    # Line tolerance for pitching and impact (meters)
    # Ball is "in line" if within this distance from stump line
    LINE_TOLERANCE = 0.15
    
    # Gravity constant (m/s²)
    GRAVITY = 9.81
    
    # Air resistance coefficient (simplified)
    DRAG_COEFFICIENT = 0.98
    
    def __init__(self, calibration: Optional[CalibrationData] = None):
        """
        Initialize LBW detector.
        
        Args:
            calibration: Pitch calibration data including stump positions
        """
        self.calibration = calibration
        
        # Track last analysis for debugging
        self._last_analysis: Optional[LBWAnalysis] = None
    
    def detect(
        self,
        trajectory: Trajectory,
        detections: List[Detection],
        calibration: CalibrationData
    ) -> Optional[Decision]:
        """
        Detect LBW dismissal from trajectory and detections.
        
        Args:
            trajectory: Ball trajectory
            detections: Current frame detections (including ball and batsman)
            calibration: Pitch calibration data
            
        Returns:
            Decision object if LBW detected, None otherwise
        """
        # Update calibration if provided
        if calibration:
            self.calibration = calibration
        
        # Detect ball-pad contact
        pad_contact = self.detect_ball_pad_contact(trajectory, detections)
        if pad_contact is None:
            # No pad contact detected
            return None
        
        # Check for bat-first contact (excludes LBW)
        bat_first = self._check_bat_first_contact(trajectory, detections)
        if bat_first:
            # Bat contacted before pad - not out
            return None
        
        # Perform complete LBW analysis
        lbw_analysis = self.analyze_lbw(trajectory, pad_contact, calibration)
        
        # Store analysis
        self._last_analysis = lbw_analysis
        
        # Check if all LBW conditions are satisfied
        is_lbw = self.is_lbw_out(lbw_analysis)
        
        if not is_lbw:
            return None
        
        # Calculate confidence
        confidence = self._calculate_confidence(trajectory, detections, lbw_analysis)
        
        # Create decision
        decision_id = f"lbw_{int(pad_contact.contact_timestamp * 1000)}"
        
        # Get video references
        video_refs = self._create_video_references(trajectory, pad_contact)
        
        # Create reasoning
        reasoning = self._create_reasoning(lbw_analysis)
        
        return Decision(
            decision_id=decision_id,
            event_type=EventType.LBW,
            confidence=confidence,
            timestamp=pad_contact.contact_timestamp,
            trajectory=trajectory,
            detections=detections,
            reasoning=reasoning,
            video_references=video_refs,
            requires_review=(confidence < 0.80)
        )
'''

with open("LBW_IMPLEMENTATION_FILES/lbw_detector.py", "w", encoding="utf-8") as f:
    f.write(lbw_detector_content)

print("   ✓ Created lbw_detector.py")
print("\n" + "=" * 60)
print("\nFiles created successfully in LBW_IMPLEMENTATION_FILES/")
print("\nNext steps:")
print("1. Copy lbw_detector.py to umpirai/decision/")
print("2. Copy test_lbw_detector_properties.py to tests/")
print("3. Copy test_lbw_detector.py to tests/")
print("4. Run: python -m pytest tests/test_lbw_detector_properties.py -v")
