# Implementation Plan: AI Auto-Umpiring System (UmpirAI)

## Overview

This implementation plan breaks down the UmpirAI system into discrete coding tasks. The system uses Python 3.10+, OpenCV for video processing, YOLOv8/PyTorch for object detection, Extended Kalman Filter for ball tracking, and Hypothesis for property-based testing. The implementation follows a bottom-up approach: core data models → individual components → integration → testing.

## Tasks

- [x] 1. Set up project structure and core data models
  - Create Python package structure with modules for each component
  - Define core data classes: Frame, Detection, DetectionResult, TrackState, Trajectory, Decision, MatchContext
  - Implement Position3D, Vector3D, BoundingBox utility classes
  - Set up configuration management for system parameters
  - Create requirements.txt with dependencies: opencv-python>=4.8, torch>=2.0, ultralytics (YOLOv8), hypothesis>=6.0, pytest>=7.0, numpy, scipy
  - _Requirements: All (foundational)_

- [x] 1.1 Write unit tests for data models
  - Test data class initialization and validation
  - Test edge cases (empty lists, None values, boundary conditions)
  - _Requirements: All (foundational)_

- [x] 2. Implement Calibration Manager
  - [x] 2.1 Create CalibrationManager class with calibration data storage
    - Implement methods: define_pitch_boundary, define_crease_line, define_wide_guideline, define_stump_positions
    - Implement camera calibration: compute homography matrix from pitch plane to image plane
    - Implement calibration validation logic
    - Implement save/load calibration to/from JSON files
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_
  
  - [x] 2.2 Write unit tests for CalibrationManager
    - Test calibration data validation
    - Test save/load functionality
    - Test homography matrix calculation
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_

- [x] 3. Implement Video Processor
  - [x] 3.1 Create VideoProcessor class with multi-camera support
    - Implement add_camera_source method supporting RTSP/HTTP streaming and USB/HDMI capture
    - Implement start_capture and stop_capture with separate thread per camera
    - Implement get_frame and get_synchronized_frames methods
    - Implement frame buffering with circular buffer (2-second capacity)
    - Implement automatic exposure adjustment for lighting changes (±30% threshold)
    - Implement frame rate monitoring (get_frame_rate method)
    - Add frame timestamp capture using system monotonic clock
    - Implement preprocessing: resize to 1280x720, normalize pixel values, gamma correction
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [x] 3.2 Write unit tests for VideoProcessor
    - Test camera source management (add, start, stop)
    - Test frame buffering and retrieval
    - Test preprocessing pipeline
    - Test error handling for camera disconnection
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 4. Implement Multi-Camera Synchronizer
  - [x] 4.1 Create MultiCameraSynchronizer class
    - Implement add_camera method with camera intrinsics storage
    - Implement synchronize_frames using cross-view object motion alignment
    - Implement estimate_temporal_offset using ball motion as reference
    - Implement epipolar constraint calculation for ball motion across views
    - Implement temporal offset optimization to minimize epipolar violations
    - Implement frame interpolation for exact alignment
    - Implement get_sync_quality metric calculation
    - _Requirements: 12.1, 12.4_
  
  - [x] 4.2 Write property test for multi-camera timestamp synchronization
    - **Property 26: Multi-Camera Timestamp Synchronization**
    - **Validates: Requirements 12.4**
  
  - [x] 4.3 Write unit tests for MultiCameraSynchronizer
    - Test temporal offset estimation
    - Test frame interpolation
    - Test sync quality calculation
    - _Requirements: 12.1, 12.4_

