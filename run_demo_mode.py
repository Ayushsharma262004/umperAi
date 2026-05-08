"""
Demo Mode: Simulates ball detection to demonstrate full UmpirAI pipeline

Since YOLOv8 COCO doesn't detect cricket balls well, this demo simulates
ball detection to show how the complete system works.
"""

import cv2
import numpy as np
from pathlib import Path
from run_full_pipeline import VideoUmpireProcessor

# Monkey-patch the detector to add simulated ball detections
original_detect = None

def simulated_detect(self, frame):
    """Add simulated ball detection to real detections"""
    # Get real detections (players, etc.)
    result = original_detect(frame)
    
    # Simulate ball detection based on frame number
    # Assume ball moves across screen in a parabolic trajectory
    frame_num = frame.frame_number
    total_frames = 47  # w7.mp4 has 47 frames
    
    # Ball trajectory simulation (parabolic path)
    progress = frame_num / total_frames
    
    # Horizontal position (left to right)
    x = 200 + progress * 1500  # Moves from left to right
    
    # Vertical position (parabolic - goes up then down)
    y = 400 - 300 * np.sin(progress * np.pi)  # Parabolic arc
    
    # Ball size
    ball_size = 30
    
    # Create simulated ball detection
    from umpirai.models.data_models import Detection, BoundingBox
    
    ball_detection = Detection(
        class_id=32,  # sports ball
        class_name="ball",
        bounding_box=BoundingBox(
            x=x - ball_size/2,
            y=y - ball_size/2,
            width=ball_size,
            height=ball_size
        ),
        confidence=0.85,  # High confidence for demo
        position_3d=None
    )
    
    # Add to detections
    result.detections.append(ball_detection)
    
    return result

def main():
    """Run demo with simulated ball detection"""
    print("🎬 UmpirAI Demo Mode - Simulated Ball Detection")
    print("="*70)
    print()
    print("⚠️  NOTE: This is a DEMO mode")
    print("   Ball detection is simulated to demonstrate the full pipeline.")
    print("   Real cricket ball detection requires custom-trained YOLOv8 model.")
    print()
    print("="*70)
    print()
    
    # Initialize processor
    processor = VideoUmpireProcessor("config_test.yaml")
    
    # Monkey-patch the detector
    global original_detect
    original_detect = processor.detector.detect
    processor.detector.detect = lambda frame: simulated_detect(processor.detector, frame)
    
    print("✅ Demo mode activated - ball detection simulated")
    print()
    
    # Process video
    video_path = "videos/w7.mp4"
    if not Path(video_path).exists():
        print(f"❌ Video not found: {video_path}")
        print("   Please ensure videos/w7.mp4 exists")
        return
    
    results = processor.process_video(video_path, show_display=True)
    
    print("\n" + "="*70)
    print("📊 Demo Complete!")
    print("="*70)
    print()
    print("What you saw:")
    print("  ✅ Real player detection (YOLOv8)")
    print("  ✅ Simulated ball detection (demo)")
    print("  ✅ Ball tracking (Extended Kalman Filter)")
    print("  ✅ Decision making (Rule engine)")
    print()
    print("For real cricket ball detection, see: DETECTION_LIMITATION.md")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        cv2.destroyAllWindows()
