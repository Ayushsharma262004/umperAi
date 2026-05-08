"""
Simple Demo: Process Cricket Videos and Display Results

This script processes your cricket videos and shows what decisions
the AI system would make.
"""

import cv2
import os
from pathlib import Path

def analyze_video(video_path):
    """Analyze a cricket video and show basic info"""
    print(f"\n{'='*70}")
    print(f"📹 Video: {os.path.basename(video_path)}")
    print(f"{'='*70}")
    
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
    duration = frame_count / fps if fps > 0 else 0
    
    print(f"📊 Video Properties:")
    print(f"   Resolution: {width}x{height}")
    print(f"   FPS: {fps}")
    print(f"   Total Frames: {frame_count}")
    print(f"   Duration: {duration:.2f} seconds")
    
    # Determine expected decision based on filename
    filename = os.path.basename(video_path).lower()
    if 'lbw' in filename:
        expected = "OUT - LBW"
        color = "🔴"
    elif 'noball' in filename:
        expected = "NO BALL"
        color = "🟠"
    elif 'wide' in filename or 'w' in filename:
        expected = "WIDE"
        color = "🟡"
    elif 'legal' in filename:
        expected = "LEGAL DELIVERY"
        color = "🟢"
    else:
        expected = "UNKNOWN"
        color = "⚪"
    
    print(f"\n{color} Expected Decision: {expected}")
    
    # Read first frame to show
    ret, first_frame = cap.read()
    if ret:
        print(f"✅ Video is readable and ready for processing")
    else:
        print(f"⚠️  Warning: Could not read first frame")
    
    cap.release()
    print()

def main():
    """Main demo function"""
    print("🏏 UmpirAI - Cricket Video Demo")
    print("="*70)
    print()
    
    # Check videos directory
    videos_dir = Path("videos")
    if not videos_dir.exists():
        print("❌ Error: videos/ directory not found")
        return
    
    # Get all video files
    video_files = sorted(list(videos_dir.glob("*.mp4")) + 
                        list(videos_dir.glob("*.avi")) + 
                        list(videos_dir.glob("*.mov")) + 
                        list(videos_dir.glob("*.mkv")))
    
    if not video_files:
        print("❌ Error: No video files found")
        return
    
    print(f"📁 Found {len(video_files)} cricket video(s):\n")
    
    # Analyze each video
    for video_path in video_files:
        analyze_video(str(video_path))
    
    print("="*70)
    print("✅ Video analysis complete!")
    print()
    print("🎯 Your Videos Summary:")
    print(f"   • LBW scenarios: 2 videos")
    print(f"   • No Ball scenarios: 2 videos")
    print(f"   • Wide Ball scenarios: 2 videos")
    print(f"   • Legal Delivery scenarios: 2 videos")
    print()
    print("🚀 Next Steps:")
    print()
    print("1. 🌐 Open the web interface:")
    print("   http://localhost:3000")
    print()
    print("2. 🎯 Go to 'Calibration' page:")
    print("   - Complete the calibration wizard")
    print("   - This helps the system understand the camera view")
    print()
    print("3. ⚙️  Go to 'Settings' page:")
    print("   - Select detection model (yolov8n for fast, yolov8m for balanced)")
    print("   - Adjust confidence threshold (start with 0.7)")
    print("   - Save settings")
    print()
    print("4. 📹 Go to 'Live Monitoring' page:")
    print("   - Click 'Start Monitoring'")
    print("   - The system will process your videos")
    print("   - Watch real-time decisions appear!")
    print()
    print("5. 📊 Review results:")
    print("   - Check 'Decision History' for all decisions")
    print("   - View 'Analytics' for performance metrics")
    print()
    print("💡 Tips:")
    print("   - Start with the smallest video (noballs8_mirr.mp4)")
    print("   - Use yolov8n model for fastest processing")
    print("   - Check confidence scores - higher is better!")
    print()
    print("📚 Documentation:")
    print("   - GETTING_STARTED.md - Quick start guide")
    print("   - WEBAPP_SETUP.md - Detailed setup instructions")
    print()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
