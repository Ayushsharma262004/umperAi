# UmpirAI Web Application

A modern, interactive React web application for monitoring and controlling the UmpirAI AI-powered cricket umpiring system.

## 🎯 Features

### Dashboard
- **Real-time Statistics**: View total decisions, accuracy, latency, and active cameras
- **Recent Decisions**: Monitor the latest umpiring decisions with confidence scores
- **System Health**: Track FPS, CPU, memory, and GPU usage
- **Quick Actions**: Start monitoring, calibrate cameras, view analytics, and run diagnostics

### Live Monitoring
- **Real-time Video Feeds**: View primary and multi-camera feeds
- **Ball Tracking Visualization**: See ball trajectory overlays in real-time
- **Decision Overlays**: Instant decision display with confidence scores
- **Performance Metrics**: Monitor processing time, FPS, and sync quality
- **Camera Status**: Track all camera feeds and their health

### Decision History
- **Searchable History**: Browse all past decisions with filters
- **Detailed Information**: View timestamp, over, decision type, confidence, and review status
- **Export Functionality**: Download decision data for analysis
- **Pagination**: Navigate through large datasets efficiently

### Calibration
- **Step-by-Step Wizard**: Guided calibration process
- **Visual Feedback**: Interactive pitch marking interface
- **Progress Tracking**: Monitor calibration completion status
- **Camera Management**: View and manage all camera calibrations

### Analytics
- **Decision Distribution**: Pie chart showing decision type breakdown
- **Confidence Analysis**: Bar chart of confidence score distribution
- **Performance Trends**: Line charts tracking FPS, latency, and accuracy over time
- **Detailed Statistics**: Comprehensive metrics for all system components

### Settings
- **Detection Configuration**: Model selection, confidence thresholds, camera limits
- **Tracking Parameters**: Occlusion handling, noise parameters
- **Decision Rules**: Confidence thresholds, wide guidelines, detector toggles
- **Output Options**: Text, audio, and visual output configuration
- **Performance Tuning**: FPS targets, memory limits, GPU acceleration

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ and npm
- Python 3.10+ (for backend API)
- UmpirAI system installed and configured

### Installation

1. **Install dependencies**:
   ```bash
   cd webapp
   npm install
   ```

2. **Start the development server**:
   ```bash
   npm run dev
   ```

3. **Open your browser**:
   Navigate to `http://localhost:3000`

### Production Build

```bash
npm run build
npm run preview
```

## 🏗️ Architecture

### Technology Stack

- **Frontend Framework**: React 18
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Routing**: React Router v6
- **Charts**: Recharts
- **Icons**: Lucide React
- **Animations**: Framer Motion
- **HTTP Client**: Axios

### Project Structure

```
webapp/
├── public/              # Static assets
├── src/
│   ├── components/      # Reusable components
│   │   └── Layout.jsx   # Main layout with sidebar
│   ├── pages/           # Page components
│   │   ├── Dashboard.jsx
│   │   ├── LiveMonitoring.jsx
│   │   ├── DecisionHistory.jsx
│   │   ├── Calibration.jsx
│   │   ├── Analytics.jsx
│   │   └── Settings.jsx
│   ├── App.jsx          # Main app component
│   ├── main.jsx         # Entry point
│   └── index.css        # Global styles
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

## 🔌 Backend Integration

The webapp expects a REST API backend running on `http://localhost:8000` with the following endpoints:

### API Endpoints

#### System Status
- `GET /api/status` - Get system status
- `POST /api/start` - Start monitoring
- `POST /api/stop` - Stop monitoring

#### Decisions
- `GET /api/decisions` - Get decision history
- `GET /api/decisions/:id` - Get specific decision
- `GET /api/decisions/live` - Get current decision

#### Calibration
- `GET /api/calibration` - Get calibration data
- `POST /api/calibration` - Save calibration
- `POST /api/calibration/step` - Complete calibration step

#### Analytics
- `GET /api/analytics/summary` - Get analytics summary
- `GET /api/analytics/performance` - Get performance metrics
- `GET /api/analytics/decisions` - Get decision statistics

#### Settings
- `GET /api/settings` - Get current settings
- `PUT /api/settings` - Update settings

#### WebSocket
- `ws://localhost:8000/ws` - Real-time updates for live monitoring

### Creating the Backend API

You'll need to create a FastAPI backend to serve the UmpirAI system. Here's a basic example:

```python
# backend/api.py
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/status")
async def get_status():
    return {
        "running": True,
        "cameras": 4,
        "fps": 30,
        "latency": 0.8
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Send real-time updates
    while True:
        data = {"type": "decision", "data": {...}}
        await websocket.send_json(data)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 🎨 Customization

### Theme Colors

Edit `tailwind.config.js` to customize the color scheme:

```javascript
colors: {
  cricket: {
    green: '#2D5016',    // Pitch green
    pitch: '#8B7355',    // Pitch brown
    ball: '#DC143C',     // Cricket ball red
    stumps: '#F5DEB3',   // Stump color
    primary: '#1E3A8A',  // Primary blue
    secondary: '#059669', // Secondary green
  }
}
```

### Adding New Pages

1. Create a new component in `src/pages/`
2. Add route in `src/App.jsx`
3. Add navigation item in `src/components/Layout.jsx`

## 📱 Responsive Design

The application is fully responsive and works on:
- Desktop (1920x1080 and above)
- Laptop (1366x768 and above)
- Tablet (768x1024)
- Mobile (375x667 and above)

## 🔧 Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Hot Module Replacement

Vite provides instant HMR for a smooth development experience. Changes are reflected immediately without full page reloads.

## 🚢 Deployment

### Build for Production

```bash
npm run build
```

The build output will be in the `dist/` directory.

### Deploy to Static Hosting

The built application can be deployed to:
- Vercel
- Netlify
- GitHub Pages
- AWS S3 + CloudFront
- Any static hosting service

### Environment Variables

Create a `.env` file for environment-specific configuration:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

Access in code:
```javascript
const apiUrl = import.meta.env.VITE_API_URL
```

## 🐛 Troubleshooting

### Port Already in Use

If port 3000 is already in use, modify `vite.config.js`:

```javascript
server: {
  port: 3001, // Change to any available port
}
```

### API Connection Issues

1. Ensure the backend API is running on port 8000
2. Check CORS configuration in the backend
3. Verify proxy settings in `vite.config.js`

### Build Errors

Clear cache and reinstall:
```bash
rm -rf node_modules package-lock.json
npm install
```

## 📄 License

This project is part of the UmpirAI system. See the main project LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check the main UmpirAI documentation
- Contact the development team

## 🎯 Roadmap

- [ ] Real-time WebSocket integration
- [ ] Video playback controls
- [ ] Decision replay functionality
- [ ] Advanced filtering and search
- [ ] User authentication and roles
- [ ] Multi-match support
- [ ] Mobile app version
- [ ] Offline mode support

---

Built with ❤️ for cricket and technology
