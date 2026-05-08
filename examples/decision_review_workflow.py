#!/usr/bin/env python3
"""
Decision Review Workflow Example

This example demonstrates how to use the decision review system to review
and override system decisions when necessary.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from umpirai.system.umpirai_system import UmpirAISystem
from umpirai.review.decision_review_system import DecisionReviewSystem
from umpirai.config.config_manager import ConfigManager
from umpirai.data_models import MatchContext, DecisionType


def display_decision(decision):
    """Display decision details."""
    print("\n" + "=" * 60)
    print(f"Decision ID: {decision.decision_id}")
    print(f"Type: {decision.decision_type.value}")
    print(f"Timestamp: {decision.timestamp}")
    print(f"Confidence: {decision.confidence:.1%}")
    print(f"Details: {decision.details}")
    
    if decision.uncertainty_flag:
        print("⚠️  UNCERTAINTY FLAG: Low confidence decision")
    
    print("=" * 60)


def review_decision(review_system, decision):
    """Interactive decision review."""
    display_decision(decision)
    
    # Show video replay
    print("\nShowing video replay...")
    review_system.show_replay(decision.decision_id)
    
    # Get user input
    print("\nOptions:")
    print("1. Accept system decision")
    print("2. Override decision")
    print("3. Request more information")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        print("✓ Decision accepted")
        return None
    
    elif choice == "2":
        print("\nOverride decision:")
        print("Available decision types:")
        for i, dt in enumerate(DecisionType, 1):
            print(f"{i}. {dt.value}")
        
        override_choice = input("\nEnter new decision type (1-7): ").strip()
        try:
            override_type = list(DecisionType)[int(override_choice) - 1]
        except (ValueError, IndexError):
            print("Invalid choice. Keeping original decision.")
            return None
        
        justification = input("Enter justification for override: ").strip()
        
        # Submit override
        override = review_system.override_decision(
            decision_id=decision.decision_id,
            new_decision_type=override_type,
            justification=justification,
            reviewer="Umpire"
        )
        
        print(f"✓ Decision overridden to: {override_type.value}")
        return override
    
    elif choice == "3":
        print("\nAdditional information:")
        
        # Show trajectory visualization
        print("- Showing ball trajectory...")
        review_system.show_trajectory(decision.decision_id)
        
        # Show detection confidence over time
        print("- Showing detection confidence...")
        review_system.show_confidence_timeline(decision.decision_id)
        
        # Show multi-camera views
        print("- Showing multi-camera views...")
        review_system.show_multi_camera_views(decision.decision_id)
        
        # Recurse to review again with more info
        return review_decision(review_system, decision)
    
    else:
        print("Invalid choice. Keeping original decision.")
        return None


def main():
    """Run decision review workflow."""
    
    print("UmpirAI Decision Review System")
    print("=" * 60)
    
    # Load configuration
    config = ConfigManager.load_from_file("config.yaml")
    
    # Create match context
    match_context = MatchContext(
        match_id="REVIEW_DEMO_001",
        venue="Practice Ground",
        date=datetime.now().strftime("%Y-%m-%d"),
        teams=["Team A", "Team B"],
        format="T20"
    )
    
    # Initialize system
    print("\nInitializing UmpirAI system...")
    system = UmpirAISystem(config, match_context)
    system.load_calibration("calibration.json")
    
    # Initialize review system
    print("Initializing review system...")
    review_system = DecisionReviewSystem(system)
    
    # Start system
    print("Starting system...")
    system.start()
    
    try:
        print("\nSystem running. Monitoring for decisions...")
        print("Press Ctrl+C to stop.\n")
        
        last_decision_count = 0
        
        while True:
            # Check for new decisions
            current_decision_count = system.get_decision_count()
            
            if current_decision_count > last_decision_count:
                # New decision(s) made
                new_decisions = system.get_recent_decisions(
                    count=current_decision_count - last_decision_count
                )
                
                for decision in new_decisions:
                    # Check if decision needs review
                    needs_review = (
                        decision.uncertainty_flag or
                        decision.decision_type in [
                            DecisionType.DISMISSAL_LBW,
                            DecisionType.DISMISSAL_CAUGHT,
                        ]
                    )
                    
                    if needs_review:
                        print("\n🔔 Decision requires review!")
                        override = review_decision(review_system, decision)
                        
                        if override:
                            print(f"\n✓ Override recorded: {override.override_id}")
                    else:
                        print(f"\n✓ Decision auto-accepted: {decision.decision_type.value}")
                
                last_decision_count = current_decision_count
    
    except KeyboardInterrupt:
        print("\n\nStopping system...")
        system.stop()
        
        # Generate review report
        print("\nGenerating review report...")
        report = review_system.generate_report()
        
        print("\n" + "=" * 60)
        print("Review Session Summary")
        print("=" * 60)
        print(f"Total decisions: {report['total_decisions']}")
        print(f"Decisions reviewed: {report['reviewed_decisions']}")
        print(f"Decisions overridden: {report['overridden_decisions']}")
        print(f"Override rate: {report['override_rate']:.1%}")
        print(f"Average confidence: {report['average_confidence']:.1%}")
        print("=" * 60)
        
        # Export review data
        print("\nExporting review data...")
        review_system.export_review_data("review_data.json")
        
        # Export logs
        print("Exporting logs...")
        system.export_logs("match_logs_with_reviews.jsonl")
        
        print("\nSystem stopped successfully.")


if __name__ == "__main__":
    main()
