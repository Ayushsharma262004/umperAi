# 📚 UmpirAI Project - Complete Index

**Your complete guide to the UmpirAI AI-Powered Cricket Umpiring System**

## 🎯 Quick Navigation

### 🚀 Getting Started
- **[GETTING_STARTED.md](GETTING_STARTED.md)** ⭐ **START HERE!**
  - 5-minute quick start guide
  - Installation instructions
  - First test run

- **[WEBAPP_COMPLETE.md](WEBAPP_COMPLETE.md)** ✅ **COMPLETION STATUS**
  - What has been built
  - Statistics and metrics
  - Launch commands

### 📖 Web Application Documentation
- **[README_WEBAPP.md](README_WEBAPP.md)** - Main webapp documentation
- **[WEBAPP_SETUP.md](WEBAPP_SETUP.md)** - Detailed setup guide
- **[WEBAPP_SUMMARY.md](WEBAPP_SUMMARY.md)** - Feature summary
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture
- **[VISUAL_GUIDE.md](VISUAL_GUIDE.md)** - Visual walkthrough

### 🏗️ Core System Documentation
- **[docs/INSTALLATION.md](docs/INSTALLATION.md)** - Core system installation
- **[docs/OPERATION.md](docs/OPERATION.md)** - Operation manual
- **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)** - Configuration guide
- **[docs/CLI.md](docs/CLI.md)** - Command-line interface
- **[docs/SYSTEM_TESTING.md](docs/SYSTEM_TESTING.md)** - System testing guide
- **[docs/PERFORMANCE_OPTIMIZATION.md](docs/PERFORMANCE_OPTIMIZATION.md)** - Performance tuning
- **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Troubleshooting guide

## 📂 Project Structure

```
UmpirAI Project/
│
├── 🌐 Web Application
│   ├── webapp/                    # React frontend
│   │   ├── src/pages/             # 6 complete pages
│   │   ├── src/components/        # Reusable components
│   │   └── package.json           # Dependencies
│   │
│   └── backend/                   # FastAPI server
│       ├── api_server.py          # Main API
│       └── requirements.txt       # Dependencies
│
├── 🎯 Core System
│   ├── umpirai/                   # Main system code
│   │   ├── video/                 # Video processing
│   │   ├── detection/             # Object detection
│   │   ├── tracking/              # Ball tracking
│   │   ├── decision/              # Decision engine
│   │   ├── calibration/           # Calibration
│   │   ├── output/                # Decision output
│   │   ├── logging/               # Event logging
│   │   ├── performance/           # Performance monitoring
│   │   ├── review/                # Decision review
│   │   ├── training/              # Training data
│   │   ├── config/                # Configuration
│   │   ├── cli/                   # Command-line interface
│   │   └── system/                # System integration
│   │
│   └── tests/                     # 705 passing tests ✅
│       ├── test_*.py              # Unit tests
│       └── test_*_properties.py   # Property-based tests
│
├── 📚 Documentation
│   ├── docs/                      # Core system docs
│   ├── examples/                  # Example scripts
│   ├── scripts/                   # Utility scripts
│   │
│   ├── GETTING_STARTED.md         # ⭐ Start here
│   ├── WEBAPP_COMPLETE.md         # ✅ Completion status
│   ├── README_WEBAPP.md           # Main webapp docs
│   ├── WEBAPP_SETUP.md            # Setup guide
│   ├── WEBAPP_SUMMARY.md          # Feature summary
│   ├── ARCHITECTURE.md            # Architecture
│   ├── VISUAL_GUIDE.md            # Visual walkthrough
│   └── INDEX.md                   # This file
│
├── 🚀 Startup Scripts
│   ├── start_webapp.sh            # Linux/Mac
│   └── start_webapp.bat           # Windows
│
└── ⚙️ Configuration
    ├── config.yaml                # Main config
    ├── config.yaml.example        # Config template
    ├── config_high_performance.yaml
    ├── config_balanced.yaml
    └── config_low_resource.yaml
```

## 🎯 Common Tasks

### Starting the Application
```bash
# Windows
start_webapp.bat

# Linux/Mac
./start_webapp.sh
```

### Running Tests
```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_decision_engine.py -v

# With coverage
python -m pytest tests/ --cov=umpirai
```

### Using the CLI
```bash
# Run with video file
python umpirai_cli.py run --video videos/match.mp4 --calibration calibration.json

# Calibrate cameras
python umpirai_cli.py calibrate --output calibration.json

# Test system
python umpirai_cli.py test --calibration calibration.json
```

### Accessing Documentation
```bash
# API documentation (after starting backend)
http://localhost:8000/docs

# Web interface
http://localhost:3000
```

## 📊 System Components

### Frontend Pages
1. **Dashboard** (`/`) - System overview
2. **Live Monitoring** (`/live`) - Real-time decisions
3. **Decision History** (`/history`) - Browse decisions
4. **Calibration** (`/calibration`) - Camera setup
5. **Analytics** (`/analytics`) - Charts & metrics
6. **Settings** (`/settings`) - Configuration

### Backend Endpoints
- `GET /api/status` - System status
- `POST /api/start` - Start monitoring
- `POST /api/stop` - Stop monitoring
- `GET /api/decisions` - Decision history
- `GET /api/calibration` - Calibration data
- `GET /api/analytics/*` - Analytics data
- `GET/PUT /api/settings` - Settings
- `ws://localhost:8000/ws` - WebSocket

