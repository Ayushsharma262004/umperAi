"""
Process Cricket Videos with UmpirAI

This script processes your cricket videos one by one and shows the decisions.
Run this while the web interface is open to see results in real-time.
"""

import cv2
import time
from pathlib import Path

def process_video_simple(video_path):
    """Process a single video and show frame-by-frame"""
    print(f"\n{'='*70}")
    print(f"🎬 Processing: {video_path.name}")
    print(f"{'='*70}\n")
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print("❌ Could not open video")
        return
    
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"📊 Video: {width}x{height} @ {fps} FPS, {frame_count} frames")
    
    # Determine expected decision
    filename = video_path.name.lower()
    if 'lbw' in filename:
        decision = "OUT - LBW"
        emoji = "🔴"
    elif 'noball' in filename:
        decision = "NO BALL"
        emoji = "🟠"
    elif 'wide' in filename or 'w' in filename:
        decision = "WIDE"
        emoji = "🟡"
    elif 'legal' in filename:
        decision = "LEGAL DELIVERY"
        emoji = "🟢"
    else:
        decision = "UNKNOWN"
        emoji = "⚪"
    
    print(f"{emoji} Expected Decision: {decision}\n")
    print("🎥 Playing video...")
    
    frame_num = 0
    window_name = f"UmpirAI - {video_path.name}"
    
    # Create window
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_num += 1
        
        # Add decision overlay
        overlay = frame.copy()
        h, w = frame.shape[:2]
        
        # Add semi-transparent background for text
        cv2.rectangle(overlay, (10, 10), (w-10, 120), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        
        # Add text
        cv2.putText(frame, f"Frame: {frame_num}/{frame_count}", 
                   (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, f"Expected: {decision}", 
                   (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, "Press 'q' to skip, 'ESC' to exit", 
                   (20, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        # Show frame
        cv2.imshow(window_name, frame)
        
        # Wait for key press (adjust delay based on FPS)
        delay = int(1000 / fps) if fps > 0 else 40
        key = cv2.waitKey(delay) & 0xFF
        
        if key == ord('q'):  # Skip to next video
            print("⏭️  Skipping to next video...")
            break
        elif key == 27:  # ESC key
            print("🛑 Stopping...")
            cap.release()
            cv2.destroyAllWindows()
            return False
    
    cap.release()
    cv2.destroyWindow(window_name)
    
    print(f"✅ Completed: {frame_num} frames processed")
    print(f"{emoji} Decision: {decision}")
    
    return True

def main():
    """Main processing function"""
    print("🏏 UmpirAI - Video Processing Demo")
    print("="*70)
    print()
    print("This will play each cricket video and show the expected decision.")
    print("The actual AI processing will be integrated with the web interface.")
    print()
    print("Controls:")
    print("  • Press 'q' to skip to next video")
    print("  • Press 'ESC' to exit")
    print()
    input("Press Enter to start...")
    
    # Get video files
    videos_dir = Path("videos")
    video_files = sorted(list(videos_dir.glob("*.mp4")) + 
                        list(videos_dir.glob("*.avi")) + 
                        list(videos_dir.glob("*.mov")) + 
                        list(videos_dir.glob("*.mkv")))
    
    if not video_files:
        print("❌ No videos found in videos/ directory")
        return
    
    print(f"\n📁 Found {len(video_files)} video(s)\n")
    
    # Process each video
    for i, video_path in enumerate(video_files, 1):
        print(f"\n[{i}/{len(video_files)}]")
        
        if not process_video_simple(video_path):
            break
        
        if i < len(video_files):
            print("\n⏸️  Press Enter for next video...")
            input()
    
    cv2.destroyAllWindows()
    
    print("\n" + "="*70)
    print("✅ All videos processed!")
    print()
    print("🌐 Next: Open the web interface to see full AI analysis")
    print("   http://localhost:3000")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        cv2.destroyAllWindows()
