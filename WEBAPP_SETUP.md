# UmpirAI Web Application Setup Guide

Complete guide to set up and run the UmpirAI web interface for testing with real cricket footage.

## 📋 Prerequisites

- **Node.js 18+** and npm
- **Python 3.10+**
- **UmpirAI system** installed (already done ✅)
- **Cricket video footage** (MP4, AVI, MOV, or MKV format)

## 🚀 Quick Start

### Step 1: Install Backend Dependencies

```bash
# Install FastAPI backend dependencies
cd backend
pip install -r requirements.txt
cd ..
```

### Step 2: Install Frontend Dependencies

```bash
# Install React webapp dependencies
cd webapp
npm install
cd ..
```

### Step 3: Start the Backend API Server

```bash
# Start the FastAPI server
cd backend
python api_server.py
```

The API server will start on `http://localhost:8000`

You should see:
```
🚀 UmpirAI API Server starting...
📡 WebSocket endpoint: ws://localhost:8000/ws
🌐 API docs: http://localhost:8000/docs
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 4: Start the Frontend Development Server

Open a **new terminal** and run:

```bash
# Start the React development server
cd webapp
npm run dev
```

The webapp will start on `http://localhost:3000` (or `http://localhost:5173` with Vite)

You should see:
```
  VITE v5.0.8  ready in 500 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
  ➜  press h to show help
```

### Step 5: Open the Web Interface

Open your browser and navigate to:
```
http://localhost:3000
```

## 🎯 Using the Web Interface

### Dashboard
1. View real-time system statistics
2. Monitor recent decisions
3. Check system health metrics
4. Access quick actions

### Live Monitoring
1. Click **"Start Monitoring"** button
2. The system will begin processing video feeds
3. Watch real-time decisions appear with:
   - Decision type (OUT, WIDE, NO_BALL, etc.)
   - Confidence score
   - Ball tracking visualization
   - Multi-camera feeds

### Testing with Real Cricket Footage

#### Option 1: Using Video Files

1. Place your cricket video files in a directory (e.g., `videos/`)

2. Modify the backend to use video files instead of live cameras:

```python
# In backend/api_server.py, modify the start_monitoring function:

@app.post("/api/start")
async def start_monitoring():
    global umpirai_system
    
    try:
        if umpirai_system is None:
            config = config_manager.load_config('config.yaml')
            umpirai_system = UmpirAISystem(config)
        
        # Add video file sources
        umpirai_system.add_camera('cam1', 'file', 'videos/bowler_end.mp4')
        umpirai_system.add_camera('cam2', 'file', 'videos/batsman_end.mp4')
        
        # Load calibration
        umpirai_system.set_calibration('calibration.json')
        
        umpirai_system.startup()
        
        return {"success": True, "message": "System started successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

3. Click **"Start Monitoring"** in the web interface

#### Option 2: Using Live Camera Feeds

1. Connect your cameras (USB or RTSP)

2. Configure camera sources in `config.yaml`:

```yaml
video:
  sources:
    - camera_id: cam1
      type: rtsp
      path: rtsp://192.168.1.100:554/stream1
    - camera_id: cam2
      type: rtsp
      path: rtsp://192.168.1.101:554/stream1
    - camera_id: cam3
      type: usb
      path: 0
    - camera_id: cam4
      type: usb
      path: 1
```

3. Start monitoring from the web interface

### Calibration

1. Navigate to **Calibration** page
2. Follow the step-by-step wizard:
   - Mark pitch boundary (4 corners)
   - Define crease lines (bowling & batting)
   - Set wide guidelines
   - Mark stump positions
   - Compute camera homography
3. Click **"Save Calibration"** when complete

### Decision History

1. Navigate to **Decision History** page
2. Browse all past decisions
3. Use filters to find specific decision types
4. Export data for analysis

### Analytics

1. Navigate to **Analytics** page
2. View decision distribution charts
3. Analyze confidence score patterns
4. Monitor performance trends over time

### Settings

1. Navigate to **Settings** page
2. Configure detection parameters
3. Adjust tracking settings
4. Set decision thresholds
5. Tune performance options
6. Click **"Save Changes"**

## 🎥 Preparing Cricket Footage

### Video Requirements

- **Format**: MP4, AVI, MOV, or MKV
- **Resolution**: Minimum 1280x720 (HD), recommended 1920x1080 (Full HD)
- **Frame Rate**: 30 FPS or higher
- **Duration**: Any length (system processes frame-by-frame)

### Camera Angles Needed

For best results, use footage from multiple angles:

1. **Bowler End Camera**: Behind the bowler, facing batsman
2. **Batsman End Camera**: Behind the batsman, facing bowler
3. **Side View Camera**: Perpendicular to the pitch
4. **Wide Angle Camera**: Overhead or elevated view

### Sample Footage Sources

- **YouTube**: Download cricket match highlights (use youtube-dl or similar)
- **ICC/Cricket Boards**: Official match footage
- **Local Matches**: Record your own cricket matches
- **Test Datasets**: Use publicly available cricket datasets

### Downloading YouTube Videos

```bash
# Install yt-dlp
pip install yt-dlp

