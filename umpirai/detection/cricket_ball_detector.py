"""
Cricket Ball Detector using Computer Vision

This module detects cricket balls (red and white) using color-based
detection and circular shape matching.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class BallCandidate:
    """A potential ball detection"""
    center: Tuple[int, int]
    radius: int
    confidence: float
    color_type: str  # "red" or "white"


class CricketBallDetector:
    """
    Detects cricket balls using color and shape analysis.
    
    Works for both red and white cricket balls by:
    1. Color segmentation (HSV color space)
    2. Circular shape detection (Hough circles)
    3. Size filtering (cricket ball size range)
    4. Motion tracking (temporal consistency)
    """
    
    def __init__(self):
        """Initialize cricket ball detector"""
        # Red ball HSV ranges (cricket ball red)
        self.red_lower1 = np.array([0, 100, 50])
        self.red_upper1 = np.array([10, 255, 255])
        self.red_lower2 = np.array([170, 100, 50])
        self.red_upper2 = np.array([180, 255, 255])
        
        # White ball HSV ranges
        self.white_lower = np.array([0, 0, 180])
        self.white_upper = np.array([180, 30, 255])
        
        # Ball size constraints (in pixels)
        self.min_radius = 5
        self.max_radius = 50
        
        # Previous detection for tracking
        self.prev_detection: Optional[BallCandidate] = None
    
    def detect_red_ball(self, frame: np.ndarray) -> List[BallCandidate]:
        """
        Detect red cricket ball
        
        Args:
            frame: BGR image
            
        Returns:
            List of ball candidates
        """
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Create mask for red (two ranges due to hue wrap-around)
        mask1 = cv2.inRange(hsv, self.red_lower1, self.red_upper1)
        mask2 = cv2.inRange(hsv, self.red_lower2, self.red_upper2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        
        # Morphological operations to reduce noise
        kernel = np.ones((3, 3), np.uint8)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
        
        # Detect circles
        candidates = self._detect_circles(red_mask, "red")
        
        return candidates
    
    def detect_white_ball(self, frame: np.ndarray) -> List[BallCandidate]:
        """
        Detect white cricket ball
        
        Args:
            frame: BGR image
            
        Returns:
            List of ball candidates
        """
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Create mask for white
        white_mask = cv2.inRange(hsv, self.white_lower, self.white_upper)
        
        # Morphological operations
        kernel = np.ones((3, 3), np.uint8)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
        
        # Detect circles
        candidates = self._detect_circles(white_mask, "white")
        
        return candidates
    
    def _detect_circles(self, mask: np.ndarray, color_type: str) -> List[BallCandidate]:
        """
        Detect circular shapes in mask
        
        Args:
            mask: Binary mask
            color_type: "red" or "white"
            
        Returns:
            List of ball candidates
        """
        candidates = []
        
        # Hough Circle Transform
        circles = cv2.HoughCircles(
            mask,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=50,
            param1=50,
            param2=15,
            minRadius=self.min_radius,
            maxRadius=self.max_radius
        )
        
        if circles is not None:
            circles = np.uint16(np.around(circles))
            
            for circle in circles[0, :]:
                x, y, r = circle
                
                # Calculate confidence based on circularity and size
                confidence = self._calculate_confidence(mask, (x, y), r)
                
                candidate = BallCandidate(
                    center=(int(x), int(y)),
                    radius=int(r),
                    confidence=confidence,
                    color_type=color_type
                )
                
                candidates.append(candidate)
        
        return candidates
    
    def _calculate_confidence(
        self,
        mask: np.ndarray,
        center: Tuple[int, int],
        radius: int
    ) -> float:
        """
        Calculate detection confidence
        
        Args:
            mask: Binary mask
            center: Circle center
            radius: Circle radius
            
        Returns:
            Confidence score (0-1)
        """
        x, y = center
        h, w = mask.shape
        
        # Check bounds
        if x - radius < 0 or x + radius >= w or y - radius < 0 or y + radius >= h:
            return 0.3
        
        # Extract region
        roi = mask[y-radius:y+radius, x-radius:x+radius]
        
        if roi.size == 0:
            return 0.3
        
        # Calculate fill ratio
        total_pixels = roi.size
        white_pixels = np.sum(roi > 0)
        fill_ratio = white_pixels / total_pixels
        
        # Ideal circle should have ~78% fill ratio (π/4)
        ideal_ratio = 0.785
        confidence = 1.0 - abs(fill_ratio - ideal_ratio)
        
        # Boost confidence if consistent with previous detection
        if self.prev_detection is not None:
            prev_x, prev_y = self.prev_detection.center
            distance = np.sqrt((x - prev_x)**2 + (y - prev_y)**2)
            
            # If close to previous detection, boost confidence
            if distance < 100:  # Within 100 pixels
                confidence = min(1.0, confidence + 0.2)
        
        return max(0.3, min(1.0, confidence))
    
    def detect(self, frame: np.ndarray) -> List[BallCandidate]:
        """
        Detect cricket ball (red or white)
        
        Args:
            frame: BGR image
            
        Returns:
            List of ball candidates sorted by confidence
        """
        # Detect both red and white balls
        red_candidates = self.detect_red_ball(frame)
        white_candidates = self.detect_white_ball(frame)
        
        # Combine and sort by confidence
        all_candidates = red_candidates + white_candidates
        all_candidates.sort(key=lambda c: c.confidence, reverse=True)
        
        # Update previous detection
        if all_candidates:
            self.prev_detection = all_candidates[0]
        
        return all_candidates
    
    def reset(self):
        """Reset tracking state"""
        self.prev_detection = None
