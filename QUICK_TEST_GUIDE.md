# 🏏 Quick Test Guide - Your Cricket Videos

## ✅ What You Have

**8 Cricket Videos Ready:**
- ✅ 2 LBW scenarios (lbw20_mirr.mp4, lbw21_mirr.mp4)
- ✅ 2 Legal deliveries (legalballs32.mp4, legalballs39.mp4)
- ✅ 2 No balls (noballs3_mirr.mp4, noballs8_mirr.mp4)
- ✅ 2 Wide balls (w15.mp4, w7.mp4)

**Web Application Running:**
- ✅ Backend: http://localhost:8000
- ✅ Frontend: http://localhost:3000
- ✅ API Docs: http://localhost:8000/docs

## 🎯 Quick Test (5 Minutes)

### Option 1: View Videos with Overlays

Run this to see your videos with decision overlays:

```bash
python process_videos.py
```

**Controls:**
- Press `q` to skip to next video
- Press `ESC` to exit

This will show each video with the expected decision overlaid.

### Option 2: Use the Web Interface

1. **Open Browser:**
   ```
   http://localhost:3000
   ```

2. **Explore the Interface:**
   - **Dashboard** - See system overview
   - **Live Monitoring** - Real-time monitoring (currently demo mode)
   - **Settings** - Configure the system
   - **Analytics** - View charts and metrics

3. **Configure Settings:**
   - Go to Settings page
   - Set Detection Model: `yolov8n` (fastest)
   - Set Confidence Threshold: `0.7`
   - Click "Save Changes"

## 📊 Your Video Details

### LBW Videos
```
lbw20_mirr.mp4
  • Resolution: 852x480
  • FPS: 25
  • Duration: 1.8 seconds
  • Expected: OUT - LBW 🔴

lbw21_mirr.mp4
  • Resolution: 852x480
  • FPS: 25
  • Duration: 0.88 seconds
  • Expected: OUT - LBW 🔴
```

### Legal Delivery Videos
```
legalballs32.mp4
  • Resolution: 852x480
  • FPS: 25
  • Duration: 2.2 seconds
  • Expected: LEGAL DELIVERY 🟢

legalballs39.mp4
  • Resolution: 852x480
  • FPS: 25
  • Duration: 1.6 seconds
  • Expected: LEGAL DELIVERY 🟢
```

### No Ball Videos
```
noballs3_mirr.mp4
  • Resolution: 852x480
  • FPS: 25
  • Duration: 1.2 seconds
  • Expected: NO BALL 🟠

noballs8_mirr.mp4
  • Resolution: 1920x1080
  • FPS: 60
  • Duration: 2.88 seconds
  • Expected: NO BALL 🟠
```

### Wide Ball Videos
```
w15.mp4
  • Resolution: 1920x1080
  • FPS: 29
  • Duration: 2.83 seconds
  • Expected: WIDE 🟡

w7.mp4
  • Resolution: 1920x1080
  • FPS: 30
  • Duration: 1.57 seconds
  • Expected: WIDE 🟡
```

## 🔧 Recommended Settings

For your videos, use these settings:

```yaml
Detection:
  Model: yolov8n (fastest) or yolov8s (balanced)
  Confidence Threshold: 0.7
  
Video:
  Target FPS: 25 (matches most of your videos)
  Resolution: Auto-detect
  
Performance:
  Enable GPU: Yes (if available)
  Memory Threshold: 8 GB
```

## 🎬 Full AI Processing (Coming Next)

To integrate full AI processing with your videos:

1. **Calibration Required:**
   - The system needs to understand the camera view
   - Go to Calibration page in web interface
   - Mark pitch boundaries, creases, stumps

2. **Model Download:**
   - YOLOv8 model will download automatically on first run
   - This may take a few minutes
   - Requires internet connection

3. **Processing:**
   - System will detect ball, players, stumps
   - Track ball trajectory
   - Make umpiring decisions
   - Display results in real-time

## 📝 Test Scenarios

### Test 1: LBW Detection
```bash
# Test with LBW videos
python process_videos.py
# Watch lbw20_mirr.mp4 and lbw21_mirr.mp4
```

**Expected Results:**
- Ball trajectory should be tracked
- Impact point detected
- Decision: OUT - LBW
- Confidence: >80%

### Test 2: No Ball Detection
```bash
# Test with No Ball videos
python process_videos.py
# Watch noballs3_mirr.mp4 and noballs8_mirr.mp4
```

**Expected Results:**
- Bowler's foot position tracked
- Front foot over crease detected
- Decision: NO BALL
- Confidence: >90%

### Test 3: Wide Ball Detection
```bash
# Test with Wide Ball videos
python process_videos.py
# Watch w15.mp4 and w7.mp4
```

**Expected Results:**
- Ball trajectory tracked
- Ball outside wide guideline
- Decision: WIDE
- Confidence: >85%

### Test 4: Legal Delivery
```bash
# Test with Legal Delivery videos
python process_videos.py
# Watch legalballs32.mp4 and legalballs39.mp4
```

**Expected Results:**
- All checks pass
- No violations detected
- Decision: LEGAL DELIVERY
- Confidence: >95%

## 🎯 Success Criteria

For each video, check:
- ✅ Video plays smoothly
- ✅ Decision matches expected outcome
- ✅ Confidence score >70%
- ✅ Processing time <2 seconds
- ✅ No errors or crashes

## 🐛 Troubleshooting

### Video Won't Play
```bash
# Check if OpenCV can read the video
python -c "import cv2; cap = cv2.VideoCapture('videos/w7.mp4'); print('OK' if cap.isOpened() else 'FAIL')"
```

### Low FPS
- Use smaller model (yolov8n)
- Reduce video resolution
- Enable GPU acceleration
- Close other applications

### Wrong Decisions
- Check calibration settings
- Adjust confidence threshold
- Review video quality
- Ensure good lighting in video

## 📚 Next Steps

1. **✅ Test Videos** - Run `python process_videos.py`
2. **🌐 Explore Web Interface** - http://localhost:3000
3. **⚙️ Configure Settings** - Optimize for your hardware
4. **🎯 Calibrate System** - For accurate decisions
5. **📊 Review Analytics** - Check performance metrics

## 💡 Tips

- **Start Small**: Test with shortest video first (lbw21_mirr.mp4)
- **Check Quality**: Higher resolution videos (1920x1080) work better
- **Be Patient**: First run downloads models (may take time)
- **Monitor Performance**: Check FPS and latency in web interface
- **Iterate**: Adjust settings based on results

## 🎉 You're Ready!

Your cricket videos are perfect for testing the UmpirAI system!

**Quick Start:**
```bash
python process_videos.py
```

**Web Interface:**
```
http://localhost:3000
```

**Have fun testing! 🏏**
