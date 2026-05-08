# UmpirAI Installation Guide

This guide provides step-by-step instructions for installing and setting up the UmpirAI cricket umpiring system.

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
- [Dependencies](#dependencies)
- [Installation Steps](#installation-steps)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

## System Requirements

### Minimum Requirements

- **Operating System**: Windows 10/11, Linux (Ubuntu 20.04+), macOS 10.15+
- **Python**: 3.10 or higher
- **RAM**: 8 GB
- **Storage**: 10 GB free space
- **Processor**: Intel Core i5 or equivalent
- **Camera**: USB webcam or network camera (RTSP/HTTP)

### Recommended Requirements

- **Operating System**: Ubuntu 22.04 LTS or Windows 11
- **Python**: 3.11
- **RAM**: 16 GB or more
- **Storage**: 50 GB SSD
- **Processor**: Intel Core i7 or AMD Ryzen 7 (8+ cores)
- **GPU**: NVIDIA GPU with CUDA support (for faster processing)
- **Camera**: Multiple HD cameras (1280x720 or higher)

### GPU Support (Optional but Recommended)

For optimal performance, especially with multiple cameras:

- **NVIDIA GPU** with CUDA 11.8 or higher
- **CUDA Toolkit** installed
- **cuDNN** library installed
- **Minimum 4GB VRAM** (8GB+ recommended)

## Installation Methods

### Method 1: From Source (Recommended for Development)

```bash
# Clone the repository
git clone https://github.com/yourusername/umpirai.git
cd umpirai

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Method 2: Using pip (When Available)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install UmpirAI
pip install umpirai

# Verify installation
umpirai version
```

## Dependencies

### Core Dependencies

The following packages are automatically installed:

- **opencv-python** (>=4.8.0) - Video processing
- **torch** (>=2.0.0) - Deep learning framework
- **ultralytics** - YOLOv8 object detection
- **numpy** (>=1.24.0) - Numerical computing
- **scipy** (>=1.10.0) - Scientific computing
- **pyyaml** (>=6.0) - Configuration file parsing
- **hypothesis** (>=6.0.0) - Property-based testing

### Optional Dependencies

For enhanced functionality:

```bash
# GPU support (NVIDIA)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Audio announcements
pip install pyttsx3

# Advanced logging
pip install python-json-logger
```

## Installation Steps

### Step 1: Install Python

Ensure Python 3.10 or higher is installed:

```bash
python --version
```

If not installed, download from [python.org](https://www.python.org/downloads/).

### Step 2: Install System Dependencies

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    libopencv-dev \
    ffmpeg \
    libsm6 \
    libxext6
```

#### macOS

```bash
brew install python@3.11
brew install opencv
brew install ffmpeg
```

#### Windows

- Install [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
- Install [FFmpeg](https://ffmpeg.org/download.html) (optional, for video file support)

### Step 3: Clone Repository

```bash
git clone https://github.com/yourusername/umpirai.git
cd umpirai
```

### Step 4: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### Step 5: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

### Step 6: Download YOLOv8 Model

```bash
# The model will be downloaded automatically on first run
# Or download manually:
python -c "from ultralytics import YOLO; YOLO('yolov8m.pt')"
```

### Step 7: Verify Installation

```bash
# Run tests
pytest tests/ -v

# Check CLI
python umpirai_cli.py version
```

## Verification

### Test Basic Functionality

```bash
# Create default configuration
python umpirai_cli.py config create

# Validate configuration
python umpirai_cli.py config validate

# Show configuration
python umpirai_cli.py config show
```

### Test with Sample Video

```bash
# Download sample cricket video (or use your own)
# Test with video file
python umpirai_cli.py test --video sample_match.mp4
```

### Check GPU Support (if applicable)

```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"GPU count: {torch.cuda.device_count()}")
if torch.cuda.is_available():
    print(f"GPU name: {torch.cuda.get_device_name(0)}")
```

## Troubleshooting

### Common Issues

#### Issue: "ModuleNotFoundError: No module named 'cv2'"

**Solution:**
```bash
pip install opencv-python
```

#### Issue: "CUDA out of memory"

**Solutions:**
1. Reduce video resolution in configuration
2. Reduce number of cameras
3. Use CPU instead of GPU
4. Upgrade GPU memory

#### Issue: "Permission denied" when accessing camera

**Linux Solution:**
```bash
# Add user to video group
sudo usermod -a -G video $USER
# Log out and log back in
```

**Windows Solution:**
- Check camera permissions in Windows Settings > Privacy > Camera

#### Issue: "YOLOv8 model download fails"

**Solution:**
```bash
# Download manually
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m.pt
# Place in project root or specify path in config
```

#### Issue: "ImportError: DLL load failed" (Windows)

**Solution:**
- Install Visual C++ Redistributable
- Reinstall opencv-python: `pip uninstall opencv-python && pip install opencv-python`

#### Issue: "Hypothesis tests are slow"

**Solution:**
- This is normal for property-based tests
- Use `pytest -k "not property"` to skip property tests during development
- Property tests are important for validation but can be run less frequently

### Getting Help

If you encounter issues not covered here:

1. Check the [FAQ](FAQ.md)
2. Search [GitHub Issues](https://github.com/yourusername/umpirai/issues)
3. Create a new issue with:
   - Python version (`python --version`)
   - Operating system
   - Error message and full traceback
   - Steps to reproduce

## Next Steps

After successful installation:

1. **Read the User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
2. **Configure the System**: [CONFIGURATION.md](CONFIGURATION.md)
3. **Run Calibration**: [CALIBRATION.md](CALIBRATION.md)
4. **Start Using UmpirAI**: [OPERATION.md](OPERATION.md)

## Updating UmpirAI

### From Source

```bash
cd umpirai
git pull origin main
pip install -r requirements.txt --upgrade
```

### From pip

```bash
pip install --upgrade umpirai
```

## Uninstallation

```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment
rm -rf venv  # Linux/macOS
# or
rmdir /s venv  # Windows

# Remove cloned repository
cd ..
rm -rf umpirai
```

## Development Installation

For contributors and developers:

```bash
# Clone repository
git clone https://github.com/yourusername/umpirai.git
cd umpirai

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in editable mode with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/ -v

# Run linting
flake8 umpirai/
black umpirai/
mypy umpirai/
```

## Docker Installation (Alternative)

For containerized deployment:

```bash
# Build Docker image
docker build -t umpirai:latest .

# Run container
docker run -it --rm \
  --device=/dev/video0 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/calibrations:/app/calibrations \
  umpirai:latest run --config config.yaml
```

See [DOCKER.md](DOCKER.md) for detailed Docker instructions.

## Performance Optimization

### For CPU-Only Systems

```yaml
# config.yaml
video:
  target_fps: 15  # Reduce FPS
  resolution_width: 640  # Lower resolution
  resolution_height: 480

detection:
  max_cameras: 1  # Single camera only
```

### For GPU Systems

```yaml
# config.yaml
video:
  target_fps: 30
  resolution_width: 1280
  resolution_height: 720

detection:
  max_cameras: 4  # Multiple cameras supported
```

## License

UmpirAI is released under the MIT License. See [LICENSE](../LICENSE) for details.

## Support

- **Documentation**: [docs/](.)
- **Issues**: [GitHub Issues](https://github.com/yourusername/umpirai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/umpirai/discussions)
