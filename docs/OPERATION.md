# UmpirAI Operation Manual

This manual provides detailed instructions for operating the UmpirAI cricket umpiring system during matches.

## Table of Contents

- [Pre-Match Setup](#pre-match-setup)
- [System Startup](#system-startup)
- [During Match Operation](#during-match-operation)
- [Decision Review](#decision-review)
- [System Monitoring](#system-monitoring)
- [Post-Match Procedures](#post-match-procedures)
- [Emergency Procedures](#emergency-procedures)
- [Best Practices](#best-practices)

## Pre-Match Setup

### 1. Hardware Setup

**Camera Placement:**
- Position cameras to cover the entire pitch
- Ensure clear view of stumps, crease lines, and pitch boundaries
- Avoid backlighting and direct sunlight
- Recommended positions:
  - Camera 1: Behind bowler (straight-on view)
  - Camera 2: Side-on view (square leg)
  - Camera 3: Behind batsman (reverse angle)
  - Camera 4: Overhead view (if available)

**Network Setup:**
- Verify all cameras are accessible on the network
- Test RTSP/HTTP streams are working
- Ensure stable network connection (wired preferred)
- Check bandwidth is sufficient for multiple streams

**System Hardware:**
- Connect system to power supply with UPS backup
- Ensure adequate cooling/ventilation
- Connect display monitors
- Test audio output (if using announcements)

### 2. Software Configuration

**Load Configuration:**
```bash
# Use pre-configured match settings
python umpirai_cli.py config show --file match_config.yaml
```

**Verify Settings:**
- Video resolution and FPS appropriate for cameras
- Detection confidence thresholds set correctly
- Decision engine detectors enabled as needed
- Logging configured for match recording

### 3. Calibration

**Load Existing Calibration:**
```bash
# If pitch was previously calibrated
python umpirai_cli.py run --calibration venue_pitch_1.json
```

**New Calibration:**
```bash
# If first time at venue or pitch changed
python umpirai_cli.py calibrate --camera rtsp://camera1 --output new_calibration.json
```

**Calibration Steps:**
1. Mark pitch boundary corners
2. Mark bowling crease
3. Mark batting crease
4. Mark stump positions
5. Verify wide guidelines
6. Save calibration

**Calibration Verification:**
- Check overlay aligns with actual pitch markings
- Verify stump positions are accurate
- Test with practice delivery if possible

## System Startup

### Standard Startup Procedure

```bash
# 1. Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# 2. Start system with configuration
python umpirai_cli.py run \
  --config match_config.yaml \
  --calibration venue_calibration.json \
  --cameras rtsp://camera1 rtsp://camera2 rtsp://camera3
```

### Startup Checklist

- [ ] Virtual environment activated
- [ ] Configuration file loaded
- [ ] Calibration file loaded
- [ ] All cameras connected and streaming
- [ ] Video feeds displaying correctly
- [ ] System logs showing no errors
- [ ] Performance metrics within normal range
- [ ] Decision output display working
- [ ] Backup systems ready (if applicable)

### Startup Verification

**Check System Status:**
- All cameras showing "Connected"
- FPS at target rate (30 FPS)
- Detection confidence levels normal
- No error alerts

**Test Detection:**
- Verify ball detection working
- Check stump detection
- Confirm player detection
- Test crease line detection

**Test Decision Output:**
- Verify text display working
- Check visual indicators
- Test audio announcements (if enabled)

## During Match Operation

### Normal Operation

**System runs automatically:**
- Captures video from all cameras
- Detects cricket elements in real-time
- Tracks ball trajectory
- Makes umpiring decisions
- Outputs decisions with confidence scores

**Operator Responsibilities:**
1. Monitor system performance
2. Watch for alerts
3. Review uncertain decisions
4. Log any issues
5. Maintain system logs

### Monitoring Dashboard

**Key Metrics to Watch:**
- **FPS**: Should stay at 30 FPS (alert if <25)
- **Latency**: Should be <1 second (alert if >2s)
- **Detection Accuracy**: Should be >85%
- **Memory Usage**: Should be <90%
- **Decision Confidence**: Note decisions <80%

**Visual Indicators:**
- 🟢 Green: Legal delivery
- 🟡 Yellow: Wide ball
- 🔴 Red: No ball
- 🔵 Blue: Dismissal
- ⚠️ Orange: Uncertain decision (requires review)

### Decision Types

**Automatic Decisions (High Confidence ≥80%):**
- System makes decision automatically
- Decision displayed immediately
- Logged for record

**Review Required (Confidence <80%):**
- System flags for manual review
- Operator reviews video evidence
- Operator confirms or overrides decision
- Override logged with justification

### Handling Uncertain Decisions

**When System Flags Decision:**
1. Pause if necessary (between deliveries)
2. Review video from all camera angles
3. Check trajectory visualization
4. Consult with on-field umpire if needed
5. Make final decision
6. Log decision and reasoning

**Override Procedure:**
```
1. System Decision: "Wide Ball (Confidence: 75%)"
2. Operator Review: Check video evidence
3. Operator Decision: Confirm or Override
4. Log: "Operator confirmed: Wide Ball"
```

### Common Scenarios

**Scenario 1: Close LBW Decision**
- System provides trajectory projection
- Shows pitching point, impact point, and projected path
- Displays confidence score
- Operator reviews and confirms/overrides

**Scenario 2: Caught Behind**
- System detects ball-bat contact
- Tracks ball to fielder
- Verifies fielder control
- Checks for ground contact
- Makes decision with confidence

**Scenario 3: No Ball (Foot Over Crease)**
- System detects bowler foot position at release
- Measures distance from crease
- Makes decision
- Displays foot position overlay

**Scenario 4: Wide Ball**
- System tracks ball path relative to batsman
- Checks against wide guidelines
- Adjusts for batsman movement
- Makes decision

## Decision Review

### Review Interface

**Access Review:**
- System automatically flags low-confidence decisions
- Operator can manually request review of any decision

**Review Information Displayed:**
- Decision type and confidence
- Video clips from all camera angles
- Trajectory visualization
- Detection confidence scores
- Timing information

### Override Process

**When to Override:**
- System confidence <80%
- Visual evidence contradicts system decision
- On-field umpire requests review
- Obvious system error

**How to Override:**
1. Access decision in review interface
2. Review all available evidence
3. Select correct decision
4. Provide justification
5. Confirm override

**Override Logging:**
- Original system decision recorded
- Override decision recorded
- Justification logged
- Timestamp recorded
- Used for system improvement

## System Monitoring

### Performance Monitoring

**Real-Time Metrics:**
```
FPS: 30.2 ✓
Latency: 450ms ✓
CPU: 65% ✓
Memory: 72% ✓
Detection Accuracy: 92% ✓
```

**Alert Conditions:**
- FPS <25: "Frame rate degraded"
- Latency >2s: "Processing latency high"
- CPU >90%: "High CPU usage"
- Memory >90%: "Memory pressure"
- Accuracy <80%: "Detection quality low"

### Handling Alerts

**FPS Degradation:**
1. Check camera connections
2. Verify network bandwidth
3. Consider reducing resolution
4. Check system resources

**High Latency:**
1. Check processing load
2. Verify GPU is being used (if available)
2. Consider disabling non-essential detectors
3. Reduce number of cameras if necessary

**Detection Quality Issues:**
1. Check lighting conditions
2. Verify camera focus
3. Check for obstructions
4. Review calibration

### Log Monitoring

**Event Logs:**
- All decisions logged with timestamps
- Confidence scores recorded
- Video references saved
- Review decisions logged

**Performance Logs:**
- System metrics logged every minute
- Alerts logged immediately
- Resource usage tracked

**Access Logs:**
```bash
# View recent events
tail -f logs/events_20240508.jsonl

# View performance metrics
tail -f logs/performance_20240508.jsonl
```

## Post-Match Procedures

### System Shutdown

**Graceful Shutdown:**
```bash
# Press Ctrl+C to stop system
# System will:
# 1. Complete current processing
# 2. Save all logs
# 3. Close camera connections
# 4. Shut down cleanly
```

**Shutdown Checklist:**
- [ ] All decisions logged
- [ ] Logs saved successfully
- [ ] Camera connections closed
- [ ] No error messages
- [ ] System status: Stopped

### Data Backup

**Backup Match Data:**
```bash
# Copy logs to backup location
cp -r logs/ backup/match_YYYYMMDD/

# Copy calibration used
cp calibration.json backup/match_YYYYMMDD/

# Copy configuration used
cp config.yaml backup/match_YYYYMMDD/
```

### Match Report

**Generate Report:**
- Total deliveries processed
- Decision breakdown (legal, wide, no ball, dismissals)
- Average confidence scores
- System performance metrics
- Any issues encountered
- Override decisions made

### System Maintenance

**After Each Match:**
- Review system logs for errors
- Check disk space
- Verify backups completed
- Clean up temporary files
- Update match statistics

**Weekly Maintenance:**
- Review system performance trends
- Update model if new version available
- Check for software updates
- Verify calibrations still valid

## Emergency Procedures

### System Crash

**Immediate Actions:**
1. Note time and circumstances
2. Check if logs were saved
3. Restart system if possible
4. Fall back to manual umpiring if needed

**Recovery:**
```bash
# Restart system
python umpirai_cli.py run --config config.yaml --calibration calibration.json --cameras ...
```

### Camera Failure

**Single Camera Failure:**
- System continues with remaining cameras
- Decision confidence may be lower
- Monitor for degraded performance

**Multiple Camera Failure:**
- System may need to operate with reduced capability
- Consider manual umpiring for critical decisions
- Attempt to restore cameras

### Network Issues

**Network Interruption:**
- System alerts on camera disconnection
- Attempts automatic reconnection
- Falls back to available cameras

**Recovery:**
- Check network connectivity
- Verify camera accessibility
- Restart cameras if needed
- Restart system if necessary

### Power Failure

**With UPS:**
- System continues on battery power
- Graceful shutdown if battery low
- Logs saved automatically

**Without UPS:**
- System stops immediately
- May lose recent data
- Restart required

## Best Practices

### Operational Best Practices

1. **Always calibrate before matches** at new venues
2. **Test system** with practice deliveries before match
3. **Monitor performance** continuously during match
4. **Review uncertain decisions** promptly
5. **Keep backup systems** ready
6. **Document all issues** for improvement
7. **Regular maintenance** between matches

### Decision Making Best Practices

1. **Trust high-confidence decisions** (≥90%)
2. **Review medium-confidence decisions** (70-90%)
3. **Always review low-confidence decisions** (<70%)
4. **Use multiple camera angles** for reviews
5. **Consult trajectory visualizations** for LBW
6. **Document override reasoning** clearly

### Performance Optimization

1. **Use wired network connections** for cameras
2. **Ensure adequate lighting** on pitch
3. **Keep cameras clean** and focused
4. **Use GPU acceleration** if available
5. **Monitor system resources** proactively
6. **Close unnecessary applications** on system

### Safety and Reliability

1. **Use UPS** for power backup
2. **Have backup system** ready
3. **Train multiple operators**
4. **Keep manual umpiring** as fallback
5. **Regular system testing**
6. **Maintain equipment** properly

## Troubleshooting During Operation

### Issue: Decision Latency Increasing

**Symptoms:** Decisions taking >2 seconds
**Solutions:**
- Check system resources
- Reduce video resolution temporarily
- Disable non-critical detectors
- Restart system if necessary

### Issue: Low Detection Confidence

**Symptoms:** Many decisions flagged for review
**Solutions:**
- Check lighting conditions
- Verify camera focus and positioning
- Review calibration accuracy
- Check for obstructions

### Issue: Camera Feed Lost

**Symptoms:** Camera shows "Disconnected"
**Solutions:**
- Check network connection
- Verify camera power
- Test camera URL/stream
- Restart camera
- Continue with remaining cameras

## Support During Operation

**For Technical Issues:**
- Check troubleshooting section
- Review system logs
- Contact technical support if needed

**For Rule Clarifications:**
- Consult ICC cricket laws
- Refer to umpiring guidelines
- Consult with match referee

## Training and Certification

Operators should be trained on:
- System operation procedures
- Decision review process
- Emergency procedures
- Cricket rules and regulations
- System troubleshooting

Recommended training: 8-16 hours including:
- 4 hours classroom instruction
- 4 hours hands-on practice
- 4-8 hours supervised operation

## See Also

- [Installation Guide](INSTALLATION.md)
- [Configuration Guide](CONFIGURATION.md)
- [Calibration Guide](CALIBRATION.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [CLI Reference](CLI.md)
