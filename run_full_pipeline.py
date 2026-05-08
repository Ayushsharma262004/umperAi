"""
Full UmpirAI Pipeline with YOLOv8 Integration

This script runs the complete UmpirAI system with YOLOv8 object detection
on real cricket videos, showing real-time decisions and analysis.
"""

import sys
import cv2
import time
import yaml
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Import UmpirAI components
from umpirai.models.data_models import Frame, BoundingBox, Detection, Position3D
from umpirai.detection.hybrid_detector import HybridDetector
from umpirai.tracking.ball_tracker import BallTracker, BallDetection
from umpirai.decision.decision_engine import DecisionEngine, DecisionEngineConfig
from umpirai.calibration.calibration_manager import CalibrationManager, CalibrationData


class VideoUmpireProcessor:
    """Process cricket videos with full UmpirAI pipeline"""
    
    def __init__(self, config_path: str = "config_test.yaml"):
        """Initialize processor with configuration"""
        print("🏏 Initializing UmpirAI Full Pipeline")
        print("="*70)
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        print(f"✅ Configuration loaded from {config_path}")
        
        # Initialize object detector with YOLOv8
        model_name = self.config['detection']['model']
        print(f"📦 Loading Hybrid Detector (YOLOv8 + Cricket Ball Detection)")
        
        try:
            self.detector = HybridDetector(
                model_path=f"{model_name}.pt",
                device="cpu"  # Use CPU for now
            )
            print(f"✅ Hybrid detector initialized")
            print(f"   YOLOv8: Player detection")
            print(f"   Cricket Ball Detector: Red/White ball detection")
            print(f"   Device: {self.detector.device}")
        except Exception as e:
            print(f"❌ Failed to initialize detector: {e}")
            raise
        
        # Initialize ball tracker
        fps = self.config['video']['fps']
        self.tracker = BallTracker(
            dt=1.0 / fps,
            measurement_noise=self.config['tracking']['measurement_noise'],
            process_noise=self.config['tracking']['process_noise']
        )
        print(f"✅ Ball tracker initialized (FPS: {fps})")
        
        # Initialize decision engine
        decision_config = DecisionEngineConfig(
            min_confidence_threshold=self.config['decision']['confidence_threshold'],
            enable_wide_detection=True,
            enable_no_ball_detection=True,
            enable_bowled_detection=self.config['decision']['enable_bowled'],
            enable_caught_detection=self.config['decision']['enable_caught'],
            enable_lbw_detection=self.config['decision']['enable_lbw']
        )
        
        # Create default calibration
        self.calibration = self._create_default_calibration()
        
        self.decision_engine = DecisionEngine(
            calibration=self.calibration,
            config=decision_config
        )
        print(f"✅ Decision engine initialized")
        print(f"   Confidence threshold: {decision_config.min_confidence_threshold}")
        print(f"   LBW detection: {'enabled' if decision_config.enable_lbw_detection else 'disabled'}")
        print(f"   Bowled detection: {'enabled' if decision_config.enable_bowled_detection else 'disabled'}")
        
        # Statistics
        self.stats = {
            'frames_processed': 0,
            'balls_detected': 0,
            'players_detected': 0,
            'decisions_made': 0,
            'decision_types': {}
        }
        
        print("\n✅ Full pipeline ready!")
        print("="*70)
    
    def _create_default_calibration(self) -> CalibrationData:
        """Create default pitch calibration"""
        from datetime import datetime
        from umpirai.calibration.calibration_manager import Point2D
        
        # Create simple default calibration
        return CalibrationData(
            calibration_name="default",
            created_at=datetime.now().isoformat(),
            pitch_boundary=[
                Point2D(0, 0),
                Point2D(100, 0),
                Point2D(100, 100),
                Point2D(0, 100)
            ],
            crease_lines={
                "bowling": [Point2D(50, 20), Point2D(50, 80)],
                "batting": [Point2D(50, 30), Point2D(50, 70)]
            },
            wide_guidelines={"left": 0.5, "right": 0.5},
            stump_positions={
                "bowling": Point2D(50, 25),
                "batting": Point2D(50, 75)
            },
            camera_calibrations={}
        )
    
    def process_video(self, video_path: str, show_display: bool = True) -> Dict:
        """
        Process a cricket video through the full pipeline
        
        Args:
            video_path: Path to video file
            show_display: Whether to show visual display
            
        Returns:
            Dictionary with processing results and statistics
        """
        print(f"\n{'='*70}")
        print(f"🎬 Processing: {Path(video_path).name}")
        print(f"{'='*70}\n")
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"❌ Error: Could not open video")
            return None
        
        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        
        print(f"📊 Video Properties:")
        print(f"   Resolution: {width}x{height}")
        print(f"   FPS: {fps}")
        print(f"   Frames: {frame_count}")
        print(f"   Duration: {duration:.2f}s")
        print()
        
        # Reset tracker and stats
        self.tracker.reset()
        video_stats = {
            'frames_processed': 0,
            'balls_detected': 0,
            'players_detected': 0,
            'decisions': [],
            'processing_times': []
        }
        
        # Create window if displaying
        if show_display:
            window_name = f"UmpirAI - {Path(video_path).name}"
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 1280, 720)
            print("🖥️  Display window opened")
            print("   Press 'q' to quit, 'p' to pause, 's' to save frame")
            print()
        
        print("🎯 Processing frames...")
        print()
        
        frame_num = 0
        paused = False
        last_decision = None
        decision_display_until = 0
        
        while True:
            if not paused:
                ret, image = cap.read()
                if not ret:
                    break
                
                frame_num += 1
                timestamp = frame_num / fps
                
                # Create Frame object
                frame = Frame(
                    frame_number=frame_num,
                    timestamp=timestamp,
                    image=image,
                    camera_id="main"
                )
                
                # Process frame through pipeline
                start_time = time.time()
                
                # Stage 1: Object Detection
                detection_result = self.detector.detect(frame)
                
                # Stage 2: Extract ball detections
                ball_detections = [d for d in detection_result.detections if d.class_name == "ball"]
                player_detections = [d for d in detection_result.detections if d.class_name == "person"]
                
                # Update stats
                video_stats['balls_detected'] += len(ball_detections)
                video_stats['players_detected'] += len(player_detections)
                
                # Stage 3: Ball Tracking
                track_state = None
                if ball_detections:
                    # Use highest confidence ball
                    ball_det = max(ball_detections, key=lambda d: d.confidence)
                    
                    # Create BallDetection
                    ball_detection = BallDetection(
                        detection=ball_det,
                        timestamp=timestamp,
                        pixel_coords=ball_det.bounding_box.center(),
                        position_3d=ball_det.position_3d
                    )
                    
                    # Update tracker
                    track_state = self.tracker.update(ball_detection, timestamp)
                
                # Get trajectory
                trajectory = self.tracker.get_trajectory_object()
                
                # Stage 4: Decision Making
                decision = None
                if track_state and len(trajectory.positions) > 5:  # Need some history
                    try:
                        decision = self.decision_engine.process_frame(
                            detection_result=detection_result,
                            track_state=track_state,
                            trajectory=trajectory,
                            calibration=self.calibration,
                            frame_image=image
                        )
                        
                        if decision:
                            video_stats['decisions'].append({
                                'frame': frame_num,
                                'timestamp': timestamp,
                                'type': decision.decision_type.value,
                                'confidence': decision.confidence,
                                'description': decision.description
                            })
                            last_decision = decision
                            decision_display_until = frame_num + fps * 3  # Show for 3 seconds
                            
                            # Print decision
                            print(f"⚡ DECISION at frame {frame_num} ({timestamp:.2f}s):")
                            print(f"   Type: {decision.decision_type.value}")
                            print(f"   Confidence: {decision.confidence:.1f}%")
                            print(f"   Description: {decision.description}")
                            print()
                    except Exception as e:
                        # Decision engine may fail if not enough data
                        pass
                
                # Calculate processing time
                processing_time = (time.time() - start_time) * 1000
                video_stats['processing_times'].append(processing_time)
                video_stats['frames_processed'] = frame_num
                
                # Stage 5: Visualization
                if show_display:
                    display_frame = self._create_display_frame(
                        image=image,
                        detection_result=detection_result,
                        track_state=track_state,
                        trajectory=trajectory,
                        decision=last_decision if frame_num <= decision_display_until else None,
                        frame_num=frame_num,
                        frame_count=frame_count,
                        processing_time=processing_time
                    )
                    
                    cv2.imshow(window_name, display_frame)
            
            # Handle key presses
            if show_display:
                delay = int(1000 / fps) if fps > 0 else 40
                key = cv2.waitKey(delay if not paused else 100) & 0xFF
                
                if key == ord('q'):
                    print("\n🛑 Stopped by user")
                    break
                elif key == ord('p'):
                    paused = not paused
                    print(f"{'⏸️  Paused' if paused else '▶️  Resumed'}")
                elif key == ord('s'):
                    filename = f"frame_{frame_num}_{Path(video_path).stem}.jpg"
                    cv2.imwrite(filename, display_frame)
                    print(f"💾 Saved: {filename}")
        
        cap.release()
        if show_display:
            cv2.destroyAllWindows()
        
        # Print summary
        self._print_summary(video_path, video_stats)
        
        return video_stats
    
    def _create_display_frame(
        self,
        image: np.ndarray,
        detection_result,
        track_state,
        trajectory,
        decision,
        frame_num: int,
        frame_count: int,
        processing_time: float
    ) -> np.ndarray:
        """Create annotated display frame"""
        display = image.copy()
        h, w = display.shape[:2]
        
        # Draw detections
        for det in detection_result.detections:
            bbox = det.bounding_box
            x1, y1 = int(bbox.x), int(bbox.y)
            x2, y2 = int(bbox.x + bbox.width), int(bbox.y + bbox.height)
            
            # Color based on class
            if det.class_name == "ball":
                color = (0, 255, 255)  # Yellow for ball
                thickness = 3
            elif det.class_name == "person":
                color = (0, 255, 0)  # Green for players
                thickness = 2
            else:
                color = (255, 0, 0)  # Blue for others
                thickness = 2
            
            # Draw bounding box
            cv2.rectangle(display, (x1, y1), (x2, y2), color, thickness)
            
            # Draw label
            label = f"{det.class_name} {det.confidence:.2f}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(display, (x1, y1 - label_size[1] - 5), (x1 + label_size[0], y1), color, -1)
            cv2.putText(display, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # Draw trajectory
        if trajectory and len(trajectory.positions) > 1:
            points = []
            for pos in trajectory.positions[-30:]:  # Last 30 points
                # Convert 3D to 2D (simple projection)
                px = int(pos.x * 100)  # Scale factor
                py = int(pos.z * 100)
                if 0 <= px < w and 0 <= py < h:
                    points.append((px, py))
            
            # Draw trajectory line
            for i in range(len(points) - 1):
                cv2.line(display, points[i], points[i+1], (255, 0, 255), 2)
        
        # Draw info overlay
        overlay = display.copy()
        
        # Top info bar
        cv2.rectangle(overlay, (0, 0), (w, 120), (0, 0, 0), -1)
        display = cv2.addWeighted(overlay, 0.7, display, 0.3, 0)
        
        # Frame info
        y_pos = 25
        cv2.putText(display, f"Frame: {frame_num}/{frame_count}", 
                   (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        y_pos += 25
        cv2.putText(display, f"Processing: {processing_time:.1f}ms", 
                   (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        y_pos += 25
        balls = len([d for d in detection_result.detections if d.class_name == "ball"])
        players = len([d for d in detection_result.detections if d.class_name == "person"])
        cv2.putText(display, f"Detections: {balls} ball(s), {players} player(s)", 
                   (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        y_pos += 25
        if track_state:
            cv2.putText(display, f"Tracking: Active (confidence: {track_state.confidence:.2f})", 
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        else:
            cv2.putText(display, "Tracking: Inactive", 
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128, 128, 128), 2)
        
        # Decision overlay (if present)
        if decision:
            # Large decision banner
            banner_height = 150
            banner_y = h - banner_height
            
            overlay = display.copy()
            cv2.rectangle(overlay, (0, banner_y), (w, h), (0, 0, 0), -1)
            display = cv2.addWeighted(overlay, 0.8, display, 0.2, 0)
            
            # Decision type
            decision_text = decision.decision_type.value
            text_size, _ = cv2.getTextSize(decision_text, cv2.FONT_HERSHEY_BOLD, 2.0, 3)
            text_x = (w - text_size[0]) // 2
            text_y = banner_y + 50
            
            # Color based on decision type
            if "OUT" in decision_text:
                color = (0, 0, 255)  # Red
            elif "WIDE" in decision_text or "NO_BALL" in decision_text:
                color = (0, 165, 255)  # Orange
            else:
                color = (0, 255, 0)  # Green
            
            cv2.putText(display, decision_text, (text_x, text_y), 
                       cv2.FONT_HERSHEY_BOLD, 2.0, color, 3)
            
            # Confidence
            conf_text = f"Confidence: {decision.confidence:.1f}%"
            text_size, _ = cv2.getTextSize(conf_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            text_x = (w - text_size[0]) // 2
            cv2.putText(display, conf_text, (text_x, text_y + 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            # Description
            desc_text = decision.description[:60]  # Truncate if too long
            text_size, _ = cv2.getTextSize(desc_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            text_x = (w - text_size[0]) // 2
            cv2.putText(display, desc_text, (text_x, text_y + 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        return display
    
    def _print_summary(self, video_path: str, stats: Dict):
        """Print processing summary"""
        print(f"\n{'='*70}")
        print("📊 Processing Summary")
        print(f"{'='*70}")
        print(f"Video: {Path(video_path).name}")
        print(f"Frames Processed: {stats['frames_processed']}")
        print(f"Total Balls Detected: {stats['balls_detected']}")
        print(f"Total Players Detected: {stats['players_detected']}")
        print(f"Decisions Made: {len(stats['decisions'])}")
        
        if stats['processing_times']:
            avg_time = sum(stats['processing_times']) / len(stats['processing_times'])
            avg_fps = 1000 / avg_time if avg_time > 0 else 0
            print(f"\nPerformance:")
            print(f"   Avg Processing Time: {avg_time:.1f}ms")
            print(f"   Avg FPS: {avg_fps:.1f}")
            print(f"   Min Time: {min(stats['processing_times']):.1f}ms")
            print(f"   Max Time: {max(stats['processing_times']):.1f}ms")
        
        if stats['decisions']:
            print(f"\nDecisions:")
            for i, dec in enumerate(stats['decisions'], 1):
                print(f"   {i}. Frame {dec['frame']} ({dec['timestamp']:.2f}s): "
                      f"{dec['type']} (conf: {dec['confidence']:.1f}%)")
        
        print()


def main():
    """Main function"""
    print("🏏 UmpirAI Full Pipeline with YOLOv8")
    print("="*70)
    print()
    
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python run_full_pipeline.py <video_path> [config.yaml]")
        print("\nExamples:")
        print("  python run_full_pipeline.py videos/w7.mp4")
        print("  python run_full_pipeline.py videos/lbw20_mirr.mp4 config_test.yaml")
        print()
        
        # List available videos
        videos_dir = Path("videos")
        if videos_dir.exists():
            video_files = list(videos_dir.glob("*.mp4"))
            if video_files:
                print("Available videos:")
                for video in sorted(video_files):
                    size_mb = video.stat().st_size / (1024 * 1024)
                    print(f"  • {video.name} ({size_mb:.2f} MB)")
                print()
        
        return
    
    video_path = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else "config_test.yaml"
    
    # Check if video exists
    if not Path(video_path).exists():
        print(f"❌ Error: Video not found: {video_path}")
        return
    
    # Check if config exists
    if not Path(config_path).exists():
        print(f"❌ Error: Config not found: {config_path}")
        return
    
    try:
        # Initialize processor
        processor = VideoUmpireProcessor(config_path)
        
        # Process video
        results = processor.process_video(video_path, show_display=True)
        
        print("\n✅ Processing complete!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
