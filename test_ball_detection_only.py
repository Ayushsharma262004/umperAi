"""
Test cricket ball detection only (no decisions)

This tests just the ball detection to verify it's working.
"""

import cv2
import time
from pathlib import Path
from umpirai.detection.hybrid_detector import HybridDetector
from umpirai.models.data_models import Frame

def test_ball_detection(video_path: str):
    """Test ball detection on video"""
    
    print("🏏 Testing Cricket Ball Detection")
    print("="*70)
    print()
    
    # Initialize detector
    print("Initializing hybrid detector...")
    detector = HybridDetector(model_path="yolov8n.pt", device="cpu")
    print("✅ Detector ready")
    print()
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Error: Could not open {video_path}")
        return
    
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"📹 Video: {Path(video_path).name}")
    print(f"   Resolution: {width}x{height}")
    print(f"   FPS: {fps}")
    print(f"   Frames: {frame_count}")
    print()
    
    # Create window
    window_name = f"Ball Detection Test - {Path(video_path).name}"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)
    
    print("🎯 Processing frames...")
    print("   Press 'q' to quit")
    print()
    
    frame_num = 0
    total_balls = 0
    total_players = 0
    
    while True:
        ret, image = cap.read()
        if not ret:
            break
        
        frame_num += 1
        
        # Create Frame object
        frame = Frame(
            frame_number=frame_num,
            timestamp=frame_num / fps,
            image=image,
            camera_id="main"
        )
        
        # Detect
        result = detector.detect(frame)
        
        # Count detections
        balls = [d for d in result.detections if d.class_name == "ball"]
        players = [d for d in result.detections if d.class_name == "person"]
        
        total_balls += len(balls)
        total_players += len(players)
        
        # Draw detections
        display = image.copy()
        
        for det in result.detections:
            bbox = det.bounding_box
            x1, y1 = int(bbox.x), int(bbox.y)
            x2, y2 = int(bbox.x + bbox.width), int(bbox.y + bbox.height)
            
            if det.class_name == "ball":
                color = (0, 255, 255)  # Yellow
                thickness = 3
                label = f"BALL {det.confidence:.2f}"
            else:
                color = (0, 255, 0)  # Green
                thickness = 2
                label = f"{det.class_name} {det.confidence:.2f}"
            
            cv2.rectangle(display, (x1, y1), (x2, y2), color, thickness)
            cv2.putText(display, label, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Add info
        info_text = f"Frame {frame_num}/{frame_count} | Balls: {len(balls)} | Players: {len(players)}"
        cv2.putText(display, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Show
        cv2.imshow(window_name, display)
        
        # Handle keys
        key = cv2.waitKey(int(1000/fps)) & 0xFF
        if key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Summary
    print()
    print("="*70)
    print("📊 Detection Summary")
    print("="*70)
    print(f"Frames Processed: {frame_num}")
    print(f"Total Balls Detected: {total_balls}")
    print(f"Total Players Detected: {total_players}")
    print(f"Avg Balls per Frame: {total_balls/frame_num:.1f}")
    print(f"Avg Players per Frame: {total_players/frame_num:.1f}")
    print()
    
    if total_balls > 0:
        print("✅ Ball detection is WORKING!")
    else:
        print("⚠️  No balls detected - may need tuning")
    print()

if __name__ == "__main__":
    import sys
    
    video_path = sys.argv[1] if len(sys.argv) > 1 else "videos/w7.mp4"
    
    if not Path(video_path).exists():
        print(f"❌ Video not found: {video_path}")
        exit(1)
    
    try:
        test_ball_detection(video_path)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        cv2.destroyAllWindows()
