"""
Main CLI entry point for UmpirAI system.

This module provides command-line interface for system operation, calibration,
testing, and configuration management.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

from umpirai.config import load_config, create_default_config, SystemConfig
from umpirai.system.umpirai_system import UmpirAISystem


def setup_logging(log_level: str = "INFO") -> None:
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def cmd_run(args: argparse.Namespace) -> int:
    """
    Run the UmpirAI system.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Load configuration
        if args.config:
            config = load_config(args.config)
        else:
            config = load_config()
        
        # Setup logging
        setup_logging(config.logging.log_level if not args.verbose else "DEBUG")
        logger = logging.getLogger(__name__)
        
        logger.info("Starting UmpirAI system...")
        logger.info(f"Configuration loaded from: {args.config or 'default location'}")
        
        # Initialize system
        system = UmpirAISystem(config=config.to_dict())
        
        # Load calibration if specified
        if args.calibration:
            logger.info(f"Loading calibration from: {args.calibration}")
            system.load_calibration(args.calibration)
        
        # Add cameras
        if args.cameras:
            for i, camera_source in enumerate(args.cameras):
                camera_id = f"cam{i+1}"
                logger.info(f"Adding camera {camera_id}: {camera_source}")
                system.add_camera(camera_id, camera_source)
        
        # Start system
        logger.info("Starting system operation...")
        system.startup()
        
        # Run for specified duration or until interrupted
        if args.duration:
            logger.info(f"Running for {args.duration} minutes...")
            import time
            time.sleep(args.duration * 60)
            system.shutdown()
        else:
            logger.info("Running until interrupted (Ctrl+C)...")
            try:
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Interrupt received, shutting down...")
                system.shutdown()
        
        logger.info("System stopped successfully")
        return 0
        
    except Exception as e:
        logging.error(f"Error running system: {e}", exc_info=True)
        return 1


def cmd_calibrate(args: argparse.Namespace) -> int:
    """
    Run calibration mode.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Load configuration
        if args.config:
            config = load_config(args.config)
        else:
            config = load_config()
        
        setup_logging(config.logging.log_level if not args.verbose else "DEBUG")
        logger = logging.getLogger(__name__)
        
        logger.info("Starting calibration mode...")
        
        # Initialize system
        system = UmpirAISystem(config=config.to_dict())
        
        # Add camera for calibration
        if args.camera:
            logger.info(f"Using camera: {args.camera}")
            system.add_camera("calibration_cam", args.camera)
        
        # Start calibration
        logger.info("Calibration mode active. Follow on-screen instructions.")
        logger.info("Press Ctrl+C when calibration is complete.")
        
        # TODO: Implement interactive calibration UI
        # For now, just provide instructions
        print("\nCalibration Instructions:")
        print("1. Ensure the camera has a clear view of the entire pitch")
        print("2. Mark the four corners of the pitch boundary")
        print("3. Mark the bowling and batting crease lines")
        print("4. Mark the stump positions")
        print("5. Verify the calibration overlay")
        print("\nCalibration interface not yet implemented.")
        print("Use the Python API for programmatic calibration.")
        
        return 0
        
    except Exception as e:
        logging.error(f"Error in calibration mode: {e}", exc_info=True)
        return 1


def cmd_test(args: argparse.Namespace) -> int:
    """
    Run test mode with recorded footage.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Load configuration
        if args.config:
            config = load_config(args.config)
        else:
            config = load_config()
        
        setup_logging(config.logging.log_level if not args.verbose else "DEBUG")
        logger = logging.getLogger(__name__)
        
        logger.info("Starting test mode...")
        logger.info(f"Test video: {args.video}")
        
        # Initialize system
        system = UmpirAISystem(config=config.to_dict())
        
        # Load calibration if specified
        if args.calibration:
            logger.info(f"Loading calibration from: {args.calibration}")
            system.load_calibration(args.calibration)
        
        # Add video file as camera source
        logger.info(f"Loading test video: {args.video}")
        system.add_camera("test_cam", args.video)
        
        # Start system
        system.startup()
        
        logger.info("Processing test video...")
        logger.info("Press Ctrl+C to stop.")
        
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Test interrupted")
        
        system.shutdown()
        logger.info("Test complete")
        
        return 0
        
    except Exception as e:
        logging.error(f"Error in test mode: {e}", exc_info=True)
        return 1


