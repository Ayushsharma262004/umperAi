#!/usr/bin/env python3
"""
Test script for single delivery validation.

This script tests the UmpirAI system with a single delivery video
and compares the result with expected decision.
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from umpirai.system.umpirai_system import UmpirAISystem
from umpirai.config.config_manager import ConfigManager
from umpirai.data_models import MatchContext, DecisionType


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test single delivery')
    parser.add_argument('--video', required=True, help='Path to video file')
    parser.add_argument('--calibration', required=True, help='Path to calibration file')
    parser.add_argument('--expected-decision', required=True, 
                       choices=[dt.value for dt in DecisionType],
                       help='Expected decision type')
    parser.add_argument('--config', default='config.yaml', help='Path to config file')
    parser.add_argument('--output', required=True, help='Path to output JSON file')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    return parser.parse_args()


def main():
    """Run single delivery test."""
    args = parse_args()
    
    print(f"Testing single delivery: {args.video}")
    print(f"Expected decision: {args.expected_decision}")
    print("-" * 60)
    
    # Load configuration
    config = ConfigManager.load_from_file(args.config)
    
    # Override video source
    config.video.camera_sources = [args.video]
    config.video.enable_multi_camera = False
    
    # Create match context
    match_context = MatchContext(
        match_id=f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        venue="Test Venue",
        date=datetime.now().strftime("%Y-%m-%d"),
        teams=["Team A", "Team B"],
        format="Test"
    )
    
    # Initialize system
    if args.verbose:
        print("Initializing UmpirAI system...")
    
    system = UmpirAISystem(config, match_context)
    system.load_calibration(args.calibration)
    
    # Start system
    if args.verbose:
        print("Starting system...")
    
    system.start()
    
    # Wait for decision (timeout after 30 seconds)
    import time
    start_time = time.time()
    timeout = 30
    decision = None
    
    while time.time() - start_time < timeout:
        decisions = system.get_recent_decisions(count=1)
        if decisions:
            decision = decisions[0]
            break
        time.sleep(0.1)
    
    # Stop system
    system.stop()
    
    # Analyze results
    if decision is None:
        print("❌ FAILED: No decision made within timeout")
        result = {
            "status": "FAILED",
            "reason": "No decision made within timeout",
            "video": args.video,
            "expected_decision": args.expected_decision,
            "actual_decision": None,
            "timestamp": datetime.now().isoformat()
        }
    else:
        expected_type = DecisionType(args.expected_decision)
        actual_type = decision.decision_type
        
        match = expected_type == actual_type
        latency = decision.timestamp - start_time
        
        if match:
            print(f"✅ PASSED: Decision matches expected")
        else:
            print(f"❌ FAILED: Decision mismatch")
        
        print(f"   Expected: {expected_type.value}")
        print(f"   Actual: {actual_type.value}")
        print(f"   Confidence: {decision.confidence:.1%}")
        print(f"   Latency: {latency:.3f}s")
        print(f"   Uncertainty Flag: {decision.uncertainty_flag}")
        
        result = {
            "status": "PASSED" if match else "FAILED",
            "video": args.video,
            "expected_decision": expected_type.value,
            "actual_decision": actual_type.value,
            "confidence": decision.confidence,
            "latency_seconds": latency,
            "uncertainty_flag": decision.uncertainty_flag,
            "details": decision.details,
            "timestamp": datetime.now().isoformat()
        }
    
    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\nResults saved to: {args.output}")
    
    # Exit with appropriate code
    sys.exit(0 if result["status"] == "PASSED" else 1)


if __name__ == "__main__":
    main()
