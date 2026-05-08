#!/usr/bin/env python3
"""
Performance profiling script for UmpirAI system.

This script profiles the system to identify performance bottlenecks
and provides optimization recommendations.
"""

import sys
import time
import json
import argparse
import cProfile
import pstats
from pathlib import Path
from io import StringIO
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from umpirai.system.umpirai_system import UmpirAISystem
from umpirai.config.config_manager import ConfigManager
from umpirai.data_models import MatchContext


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Profile UmpirAI performance')
    parser.add_argument('--video', required=True, help='Path to test video file')
    parser.add_argument('--calibration', required=True, help='Path to calibration file')
    parser.add_argument('--config', default='config.yaml', help='Path to config file')
    parser.add_argument('--duration', type=int, default=60, help='Profiling duration in seconds')
    parser.add_argument('--output', required=True, help='Path to output JSON file')
    parser.add_argument('--profile-output', help='Path to save cProfile stats')
    return parser.parse_args()


def measure_component_performance(system, duration):
    """Measure performance of individual components."""
    
    metrics = {
        'video_processing': [],
        'detection': [],
        'tracking': [],
        'decision': [],
        'total_pipeline': []
    }
    
    start_time = time.time()
    frame_count = 0
    
    print("Measuring component performance...")
    
    while time.time() - start_time < duration:
        # Measure video processing
        t0 = time.time()
        frame = system.video_processor.get_frame("main")
        t1 = time.time()
        metrics['video_processing'].append(t1 - t0)
        
        if frame is None:
            break
        
        # Measure detection
        t0 = time.time()
        detections = system.object_detector.detect(frame)
        t1 = time.time()
        metrics['detection'].append(t1 - t0)
        
        # Measure tracking
        t0 = time.time()
        ball_detections = detections.get_detections_by_class(0)  # Ball class
        if ball_detections:
            system.ball_tracker.update(ball_detections[0])
        t1 = time.time()
        metrics['tracking'].append(t1 - t0)
        
        # Measure decision
        t0 = time.time()
        decision = system.decision_engine.process_frame(frame, detections, system.ball_tracker.get_trajectory())
        t1 = time.time()
        metrics['decision'].append(t1 - t0)
        
        # Total pipeline time
        metrics['total_pipeline'].append(
            metrics['video_processing'][-1] +
            metrics['detection'][-1] +
            metrics['tracking'][-1] +
            metrics['decision'][-1]
        )
        
        frame_count += 1
    
    # Calculate statistics
    stats = {}
    for component, times in metrics.items():
        if times:
            stats[component] = {
                'mean_ms': sum(times) / len(times) * 1000,
                'min_ms': min(times) * 1000,
                'max_ms': max(times) * 1000,
                'total_s': sum(times),
                'percentage': (sum(times) / sum(metrics['total_pipeline'])) * 100 if component != 'total_pipeline' else 100
            }
    
    stats['frames_processed'] = frame_count
    stats['actual_fps'] = frame_count / duration
    
    return stats


def measure_resource_usage(system, duration):
    """Measure CPU, memory, and GPU usage."""
    import psutil
    
    process = psutil.Process()
    
    cpu_samples = []
    memory_samples = []
    
    print("Measuring resource usage...")
    
    start_time = time.time()
    while time.time() - start_time < duration:
        cpu_samples.append(process.cpu_percent(interval=0.1))
        memory_samples.append(process.memory_info().rss / 1024 / 1024)  # MB
        time.sleep(1)
    
    # Try to get GPU usage if available
    gpu_usage = None
    try:
        import torch
        if torch.cuda.is_available():
            gpu_usage = {
                'device': torch.cuda.get_device_name(0),
                'memory_allocated_mb': torch.cuda.memory_allocated(0) / 1024 / 1024,
                'memory_reserved_mb': torch.cuda.memory_reserved(0) / 1024 / 1024,
            }
    except:
        pass
    
    return {
        'cpu': {
            'mean_percent': sum(cpu_samples) / len(cpu_samples),
            'max_percent': max(cpu_samples),
            'min_percent': min(cpu_samples)
        },
        'memory': {
            'mean_mb': sum(memory_samples) / len(memory_samples),
            'max_mb': max(memory_samples),
            'min_mb': min(memory_samples)
        },
        'gpu': gpu_usage
    }