- [x] 5. Implement Object Detector
  - [x] 5.1 Create ObjectDetector class with YOLOv8 integration
    - Initialize YOLOv8m model with 8 detection classes (ball, stumps, crease, batsman, bowler, fielder, pitch boundary, wide guideline)
    - Implement detect method for single-frame detection
    - Implement detect_multi_view method for multi-camera detection
    - Implement confidence threshold evaluation (high ≥90%, medium 70-90%, low <70%)
    - Implement multi-view fusion: average bounding boxes weighted by confidence
    - Implement 3D ball position triangulation from 2+ camera views
    - Implement get_model_version and update_model methods
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 12.2, 12.3_
  
  - [x] 5.2 Write property test for detection confidence bounds
    - **Property 1: Detection Confidence Bounds**
    - **Validates: Requirements 2.6, 2.7**
  
  - [x] 5.3 Write property test for multi-camera detection fusion
    - **Property 25: Multi-Camera Detection Fusion**
    - **Validates: Requirements 12.2, 12.3**
  
  - [x] 5.4 Write unit tests for ObjectDetector
    - Test model initialization
    - Test detection on sample frames
    - Test confidence threshold classification
    - Test multi-view fusion logic
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement Ball Tracker with Extended Kalman Filter
  - [x] 7.1 Create BallTracker class with EKF implementation
    - Implement 9-dimensional state vector: position (x,y,z), velocity (vx,vy,vz), acceleration (ax,ay,az)
    - Implement EKF process model with gravity and air resistance
    - Implement EKF measurement model converting 2D pixel coordinates to 3D using camera calibration
    - Implement update method for incorporating new detections
    - Implement predict method for trajectory prediction during occlusion
    - Implement get_trajectory, get_velocity, is_occluded methods
    - Implement occlusion duration tracking (frame count without detection)
    - Implement trajectory calculation: store last 30 positions, calculate speed metrics
    - Implement reset method for new delivery tracking
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [x] 7.2 Write property test for trajectory completeness
    - **Property 2: Trajectory Completeness**
    - **Validates: Requirements 3.1, 3.4, 3.5**
  
  - [x] 7.3 Write property test for occlusion prediction
    - **Property 3: Occlusion Prediction**
    - **Validates: Requirements 3.3, 13.1**
  
  - [x] 7.4 Write property test for occlusion uncertainty flagging
    - **Property 4: Occlusion Uncertainty Flagging**
    - **Validates: Requirements 13.2**
  
  - [x] 7.5 Write property test for tracking resumption after occlusion
    - **Property 28: Tracking Resumption After Occlusion**
    - **Validates: Requirements 13.4**
  
  - [x] 7.6 Write property test for unoccluded view selection
    - **Property 27: Unoccluded View Selection**
    - **Validates: Requirements 13.3**
  
  - [x] 7.7 Write unit tests for BallTracker
    - Test EKF prediction accuracy with known trajectories
    - Test occlusion handling edge cases
    - Test trajectory calculation with various input sequences
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 8. Implement Decision Engine - Wide Ball Detector
  - [x] 8.1 Create WideBallDetector class
    - Implement batsman stance position identification from detections
    - Implement wide guideline definition: ±1.0m from batsman center
    - Implement ball path tracking as it crosses batsman's crease line
    - Implement wide ball classification logic: ball crosses outside guidelines
    - Implement guideline adaptation for batsman movement (>0.5m threshold)
    - Implement confidence calculation based on detection quality
    - _Requirements: 4.1, 4.3, 4.4_
  
  - [x] 8.2 Write property test for wide ball classification
    - **Property 5: Wide Ball Classification**
    - **Validates: Requirements 4.1, 4.3**
  
  - [x] 8.3 Write property test for wide guideline adaptation
    - **Property 6: Wide Guideline Adaptation**
    - **Validates: Requirements 4.4**
  
  - [x] 8.4 Write unit tests for WideBallDetector
    - Test edge cases: ball exactly on guideline
    - Test batsman movement scenarios
    - Test confidence calculation
    - _Requirements: 4.1, 4.3, 4.4_

- [x] 9. Implement Decision Engine - No Ball Detector
  - [x] 9.1 Create NoBallDetector class
    - Implement bowler front foot position detection at ball release
    - Implement ball release detection: sudden velocity change in trajectory
    - Implement foot-crease distance calculation
    - Implement no ball classification: foot crosses crease line
    - Implement confidence calculation based on foot position and crease line detection quality
    - Implement uncertainty flagging for occluded foot position
    - _Requirements: 5.1, 5.3, 5.4_
  
  - [x] 9.2 Write property test for no ball classification
    - **Property 7: No Ball Classification**
    - **Validates: Requirements 5.1**
  
  - [x] 9.3 Write property test for foot-crease distance calculation
    - **Property 8: Foot-Crease Distance Calculation**
    - **Validates: Requirements 5.3**
  
  - [x] 9.4 Write unit tests for NoBallDetector
    - Test edge case: foot exactly on crease line
    - Test ball release detection accuracy
    - Test occlusion handling
    - _Requirements: 5.1, 5.3, 5.4_

