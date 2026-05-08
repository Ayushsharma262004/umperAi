# UmpirAI Quick Reference Card

## 🚀 Quick Commands

### Test Single Video
```bash
# Windows
test_single_video.bat videos\w7.mp4

# Linux/Mac
python run_full_pipeline.py videos/w7.mp4
```

### Test All Videos
```bash
# Windows
test_all_videos.bat

# Linux/Mac
python test_all_videos.py
```

### Start Web Interface
```bash
# Windows
start_webapp.bat

# Linux/Mac
./start_webapp.sh
```

## ⌨️ Keyboard Controls (Interactive Mode)

| Key | Action |
|-----|--------|
| `q` | Quit |
| `p` | Pause/Resume |
| `s` | Save current frame |

## 📊 Your Videos

| Video | Expected Decision |
|-------|-------------------|
| w7.mp4 | WIDE |
| w15.mp4 | WIDE |
| noballs3_mirr.mp4 | NO_BALL |
| noballs8_mirr.mp4 | NO_BALL |
| lbw20_mirr.mp4 | OUT_LBW |
| lbw21_mirr.mp4 | OUT_LBW |
| legalballs32.mp4 | LEGAL_DELIVERY |
| legalballs39.mp4 | LEGAL_DELIVERY |

## 🎨 Visual Elements

| Color | Meaning |
|-------|---------|
| 🟡 Yellow Box | Ball |
| 🟢 Green Box | Player |
| 🟣 Magenta Line | Ball Trajectory |
| 🔴 Red Banner | OUT Decision |
| 🟠 Orange Banner | WIDE/NO_BALL |
| 🟢 Green Banner | LEGAL_DELIVERY |

## 📁 Output Files

| File | Content |
|------|---------|
| `test_report.json` | Detailed JSON results |
| `test_summary.txt` | Readable summary |
| `frame_*.jpg` | Saved frames (press 's') |

## 🔧 Configuration (config_test.yaml)

```yaml
detection:
  model: yolov8n  # yolov8n, yolov8s, yolov8m, yolov8l, yolov8x
  confidence_threshold: 0.5

decision:
  confidence_threshold: 0.7
  enable_lbw: true
  enable_bowled: true
```

## 📚 Documentation

| File | Purpose |
|------|---------|
| `TESTING_GUIDE.md` | Complete testing guide |
| `FULL_PIPELINE_README.md` | System overview |
| `INTEGRATION_COMPLETE.md` | What we built |
| `QUICK_REFERENCE.md` | This card |

## 🐛 Quick Troubleshooting

### No decisions made?
- Lower `confidence_threshold` in config
- Use larger model (yolov8l)
- Check ball visibility

### Slow processing?
- Use yolov8n (fastest)
- Enable GPU if available
- Reduce video resolution

### Import errors?
```bash
pip install ultralytics opencv-python
```

### Model not found?
```bash
python setup_yolov8.py
```

## 📈 Performance

| Model | FPS (CPU) | FPS (GPU) | Accuracy |
|-------|-----------|-----------|----------|
| yolov8n | 7-10 | 60+ | Good |
| yolov8s | 5-7 | 40+ | Better |
| yolov8m | 3-5 | 30+ | Better |
| yolov8l | 2-3 | 30+ | Best |

## ✅ Success Checklist

- [ ] Videos play with annotations
- [ ] Ball detected (yellow boxes)
- [ ] Players detected (green boxes)
- [ ] Trajectory visible (magenta line)
- [ ] Decisions made (banners)
- [ ] Reports generated
- [ ] No crashes

## 🎯 First Test

```bash
test_single_video.bat videos\w7.mp4
```

Expected: WIDE decision around 0.8s

---

**Need help?** Check `TESTING_GUIDE.md` for detailed instructions.