### Core Modules
- **Video Processing** - Multi-camera capture & sync
- **Object Detection** - YOLOv8-based detection
- **Ball Tracking** - Extended Kalman Filter
- **Decision Engine** - 5 detectors + counter
- **Calibration** - Camera calibration
- **Event Logging** - Decision logging
- **Performance Monitoring** - System metrics
- **Decision Review** - Manual review system
- **Training Data** - Data management

## 🎓 Learning Path

### Beginner
1. Read [GETTING_STARTED.md](GETTING_STARTED.md)
2. Start the application
3. Explore the web interface
4. Try the calibration wizard
5. Test with sample footage

### Intermediate
1. Read [WEBAPP_SETUP.md](WEBAPP_SETUP.md)
2. Configure system settings
3. Test with real cricket footage
4. Review decision history
5. Analyze performance metrics

### Advanced
1. Read [ARCHITECTURE.md](ARCHITECTURE.md)
2. Study the core system code
3. Run and analyze tests
4. Optimize performance
5. Extend functionality

## 🔍 Finding Information

### "How do I...?"

**...start the application?**
→ [GETTING_STARTED.md](GETTING_STARTED.md) - Quick Start section

**...calibrate cameras?**
→ [WEBAPP_SETUP.md](WEBAPP_SETUP.md) - Calibration section
→ Web interface: http://localhost:3000/calibration

**...configure settings?**
→ [docs/CONFIGURATION.md](docs/CONFIGURATION.md)
→ Web interface: http://localhost:3000/settings

**...test with video files?**
→ [WEBAPP_SETUP.md](WEBAPP_SETUP.md) - Testing section
→ [docs/OPERATION.md](docs/OPERATION.md)

**...improve performance?**
→ [docs/PERFORMANCE_OPTIMIZATION.md](docs/PERFORMANCE_OPTIMIZATION.md)

**...troubleshoot issues?**
→ [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
→ [WEBAPP_SETUP.md](WEBAPP_SETUP.md) - Troubleshooting section

**...understand the architecture?**
→ [ARCHITECTURE.md](ARCHITECTURE.md)

**...see what the UI looks like?**
→ [VISUAL_GUIDE.md](VISUAL_GUIDE.md)

**...use the API?**
→ http://localhost:8000/docs (after starting backend)

**...run tests?**
→ [docs/SYSTEM_TESTING.md](docs/SYSTEM_TESTING.md)

## 📈 Project Statistics

### Code
- **Total Files**: 100+ files
- **Lines of Code**: ~15,000 lines
- **Tests**: 705 tests (100% passing)
- **Test Coverage**: Comprehensive

### Web Application
- **Pages**: 6 complete pages
- **Components**: 10+ reusable components
- **API Endpoints**: 15+ REST endpoints
- **WebSocket**: Real-time support

### Core System
- **Modules**: 12 major modules
- **Detectors**: 5 decision detectors
- **Supported Formats**: MP4, AVI, MOV, MKV
- **Camera Support**: USB, RTSP, File

### Documentation
- **Guides**: 7 comprehensive guides
- **Examples**: 5 example scripts
- **API Docs**: Interactive Swagger UI
- **Total Pages**: 50+ pages of documentation

## 🎯 Quick Reference

### Ports
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **WebSocket**: ws://localhost:8000/ws

### Configuration Files
- `config.yaml` - Main configuration
- `calibration.json` - Camera calibration
- `webapp/.env` - Frontend environment
- `backend/.env` - Backend environment

### Key Commands
```bash
# Start webapp
start_webapp.bat / ./start_webapp.sh

# Run tests
python -m pytest tests/ -v

# Use CLI
python umpirai_cli.py run --video VIDEO_FILE

# Install dependencies
pip install -r requirements.txt  # Backend
npm install                      # Frontend
```

## 🎉 Status Summary

### ✅ Complete
- Core UmpirAI system (705 tests passing)
- React web application (6 pages)
- FastAPI backend (REST + WebSocket)
- Comprehensive documentation
- Startup scripts
- Configuration system
- Example scripts

### 🚀 Ready to Use
- Real-time monitoring
- Interactive calibration
- Decision history
- Analytics dashboard
- Settings management
- API integration

### 📚 Fully Documented
- Setup guides
- Operation manuals
- API documentation
- Architecture diagrams
- Visual walkthroughs
- Troubleshooting guides

## 🎬 Next Steps

1. **Read** [GETTING_STARTED.md](GETTING_STARTED.md)
2. **Start** the application
3. **Explore** the web interface
4. **Test** with cricket footage
5. **Analyze** the results

---

## 📞 Need Help?

### Documentation
- Start with [GETTING_STARTED.md](GETTING_STARTED.md)
- Check [WEBAPP_SETUP.md](WEBAPP_SETUP.md) for detailed setup
- See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for issues

### API Reference
- Visit http://localhost:8000/docs (after starting backend)

### Examples
- Check `examples/` folder for sample scripts

---

**Welcome to UmpirAI! 🏏**

**Start here:** [GETTING_STARTED.md](GETTING_STARTED.md)

**Launch command:**
```bash
start_webapp.bat  # Windows
./start_webapp.sh # Linux/Mac
```

**Then open:** http://localhost:3000

---

*Built with ❤️ for cricket and technology*
