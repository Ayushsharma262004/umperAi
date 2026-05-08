"""
Test YOLOv8 Detection on a Single Cricket Video

This script processes a single cricket video with YOLOv8 object detection
and shows the detected objects in real-time.
"""

import sys
import cv2
import time
from pathlib import Path

def test_video_with_yolov8(video_path, model_name='yolov8n'):
    """Process video with YOLOv8 detection"""
    
    print(f"\n{'='*70}")
    print(f"🎬 Testing: {Path(video_path).name}")
    print(f"{'='*70}\n")
    
    # Import YOLOv8
    try:
        from ultralytics import YOLO
        print(f"✅ Loading YOLOv8 model: {model_name}")
        model = YOLO(f'{model_name}.pt')
        print(f"✅ Model loaded successfully")
        print(f"   Device: {model.device}")
    except ImportError:
        print("❌ Error: ultralytics package not installed")
        print("   Run: pip install ultralytics")
        return
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Error: Could not open video")
        return
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"\n📊 Video Properties:")
    print(f"   Resolution: {width}x{height}")
    print(f"   FPS: {fps}")
    print(f"   Frames: {frame_count}")
    print(f"   Duration: {frame_count/fps:.2f}s")
    print()
    
    # Cricket-related classes (COCO dataset)
    cricket_classes = {
        0: 'person',      # Players, umpires
        32: 'sports ball', # Cricket ball
        # Note: Stumps may not be in COCO, will need custom training
    }
    
    print("🎯 Detecting objects...")
    print("   Looking for: players, ball")
    print()
    print("Controls:")
    print("   • Press 'q' to quit")
    print("   • Press 'p' to pause/resume")
    print("   • Press 's' to save current frame")
    print()
    
    # Create window
    window_name = f"YOLOv8 Detection - {Path(video_path).name}"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)
    
    frame_num = 0
    paused = False
    total_detections = {'person': 0, 'sports ball': 0}
    processing_times = []
    
    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_num += 1
            
            # Run YOLOv8 detection
            start_time = time.time()
            results = model(frame, verbose=False, conf=0.3)
            inference_time = (time.time() - start_time) * 1000  # ms
            processing_times.append(inference_time)
            
            # Get detections
            detections = results[0].boxes
            
            # Draw detections
            annotated_frame = results[0].plot()
            
            # Count detections
            frame_detections = {'person': 0, 'sports ball': 0}
            for box in detections:
                cls = int(box.cls[0])
                if cls == 0:  # person
                    frame_detections['person'] += 1
                    total_detections['person'] += 1
                elif cls == 32:  # sports ball
                    frame_detections['sports ball'] += 1
                    total_detections['sports ball'] += 1
            
            # Add info overlay
            h, w = annotated_frame.shape[:2]
            
            # Semi-transparent background
            overlay = annotated_frame.copy()
            cv2.rectangle(overlay, (10, 10), (w-10, 150), (0, 0, 0), -1)
            annotated_frame = cv2.addWeighted(overlay, 0.7, annotated_frame, 0.3, 0)
            
            # Add text
            y_pos = 35
            cv2.putText(annotated_frame, f"Frame: {frame_num}/{frame_count}", 
                       (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            y_pos += 30
            cv2.putText(annotated_frame, f"Inference: {inference_time:.1f}ms", 
                       (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            y_pos += 30
            cv2.putText(annotated_frame, f"Players: {frame_detections['person']}", 
                       (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            y_pos += 30
            cv2.putText(annotated_frame, f"Ball: {frame_detections['sports ball']}", 
                       (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Show frame
            cv2.imshow(window_name, annotated_frame)
        
        # Handle key presses
        delay = int(1000 / fps) if fps > 0 else 40
        key = cv2.waitKey(delay if not paused else 100) & 0xFF
        
        if key == ord('q'):
            print("\n🛑 Stopped by user")
            break
        elif key == ord('p'):
            paused = not paused
            print(f"{'⏸️  Paused' if paused else '▶️  Resumed'}")
        elif key == ord('s'):
            filename = f"detection_frame_{frame_num}.jpg"
            cv2.imwrite(filename, annotated_frame)
            print(f"💾 Saved: {filename}")
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 Detection Summary")
    print(f"{'='*70}")
    print(f"Frames Processed: {frame_num}")
    print(f"Total Players Detected: {total_detections['person']}")
    print(f"Total Balls Detected: {total_detections['sports ball']}")
    
    if processing_times:
        avg_time = sum(processing_times) / len(processing_times)
        avg_fps = 1000 / avg_time if avg_time > 0 else 0
        print(f"\nPerformance:")
        print(f"   Avg Inference Time: {avg_time:.1f}ms")
        print(f"   Avg FPS: {avg_fps:.1f}")
        print(f"   Min Time: {min(processing_times):.1f}ms")
        print(f"   Max Time: {max(processing_times):.1f}ms")
    
    print(f"\n💡 Notes:")
    print(f"   • YOLOv8 uses COCO dataset (80 classes)")
    print(f"   • 'person' class detects players, umpires, fielders")
    print(f"   • 'sports ball' class detects cricket ball")
    print(f"   • Stumps not in COCO - needs custom training")
    print(f"   • For better cricket detection, fine-tune on cricket dataset")
    print()

def main():
    """Main function"""
    print("🏏 YOLOv8 Cricket Video Test")
    print("="*70)
    
    # Check arguments
    if len(sys.argv) < 2:
        print("\nUsage: python test_single_video.py <video_path> [model]")
        print("\nExamples:")
        print("  python test_single_video.py videos/w7.mp4")
        print("  python test_single_video.py videos/w7.mp4 yolov8s")
        print("\nAvailable models:")
        print("  • yolov8n - Nano (fastest)")
        print("  • yolov8s - Small")
        print("  • yolov8m - Medium (balanced)")
        print("  • yolov8l - Large")
        print("  • yolov8x - XLarge (most accurate)")
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
    model_name = sys.argv[2] if len(sys.argv) > 2 else 'yolov8n'
    
    # Check if video exists
    if not Path(video_path).exists():
        print(f"❌ Error: Video not found: {video_path}")
        return
    
    # Test video
    test_video_with_yolov8(video_path, model_name)

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
