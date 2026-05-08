#!/usr/bin/env python3
"""
Multi-Camera Setup Example

This example demonstrates how to set up and run the UmpirAI system
with multiple synchronized cameras for enhanced accuracy.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from umpirai.system.umpirai_system import UmpirAISystem
from umpirai.config.config_manager import ConfigManager
from umpirai.data_models import MatchContext


def main():
    """Run multi-camera setup."""
    
    # Load configuration
    config = ConfigManager.load_from_file("config.yaml")
    
    # Configure multiple cameras
    config.video.camera_sources = [
        "rtsp://192.168.1.100:554/stream",  # Bowler's end
        "rtsp://192.168.1.101:554/stream",  # Side-on view
        "rtsp://192.168.1.102:554/stream",  # Batsman's end
    ]
    config.video.enable_multi_camera = True
    
    # Enable multi-camera features
    config.detection.enable_multi_view_fusion = True
    config.tracking.use_multi_camera_triangulation = True
    
    # Create match context
    match_context = MatchContext(
        match_id="MATCH_2026_001",
        venue="Main Stadium",
        date="2026-05-08",
        teams=["Mumbai Indians", "Chennai Super Kings"],
        format="T20"
    )
    
    # Initialize system
    print("Initializing UmpirAI system with multi-camera support...")
    system = UmpirAISystem(config, match_context)
    
    # Load calibration for each camera
    print("Loading calibrations...")
    system.load_calibration("calibration_multi_camera.json")
    
    # Verify camera synchronization
    print("Verifying camera synchronization...")
    sync_quality = system.get_sync_quality()
    print(f"Synchronization quality: {sync_quality:.2%}")
    
    if sync_quality < 0.8:
        print("⚠️  Warning: Low synchronization quality. Consider recalibrating.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting.")
            return
    
    # Start system
    print("Starting system...")
    system.start()
    
    try:
        print("System running. Press Ctrl+C to stop.")
        print("\nMonitoring:")
        
        # Run for demonstration
        while True:
            # Get current performance metrics
            metrics = system.get_performance_metrics()
            
            # Display metrics
            print(f"\rFPS: {metrics['fps']:.1f} | "
                  f"Latency: {metrics['latency_ms']:.0f}ms | "
                  f"Decisions: {metrics['total_decisions']} | "
                  f"Sync: {metrics['sync_quality']:.1%}", end="")
            
            # Check for alerts
            alerts = system.get_active_alerts()
            if alerts:
                print(f"\n⚠️  Alerts: {', '.join(alerts)}")
            
            # Display camera status
            camera_status = system.get_camera_status()
            active_cameras = sum(1 for status in camera_status.values() if status == "active")
            if active_cameras < len(config.video.camera_sources):
                print(f"\n⚠️  Only {active_cameras}/{len(config.video.camera_sources)} cameras active")
            
    except KeyboardInterrupt:
        print("\n\nStopping system...")
        system.stop()
        
        # Export logs
        print("Exporting logs...")
        system.export_logs("match_logs_multi_camera.jsonl")
        
        # Export training data if any overrides occurred
        if system.has_overrides():
            print("Exporting training data from overrides...")
            system.export_training_data("training_data/")
        
        print("System stopped successfully.")


if __name__ == "__main__":
    main()