# Download cricket video
yt-dlp -f "best[height<=1080]" -o "videos/cricket_match.mp4" "YOUTUBE_URL"
```

## 🔧 Configuration

### Backend Configuration

Edit `config.yaml` to configure the UmpirAI system:

```yaml
video:
  fps: 30
  resolution: [1920, 1080]
  buffer_size: 30

detection:
  model: yolov8m
  confidence_threshold: 0.7
  nms_threshold: 0.5

tracking:
  max_occlusion_frames: 10
  process_noise: 0.1
  measurement_noise: 0.5

decision:
  confidence_threshold: 0.8
  wide_guideline_distance: 0.5
  enable_lbw: true
  enable_bowled: true
  enable_caught: true

performance:
  target_fps: 30
  fps_threshold: 25
  memory_threshold: 8.0
  enable_gpu: true
```

### Frontend Configuration

Create `webapp/.env` for environment variables:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## 📊 API Documentation

Once the backend is running, visit:
```
http://localhost:8000/docs
```

This provides interactive API documentation with:
- All available endpoints
- Request/response schemas
- Try-it-out functionality

## 🐛 Troubleshooting

### Backend Issues

**Problem**: `ModuleNotFoundError: No module named 'fastapi'`
```bash
cd backend
pip install -r requirements.txt
```

**Problem**: Port 8000 already in use
```bash
# Change port in api_server.py
uvicorn.run("api_server:app", host="0.0.0.0", port=8001)
```

**Problem**: Cannot import UmpirAI modules
```bash
# Ensure you're in the project root directory
cd /path/to/Ai_umpire
python backend/api_server.py
```

### Frontend Issues

**Problem**: `npm: command not found`
```bash
# Install Node.js from https://nodejs.org/
# Or use nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
```

**Problem**: Port 3000 already in use
```bash
# Vite will automatically use next available port
# Or specify in vite.config.js:
server: { port: 3001 }
```

**Problem**: API connection refused
- Ensure backend is running on port 8000
- Check CORS settings in `api_server.py`
- Verify proxy configuration in `vite.config.js`

### Video Processing Issues

**Problem**: Video not loading
- Check video file path is correct
- Ensure video codec is supported (H.264 recommended)
- Verify file permissions

**Problem**: Low FPS during processing
- Reduce video resolution in settings
- Use smaller YOLO model (yolov8n or yolov8s)
- Enable GPU acceleration
- Close other applications

**Problem**: High memory usage
- Reduce buffer size in config
- Lower video resolution
- Decrease max_cameras setting

## 🎬 Example Workflow

### Complete Test Run

1. **Prepare Video**:
   ```bash
   mkdir videos
   # Place your cricket video in videos/match.mp4
   ```

2. **Start Backend**:
   ```bash
   cd backend
   python api_server.py
   ```

3. **Start Frontend** (new terminal):
   ```bash
   cd webapp
   npm run dev
   ```

4. **Open Browser**:
   - Navigate to `http://localhost:3000`

5. **Calibrate System**:
   - Go to Calibration page
   - Complete all calibration steps
   - Save calibration

6. **Configure Settings**:
   - Go to Settings page
   - Adjust detection model (yolov8s for faster processing)
   - Set confidence thresholds
   - Save changes

7. **Start Monitoring**:
   - Go to Live Monitoring page
   - Click "Start Monitoring"
   - Watch real-time decisions!

8. **Review Results**:
   - Check Decision History for all decisions
   - View Analytics for performance metrics
   - Export data if needed

## 📈 Performance Optimization

### For Real-Time Processing

```yaml
# config.yaml - High Performance
detection:
  model: yolov8m  # Balanced speed/accuracy
video:
  resolution: [1280, 720]  # HD resolution
  fps: 30
performance:
  enable_gpu: true
  target_fps: 30
```

### For Accuracy

```yaml
# config.yaml - High Accuracy
detection:
  model: yolov8x  # Most accurate
  confidence_threshold: 0.8
video:
  resolution: [1920, 1080]  # Full HD
  fps: 30
```

### For Low-Resource Systems

```yaml
# config.yaml - Low Resource
detection:
  model: yolov8n  # Fastest
  confidence_threshold: 0.6
video:
  resolution: [960, 540]
  fps: 25
performance:
  enable_gpu: false
  memory_threshold: 4.0
```

## 🎉 Next Steps

1. **Test with Different Footage**: Try various cricket videos
2. **Fine-tune Settings**: Adjust thresholds for your use case
3. **Collect Data**: Export decisions for analysis
4. **Improve Calibration**: Refine calibration for better accuracy
5. **Add Features**: Extend the webapp with custom functionality

## 📞 Support

For issues or questions:
- Check the main UmpirAI documentation
- Review API docs at `http://localhost:8000/docs`
- Open an issue on GitHub

---

**Happy Testing! 🏏**
