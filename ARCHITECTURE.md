# UmpirAI Web Application Architecture

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                             │
│                     http://localhost:3000                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP/WebSocket
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    REACT WEB APPLICATION                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Components                                               │  │
│  │  ├── Layout (Sidebar + Header)                           │  │
│  │  ├── Dashboard                                            │  │
│  │  ├── Live Monitoring                                      │  │
│  │  ├── Decision History                                     │  │
│  │  ├── Calibration                                          │  │
│  │  ├── Analytics                                            │  │
│  │  └── Settings                                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  Technology Stack:                                               │
│  • React 18 + Vite                                              │
│  • Tailwind CSS                                                  │
│  • Recharts (Charts)                                            │
│  • Framer Motion (Animations)                                   │
│  • Axios (HTTP Client)                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ REST API + WebSocket
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    FASTAPI BACKEND SERVER                        │
│                     http://localhost:8000                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  REST API Endpoints                                       │  │
│  │  ├── GET  /api/status                                     │  │
│  │  ├── POST /api/start                                      │  │
│  │  ├── POST /api/stop                                       │  │
│  │  ├── GET  /api/decisions                                  │  │
│  │  ├── GET  /api/calibration                                │  │
│  │  ├── POST /api/calibration                                │  │
│  │  ├── GET  /api/analytics/*                                │  │
│  │  └── GET/PUT /api/settings                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  WebSocket Endpoint                                       │  │
│  │  └── ws://localhost:8000/ws                               │  │
│  │      • Real-time decision updates                         │  │
│  │      • System status changes                              │  │
│  │      • Performance metrics                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  Technology Stack:                                               │
│  • FastAPI                                                       │
│  • Uvicorn (ASGI Server)                                        │
│  • WebSockets                                                    │
│  • Pydantic (Validation)                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Python API
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      UMPIRAI CORE SYSTEM                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Video Processing                                         │  │
│  │  ├── Multi-camera capture                                 │  │
│  │  ├── Frame synchronization                                │  │
│  │  └── Preprocessing                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Object Detection (YOLOv8)                                │  │
│  │  ├── Ball detection                                       │  │
│  │  ├── Player detection                                     │  │
│  │  ├── Stump detection                                      │  │
│  │  └── Multi-view fusion                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Ball Tracking (EKF)                                      │  │
│  │  ├── Trajectory prediction                                │  │
│  │  ├── Occlusion handling                                   │  │
│  │  └── 3D position estimation                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Decision Engine                                          │  │
│  │  ├── Wide Ball Detector                                   │  │
│  │  ├── No Ball Detector                                     │  │
│  │  ├── LBW Detector                                         │  │
│  │  ├── Bowled Detector                                      │  │
│  │  ├── Caught Detector                                      │  │
│  │  └── Legal Delivery Counter                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Supporting Systems                                       │  │
│  │  ├── Calibration Manager                                  │  │
│  │  ├── Event Logger                                         │  │
│  │  ├── Performance Monitor                                  │  │
│  │  ├── Decision Review System                               │  │
│  │  └── Training Data Manager                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  Technology Stack:                                               │
│  • Python 3.10+                                                  │
│  • OpenCV (Video Processing)                                    │
│  • YOLOv8/PyTorch (Detection)                                   │
│  • NumPy/SciPy (Tracking)                                       │
│  • Hypothesis (Testing)                                         │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Data Flow

### 1. Live Monitoring Flow

```
Video Source → Video Processor → Object Detector → Ball Tracker
                                                         │
                                                         ▼
                                                  Decision Engine
                                                         │
                                                         ▼
                                                  Decision Output
                                                         │
                                                         ▼
                                                   Event Logger
                                                         │
                                                         ▼
                                              FastAPI Backend (WebSocket)
                                                         │
                                                         ▼
                                                React Frontend
                                                         │
                                                         ▼
                                                   User Display
```

### 2. Configuration Flow

```
User (Settings Page) → React Frontend → FastAPI Backend
                                              │
                                              ▼
                                       Config Manager
                                              │
                                              ▼
                                       UmpirAI System
                                              │
                                              ▼
                                    Apply New Settings
```

### 3. Calibration Flow

```
User (Calibration Page) → React Frontend → FastAPI Backend
                                                 │
                                                 ▼
                                        Calibration Manager
                                                 │
                                                 ▼
                                        Save Calibration Data
                                                 │
                                                 ▼
                                        Update Camera Transforms
```

## 🔄 Communication Patterns

### REST API (Request/Response)
```
Frontend                Backend                 UmpirAI
   │                       │                       │
   ├─── GET /api/status ──>│                       │
   │                       ├─── get_status() ────>│
   │                       │<──── status ──────────┤
   │<──── 200 OK ──────────┤                       │
   │                       │                       │
```

### WebSocket (Real-time)
```
Frontend                Backend                 UmpirAI
   │                       │                       │
   ├─── Connect WS ───────>│                       │
   │<──── Connected ────────┤                       │
   │                       │                       │
   │                       │<──── Decision ────────┤
   │<──── Decision Event ───┤                       │
   │                       │                       │
   │                       │<──── Status Update ───┤
   │<──── Status Event ─────┤                       │
   │                       │                       │
```

## 🎯 Component Responsibilities

### Frontend (React)

#### Layout Component
- **Responsibility**: Application shell, navigation
- **State**: Sidebar open/closed
- **Props**: Children components

#### Dashboard Page
- **Responsibility**: System overview
- **State**: Statistics, recent decisions
- **API Calls**: GET /api/status, GET /api/decisions

#### Live Monitoring Page
- **Responsibility**: Real-time monitoring
- **State**: Current decision, ball tracking, camera feeds
- **API Calls**: POST /api/start, POST /api/stop
- **WebSocket**: Real-time decision updates

#### Decision History Page
- **Responsibility**: Browse past decisions
- **State**: Decision list, filters, pagination
- **API Calls**: GET /api/decisions

#### Calibration Page
- **Responsibility**: Camera calibration
- **State**: Calibration steps, progress
- **API Calls**: GET /api/calibration, POST /api/calibration

#### Analytics Page
- **Responsibility**: Data visualization
- **State**: Charts data, metrics
- **API Calls**: GET /api/analytics/*

#### Settings Page
- **Responsibility**: System configuration
- **State**: Settings form
- **API Calls**: GET /api/settings, PUT /api/settings

### Backend (FastAPI)

#### API Server
- **Responsibility**: HTTP endpoints, WebSocket
- **Dependencies**: UmpirAI system, Config manager
- **Endpoints**: 15+ REST endpoints + WebSocket

#### Connection Manager
- **Responsibility**: WebSocket connections
- **Methods**: connect(), disconnect(), broadcast()

### Core System (UmpirAI)

#### Video Processor
- **Input**: Camera sources
- **Output**: Synchronized frames
- **Processing**: Capture, sync, preprocess

#### Object Detector
- **Input**: Video frames
- **Output**: Detections (ball, players, stumps)
- **Model**: YOLOv8

#### Ball Tracker
- **Input**: Ball detections
- **Output**: Ball trajectory
- **Algorithm**: Extended Kalman Filter

#### Decision Engine
- **Input**: Trajectory, detections, calibration
- **Output**: Umpiring decisions
- **Components**: 5 detectors + counter

## 🔐 Security Considerations

### CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Future Enhancements
- [ ] JWT authentication
- [ ] Role-based access control
- [ ] API rate limiting
- [ ] Input validation
- [ ] HTTPS/WSS in production

## 📈 Scalability

### Current Architecture
- **Single Server**: Backend + UmpirAI on same machine
- **Single Match**: One match at a time
- **Local Storage**: In-memory data

### Future Scaling Options

#### Horizontal Scaling
```
Load Balancer
     │
     ├─── Backend Server 1 ─── UmpirAI Instance 1
     ├─── Backend Server 2 ─── UmpirAI Instance 2
     └─── Backend Server 3 ─── UmpirAI Instance 3
```

#### Microservices
```
Frontend ─┬─── API Gateway
          │
          ├─── Video Service
          ├─── Detection Service
          ├─── Decision Service
          ├─── Analytics Service
          └─── Storage Service
```

#### Cloud Deployment
```
User Browser
     │
     ▼
CDN (Frontend)
     │
     ▼
API Gateway (AWS/Azure)
     │
     ├─── Lambda/Functions (Backend)
     ├─── GPU Instances (Detection)
     ├─── Database (PostgreSQL)
     └─── Object Storage (S3/Blob)
```

## 🎨 Design Patterns

### Frontend Patterns
- **Component Composition**: Reusable UI components
- **Container/Presentational**: Separate logic from UI
- **Custom Hooks**: Shared state logic
- **Context API**: Global state management

### Backend Patterns
- **Dependency Injection**: FastAPI dependencies
- **Repository Pattern**: Data access abstraction
- **Observer Pattern**: WebSocket broadcasting
- **Singleton Pattern**: System instance

### System Patterns
- **Pipeline Pattern**: Video → Detection → Tracking → Decision
- **Strategy Pattern**: Multiple detector implementations
- **Factory Pattern**: Camera source creation
- **State Pattern**: System operational modes

## 🔧 Configuration Management

### Environment Variables
```
# Frontend (.env)
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000

# Backend (.env)
UMPIRAI_CONFIG_PATH=config.yaml
LOG_LEVEL=INFO
```

### Configuration Files
```
config.yaml              # Main system config
calibration.json         # Camera calibration
settings.json            # User preferences
```

## 📊 Monitoring & Logging

### Application Logs
```
backend/logs/
├── api.log              # API requests/responses
├── system.log           # System events
├── decisions.log        # Decision history
└── errors.log           # Error tracking
```

### Performance Metrics
- Request latency
- WebSocket message rate
- System FPS
- Memory usage
- GPU utilization

## 🚀 Deployment Options

### Development
```bash
# Local development
npm run dev              # Frontend
python api_server.py     # Backend
```

### Production

#### Option 1: Single Server
```bash
# Build frontend
npm run build

# Serve with Nginx
nginx -c nginx.conf

# Run backend with Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker api_server:app
```

#### Option 2: Docker
```dockerfile
# Frontend
FROM node:18 AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# Backend
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Option 3: Cloud (AWS)
```
Frontend: S3 + CloudFront
Backend: ECS/Fargate
Database: RDS PostgreSQL
Storage: S3
GPU: EC2 G4 instances
```

---

**Architecture designed for scalability, maintainability, and performance** 🏗️