- [x] 10. Implement Decision Engine - Dismissal Detector (Bowled)
  - [x] 10.1 Create BowledDetector class
    - Implement ball-stump contact detection: bounding box intersection
    - Implement bail dislodgement verification: change in stump region appearance
    - Implement contact sequence verification: ball contacted stumps before other objects
    - Implement bowled dismissal classification logic
    - Implement non-dismissal classification: stumps hit but bails not dislodged
    - Implement confidence calculation
    - _Requirements: 6.1, 6.3, 6.4_
  
  - [x] 10.2 Write property test for bowled dismissal classification
    - **Property 9: Bowled Dismissal Classification**
    - **Validates: Requirements 6.1, 6.3**
  
  - [x] 10.3 Write property test for bowled non-dismissal
    - **Property 10: Bowled Non-Dismissal**
    - **Validates: Requirements 6.4**
  
  - [x] 10.4 Write unit tests for BowledDetector
    - Test bail dislodgement detection
    - Test contact sequence verification
    - Test edge cases
    - _Requirements: 6.1, 6.3, 6.4_

- [x] 11. Implement Decision Engine - Dismissal Detector (LBW)
  - [x] 11.1 Create LBWDetector class
    - Implement ball-pad contact detection: trajectory intersects batsman leg region
    - Implement pitching point determination: check if ball pitched in line with stumps
    - Implement impact point determination: check if contact in line with stumps
    - Implement trajectory projection: extend ball path to stumps using physics model
    - Implement stump intersection calculation
    - Implement LBW decision logic: all conditions satisfied
    - Implement bat-first exclusion: classify as not out if bat contacted before pad
    - Implement trajectory visualization generation
    - Implement confidence calculation
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_
  
  - [x] 11.2 Write property test for LBW trajectory projection
    - **Property 11: LBW Trajectory Projection**
    - **Validates: Requirements 7.1**
  
  - [x] 11.3 Write property test for LBW pitching line determination
    - **Property 12: LBW Pitching Line Determination**
    - **Validates: Requirements 7.2**
  
  - [x] 11.4 Write property test for LBW impact line determination
    - **Property 13: LBW Impact Line Determination**
    - **Validates: Requirements 7.3**
  
  - [x] 11.5 Write property test for LBW decision logic
    - **Property 14: LBW Decision Logic**
    - **Validates: Requirements 7.4**
  
  - [x] 11.6 Write property test for LBW bat-first exclusion
    - **Property 15: LBW Bat-First Exclusion**
    - **Validates: Requirements 7.6**
  
  - [x] 11.7 Write unit tests for LBWDetector
    - Test umpire's call scenarios (ball clipping stumps)
    - Test bat-pad contact sequence detection
    - Test trajectory projection accuracy
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 12. Implement Decision Engine - Dismissal Detector (Caught)
  - [x] 12.1 Create CaughtDetector class
    - Implement ball-bat contact detection: trajectory direction change near bat
    - Implement ball-to-fielder tracking
    - Implement fielder control verification: ball remains in fielder box for ≥3 frames
    - Implement ground contact verification: ball height >0.1m throughout flight
    - Implement caught dismissal classification logic
    - Implement confidence calculation
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [x] 12.2 Write property test for caught dismissal classification
    - **Property 16: Caught Dismissal Classification**
    - **Validates: Requirements 8.1, 8.2, 8.3**
  
  - [x] 12.3 Write unit tests for CaughtDetector
    - Test fielder control verification
    - Test ground contact detection
    - Test edge cases (ball bouncing before catch)
    - _Requirements: 8.1, 8.2, 8.3_

