"""
Decision Review and Override System Module

This module provides functionality for reviewing and overriding system decisions,
including authorization, logging, and feedback collection for model improvement.
"""

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

from umpirai.models.data_models import Decision, VideoReference


class UserRole(Enum):
    """User roles for authorization."""
    OPERATOR = "operator"
    UMPIRE = "umpire"
    ADMIN = "admin"


@dataclass
class User:
    """User information for authorization."""
    user_id: str
    username: str
    role: UserRole
    
    def __post_init__(self):
        """Validate user data."""
        if not isinstance(self.user_id, str) or not self.user_id:
            raise ValueError("user_id must be a non-empty string")
        if not isinstance(self.username, str) or not self.username:
            raise ValueError("username must be a non-empty string")
        if not isinstance(self.role, UserRole):
            raise TypeError("role must be a UserRole enum")
    
    def is_authorized_to_override(self) -> bool:
        """Check if user is authorized to override decisions."""
        return self.role in [UserRole.UMPIRE, UserRole.ADMIN]


@dataclass
class DecisionOverride:
    """Decision override record."""
    override_id: str
    original_decision: Decision
    override_decision_type: str  # Event type as string
    override_confidence: float
    justification: str
    user: User
    timestamp: float
    video_references: List[VideoReference]
    
    def __post_init__(self):
        """Validate override data."""
        if not isinstance(self.override_id, str) or not self.override_id:
            raise ValueError("override_id must be a non-empty string")
        if not isinstance(self.original_decision, Decision):
            raise TypeError("original_decision must be a Decision instance")
        if not isinstance(self.override_decision_type, str) or not self.override_decision_type:
            raise ValueError("override_decision_type must be a non-empty string")
        if not isinstance(self.override_confidence, (int, float)):
            raise TypeError("override_confidence must be numeric")
        if not (0.0 <= self.override_confidence <= 1.0):
            raise ValueError("override_confidence must be in range [0.0, 1.0]")
        if not isinstance(self.justification, str) or not self.justification:
            raise ValueError("justification must be a non-empty string")
        if not isinstance(self.user, User):
            raise TypeError("user must be a User instance")
        if not isinstance(self.timestamp, (int, float)) or self.timestamp < 0:
            raise ValueError("timestamp must be a non-negative number")
        if not isinstance(self.video_references, list):
            raise TypeError("video_references must be a list")
        if not all(isinstance(v, VideoReference) for v in self.video_references):
            raise TypeError("all video_references must be VideoReference instances")


@dataclass
class ReviewInterface:
    """Review interface data for displaying decision and video."""
    decision: Decision
    video_clips: List[Dict[str, Any]]  # List of video clip metadata
    system_reasoning: str
    confidence_breakdown: Dict[str, float]
    
    def __post_init__(self):
        """Validate review interface data."""
        if not isinstance(self.decision, Decision):
            raise TypeError("decision must be a Decision instance")
        if not isinstance(self.video_clips, list):
            raise TypeError("video_clips must be a list")
        if not isinstance(self.system_reasoning, str):
            raise TypeError("system_reasoning must be a string")
        if not isinstance(self.confidence_breakdown, dict):
            raise TypeError("confidence_breakdown must be a dictionary")