def identify_bottlenecks(component_stats):
    """Identify performance bottlenecks."""
    
    bottlenecks = []
    recommendations = []
    
    # Check if any component takes >50% of pipeline time
    for component, stats in component_stats.items():
        if component == 'total_pipeline' or component == 'frames_processed' or component == 'actual_fps':
            continue
        
        if stats['percentage'] > 50:
            bottlenecks.append({
                'component': component,
                'percentage': stats['percentage'],
                'mean_ms': stats['mean_ms']
            })
    
    # Generate recommendations
    if component_stats.get('detection', {}).get('percentage', 0) > 50:
        recommendations.append({
            'issue': 'Detection is the bottleneck',
            'suggestions': [
                'Use a smaller YOLOv8 model (e.g., YOLOv8n instead of YOLOv8m)',
                'Reduce input resolution',
                'Enable GPU acceleration if not already enabled',
                'Reduce detection frequency (skip frames)'
            ]
        })
    
    if component_stats.get('video_processing', {}).get('percentage', 0) > 30:
        recommendations.append({
            'issue': 'Video processing is slow',
            'suggestions': [
                'Reduce video resolution',
                'Disable unnecessary preprocessing steps',
                'Use hardware-accelerated video decoding',
                'Optimize frame buffer size'
            ]
        })
    
    if component_stats.get('tracking', {}).get('percentage', 0) > 20:
        recommendations.append({
            'issue': 'Tracking is consuming significant time',
            'suggestions': [
                'Optimize EKF matrix operations',
                'Reduce trajectory history length',
                'Use sparse matrix operations'
            ]
        })
    
    # Check FPS
    actual_fps = component_stats.get('actual_fps', 0)
    if actual_fps < 25:
        recommendations.append({
            'issue': f'Frame rate is below target (actual: {actual_fps:.1f} FPS, target: 30 FPS)',
            'suggestions': [
                'Apply bottleneck optimizations above',
                'Consider reducing video resolution',
                'Enable multi-threading for parallel processing',
                'Upgrade hardware (CPU/GPU)'
            ]
        })
    
    return bottlenecks, recommendations


def main():
    """Run performance profiling."""
    args = parse_args()
    
    print("=" * 60)
    print("UmpirAI Performance Profiling")
    print("=" * 60)
    print(f"Video: {args.video}")
    print(f"Duration: {args.duration}s")
    print("=" * 60)
    
    # Load configuration
    config = ConfigManager.load_from_file(args.config)
    config.video.camera_sources = [args.video]
    config.video.enable_multi_camera = False
    
    # Create match context
    match_context = MatchContext(
        match_id=f"PROFILE_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        venue="Test Venue",
        date=datetime.now().strftime("%Y-%m-%d"),
        teams=["Team A", "Team B"],
        format="Test"
    )
    
    # Initialize system
    print("\nInitializing system...")
    system = UmpirAISystem(config, match_context)
    system.load_calibration(args.calibration)
    system.start()
    
    # Profile with cProfile if requested
    if args.profile_output:
        print("\nRunning cProfile...")
        profiler = cProfile.Profile()
        profiler.enable()
    
    # Measure component performance
    component_stats = measure_component_performance(system, args.duration)
    
    # Measure resource usage
    resource_stats = measure_resource_usage(system, min(args.duration, 30))
    
    # Stop profiler
    if args.profile_output:
        profiler.disable()
        
        # Save cProfile stats
        profiler.dump_stats(args.profile_output)
        
        # Print top functions
        s = StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)
        cprofile_summary = s.getvalue()
    else:
        cprofile_summary = None
    
    # Stop system
    system.stop()
    
    # Identify bottlenecks
    bottlenecks, recommendations = identify_bottlenecks(component_stats)
    
    # Print results
    print("\n" + "=" * 60)
    print("PERFORMANCE RESULTS")
    print("=" * 60)
    
    print("\nComponent Performance:")
    for component, stats in component_stats.items():
        if component in ['frames_processed', 'actual_fps']:
            continue
        print(f"  {component:20s}: {stats['mean_ms']:6.2f}ms ({stats['percentage']:5.1f}%)")
    
    print(f"\nFrames Processed: {component_stats['frames_processed']}")
    print(f"Actual FPS: {component_stats['actual_fps']:.1f}")
    
    print("\nResource Usage:")
    print(f"  CPU: {resource_stats['cpu']['mean_percent']:.1f}% (max: {resource_stats['cpu']['max_percent']:.1f}%)")
    print(f"  Memory: {resource_stats['memory']['mean_mb']:.1f}MB (max: {resource_stats['memory']['max_mb']:.1f}MB)")
    if resource_stats['gpu']:
        print(f"  GPU: {resource_stats['gpu']['device']}")
        print(f"       Memory: {resource_stats['gpu']['memory_allocated_mb']:.1f}MB")
    
    if bottlenecks:
        print("\nBottlenecks Identified:")
        for bottleneck in bottlenecks:
            print(f"  - {bottleneck['component']}: {bottleneck['percentage']:.1f}% of pipeline time")
    
    if recommendations:
        print("\nOptimization Recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['issue']}")
            for suggestion in rec['suggestions']:
                print(f"   - {suggestion}")
    
    # Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'video': args.video,
        'duration_seconds': args.duration,
        'component_performance': component_stats,
        'resource_usage': resource_stats,
        'bottlenecks': bottlenecks,
        'recommendations': recommendations,
        'cprofile_summary': cprofile_summary
    }
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'=' * 60}")
    print(f"Results saved to: {args.output}")
    if args.profile_output:
        print(f"cProfile stats saved to: {args.profile_output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
