# UmpirAI Full Pipeline Testing Guide

## 🎯 Overview

This guide explains how to test the complete UmpirAI system with YOLOv8 object detection on your cricket videos.

## 📋 Prerequisites

✅ All dependencies installed (from previous setup)
✅ YOLOv8 model downloaded (yolov8n.pt or yolov8l.pt)
✅ Cricket videos in `videos/` directory
✅ Configuration file (`config_test.yaml`)

## 🚀 Quick Start

### Test Single Video (Interactive)

```bash
python run_full_pipeline.py videos/w7.mp4
```

This will:
- Open a display window showing real-time processing
- Detect players and ball using YOLOv8
- Track ball trajectory
- Make umpiring decisions
- Show decisions as overlays on video

**Controls:**
- `q` - Quit
- `p` - Pause/Resume
- `s` - Save current frame

### Test All Videos (Batch Mode)

```bash
python test_all_videos.py
```

This will:
- Process all videos in `videos/` directory
- Run without display (faster)
- Generate comprehensive report
- Save results to `test_report.json` and `test_summary.txt`

## 📊 What to Expect

### 1. Wide Ball Videos (w7.mp4, w15.mp4)

**Expected Decisions:**
- `WIDE` - Ball passes outside wide guideline
- High confidence (>80%)

**What You'll See:**
- Ball detected and tracked
- Trajectory shown in magenta
- Wide decision banner when ball crosses guideline

### 2. No Ball Videos (noballs3_mirr.mp4, noballs8_mirr.mp4)

**Expected Decisions:**
- `NO_BALL` - Bowler foot fault or ball height violation
- Medium to high confidence (70-90%)

**What You'll See:**
- Players detected (bowler, batsman)
- Ball trajectory
- No ball decision when violation detected

### 3. LBW Videos (lbw20_mirr.mp4, lbw21_mirr.mp4)

**Expected Decisions:**
- `OUT_LBW` - Leg Before Wicket
- Medium confidence (70-85%)

**What You'll See:**
- Ball trajectory toward stumps
- Batsman detected
- LBW decision if ball would hit stumps

### 4. Legal Delivery Videos (legalballs32.mp4, legalballs39.mp4)

**Expected Decisions:**
- `LEGAL_DELIVERY` - Fair delivery
- High confidence (>85%)

**What You'll See:**
- Normal ball trajectory
- No violations detected
- Legal delivery confirmation

## 🔧 Configuration

Edit `config_test.yaml` to adjust settings:

```yaml
detection:
  model: yolov8n  # Change to yolov8l for better accuracy (slower)
  confidence_threshold: 0.5  # Lower = more detections, higher = fewer false positives

decision:
  confidence_threshold: 0.7  # Minimum confidence for decisions
  enable_lbw: true  # Enable/disable LBW detection
  enable_bowled: true  # Enable/disable bowled detection
```

## 📈 Performance Expectations

### On CPU (Current Setup)

| Model | FPS | Accuracy | Use Case |
|-------|-----|----------|----------|
| yolov8n | 7-10 | Good | Fast testing |
| yolov8s | 5-7 | Better | Balanced |
| yolov8m | 3-5 | Better | More accurate |
| yolov8l | 2-3 | Best | Production |

### On GPU (If Available)

| Model | FPS | Accuracy |
|-------|-----|----------|
| yolov8n | 60+ | Good |
| yolov8l | 30+ | Best |

## 🎬 Example Commands

### Test Specific Video Types

```bash
# Test wide ball
python run_full_pipeline.py videos/w7.mp4

# Test LBW
python run_full_pipeline.py videos/lbw20_mirr.mp4

# Test no ball
python run_full_pipeline.py videos/noballs3_mirr.mp4

# Test legal delivery
python run_full_pipeline.py videos/legalballs32.mp4
```

### Use Different Models

```bash
# Fast (Nano model)
python run_full_pipeline.py videos/w7.mp4 config_test.yaml

# Accurate (Large model) - Edit config first to set model: yolov8l
python run_full_pipeline.py videos/w7.mp4 config_test.yaml
```

### Batch Testing

