#!/usr/bin/env python3
"""
Basic Single-Camera Setup Example

This example demonstrates how to set up and run the UmpirAI system
with a single camera for basic cricket match umpiring.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from umpirai.system.umpirai_system import UmpirAISystem
from umpirai.config.config_manager import ConfigManager
from umpirai.data_models import MatchContext


def main():
    """Run basic single-camera setup."""
    
    # Load configuration
    config = ConfigManager.load_from_file("config.yaml")
    
    # Override for single camera
    config.video.camera_sources = ["rtsp://192.168.1.100:554/stream"]
    config.video.enable_multi_camera = False
    
    # Create match context
    match_context = MatchContext(
        match_id="TEST_001",
        venue="Practice Ground",
        date="2026-05-08",
        teams=["Team A", "Team B"],
        format="T20"
    )
    
    # Initialize system
    print("Initializing UmpirAI system...")
    system = UmpirAISystem(config, match_context)
    
    # Load calibration
    print("Loading calibration...")
    system.load_calibration("calibration_single_camera.json")
    
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
                  f"Decisions: {metrics['total_decisions']}", end="")
            
            # Check for alerts
            alerts = system.get_active_alerts()
            if alerts:
                print(f"\n⚠️  Alerts: {', '.join(alerts)}")
            
    except KeyboardInterrupt:
        print("\n\nStopping system...")
        system.stop()
        
        # Export logs
        print("Exporting logs...")
        system.export_logs("match_logs_single_camera.jsonl")
        
        print("System stopped successfully.")


if __name__ == "__main__":
    main()
