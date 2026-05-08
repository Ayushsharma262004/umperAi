#!/usr/bin/env python3
"""
Custom Calibration Example

This example demonstrates how to perform custom calibration for the UmpirAI system,
including pitch boundary definition, crease lines, stump positions, and camera parameters.
"""

import sys
from pathlib import Path
import cv2
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from umpirai.calibration.calibration_manager import CalibrationManager
from umpirai.video.video_processor import VideoProcessor


def main():
    """Perform custom calibration."""
    
    print("UmpirAI Custom Calibration Tool")
    print("=" * 50)
    
    # Initialize calibration manager
    calibration = CalibrationManager()
    
    # Step 1: Define pitch boundary
    print("\n1. Defining pitch boundary...")
    pitch_boundary = [
        (0.0, 0.0),      # Corner 1
        (20.12, 0.0),    # Corner 2 (22 yards = 20.12m)
        (20.12, 3.05),   # Corner 3 (10 feet = 3.05m)
        (0.0, 3.05),     # Corner 4
    ]
    calibration.define_pitch_boundary(pitch_boundary)
    print("✓ Pitch boundary defined")
    
    # Step 2: Define crease lines
    print("\n2. Defining crease lines...")
    
    # Bowling crease (at bowler's end)
    bowling_crease_start = (0.0, 0.0)
    bowling_crease_end = (0.0, 3.05)
    calibration.define_crease_line("bowling", bowling_crease_start, bowling_crease_end)
    
    # Popping crease (1.22m in front of stumps)
    popping_crease_start = (1.22, 0.0)
    popping_crease_end = (1.22, 3.05)
    calibration.define_crease_line("popping", popping_crease_start, popping_crease_end)
    
    # Return crease (parallel to stumps, 1.32m on each side)
    return_crease_start = (0.0, 1.525 - 1.32)
    return_crease_end = (0.0, 1.525 + 1.32)
    calibration.define_crease_line("return", return_crease_start, return_crease_end)
    
    print("✓ Crease lines defined")
    
    # Step 3: Define stump positions
    print("\n3. Defining stump positions...")
    
    # Stumps are 0.71m (28 inches) high, 0.23m (9 inches) wide
    # Center of pitch is at 1.525m (half of 3.05m)
    stump_center_y = 1.525
    
    # Bowler's end stumps
    bowler_stumps = {
        "off": (0.0, stump_center_y + 0.115),
        "middle": (0.0, stump_center_y),
        "leg": (0.0, stump_center_y - 0.115),
    }
    calibration.define_stump_positions("bowler", bowler_stumps)
    
    # Batsman's end stumps (20.12m away)
    batsman_stumps = {
        "off": (20.12, stump_center_y + 0.115),
        "middle": (20.12, stump_center_y),
        "leg": (20.12, stump_center_y - 0.115),
    }
    calibration.define_stump_positions("batsman", batsman_stumps)
    
    print("✓ Stump positions defined")
    
    # Step 4: Define wide guidelines
    print("\n4. Defining wide guidelines...")
    
    # Wide guidelines are typically 1.0m from batsman's center
    # Assuming batsman stands at center of pitch
    wide_guideline_left = stump_center_y - 1.0
    wide_guideline_right = stump_center_y + 1.0
    
    calibration.define_wide_guideline(wide_guideline_left, wide_guideline_right)
    print("✓ Wide guidelines defined")
    
    # Step 5: Camera calibration
    print("\n5. Performing camera calibration...")
    print("   This requires a reference frame with visible pitch markings.")
    
    # For demonstration, we'll use a sample frame
    # In practice, you would capture a frame from your camera
    video_processor = VideoProcessor()
    
    camera_url = input("\nEnter camera URL (or press Enter to skip): ").strip()
    
    if camera_url:
        video_processor.add_camera_source(camera_url, "main")
        video_processor.start_capture()
        
        print("Capturing reference frame...")
        frame = video_processor.get_frame("main")
        
        if frame is not None:
            # Display frame for point selection
            print("\nClick on the following points in order:")
            print("1. Bowling crease - left edge")
            print("2. Bowling crease - right edge")
            print("3. Popping crease - left edge")
            print("4. Popping crease - right edge")
            
            points_image = []
            points_world = [
                (0.0, 0.0),      # Bowling crease left
                (0.0, 3.05),     # Bowling crease right
                (1.22, 0.0),     # Popping crease left
                (1.22, 3.05),    # Popping crease right
            ]
            
            def mouse_callback(event, x, y, flags, param):
                if event == cv2.EVENT_LBUTTONDOWN:
                    points_image.append((x, y))
                    cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
                    cv2.imshow("Calibration", frame)
                    print(f"   Point {len(points_image)}: ({x}, {y})")
            
            cv2.namedWindow("Calibration")
            cv2.setMouseCallback("Calibration", mouse_callback)
            cv2.imshow("Calibration", frame)
            
            print("\nPress any key when done...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            
            if len(points_image) >= 4:
                # Compute homography
                points_image_array = np.array(points_image[:4], dtype=np.float32)
                points_world_array = np.array(points_world, dtype=np.float32)
                
                homography, _ = cv2.findHomography(points_image_array, points_world_array)
                
                # Add camera calibration
                camera_params = {
                    "homography": homography.tolist(),
                    "resolution": (frame.shape[1], frame.shape[0]),
                }
                calibration.add_camera_calibration("main", camera_params)
                
                print("✓ Camera calibration completed")
            else:
                print("⚠️  Insufficient points selected. Skipping camera calibration.")
        
        video_processor.stop_capture()
    else:
        print("⚠️  Skipping camera calibration")
    
    # Step 6: Validate calibration
    print("\n6. Validating calibration...")
    is_valid, errors = calibration.validate()
    
    if is_valid:
        print("✓ Calibration is valid")
    else:
        print("⚠️  Calibration validation failed:")
        for error in errors:
            print(f"   - {error}")
    
    # Step 7: Save calibration
    print("\n7. Saving calibration...")
    output_file = input("Enter output filename (default: calibration.json): ").strip()
    if not output_file:
        output_file = "calibration.json"
    
    calibration.save_to_file(output_file)
    print(f"✓ Calibration saved to {output_file}")
    
    print("\n" + "=" * 50)
    print("Calibration complete!")
    print(f"\nTo use this calibration, load it in your UmpirAI system:")
    print(f"  system.load_calibration('{output_file}')")


if __name__ == "__main__":
    main()