```bash
# Test all videos
python test_all_videos.py

# Test videos in different directory
python test_all_videos.py path/to/videos

# Use custom config
python test_all_videos.py videos custom_config.yaml
```

## 📊 Understanding Results

### Display Window Elements

**Top Info Bar:**
- Frame number and total frames
- Processing time per frame
- Number of detections (balls, players)
- Tracking status

**Detections:**
- Yellow boxes = Ball
- Green boxes = Players
- Magenta line = Ball trajectory

**Decision Banner (Bottom):**
- Decision type (WIDE, NO_BALL, OUT, etc.)
- Confidence percentage
- Brief description

### Report Files

**test_report.json:**
- Detailed JSON with all results
- Frame-by-frame decisions
- Processing times
- Detection counts

**test_summary.txt:**
- Human-readable summary
- Per-video statistics
- Decision breakdown

## 🐛 Troubleshooting

### Issue: No Decisions Made

**Possible Causes:**
1. Not enough frames processed (need >5 frames with ball detected)
2. Ball not detected by YOLOv8
3. Confidence threshold too high

**Solutions:**
- Lower `confidence_threshold` in config
- Use larger YOLOv8 model (yolov8l)
- Check if ball is visible in video

### Issue: Slow Processing

**Possible Causes:**
1. Large YOLOv8 model on CPU
2. High resolution video

**Solutions:**
- Use yolov8n (nano) model
- Reduce video resolution in config
- Enable GPU if available

### Issue: Wrong Decisions

**Possible Causes:**
1. Poor ball detection
2. Incorrect calibration
3. Insufficient trajectory data

**Solutions:**
- Improve detection confidence threshold
- Adjust calibration parameters
- Ensure ball is tracked for longer

### Issue: "Model not found"

**Solution:**
```bash
# Download the model
python setup_yolov8.py
```

### Issue: Import errors

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt
pip install ultralytics opencv-python
```

## 🎯 Next Steps

### 1. Optimize Performance
- Test with GPU if available
- Fine-tune confidence thresholds
- Adjust tracking parameters

### 2. Improve Accuracy
- Train custom YOLOv8 model on cricket dataset
- Add stump detection (not in COCO dataset)
- Calibrate for specific camera angles

### 3. Integrate with Web Interface
- Connect to FastAPI backend
- Stream decisions to web UI
- Enable real-time monitoring

### 4. Production Deployment
- Multi-camera setup
- Real-time processing
- Decision review system

## 📚 Additional Resources

- **YOLOv8 Documentation:** https://docs.ultralytics.com/
- **UmpirAI Architecture:** See `ARCHITECTURE.md`
- **Web Interface Guide:** See `WEBAPP_SETUP.md`
- **API Documentation:** See `backend/api_server.py`

## 💡 Tips

1. **Start with yolov8n** for fast testing, then upgrade to yolov8l for accuracy
2. **Test one video first** before batch processing
3. **Save interesting frames** using 's' key for analysis
4. **Check test_summary.txt** for quick overview of results
5. **Use batch mode** for comprehensive testing without display

## 🏏 Expected Test Results

Based on your 8 videos, you should see:

- **2 Wide decisions** (from w7.mp4, w15.mp4)
- **2 No ball decisions** (from noballs3_mirr.mp4, noballs8_mirr.mp4)
- **2 LBW decisions** (from lbw20_mirr.mp4, lbw21_mirr.mp4)
- **2 Legal delivery confirmations** (from legalballs32.mp4, legalballs39.mp4)

**Note:** Actual results may vary based on:
- Video quality and angle
- Ball visibility
- Detection confidence
- Tracking accuracy

## ✅ Success Criteria

Your system is working correctly if:

1. ✅ Videos play smoothly with detections
2. ✅ Ball is detected and tracked in most frames
3. ✅ Players are detected consistently
4. ✅ Decisions are made with reasonable confidence (>70%)
5. ✅ Decision types match video content (wide videos → WIDE decisions)
6. ✅ Processing runs without crashes
7. ✅ Reports are generated successfully

---

**Ready to test?** Start with:
```bash
python run_full_pipeline.py videos/w7.mp4
```

Good luck! 🏏🎯
