"""
Batch Test All Cricket Videos with UmpirAI Pipeline

This script processes all cricket videos in the videos directory
and generates a comprehensive report.
"""

import sys
import time
from pathlib import Path
from typing import List, Dict
import json

# Import the processor
from run_full_pipeline import VideoUmpireProcessor


def test_all_videos(videos_dir: str = "videos", config_path: str = "config_test.yaml"):
    """
    Test all videos in the directory
    
    Args:
        videos_dir: Directory containing videos
        config_path: Configuration file path
    """
    print("🏏 UmpirAI Batch Video Testing")
    print("="*70)
    print()
    
    # Find all videos
    videos_path = Path(videos_dir)
    if not videos_path.exists():
        print(f"❌ Error: Videos directory not found: {videos_dir}")
        return
    
    video_files = sorted(videos_path.glob("*.mp4"))
    
    if not video_files:
        print(f"❌ Error: No MP4 videos found in {videos_dir}")
        return
    
    print(f"📁 Found {len(video_files)} videos in {videos_dir}")
    for video in video_files:
        size_mb = video.stat().st_size / (1024 * 1024)
        print(f"   • {video.name} ({size_mb:.2f} MB)")
    print()
    
    # Initialize processor once
    print("🔧 Initializing UmpirAI processor...")
    try:
        processor = VideoUmpireProcessor(config_path)
    except Exception as e:
        print(f"❌ Failed to initialize processor: {e}")
        return
    
    print()
    
    # Process each video
    all_results = []
    
    for i, video_path in enumerate(video_files, 1):
        print(f"\n{'='*70}")
        print(f"📹 Video {i}/{len(video_files)}: {video_path.name}")
        print(f"{'='*70}")
        
        try:
            # Process video without display for batch mode
            start_time = time.time()
            results = processor.process_video(str(video_path), show_display=False)
            processing_duration = time.time() - start_time
            
            if results:
                results['video_name'] = video_path.name
                results['processing_duration'] = processing_duration
                all_results.append(results)
                
                print(f"✅ Completed in {processing_duration:.1f}s")
            else:
                print(f"⚠️  No results returned")
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            break
        except Exception as e:
            print(f"❌ Error processing {video_path.name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Generate comprehensive report
    print(f"\n\n{'='*70}")
    print("📊 COMPREHENSIVE TEST REPORT")
    print(f"{'='*70}\n")
    
    _print_comprehensive_report(all_results)
    
    # Save report to file
    report_path = Path("test_report.json")
    with open(report_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n💾 Detailed report saved to: {report_path}")
    
    # Save summary to text file
    summary_path = Path("test_summary.txt")
    with open(summary_path, 'w') as f:
        f.write("UmpirAI Video Test Summary\n")
        f.write("="*70 + "\n\n")
        
        for result in all_results:
            f.write(f"Video: {result['video_name']}\n")
            f.write(f"  Frames: {result['frames_processed']}\n")
            f.write(f"  Balls Detected: {result['balls_detected']}\n")
            f.write(f"  Players Detected: {result['players_detected']}\n")
            f.write(f"  Decisions: {len(result['decisions'])}\n")
            
            if result['processing_times']:
                avg_time = sum(result['processing_times']) / len(result['processing_times'])
                f.write(f"  Avg Processing Time: {avg_time:.1f}ms\n")
            
            if result['decisions']:
                f.write(f"  Decision Types:\n")
                for dec in result['decisions']:
                    f.write(f"    - {dec['type']} at {dec['timestamp']:.2f}s (conf: {dec['confidence']:.1f}%)\n")
            
            f.write("\n")
    
    print(f"💾 Summary saved to: {summary_path}")
    print()


def _print_comprehensive_report(results: List[Dict]):
    """Print comprehensive test report"""
    
    if not results:
        print("⚠️  No results to report")
        return
    
    # Overall statistics
    total_frames = sum(r['frames_processed'] for r in results)
    total_balls = sum(r['balls_detected'] for r in results)
    total_players = sum(r['players_detected'] for r in results)
    total_decisions = sum(len(r['decisions']) for r in results)
    total_duration = sum(r['processing_duration'] for r in results)
    
    print("📈 Overall Statistics:")
    print(f"   Videos Processed: {len(results)}")
    print(f"   Total Frames: {total_frames:,}")
    print(f"   Total Balls Detected: {total_balls:,}")
    print(f"   Total Players Detected: {total_players:,}")
    print(f"   Total Decisions: {total_decisions}")
    print(f"   Total Processing Time: {total_duration:.1f}s")
    
    # Performance metrics
    all_times = []
    for r in results:
        all_times.extend(r['processing_times'])
    
    if all_times:
        avg_time = sum(all_times) / len(all_times)
        avg_fps = 1000 / avg_time if avg_time > 0 else 0
        print(f"\n⚡ Performance Metrics:")
        print(f"   Avg Processing Time: {avg_time:.1f}ms per frame")
        print(f"   Avg FPS: {avg_fps:.1f}")
        print(f"   Min Time: {min(all_times):.1f}ms")
        print(f"   Max Time: {max(all_times):.1f}ms")
    
    # Decision breakdown
    decision_types = {}
    for r in results:
        for dec in r['decisions']:
            dec_type = dec['type']
            if dec_type not in decision_types:
                decision_types[dec_type] = 0
            decision_types[dec_type] += 1
    
    if decision_types:
        print(f"\n🎯 Decision Breakdown:")
        for dec_type, count in sorted(decision_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {dec_type}: {count}")
    
    # Per-video summary
    print(f"\n📹 Per-Video Summary:")
    print(f"{'Video':<25} {'Frames':<10} {'Balls':<10} {'Players':<10} {'Decisions':<12} {'Avg FPS':<10}")
    print("-" * 85)
    
    for r in results:
        video_name = r['video_name'][:24]
        frames = r['frames_processed']
        balls = r['balls_detected']
        players = r['players_detected']
        decisions = len(r['decisions'])
        
        if r['processing_times']:
            avg_time = sum(r['processing_times']) / len(r['processing_times'])
            avg_fps = 1000 / avg_time if avg_time > 0 else 0
        else:
            avg_fps = 0
        
        print(f"{video_name:<25} {frames:<10} {balls:<10} {players:<10} {decisions:<12} {avg_fps:<10.1f}")
    
    # Expected vs Actual (based on video names)
    print(f"\n🔍 Expected vs Actual Analysis:")
    
    for r in results:
        video_name = r['video_name'].lower()
        decisions = r['decisions']
        
        print(f"\n   {r['video_name']}:")
        
        # Determine expected decision type from filename
        if 'lbw' in video_name:
            expected = "LBW or OUT"
            print(f"      Expected: {expected}")
        elif 'noball' in video_name:
            expected = "NO_BALL"
            print(f"      Expected: {expected}")
        elif 'wide' in video_name or 'w' in video_name.split('.')[0]:
            expected = "WIDE"
            print(f"      Expected: {expected}")
        elif 'legal' in video_name:
            expected = "LEGAL_DELIVERY"
            print(f"      Expected: {expected}")
        else:
            expected = "Unknown"
            print(f"      Expected: {expected}")
        
        if decisions:
            print(f"      Actual: {len(decisions)} decision(s)")
            for dec in decisions:
                print(f"         - {dec['type']} at {dec['timestamp']:.2f}s (conf: {dec['confidence']:.1f}%)")
        else:
            print(f"      Actual: No decisions made")
            print(f"      ⚠️  Note: May need more frames or better detection")


def main():
    """Main function"""
    videos_dir = sys.argv[1] if len(sys.argv) > 1 else "videos"
    config_path = sys.argv[2] if len(sys.argv) > 2 else "config_test.yaml"
    
    test_all_videos(videos_dir, config_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