def cmd_config(args: argparse.Namespace) -> int:
    """
    Manage configuration.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        setup_logging("INFO" if not args.verbose else "DEBUG")
        logger = logging.getLogger(__name__)
        
        if args.action == 'create':
            # Create default configuration
            output_path = args.output or 'config.yaml'
            logger.info(f"Creating default configuration: {output_path}")
            config = create_default_config(output_path)
            logger.info(f"Default configuration created: {output_path}")
            return 0
        
        elif args.action == 'validate':
            # Validate configuration
            config_path = args.file or None
            logger.info(f"Validating configuration: {config_path or 'default location'}")
            config = load_config(config_path)
            logger.info("Configuration is valid ✓")
            return 0
        
        elif args.action == 'show':
            # Show configuration
            config_path = args.file or None
            logger.info(f"Loading configuration: {config_path or 'default location'}")
            config = load_config(config_path)
            
            print("\n=== UmpirAI Configuration ===\n")
            print(f"Video: {config.video.target_fps} FPS, {config.video.resolution_width}x{config.video.resolution_height}")
            print(f"Detection: Model={config.detection.model_path}, Cameras={config.detection.max_cameras}")
            print(f"Tracking: Max occlusion={config.tracking.max_occlusion_frames} frames")
            print(f"Decision: Review threshold={config.decision.confidence_review_threshold}")
            print(f"Output: Text={config.output.enable_text_display}, Audio={config.output.enable_audio_announcement}")
            print(f"Logging: Level={config.logging.log_level}, Format={config.logging.log_format}")
            print(f"Performance: FPS alert={config.performance.fps_alert_threshold}")
            print(f"System: Max runtime={config.max_runtime_minutes} min, Graceful degradation={config.enable_graceful_degradation}")
            print()
            
            return 0
        
        else:
            logger.error(f"Unknown config action: {args.action}")
            return 1
        
    except Exception as e:
        logging.error(f"Error managing configuration: {e}", exc_info=True)
        return 1


def cmd_version(args: argparse.Namespace) -> int:
    """
    Show version information.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        Exit code (0 for success)
    """
    print("UmpirAI - AI-Powered Cricket Umpiring System")
    print("Version: 0.1.0")
    print("Python: " + sys.version.split()[0])
    return 0


def create_parser() -> argparse.ArgumentParser:
    """
    Create argument parser for CLI.
    
    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog='umpirai',
        description='UmpirAI - AI-Powered Cricket Umpiring System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default configuration
  umpirai run
  
  # Run with custom configuration and cameras
  umpirai run --config config.yaml --cameras rtsp://camera1 rtsp://camera2
  
  # Run calibration mode
  umpirai calibrate --camera rtsp://camera1 --output calibration.json
  
  # Test with recorded video
  umpirai test --video match.mp4 --calibration calibration.json
  
  # Create default configuration
  umpirai config create --output my_config.yaml
  
  # Validate configuration
  umpirai config validate --file my_config.yaml
  
  # Show configuration
  umpirai config show
        """
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='UmpirAI 0.1.0'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run the UmpirAI system')
    run_parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file'
    )
    run_parser.add_argument(
        '--calibration',
        type=str,
        help='Path to calibration file'
    )
    run_parser.add_argument(
        '--cameras',
        nargs='+',
        help='Camera sources (RTSP URLs, USB device IDs, or video files)'
    )
    run_parser.add_argument(
        '--duration',
        type=int,
        help='Run duration in minutes (default: run until interrupted)'
    )
    run_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    run_parser.set_defaults(func=cmd_run)
    
    # Calibrate command
    calibrate_parser = subparsers.add_parser('calibrate', help='Run calibration mode')
    calibrate_parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file'
    )
    calibrate_parser.add_argument(
        '--camera',
        type=str,
        required=True,
        help='Camera source for calibration'
    )
    calibrate_parser.add_argument(
        '--output', '-o',
        type=str,
        default='calibration.json',
        help='Output calibration file path'
    )
    calibrate_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    calibrate_parser.set_defaults(func=cmd_calibrate)
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test with recorded video')
    test_parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file'
    )
    test_parser.add_argument(
        '--video',
        type=str,
        required=True,
        help='Path to test video file'
    )
    test_parser.add_argument(
        '--calibration',
        type=str,
        help='Path to calibration file'
    )
    test_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    test_parser.set_defaults(func=cmd_test)
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Manage configuration')
    config_subparsers = config_parser.add_subparsers(dest='action', help='Config actions')
    
    # Config create
    config_create = config_subparsers.add_parser('create', help='Create default configuration')
    config_create.add_argument(
        '--output', '-o',
        type=str,
        help='Output configuration file path (default: config.yaml)'
    )
    config_create.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    # Config validate
    config_validate = config_subparsers.add_parser('validate', help='Validate configuration')
    config_validate.add_argument(
        '--file', '-f',
        type=str,
        help='Configuration file to validate'
    )
    config_validate.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    # Config show
    config_show = config_subparsers.add_parser('show', help='Show configuration')
    config_show.add_argument(
        '--file', '-f',
        type=str,
        help='Configuration file to show'
    )
    config_show.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    config_parser.set_defaults(func=cmd_config)
    
    # Version command
    version_parser = subparsers.add_parser('version', help='Show version information')
    version_parser.set_defaults(func=cmd_version)
    
    return parser


def cli() -> int:
    """
    Main CLI entry point.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
    args = parser.parse_args()
    
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1
    
    return args.func(args)


def main() -> None:
    """Main entry point for CLI."""
    sys.exit(cli())


if __name__ == '__main__':
    main()