- [x] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Implement Decision Engine - Legal Delivery Counter
  - [x] 14.1 Create LegalDeliveryCounter class
    - Implement legal delivery classification: NOT wide AND NOT no ball
    - Implement legal delivery counting within each over
    - Implement over completion detection: 6 legal deliveries
    - Implement counter reset after over completion
    - Implement match state tracking
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  
  - [x] 14.2 Write property test for legal delivery classification
    - **Property 17: Legal Delivery Classification**
    - **Validates: Requirements 9.1**
  
  - [x] 14.3 Write property test for legal delivery counting
    - **Property 18: Legal Delivery Counting**
    - **Validates: Requirements 9.2**
  
  - [x] 14.4 Write property test for over completion signal
    - **Property 19: Over Completion Signal**
    - **Validates: Requirements 9.3**
  
  - [x] 14.5 Write property test for over counter reset
    - **Property 20: Over Counter Reset**
    - **Validates: Requirements 9.4**
  
  - [x] 14.6 Write unit tests for LegalDeliveryCounter
    - Test counter state transitions
    - Test over completion logic
    - Test edge cases
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 15. Implement Decision Engine - Main Controller
  - [x] 15.1 Create DecisionEngine class integrating all detectors
    - Implement process_frame method coordinating all sub-detectors
    - Implement classify_delivery method using detector outputs
    - Implement decision priority logic: dismissal > no ball > wide
    - Implement confidence calculation aggregating detector confidences
    - Implement uncertainty flagging: confidence <80%
    - Implement get_match_state method
    - Implement conflicting rule resolution
    - _Requirements: 10.1, 11.1, 11.2, 11.4_
  
  - [x] 15.2 Write property test for confidence score bounds
    - **Property 23: Confidence Score Bounds**
    - **Validates: Requirements 11.1**
  
  - [x] 15.3 Write property test for low confidence flagging
    - **Property 24: Low Confidence Flagging**
    - **Validates: Requirements 11.2, 11.4**
  
  - [x] 15.4 Write unit tests for DecisionEngine
    - Test decision priority logic
    - Test conflicting rule scenarios (wide + no ball)
    - Test confidence aggregation
    - _Requirements: 10.1, 11.1, 11.2, 11.4_

- [x] 16. Implement Decision Output
  - [x] 16.1 Create DecisionOutput class
    - Implement display_decision method with on-screen text overlay
    - Implement announce_decision method with text-to-speech synthesis
    - Implement visual indicators: color-coded overlays (green=legal, yellow=wide, red=no ball, blue=dismissal)
    - Implement output format configuration (text, audio, visual)
    - Implement decision priority system: dismissal highest, no ball/wide medium, legal low
    - Implement latency tracking: measure time from event to output
    - _Requirements: 10.2, 10.3, 10.4, 10.5_
  
  - [x] 16.2 Write property test for decision output completeness
    - **Property 21: Decision Output Completeness**
    - **Validates: Requirements 10.2, 10.4, 11.3**
  
  - [x] 16.3 Write property test for decision priority ordering
    - **Property 22: Decision Priority Ordering**
    - **Validates: Requirements 10.5**
  
  - [x] 16.4 Write unit tests for DecisionOutput
    - Test output format switching
    - Test priority system
    - Test latency measurement
    - _Requirements: 10.2, 10.3, 10.4, 10.5_

- [x] 17. Implement Event Logger
  - [x] 17.1 Create EventLogger class
    - Implement log_event method with structured JSON format
    - Implement log_decision method with video frame references
    - Implement log_performance method for system metrics
    - Implement export_logs method supporting JSON Lines format
    - Implement query_events method with filtering capabilities
    - Implement log storage with 30-day retention
    - Implement log indexing by timestamp, event type, confidence level
    - _Requirements: 15.1, 15.2, 15.3, 15.4_
  
  - [x] 17.2 Write property test for event logging completeness
    - **Property 29: Event Logging Completeness**
    - **Validates: Requirements 15.1, 15.2, 15.3**
  
  - [x] 17.3 Write unit tests for EventLogger
    - Test log structure validation
    - Test query filtering
    - Test log rotation and retention
    - _Requirements: 15.1, 15.2, 15.3, 15.4_

