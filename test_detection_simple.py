"""
Simple detection test to see what YOLOv8 is detecting
"""

import cv2
from umpirai.detection.object_detector import ObjectDetector
from umpirai.models.data_models import Frame

# Initialize detector
print("Initializing detector...")
detector = ObjectDetector(model_path="yolov8n.pt", device="cpu")
print(f"Detector ready on {detector.device}")

# Load video
video_path = "videos/w7.mp4"
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print(f"Error: Could not open {video_path}")
    exit(1)

print(f"\nProcessing {video_path}...")

# Process first 10 frames
for frame_num in range(1, 11):
    ret, image = cap.read()
    if not ret:
        break
    
    # Create Frame object
    frame = Frame(
        frame_number=frame_num,
        timestamp=frame_num / 30.0,
        image=image,
        camera_id="main"
    )
    
    # Detect
    result = detector.detect(frame)
    
    # Count detections by class
    class_counts = {}
    for det in result.detections:
        class_name = det.class_name
        if class_name not in class_counts:
            class_counts[class_name] = 0
        class_counts[class_name] += 1
    
    print(f"Frame {frame_num}: {len(result.detections)} detections - {class_counts}")

cap.release()

print("\nTest complete!")
