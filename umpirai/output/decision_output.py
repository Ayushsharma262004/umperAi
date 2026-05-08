"""
Decision Output module for the UmpirAI system.

This module provides the DecisionOutput class which formats and presents
umpiring decisions through multiple output channels: text display, audio
announcement, and visual indicators.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import time
import numpy as np

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from umpirai.models.data_models import Decision, EventType


class OutputFormat(Enum):
    """Output format types."""
    TEXT = "text"
    AUDIO = "audio"
    VISUAL = "visual"
    ALL = "all"


class DecisionPriority(Enum):
    """Decision priority levels."""
    HIGH = 3  # Dismissals
    MEDIUM = 2  # No ball, Wide
    LOW = 1  # Legal delivery


@dataclass
class OutputConfig:
    """Configuration for DecisionOutput."""
    enable_text: bool = True
    enable_audio: bool = True
    enable_visual: bool = True
    audio_rate: int = 150  # words per minute
    audio_volume: float = 1.0  # 0.0 to 1.0
    overlay_duration_ms: int = 3000  # milliseconds
    
    def __post_init__(self):
        """Validate configuration."""
        if not isinstance(self.audio_rate, int) or self.audio_rate <= 0:
            raise ValueError("audio_rate must be a positive integer")
        if not isinstance(self.audio_volume, (int, float)) or not (0.0 <= self.audio_volume <= 1.0):
            raise ValueError("audio_volume must be in range [0.0, 1.0]")
        if not isinstance(self.overlay_duration_ms, int) or self.overlay_duration_ms <= 0:
            raise ValueError("overlay_duration_ms must be a positive integer")


class DecisionOutput:
    """
    Decision output handler for the UmpirAI system.
    
    This class formats and presents umpiring decisions through multiple channels:
    - Text Display: On-screen overlay with event type, confidence, timestamp
    - Audio Announcement: Text-to-speech synthesis for decision type
    - Visual Indicators: Color-coded overlays (green=legal, yellow=wide, red=no ball, blue=dismissal)
    
    Priority System:
    - Dismissal events (BOWLED, CAUGHT, LBW): highest priority
    - No ball / Wide: medium priority
    - Legal delivery: low priority
    
    Latency Tracking:
    - Measures time from decision timestamp to output display
    - Target: <500ms, Maximum: 1000ms
    """
    
    # Color mappings for visual indicators (BGR format for OpenCV)
    COLOR_MAP = {
        EventType.LEGAL: (0, 255, 0),  # Green
        EventType.WIDE: (0, 255, 255),  # Yellow
        EventType.NO_BALL: (0, 0, 255),  # Red
        EventType.BOWLED: (255, 0, 0),  # Blue
        EventType.CAUGHT: (255, 0, 0),  # Blue
        EventType.LBW: (255, 0, 0),  # Blue
        EventType.OVER_COMPLETE: (255, 255, 255),  # White
    }
    
    # Priority mappings
    PRIORITY_MAP = {
        EventType.BOWLED: DecisionPriority.HIGH,
        EventType.CAUGHT: DecisionPriority.HIGH,
        EventType.LBW: DecisionPriority.HIGH,
        EventType.NO_BALL: DecisionPriority.MEDIUM,
        EventType.WIDE: DecisionPriority.MEDIUM,
        EventType.LEGAL: DecisionPriority.LOW,
        EventType.OVER_COMPLETE: DecisionPriority.MEDIUM,
    }
    
    def __init__(self, config: Optional[OutputConfig] = None):
        """
        Initialize DecisionOutput.
        
        Args:
            config: Output configuration
        """
        self.config = config or OutputConfig()
        
        # Initialize text-to-speech engine if available and enabled
        self.tts_engine = None
        if self.config.enable_audio and PYTTSX3_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', self.config.audio_rate)
                self.tts_engine.setProperty('volume', self.config.audio_volume)
            except Exception as e:
                print(f"Warning: Failed to initialize text-to-speech engine: {e}")
                self.tts_engine = None
        
        # Track latency measurements
        self.latency_measurements: List[float] = []
        
        # Track last output for priority management
        self.last_output_time: float = 0.0
        self.last_output_priority: Optional[DecisionPriority] = None
    
    def display_decision(
        self,
        decision: Decision,
        frame: Optional[np.ndarray] = None
    ) -> Optional[np.ndarray]:
        """
        Display decision as on-screen text overlay.
        
        Args:
            decision: Decision to display
            frame: Optional video frame to overlay text on
            
        Returns:
            Frame with text overlay if frame provided, None otherwise
        """
        if not self.config.enable_text:
            return frame
        
        # Calculate latency
        current_time = time.time()
        latency_ms = (current_time - decision.timestamp) * 1000
        self.latency_measurements.append(latency_ms)
        
        # Format decision text
        text = self._format_decision_text(decision, latency_ms)
        
        # If no frame provided, just print to console
        if frame is None or not CV2_AVAILABLE:
            print(text)
            return frame
        
        # Overlay text on frame
        frame_with_overlay = self._overlay_text_on_frame(frame, decision, text)
        
        return frame_with_overlay
    
    def announce_decision(self, decision: Decision) -> None:
        """
        Announce decision using text-to-speech synthesis.
        
        Args:
            decision: Decision to announce
        """
        if not self.config.enable_audio:
            return
        
        if self.tts_engine is None:
            # TTS not available, skip
            return
        
        # Format announcement text
        announcement = self._format_announcement_text(decision)
        
        # Speak announcement (non-blocking)
        try:
            self.tts_engine.say(announcement)
            self.tts_engine.runAndWait()
        except Exception as e:
            print(f"Warning: Failed to announce decision: {e}")
    
    def display_visual_indicator(
        self,
        decision: Decision,
        frame: np.ndarray
    ) -> np.ndarray:
        """
        Display color-coded visual indicator on frame.
        
        Color coding:
        - Green: Legal delivery
        - Yellow: Wide
        - Red: No ball
        - Blue: Dismissal (bowled, caught, LBW)
        - White: Over complete
        
        Args:
            decision: Decision to visualize
            frame: Video frame to overlay indicator on
            
        Returns:
            Frame with visual indicator overlay
        """
        if not self.config.enable_visual or not CV2_AVAILABLE:
            return frame
        
        # Get color for event type
        color = self.COLOR_MAP.get(decision.event_type, (255, 255, 255))
        
        # Draw colored border around frame
        frame_with_indicator = frame.copy()
        border_thickness = 10
        
        # Top border
        cv2.rectangle(
            frame_with_indicator,
            (0, 0),
            (frame.shape[1], border_thickness),
            color,
            -1
        )
        
        # Bottom border
        cv2.rectangle(
            frame_with_indicator,
            (0, frame.shape[0] - border_thickness),
            (frame.shape[1], frame.shape[0]),
            color,
            -1
        )
        
        # Left border
        cv2.rectangle(
            frame_with_indicator,
            (0, 0),
            (border_thickness, frame.shape[0]),
            color,
            -1
        )
        
        # Right border
        cv2.rectangle(
            frame_with_indicator,
            (frame.shape[1] - border_thickness, 0),
            (frame.shape[1], frame.shape[0]),
            color,
            -1
        )
        
        return frame_with_indicator
    
    def output_decision(
        self,
        decision: Decision,
        frame: Optional[np.ndarray] = None,
        output_format: OutputFormat = OutputFormat.ALL
    ) -> Optional[np.ndarray]:
        """
        Output decision using configured format(s).
        
        This method coordinates all output channels and applies priority logic.
        
        Args:
            decision: Decision to output
            frame: Optional video frame for visual output
            output_format: Output format to use
            
        Returns:
            Frame with overlays if frame provided, None otherwise
        """
        # Check priority - only output if priority is high enough
        current_priority = self.get_decision_priority(decision)
        current_time = time.time()
        
        # If last output was recent and higher priority, skip this output
        if (self.last_output_priority is not None and
            current_time - self.last_output_time < 1.0 and
            current_priority.value < self.last_output_priority.value):
            return frame
        
        # Update last output tracking
        self.last_output_time = current_time
        self.last_output_priority = current_priority
        
        # Apply output formats
        result_frame = frame
        
        if output_format in (OutputFormat.TEXT, OutputFormat.ALL):
            result_frame = self.display_decision(decision, result_frame)
        
        if output_format in (OutputFormat.AUDIO, OutputFormat.ALL):
            self.announce_decision(decision)
        
        if output_format in (OutputFormat.VISUAL, OutputFormat.ALL) and result_frame is not None:
            result_frame = self.display_visual_indicator(decision, result_frame)
        
        return result_frame
    
    def get_decision_priority(self, decision: Decision) -> DecisionPriority:
        """
        Get priority level for a decision.
        
        Priority levels:
        - HIGH: Dismissals (bowled, caught, LBW)
        - MEDIUM: No ball, Wide, Over complete
        - LOW: Legal delivery
        
        Args:
            decision: Decision to get priority for
            
        Returns:
            Priority level
        """
        return self.PRIORITY_MAP.get(decision.event_type, DecisionPriority.LOW)
    
    def get_latency_stats(self) -> Dict[str, float]:
        """
        Get latency statistics.
        
        Returns:
            Dictionary with latency statistics (min, max, avg, latest)
        """
        if not self.latency_measurements:
            return {
                "min_ms": 0.0,
                "max_ms": 0.0,
                "avg_ms": 0.0,
                "latest_ms": 0.0,
                "count": 0
            }
        
        return {
            "min_ms": min(self.latency_measurements),
            "max_ms": max(self.latency_measurements),
            "avg_ms": sum(self.latency_measurements) / len(self.latency_measurements),
            "latest_ms": self.latency_measurements[-1],
            "count": len(self.latency_measurements)
        }
    
    def reset_latency_measurements(self) -> None:
        """Reset latency measurements."""
        self.latency_measurements = []
    
    def set_output_format(self, output_format: OutputFormat) -> None:
        """
        Configure output format.
        
        Args:
            output_format: Output format to enable
        """
        if output_format == OutputFormat.TEXT:
            self.config.enable_text = True
            self.config.enable_audio = False
            self.config.enable_visual = False
        elif output_format == OutputFormat.AUDIO:
            self.config.enable_text = False
            self.config.enable_audio = True
            self.config.enable_visual = False
        elif output_format == OutputFormat.VISUAL:
            self.config.enable_text = False
            self.config.enable_audio = False
            self.config.enable_visual = True
        elif output_format == OutputFormat.ALL:
            self.config.enable_text = True
            self.config.enable_audio = True
            self.config.enable_visual = True
    
    def get_output_format(self) -> OutputFormat:
        """
        Get current output format configuration.
        
        Returns:
            Current output format
        """
        if self.config.enable_text and self.config.enable_audio and self.config.enable_visual:
            return OutputFormat.ALL
        elif self.config.enable_text:
            return OutputFormat.TEXT
        elif self.config.enable_audio:
            return OutputFormat.AUDIO
        elif self.config.enable_visual:
            return OutputFormat.VISUAL
        else:
            return OutputFormat.TEXT  # Default
    
    def _format_decision_text(self, decision: Decision, latency_ms: float) -> str:
        """
        Format decision as text string.
        
        Args:
            decision: Decision to format
            latency_ms: Output latency in milliseconds
            
        Returns:
            Formatted text string
        """
        event_name = decision.event_type.value.upper().replace("_", " ")
        confidence_pct = decision.confidence * 100
        
        text = f"{event_name} | Confidence: {confidence_pct:.1f}% | Latency: {latency_ms:.0f}ms"
        
        if decision.requires_review:
            text += " | REVIEW REQUIRED"
        
        return text
    
    def _format_announcement_text(self, decision: Decision) -> str:
        """
        Format decision as announcement text for TTS.
        
        Args:
            decision: Decision to format
            
        Returns:
            Announcement text
        """
        event_name = decision.event_type.value.replace("_", " ")
        
        # Dismissals get special announcement
        if decision.event_type in (EventType.BOWLED, EventType.CAUGHT, EventType.LBW):
            return f"Out! {event_name}"
        elif decision.event_type == EventType.WIDE:
            return "Wide ball"
        elif decision.event_type == EventType.NO_BALL:
            return "No ball"
        elif decision.event_type == EventType.OVER_COMPLETE:
            return "Over complete"
        else:
            return event_name
    
    def _overlay_text_on_frame(
        self,
        frame: np.ndarray,
        decision: Decision,
        text: str
    ) -> np.ndarray:
        """
        Overlay text on video frame.
        
        Args:
            frame: Video frame
            decision: Decision being displayed
            text: Text to overlay
            
        Returns:
            Frame with text overlay
        """
        frame_with_text = frame.copy()
        
        # Get color for event type
        color = self.COLOR_MAP.get(decision.event_type, (255, 255, 255))
        
        # Text properties
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        
        # Get text size
        (text_width, text_height), baseline = cv2.getTextSize(
            text, font, font_scale, thickness
        )
        
        # Position text at top center
        x = (frame.shape[1] - text_width) // 2
        y = 50
        
        # Draw background rectangle
        padding = 10
        cv2.rectangle(
            frame_with_text,
            (x - padding, y - text_height - padding),
            (x + text_width + padding, y + baseline + padding),
            (0, 0, 0),
            -1
        )
        
        # Draw text
        cv2.putText(
            frame_with_text,
            text,
            (x, y),
            font,
            font_scale,
            color,
            thickness,
            cv2.LINE_AA
        )
        
        return frame_with_text