- [x] 18. Implement Performance Monitor
  - [x] 18.1 Create PerformanceMonitor class
    - Implement update_metrics method for metric collection
    - Implement get_current_fps, get_processing_latency, get_resource_usage methods
    - Implement resource usage monitoring: CPU, memory, GPU (if available)
    - Implement alert condition checking: FPS <25, latency >2s, detection accuracy <80%, memory >90%
    - Implement check_alerts method returning active alerts
    - Implement metric display functionality
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_
  
  - [x] 18.2 Write property test for performance metric display
    - **Property 30: Performance Metric Display**
    - **Validates: Requirements 16.1, 16.2**
  
  - [x] 18.3 Write property test for performance alert triggering
    - **Property 31: Performance Alert Triggering**
    - **Validates: Requirements 16.3, 16.4**
  
  - [x] 18.4 Write property test for resource usage logging
    - **Property 32: Resource Usage Logging**
    - **Validates: Requirements 16.5**
  
  - [x] 18.5 Write unit tests for PerformanceMonitor
    - Test alert threshold logic
    - Test metric aggregation
    - Test resource monitoring
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

- [x] 19. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 20. Implement Error Handling and Recovery
  - [x] 20.1 Add error handling to VideoProcessor
    - Implement camera disconnection detection and reconnection logic (3 retries with exponential backoff)
    - Implement video input loss alerting
    - Implement graceful degradation: continue with remaining cameras
    - Implement error logging with diagnostic information
    - _Requirements: 18.1_
  
  - [x] 20.2 Add error handling to ObjectDetector
    - Implement model initialization failure handling
    - Implement GPU failure fallback to CPU inference
    - Implement low confidence detection flagging
    - Implement missing critical elements alerting (>5 seconds threshold)
    - _Requirements: 18.2_
  
  - [x] 20.3 Add error handling to DecisionEngine
    - Implement processing error handling: continue operation and flag affected decisions
    - Implement transient error recovery without restart
    - Implement critical error data preservation before shutdown
    - Implement insufficient data handling
    - _Requirements: 18.3, 18.4, 18.5_
  
  - [x] 20.4 Write property test for video loss error handling
    - **Property 33: Video Loss Error Handling**
    - **Validates: Requirements 18.1**
  
  - [x] 20.5 Write property test for initialization error logging
    - **Property 34: Initialization Error Logging**
    - **Validates: Requirements 18.2**
  
  - [x] 20.6 Write property test for graceful error degradation
    - **Property 35: Graceful Error Degradation**
    - **Validates: Requirements 18.3**
  
  - [x] 20.7 Write property test for transient error recovery
    - **Property 36: Transient Error Recovery**
    - **Validates: Requirements 18.4**
  
  - [x] 20.8 Write property test for critical error data preservation
    - **Property 37: Critical Error Data Preservation**
    - **Validates: Requirements 18.5**
  
  - [x] 20.9 Write unit tests for error handling
    - Test reconnection logic
    - Test fallback mechanisms
    - Test error logging
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5_

- [x] 21. Implement Decision Review and Override System
  - [x] 21.1 Create DecisionReviewSystem class
    - Implement review interface displaying match event video and system decision
    - Implement decision override functionality for authorized users
    - Implement override logging with justification
    - Implement display of both system decision and manual override in logs
    - Implement override feedback collection for model improvement
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5_
  
  - [x] 21.2 Write property test for decision override logging
    - **Property 38: Decision Override Logging**
    - **Validates: Requirements 20.3, 20.4**
  
  - [x] 21.3 Write property test for override feedback collection
    - **Property 39: Override Feedback Collection**
    - **Validates: Requirements 20.5**
  
  - [x] 21.4 Write unit tests for DecisionReviewSystem
    - Test override workflow
    - Test authorization logic
    - Test feedback collection
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5_

- [x] 22. Implement Main System Integration
  - [x] 22.1 Create UmpirAISystem main class
    - Integrate all components: VideoProcessor, MultiCameraSynchronizer, ObjectDetector, BallTracker, DecisionEngine, DecisionOutput, EventLogger, PerformanceMonitor, CalibrationManager
    - Implement main processing loop: capture → sync → detect → track → decide → output → log
    - Implement system startup and shutdown procedures
    - Implement configuration loading and validation
    - Implement graceful degradation mode switching (Full → Reduced → Minimal → Safe)
    - Implement 120-minute continuous operation support
    - _Requirements: 1.4, 10.1, 14.1, 14.2, 14.3_
  
  - [x] 22.2 Write integration tests for main system
    - Test end-to-end processing pipeline
    - Test multi-component coordination
    - Test mode switching
    - Test continuous operation
    - _Requirements: 1.4, 10.1, 14.1, 14.2, 14.3_

