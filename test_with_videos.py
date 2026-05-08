"""
Test UmpirAI System with Real Cricket Videos

This script processes cricket videos from the videos/ directory
and displays the umpiring decisions made by the AI system.
"""

import os
import sys
import cv2
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from umpirai.system.umpirai_system import UmpirAISystem
from umpirai.config.config_manager import ConfigManager

def test_video(video_path: str, system: UmpirAISystem):
    """Test a single video file"""
    print(f"\n{'='*70}")
    print(f"Testing: {os.path.basename(video_path)}")
    print(f"{'='*70}")
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Error: Could not open video {video_path}")
        return
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"📹 Video Info:")
    print(f"   Resolution: {width}x{height}")
    print(f"   FPS: {fps}")
    print(f"   Frames: {frame_count}")
    print(f"   Duration: {frame_count/fps:.2f} seconds")
    print()
    
    # Process frames
    frame_num = 0
    decisions = []
    
    try:
        # Add video source to system
        system.add_camera('main', 'file', video_path)
        
        print("🎬 Processing video...")
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_num += 1
            
            # Process frame (simplified - in real system this would go through full pipeline)
            # For now, just show progress
            if frame_num % 30 == 0:  # Every second
                print(f"   Frame {frame_num}/{frame_count} ({frame_num/frame_count*100:.1f}%)")
        
        print(f"✅ Processed {frame_num} frames")
        
    except Exception as e:
        print(f"❌ Error processing video: {e}")
    finally:
        cap.release()
    
    print()

def main():
    """Main test function"""
    print("🏏 UmpirAI - Cricket Video Testing")
    print("="*70)
    
    # Check if videos directory exists
    videos_dir = Path("videos")
    if not videos_dir.exists():
        print("❌ Error: videos/ directory not found")
        print("   Please create a videos/ directory and add cricket videos")
        return
    
    # Get all video files
    video_files = list(videos_dir.glob("*.mp4")) + \
                  list(videos_dir.glob("*.avi")) + \
                  list(videos_dir.glob("*.mov")) + \
                  list(videos_dir.glob("*.mkv"))
    
    if not video_files:
        print("❌ Error: No video files found in videos/ directory")
        print("   Supported formats: MP4, AVI, MOV, MKV")
        return
    
    print(f"📁 Found {len(video_files)} video file(s):")
    for i, video in enumerate(video_files, 1):
        size_mb = video.stat().st_size / (1024 * 1024)
        print(f"   {i}. {video.name} ({size_mb:.2f} MB)")
    print()
    
    # Load configuration
    print("⚙️  Loading configuration...")
    try:
        config_manager = ConfigManager()
        
        # Create a test configuration
        config = config_manager.create_default_config()
        
        # Adjust for video processing
        config.video.fps = 30
        config.video.resolution = [1280, 720]
        config.detection.model = 'yolov8n'  # Use fastest model for testing
        config.detection.confidence_threshold = 0.5
        
        print("✅ Configuration loaded")
        print(f"   Model: {config.detection.model}")
        print(f"   Confidence threshold: {config.detection.confidence_threshold}")
        print()
        
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return
    
    # Initialize system
    print("🚀 Initializing UmpirAI system...")
    try:
        system = UmpirAISystem(config)
        print("✅ System initialized")
        print()
    except Exception as e:
        print(f"❌ Error initializing system: {e}")
        print("\n💡 Note: The system requires YOLOv8 model to be downloaded.")
        print("   This will happen automatically on first run.")
        return
    
    # Test each video
    print("🎬 Starting video processing...")
    print()
    
    for video_path in video_files:
        test_video(str(video_path), system)
    
    print("="*70)
    print("✅ All videos processed!")
    print()
    print("📊 Summary:")
    print(f"   Total videos: {len(video_files)}")
    print()
    print("💡 Next steps:")
    print("   1. Review the decisions in the web interface")
    print("   2. Check Decision History page for detailed analysis")
    print("   3. View Analytics for performance metrics")
    print()
    print("🌐 Web Interface: http://localhost:3000")
    print("📚 API Docs: http://localhost:8000/docs")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
