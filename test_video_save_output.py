"""
Test YOLOv8 and Save Output Video

This script processes a cricket video with YOLOv8 and saves the output
with detection boxes drawn on it.
"""

import sys
import cv2
import time
from pathlib import Path
from ultralytics import YOLO

def process_and_save_video(video_path, output_path, model_name='yolov8n'):
    """Process video with YOLOv8 and save output"""
    
    print(f"\n{'='*70}")
    print(f"🎬 Processing: {Path(video_path).name}")
    print(f"{'='*70}\n")
    
    # Load model
    print(f"📥 Loading YOLOv8 model: {model_name}")
    model = YOLO(f'{model_name}.pt')
    print(f"✅ Model loaded on: {model.device}\n")
    
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
    
    print(f"📊 Video Info:")
    print(f"   Resolution: {width}x{height}")
    print(f"   FPS: {fps}")
    print(f"   Frames: {frame_count}")
    print(f"   Duration: {frame_count/fps:.2f}s\n")
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    print(f"🎥 Processing video...")
    print(f"   Output: {output_path}\n")
    
    frame_num = 0
    total_players = 0
    total_balls = 0
    processing_times = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_num += 1
        
        # Run YOLOv8 detection
        start_time = time.time()
        results = model(frame, verbose=False, conf=0.3)
        inference_time = (time.time() - start_time) * 1000
        processing_times.append(inference_time)
        
        # Get annotated frame
        annotated_frame = results[0].plot()
        
        # Count detections
        detections = results[0].boxes
        frame_players = 0
        frame_balls = 0
        
        for box in detections:
            cls = int(box.cls[0])
            if cls == 0:  # person
                frame_players += 1
                total_players += 1
            elif cls == 32:  # sports ball
                frame_balls += 1
                total_balls += 1
        
        # Add info overlay
        info_text = [
            f"Frame: {frame_num}/{frame_count}",
            f"Players: {frame_players}",
            f"Ball: {frame_balls}",
            f"Inference: {inference_time:.1f}ms"
        ]
        
        y_pos = 30
        for text in info_text:
            cv2.putText(annotated_frame, text, (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            y_pos += 30
        
        # Write frame
        out.write(annotated_frame)
        
        # Progress
        if frame_num % 10 == 0:
            progress = (frame_num / frame_count) * 100
            print(f"   Progress: {progress:.1f}% ({frame_num}/{frame_count} frames)")
    
    cap.release()
    out.release()
    
    # Summary
    print(f"\n{'='*70}")
    print("✅ Processing Complete!")
    print(f"{'='*70}\n")
    
    print(f"📊 Detection Summary:")
    print(f"   Frames Processed: {frame_num}")
    print(f"   Total Players: {total_players}")
    print(f"   Total Balls: {total_balls}")
    print(f"   Avg Players/Frame: {total_players/frame_num:.1f}")
    print(f"   Avg Balls/Frame: {total_balls/frame_num:.2f}")
    
    if processing_times:
        avg_time = sum(processing_times) / len(processing_times)
        avg_fps = 1000 / avg_time if avg_time > 0 else 0
        print(f"\n⚡ Performance:")
        print(f"   Avg Inference: {avg_time:.1f}ms")
        print(f"   Avg FPS: {avg_fps:.1f}")
        print(f"   Min Time: {min(processing_times):.1f}ms")
        print(f"   Max Time: {max(processing_times):.1f}ms")
    
    print(f"\n💾 Output saved to: {output_path}")
    print(f"\n🎬 You can now play the video to see detections!")
    print()

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python test_video_save_output.py <video_path> [model] [output_path]")
        print("\nExample:")
        print("  python test_video_save_output.py videos/w7.mp4")
        print("  python test_video_save_output.py videos/w7.mp4 yolov8s output_w7.mp4")
        return
    
    video_path = sys.argv[1]
    model_name = sys.argv[2] if len(sys.argv) > 2 else 'yolov8n'
    
    # Generate output path
    if len(sys.argv) > 3:
        output_path = sys.argv[3]
    else:
        video_name = Path(video_path).stem
        output_path = f"output_{video_name}_detected.mp4"
    
    # Check if video exists
    if not Path(video_path).exists():
        print(f"❌ Error: Video not found: {video_path}")
        return
    
    # Process video
    process_and_save_video(video_path, output_path, model_name)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
