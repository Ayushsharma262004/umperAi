"""
Test All Cricket Videos with YOLOv8

This script processes all cricket videos in the videos/ directory
and saves output videos with detections.
"""

import cv2
import time
from pathlib import Path
from ultralytics import YOLO

def process_video(video_path, output_dir, model):
    """Process a single video"""
    
    video_name = Path(video_path).stem
    output_path = output_dir / f"{video_name}_detected.mp4"
    
    print(f"\n{'='*70}")
    print(f"🎬 Processing: {Path(video_path).name}")
    print(f"{'='*70}\n")
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"❌ Error: Could not open video")
        return None
    
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
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    print(f"🎥 Processing...")
    
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
        
        # Add info overlay with semi-transparent background
        overlay = annotated_frame.copy()
        cv2.rectangle(overlay, (10, 10), (400, 140), (0, 0, 0), -1)
        annotated_frame = cv2.addWeighted(overlay, 0.6, annotated_frame, 0.4, 0)
        
        # Add text
        info_text = [
            f"Frame: {frame_num}/{frame_count}",
            f"Players: {frame_players}",
            f"Ball: {frame_balls}",
            f"Inference: {inference_time:.1f}ms"
        ]
        
        y_pos = 35
        for text in info_text:
            cv2.putText(annotated_frame, text, (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            y_pos += 30
        
        # Write frame
        out.write(annotated_frame)
    
    cap.release()
    out.release()
    
    # Calculate stats
    avg_time = sum(processing_times) / len(processing_times) if processing_times else 0
    avg_fps = 1000 / avg_time if avg_time > 0 else 0
    
    stats = {
        'video_name': video_name,
        'frames': frame_num,
        'total_players': total_players,
        'total_balls': total_balls,
        'avg_players_per_frame': total_players / frame_num if frame_num > 0 else 0,
        'avg_balls_per_frame': total_balls / frame_num if frame_num > 0 else 0,
        'avg_inference_ms': avg_time,
        'avg_fps': avg_fps,
        'output_path': output_path
    }
    
    print(f"✅ Complete!")
    print(f"   Players: {total_players} ({stats['avg_players_per_frame']:.1f}/frame)")
    print(f"   Balls: {total_balls} ({stats['avg_balls_per_frame']:.2f}/frame)")
    print(f"   Performance: {avg_fps:.1f} FPS ({avg_time:.1f}ms/frame)")
    print(f"   Output: {output_path.name}")
    
    return stats

def main():
    """Main function"""
    print("🏏 UmpirAI - Cricket Video Detection Test")
    print("="*70)
    print()
    
    # Setup
    videos_dir = Path("videos")
    output_dir = Path("output_videos")
    output_dir.mkdir(exist_ok=True)
    
    # Load model
    model_name = 'yolov8n'
    print(f"📥 Loading YOLOv8 model: {model_name}")
    model = YOLO(f'{model_name}.pt')
    print(f"✅ Model loaded on: {model.device}\n")
    
    # Find all videos
    video_files = sorted(videos_dir.glob("*.mp4"))
    
    if not video_files:
        print("❌ No videos found in videos/ directory")
        return
    
    print(f"📹 Found {len(video_files)} videos:\n")
    for i, video in enumerate(video_files, 1):
        size_mb = video.stat().st_size / (1024 * 1024)
        print(f"   {i}. {video.name} ({size_mb:.2f} MB)")
    print()
    
    # Process all videos
    all_stats = []
    start_time = time.time()
    
    for video in video_files:
        stats = process_video(video, output_dir, model)
        if stats:
            all_stats.append(stats)
    
    total_time = time.time() - start_time
    
    # Final summary
    print(f"\n{'='*70}")
    print("📊 FINAL SUMMARY")
    print(f"{'='*70}\n")
    
    print(f"Videos Processed: {len(all_stats)}/{len(video_files)}")
    print(f"Total Time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print()
    
    # Group by video type
    video_types = {
        'lbw': [],
        'noball': [],
        'wide': [],
        'legal': []
    }
    
    for stats in all_stats:
        name = stats['video_name'].lower()
        if 'lbw' in name:
            video_types['lbw'].append(stats)
        elif 'noball' in name or 'noballs' in name:
            video_types['noball'].append(stats)
        elif 'wide' in name or 'w' in name:
            video_types['wide'].append(stats)
        elif 'legal' in name:
            video_types['legal'].append(stats)
    
    # Print by type
    for vtype, vstats in video_types.items():
        if vstats:
            print(f"🎯 {vtype.upper()} Videos ({len(vstats)}):")
            for s in vstats:
                print(f"   • {s['video_name']}")
                print(f"     Players: {s['total_players']} ({s['avg_players_per_frame']:.1f}/frame)")
                print(f"     Balls: {s['total_balls']} ({s['avg_balls_per_frame']:.2f}/frame)")
                print(f"     Performance: {s['avg_fps']:.1f} FPS")
            print()
    
    # Overall stats
    if all_stats:
        total_frames = sum(s['frames'] for s in all_stats)
        total_players = sum(s['total_players'] for s in all_stats)
        total_balls = sum(s['total_balls'] for s in all_stats)
        avg_fps = sum(s['avg_fps'] for s in all_stats) / len(all_stats)
        
        print(f"📈 Overall Statistics:")
        print(f"   Total Frames: {total_frames}")
        print(f"   Total Players Detected: {total_players}")
        print(f"   Total Balls Detected: {total_balls}")
        print(f"   Average FPS: {avg_fps:.1f}")
        print()
    
    print(f"💾 Output Location: {output_dir}/")
    print(f"\n🎬 All videos saved! You can now watch them to see detections.")
    print()
    
    # List output files
    print("📁 Output Files:")
    for stats in all_stats:
        print(f"   • {stats['output_path'].name}")
    print()
    
    print("💡 Next Steps:")
    print("   1. Watch the output videos in your media player")
    print("   2. Check if ball detection is working (look for yellow boxes)")
    print("   3. Check if player detection is working (look for blue boxes)")
    print("   4. Note any issues with detection accuracy")
    print()
    print("🏏 Happy Testing!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