class DecisionReviewSystem:
    """
    Decision Review and Override System for UmpirAI.
    
    Provides functionality for authorized users to review system decisions,
    override them when necessary, and collect feedback for model improvement.
    """
    
    def __init__(self, override_log_directory: str = "logs/overrides"):
        """
        Initialize decision review system.
        
        Args:
            override_log_directory: Directory for storing override logs
        """
        self.override_log_directory = Path(override_log_directory)
        self.override_log_directory.mkdir(parents=True, exist_ok=True)
        
        # Log file paths
        self.override_log_path = self.override_log_directory / "overrides.jsonl"
        self.feedback_log_path = self.override_log_directory / "feedback.jsonl"
        
        # In-memory storage for current session
        self._overrides: List[DecisionOverride] = []
        self._feedback_data: List[Dict[str, Any]] = []
        
        # Load existing overrides
        self._load_overrides()
    
    def _load_overrides(self) -> None:
        """Load existing overrides from log file."""
        if self.override_log_path.exists():
            with open(self.override_log_path, 'r') as f:
                for line in f:
                    if line.strip():
                        # Store as dict for now (full reconstruction would require Decision objects)
                        override_dict = json.loads(line)
                        # We'll keep these in memory as dicts for querying
                        # Full DecisionOverride reconstruction can be done on demand
    
    def create_review_interface(
        self,
        decision: Decision,
        video_clips: Optional[List[Dict[str, Any]]] = None
    ) -> ReviewInterface:
        """
        Create a review interface for displaying decision and video.
        
        Args:
            decision: The decision to review
            video_clips: Optional list of video clip metadata
            
        Returns:
            ReviewInterface object containing decision and video data
            
        **Validates: Requirements 20.1**
        """
        if not isinstance(decision, Decision):
            raise TypeError("decision must be a Decision instance")
        
        # Prepare video clips from decision's video references
        if video_clips is None:
            video_clips = [
                {
                    "camera_id": vr.camera_id,
                    "frame_number": vr.frame_number,
                    "timestamp": vr.timestamp,
                    "clip_duration": 5.0,  # 5 seconds around the event
                }
                for vr in decision.video_references
            ]
        
        # Prepare confidence breakdown
        confidence_breakdown = {
            "overall": decision.confidence,
            "detection_quality": self._calculate_detection_confidence(decision),
            "trajectory_quality": self._calculate_trajectory_confidence(decision),
        }
        
        return ReviewInterface(
            decision=decision,
            video_clips=video_clips,
            system_reasoning=decision.reasoning,
            confidence_breakdown=confidence_breakdown,
        )
    
    def _calculate_detection_confidence(self, decision: Decision) -> float:
        """Calculate average detection confidence."""
        if not decision.detections:
            return 0.0
        return sum(d.confidence for d in decision.detections) / len(decision.detections)
    
    def _calculate_trajectory_confidence(self, decision: Decision) -> float:
        """Calculate trajectory confidence based on completeness."""
        trajectory = decision.trajectory
        if trajectory.length() == 0:
            return 0.0
        
        # Higher confidence for longer, more complete trajectories
        # Assume 30 positions is ideal (1 second at 30 FPS)
        completeness = min(1.0, trajectory.length() / 30.0)
        
        # Reduce confidence if trajectory has gaps (would need occlusion info)
        # For now, use completeness as proxy
        return completeness
    
    def override_decision(
        self,
        decision: Decision,
        override_decision_type: str,
        justification: str,
        user: User,
        override_confidence: float = 1.0,
    ) -> DecisionOverride:
        """
        Override a system decision with manual judgment.
        
        Args:
            decision: The original system decision
            override_decision_type: The corrected decision type
            justification: Explanation for the override
            user: User performing the override
            override_confidence: Confidence in the override (default: 1.0)
            
        Returns:
            DecisionOverride object
            
        Raises:
            PermissionError: If user is not authorized to override
            
        **Validates: Requirements 20.2**
        """
        # Check authorization
        if not user.is_authorized_to_override():
            raise PermissionError(
                f"User {user.username} with role {user.role.value} "
                "is not authorized to override decisions"
            )
        
        # Validate inputs
        if not isinstance(decision, Decision):
            raise TypeError("decision must be a Decision instance")
        if not isinstance(override_decision_type, str) or not override_decision_type:
            raise ValueError("override_decision_type must be a non-empty string")
        if not isinstance(justification, str) or not justification:
            raise ValueError("justification must be a non-empty string")
        if not isinstance(user, User):
            raise TypeError("user must be a User instance")
        if not isinstance(override_confidence, (int, float)):
            raise TypeError("override_confidence must be numeric")
        if not (0.0 <= override_confidence <= 1.0):
            raise ValueError("override_confidence must be in range [0.0, 1.0]")
        
        # Create override record
        override = DecisionOverride(
            override_id=f"override_{int(time.time() * 1000)}_{user.user_id}",
            original_decision=decision,
            override_decision_type=override_decision_type,
            override_confidence=override_confidence,
            justification=justification,
            user=user,
            timestamp=time.time(),
            video_references=decision.video_references,
        )
        
        # Log the override
        self._log_override(override)
        
        # Collect feedback
        self._collect_feedback(override)
        
        # Store in memory
        self._overrides.append(override)
        
        return override
    
    def _log_override(self, override: DecisionOverride) -> None:
        """
        Log decision override with justification.
        
        Args:
            override: The override to log
            
        **Validates: Requirements 20.3, 20.4**
        """
        # Create log entry with both system decision and override
        log_entry = {
            "override_id": override.override_id,
            "timestamp": override.timestamp,
            "timestamp_iso": datetime.fromtimestamp(override.timestamp).isoformat(),
            "user_id": override.user.user_id,
            "username": override.user.username,
            "user_role": override.user.role.value,
            "system_decision": {
                "decision_id": override.original_decision.decision_id,
                "event_type": override.original_decision.event_type.value,
                "confidence": override.original_decision.confidence,
                "reasoning": override.original_decision.reasoning,
                "requires_review": override.original_decision.requires_review,
            },
            "manual_override": {
                "decision_type": override.override_decision_type,
                "confidence": override.override_confidence,
                "justification": override.justification,
            },
            "video_references": [
                {
                    "camera_id": vr.camera_id,
                    "frame_number": vr.frame_number,
                    "timestamp": vr.timestamp,
                }
                for vr in override.video_references
            ],
        }
        
        # Write to override log (JSON Lines format)
        with open(self.override_log_path, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def _collect_feedback(self, override: DecisionOverride) -> None:
        """
        Collect override as feedback for model improvement.
        
        Args:
            override: The override to collect as feedback
            
        **Validates: Requirements 20.5**
        """
        # Create feedback entry for model training
        feedback_entry = {
            "feedback_id": f"feedback_{override.override_id}",
            "timestamp": override.timestamp,
            "timestamp_iso": datetime.fromtimestamp(override.timestamp).isoformat(),
            "original_decision": {
                "event_type": override.original_decision.event_type.value,
                "confidence": override.original_decision.confidence,
            },
            "correct_decision": {
                "event_type": override.override_decision_type,
                "confidence": override.override_confidence,
            },
            "justification": override.justification,
            "video_references": [
                {
                    "camera_id": vr.camera_id,
                    "frame_number": vr.frame_number,
                    "timestamp": vr.timestamp,
                }
                for vr in override.video_references
            ],
            "trajectory_data": {
                "start_position": {
                    "x": override.original_decision.trajectory.start_position.x,
                    "y": override.original_decision.trajectory.start_position.y,
                    "z": override.original_decision.trajectory.start_position.z,
                },
                "speed_max": override.original_decision.trajectory.speed_max,
                "speed_avg": override.original_decision.trajectory.speed_avg,
            },
            "detections": [
                {
                    "class_id": d.class_id,
                    "class_name": d.class_name,
                    "confidence": d.confidence,
                }
                for d in override.original_decision.detections
            ],
            "user_role": override.user.role.value,
        }
        
        # Write to feedback log
        with open(self.feedback_log_path, 'a') as f:
            f.write(json.dumps(feedback_entry) + '\n')
        
        # Store in memory
        self._feedback_data.append(feedback_entry)
    
    def get_override_history(
        self,
        start_timestamp: Optional[float] = None,
        end_timestamp: Optional[float] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query override history with filtering.
        
        Args:
            start_timestamp: Start of time range
            end_timestamp: End of time range
            user_id: Filter by specific user
            
        Returns:
            List of override records matching the filter criteria
        """
        results = []
        
        if not self.override_log_path.exists():
            return results
        
        with open(self.override_log_path, 'r') as f:
            for line in f:
                if line.strip():
                    override = json.loads(line)
                    
                    # Apply filters
                    if start_timestamp is not None and override["timestamp"] < start_timestamp:
                        continue
                    if end_timestamp is not None and override["timestamp"] > end_timestamp:
                        continue
                    if user_id is not None and override["user_id"] != user_id:
                        continue
                    
                    results.append(override)
        
        return results
    
    def get_feedback_data(
        self,
        start_timestamp: Optional[float] = None,
        end_timestamp: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get feedback data for model improvement.
        
        Args:
            start_timestamp: Start of time range
            end_timestamp: End of time range
            
        Returns:
            List of feedback records
        """
        results = []
        
        if not self.feedback_log_path.exists():
            return results
        
        with open(self.feedback_log_path, 'r') as f:
            for line in f:
                if line.strip():
                    feedback = json.loads(line)
                    
                    # Apply filters
                    if start_timestamp is not None and feedback["timestamp"] < start_timestamp:
                        continue
                    if end_timestamp is not None and feedback["timestamp"] > end_timestamp:
                        continue
                    
                    results.append(feedback)
        
        return results
    
    def export_feedback_for_training(self, output_path: str) -> str:
        """
        Export feedback data in format suitable for model retraining.
        
        Args:
            output_path: Path for exported feedback file
            
        Returns:
            Path to exported file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Get all feedback data
        feedback_data = self.get_feedback_data()
        
        # Write to output file
        with open(output_file, 'w') as f:
            json.dump(feedback_data, f, indent=2)
        
        return str(output_file)
    
    def get_override_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about decision overrides.
        
        Returns:
            Dictionary containing override statistics
        """
        overrides = self.get_override_history()
        
        if not overrides:
            return {
                "total_overrides": 0,
                "overrides_by_user": {},
                "overrides_by_decision_type": {},
                "average_system_confidence": 0.0,
            }
        
        # Count by user
        user_counts = {}
        for override in overrides:
            username = override["username"]
            user_counts[username] = user_counts.get(username, 0) + 1
        
        # Count by original decision type
        decision_type_counts = {}
        for override in overrides:
            decision_type = override["system_decision"]["event_type"]
            decision_type_counts[decision_type] = decision_type_counts.get(decision_type, 0) + 1
        
        # Calculate average system confidence for overridden decisions
        confidences = [o["system_decision"]["confidence"] for o in overrides]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            "total_overrides": len(overrides),
            "overrides_by_user": user_counts,
            "overrides_by_decision_type": decision_type_counts,
            "average_system_confidence": avg_confidence,
            "log_directory": str(self.override_log_directory),
        }
