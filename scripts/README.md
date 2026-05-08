# UmpirAI Test Scripts

This directory contains scripts for system testing and validation.

## Available Scripts

### test_single_delivery.py
Test individual deliveries against expected decisions.

**Usage:**
```bash
python scripts/test_single_delivery.py \
    --video test_data/wide_001.mp4 \
    --calibration calibration.json \
    --expected-decision WIDE \
    --output results/wide_001.json
```

### simulate_cricket_footage.py
Generate synthetic cricket footage for testing without real videos.

**Usage:**
```bash
python scripts/simulate_cricket_footage.py \
    --scenario wide \
    --output test_data/simulated/wide_001.mp4 \
    --duration 10
```

### measure_accuracy.py
Calculate accuracy metrics from test results.

**Usage:**
```bash
python scripts/measure_accuracy.py \
    --results results/ \
    --ground-truth ground_truth.json \
    --output accuracy_report.json
```

### analyze_test_results.py
Generate comprehensive test analysis report.

**Usage:**
```bash
python scripts/analyze_test_results.py \
    --results-dir results/ \
    --ground-truth ground_truth.json \
    --output test_report.html
```

## Test Data Structure

```
test_data/
├── single_deliveries/
│   ├── wide/
│   ├── no_ball/
│   ├── bowled/
│   ├── lbw/
│   └── caught/
├── overs/
├── multi_camera/
├── full_match/
└── difficult/
```

## Results Structure

```
results/
├── single_deliveries/
├── overs/
├── multi_camera/
├── continuous_operation/
└── error_recovery/
```

## Ground Truth Format

```json
{
  "video_id": "wide_001",
  "deliveries": [
    {
      "timestamp": 5.2,
      "decision_type": "WIDE",
      "confidence": 1.0,
      "details": {}
    }
  ]
}
```

## Running All Tests

```bash
# Run all system tests
python scripts/run_all_tests.py \
    --test-data test_data/ \
    --calibration calibration.json \
    --output results/

# Generate report
python scripts/generate_test_report.py \
    --results results/ \
    --output test_report.pdf
```

## Notes

- Ensure system is calibrated before running tests
- Use `--verbose` flag for detailed output
- Check `docs/SYSTEM_TESTING.md` for comprehensive testing guide
