"""
Setup YOLOv8 for UmpirAI System

This script downloads and configures YOLOv8 for cricket object detection.
"""

import os
import sys
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed"""
    print("🔍 Checking dependencies...")
    
    required = {
        'torch': 'PyTorch',
        'ultralytics': 'YOLOv8',
        'opencv-python': 'OpenCV',
        'numpy': 'NumPy',
        'scipy': 'SciPy'
    }
    
    missing = []
    installed = []
    
    for package, name in required.items():
        try:
            __import__(package.replace('-', '_'))
            installed.append(f"✅ {name}")
        except ImportError:
            missing.append(package)
            installed.append(f"❌ {name} - MISSING")
    
    print("\nDependency Status:")
    for status in installed:
        print(f"  {status}")
    
    return missing

def install_dependencies(missing):
    """Install missing dependencies"""
    if not missing:
        print("\n✅ All dependencies are installed!")
        return True
    
    print(f"\n📦 Installing {len(missing)} missing package(s)...")
    print(f"   Packages: {', '.join(missing)}")
    
    import subprocess
    
    try:
        # Install missing packages
        cmd = [sys.executable, '-m', 'pip', 'install'] + missing
        print(f"\n⚙️  Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        
        print("✅ Dependencies installed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        print(e.stderr)
        return False

def download_yolov8_model(model_name='yolov8n'):
    """Download YOLOv8 model"""
    print(f"\n📥 Downloading YOLOv8 model: {model_name}")
    print("   This may take a few minutes on first run...")
    
    try:
        from ultralytics import YOLO
        
        # Download model (will be cached)
        model = YOLO(f'{model_name}.pt')
        
        print(f"✅ Model downloaded: {model_name}.pt")
        print(f"   Model path: {model.ckpt_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        return False

def test_yolov8():
    """Test YOLOv8 with a sample image"""
    print("\n🧪 Testing YOLOv8...")
    
    try:
        from ultralytics import YOLO
        import cv2
        import numpy as np
        
        # Create a test image
        test_img = np.zeros((640, 640, 3), dtype=np.uint8)
        cv2.putText(test_img, "YOLOv8 Test", (200, 320), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        
        # Load model
        model = YOLO('yolov8n.pt')
        
        # Run inference
        results = model(test_img, verbose=False)
        
        print("✅ YOLOv8 is working correctly!")
        print(f"   Model: {model.model_name}")
        print(f"   Device: {model.device}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing YOLOv8: {e}")
        return False

def check_gpu():
    """Check if GPU is available"""
    print("\n🎮 Checking GPU availability...")
    
    try:
        import torch
        
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"✅ GPU Available: {gpu_name}")
            print(f"   Memory: {gpu_memory:.2f} GB")
            print(f"   CUDA Version: {torch.version.cuda}")
            return True
        else:
            print("⚠️  No GPU detected - will use CPU")
            print("   Note: GPU significantly improves performance")
            return False
            
    except Exception as e:
        print(f"⚠️  Could not check GPU: {e}")
        return False

def create_test_config():
    """Create a test configuration file"""
    print("\n⚙️  Creating test configuration...")
    
    config_content = """# UmpirAI Test Configuration
# Optimized for YOLOv8 processing

video:
  fps: 25
  resolution: [1280, 720]
  buffer_size: 30

detection:
  model: yolov8n  # Options: yolov8n, yolov8s, yolov8m, yolov8l, yolov8x
  confidence_threshold: 0.5
  nms_threshold: 0.5
  max_cameras: 4

tracking:
  max_occlusion_frames: 10
  process_noise: 0.1
  measurement_noise: 0.5

decision:
  confidence_threshold: 0.7
  wide_guideline_distance: 0.5
  enable_lbw: true
  enable_bowled: true
  enable_caught: true

performance:
  target_fps: 25
  fps_threshold: 20
  memory_threshold: 8.0
  enable_gpu: true
"""
    
    try:
        with open('config_test.yaml', 'w') as f:
            f.write(config_content)
        
        print("✅ Test configuration created: config_test.yaml")
        return True
        
    except Exception as e:
        print(f"❌ Error creating config: {e}")
        return False

def main():
    """Main setup function"""
    print("="*70)
    print("🏏 UmpirAI - YOLOv8 Setup")
    print("="*70)
    print()
    print("This script will:")
    print("  1. Check and install required dependencies")
    print("  2. Download YOLOv8 model")
    print("  3. Test the setup")
    print("  4. Check GPU availability")
    print("  5. Create test configuration")
    print()
    
    # Step 1: Check dependencies
    missing = check_dependencies()
    
    if missing:
        print("\n⚠️  Missing dependencies detected!")
        response = input("\nInstall missing dependencies? (y/n): ")
        
        if response.lower() == 'y':
            if not install_dependencies(missing):
                print("\n❌ Setup failed - could not install dependencies")
                return
        else:
            print("\n⚠️  Setup cancelled - dependencies required")
            return
    
    # Step 2: Download YOLOv8 model
    print("\n" + "="*70)
    print("📥 YOLOv8 Model Download")
    print("="*70)
    
    models = {
        'n': ('yolov8n', 'Nano - Fastest (6MB)'),
        's': ('yolov8s', 'Small - Fast (22MB)'),
        'm': ('yolov8m', 'Medium - Balanced (52MB)'),
        'l': ('yolov8l', 'Large - Accurate (87MB)'),
        'x': ('yolov8x', 'XLarge - Most Accurate (136MB)')
    }
    
    print("\nAvailable models:")
    for key, (name, desc) in models.items():
        print(f"  {key}. {name} - {desc}")
    
    choice = input("\nSelect model (n/s/m/l/x) [default: n]: ").lower() or 'n'
    
    if choice not in models:
        print("⚠️  Invalid choice, using yolov8n")
        choice = 'n'
    
    model_name = models[choice][0]
    
    if not download_yolov8_model(model_name):
        print("\n❌ Setup failed - could not download model")
        return
    
    # Step 3: Test YOLOv8
    print("\n" + "="*70)
    print("🧪 Testing YOLOv8")
    print("="*70)
    
    if not test_yolov8():
        print("\n⚠️  YOLOv8 test failed, but you can still try using it")
    
    # Step 4: Check GPU
    print("\n" + "="*70)
    print("🎮 GPU Check")
    print("="*70)
    
    has_gpu = check_gpu()
    
    # Step 5: Create test config
    print("\n" + "="*70)
    print("⚙️  Configuration")
    print("="*70)
    
    create_test_config()
    
    # Summary
    print("\n" + "="*70)
    print("✅ Setup Complete!")
    print("="*70)
    print()
    print("📊 Summary:")
    print(f"   • YOLOv8 Model: {model_name}")
    print(f"   • GPU Available: {'Yes' if has_gpu else 'No (CPU only)'}")
    print(f"   • Config File: config_test.yaml")
    print()
    print("🚀 Next Steps:")
    print()
    print("1. Test with a single video:")
    print("   python test_single_video.py videos/w7.mp4")
    print()
    print("2. Process all videos:")
    print("   python process_all_videos.py")
    print()
    print("3. Use the web interface:")
    print("   http://localhost:3000")
    print()
    print("💡 Tips:")
    print(f"   • Model '{model_name}' is now cached and ready")
    print("   • First inference may be slower (model loading)")
    print("   • GPU will significantly improve performance")
    if not has_gpu:
        print("   • Consider using a smaller model (yolov8n) for CPU")
    print()
    print("📚 Documentation:")
    print("   • QUICK_TEST_GUIDE.md - Testing your videos")
    print("   • WEBAPP_SETUP.md - Web interface setup")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