- [x] 23. Implement Model Training Data Management
  - [x] 23.1 Create TrainingDataManager class
    - Implement export_frames method for exporting video frames with detections
    - Implement import_annotations method supporting COCO format
    - Implement model version and training data version tracking
    - Implement model retraining workflow support
    - Implement dataset versioning
    - _Requirements: 19.1, 19.2, 19.3, 19.4_
  
  - [x] 23.2 Write unit tests for TrainingDataManager
    - Test frame export functionality
    - Test annotation import
    - Test version tracking
    - _Requirements: 19.1, 19.2, 19.3, 19.4_

- [x] 24. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 25. Create Hypothesis custom generators for property tests
  - [x] 25.1 Implement custom Hypothesis strategies
    - Create cricket_ball_trajectory() generator: realistic trajectories with physics
    - Create batsman_stance() generator: valid batsman positions
    - Create bowler_foot_position() generator: foot positions relative to crease
    - Create detection_with_confidence() generator: detections with confidence scores
    - Create multi_camera_detections() generator: synchronized multi-camera detections
    - Create occluded_trajectory() generator: trajectories with occlusion gaps
    - _Requirements: All (testing infrastructure)_
  
  - [x] 25.2 Write unit tests for custom generators
    - Test generator output validity
    - Test generator constraints
    - _Requirements: All (testing infrastructure)_

- [x] 26. Create system configuration and CLI
  - [x] 26.1 Implement configuration system
    - Create YAML/JSON configuration file format
    - Implement configuration validation
    - Implement default configuration values
    - Create configuration documentation
    - _Requirements: All (system configuration)_
  
  - [x] 26.2 Implement command-line interface
    - Create CLI for system startup with configuration options
    - Implement calibration mode CLI
    - Implement test mode CLI
    - Implement logging configuration CLI
    - _Requirements: All (system operation)_
  
  - [x] 26.3 Write unit tests for configuration and CLI
    - Test configuration loading and validation
    - Test CLI argument parsing
    - Test mode switching
    - _Requirements: All (system configuration)_

- [x] 27. Create documentation and examples
  - [x] 27.1 Write user documentation
    - Create installation guide
    - Create calibration guide with screenshots
    - Create operation manual
    - Create troubleshooting guide
    - Document known limitations
    - _Requirements: All (documentation)_
  
  - [x] 27.2 Create code examples
    - Create example: basic single-camera setup
    - Create example: multi-camera setup
    - Create example: custom calibration
    - Create example: decision review workflow
    - _Requirements: All (documentation)_

- [x] 28. Final integration and system testing
  - [x] 28.1 Run complete test suite
    - Run all unit tests
    - Run all property tests with 100 iterations
    - Run integration tests
    - Verify test coverage >80%
    - _Requirements: All_
  
  - [x] 28.2 Perform system testing with real cricket footage
    - Test with recorded cricket matches
    - Test all dismissal types
    - Test wide and no ball detection
    - Test multi-camera operation
    - Test error recovery scenarios
    - Measure end-to-end latency (target: <1 second)
    - Verify 120-minute continuous operation
    - _Requirements: All_
  
  - [x] 28.3 Performance optimization
    - Profile system performance
    - Optimize bottlenecks
    - Verify frame rate maintenance (30+ FPS)
    - Verify resource usage within limits
    - _Requirements: 1.3, 10.1, 16.1, 16.2_

- [x] 29. Final checkpoint - System ready for deployment
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests validate multi-component workflows
- System tests validate complete end-to-end behavior
- The implementation uses Python 3.10+ with OpenCV, YOLOv8/PyTorch, and Hypothesis
- Checkpoints ensure incremental validation throughout development
- All 39 correctness properties from the design are covered by property test tasks
