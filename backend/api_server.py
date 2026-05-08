"""
FastAPI Backend Server for UmpirAI Web Application

This server provides REST API endpoints and WebSocket support for the
UmpirAI web interface to communicate with the umpiring system.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
from datetime import datetime
import uvicorn

# Import UmpirAI components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from umpirai.umpirai_system import UmpirAISystem, SystemConfig
from umpirai.config.config_manager import ConfigManager

app = FastAPI(title="UmpirAI API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global system instance
umpirai_system: Optional[UmpirAISystem] = None
config_manager = ConfigManager()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()


# Pydantic Models
class SystemStatus(BaseModel):
    running: bool
    cameras: int
    fps: float
    latency: float
    cpu_usage: float
    memory_usage: float
    gpu_usage: float


class Decision(BaseModel):
    id: int
    timestamp: str
    type: str
    subType: str
    confidence: float
    requiresReview: bool
    over: str
    cameras: int
    detections: Dict[str, Any]


class CalibrationStep(BaseModel):
    step: str
    data: Dict[str, Any]


class SettingsUpdate(BaseModel):
    settings: Dict[str, Any]


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "UmpirAI API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/api/status", response_model=SystemStatus)
async def get_status():
    """Get current system status"""
    global umpirai_system
    
    if umpirai_system is None:
        return SystemStatus(
            running=False,
            cameras=0,
            fps=0.0,
            latency=0.0,
            cpu_usage=0.0,
            memory_usage=0.0,
            gpu_usage=0.0
        )
    
    status = umpirai_system.get_status()
    
    return SystemStatus(
        running=status.get('running', False),
        cameras=status.get('active_cameras', 0),
        fps=status.get('fps', 0.0),
        latency=status.get('latency', 0.0),
        cpu_usage=status.get('cpu_usage', 0.0),
        memory_usage=status.get('memory_usage', 0.0),
        gpu_usage=status.get('gpu_usage', 0.0)
    )


@app.post("/api/start")
async def start_monitoring():
    """Start the umpiring system"""
    global umpirai_system
    
    try:
        if umpirai_system is None:
            # Load configuration
            config = config_manager.load_config('config.yaml')
            umpirai_system = UmpirAISystem(config)
        
        umpirai_system.startup()
        
        # Broadcast status update
        await manager.broadcast({
            "type": "status",
            "data": {"running": True}
        })
        
        return {"success": True, "message": "System started successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stop")
async def stop_monitoring():
    """Stop the umpiring system"""
    global umpirai_system
    
    try:
        if umpirai_system:
            umpirai_system.shutdown()
        
        # Broadcast status update
        await manager.broadcast({
            "type": "status",
            "data": {"running": False}
        })
        
        return {"success": True, "message": "System stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/decisions")
async def get_decisions(
    limit: int = 50,
    offset: int = 0,
    type: Optional[str] = None
):
    """Get decision history"""
    # TODO: Implement database query for decision history
    # For now, return mock data
    
    decisions = [
        {
            "id": i,
            "timestamp": datetime.now().isoformat(),
            "type": "OUT" if i % 5 == 0 else "LEGAL_DELIVERY",
            "subType": "Bowled" if i % 5 == 0 else "Fair Delivery",
            "confidence": 95.0 + (i % 5),
            "requiresReview": i % 10 == 0,
            "over": f"{i // 6}.{i % 6 + 1}",
            "cameras": 4,
            "detections": {}
        }
        for i in range(offset, offset + limit)
    ]
    
    return {
        "decisions": decisions,
        "total": 247,
        "limit": limit,
        "offset": offset
    }


@app.get("/api/decisions/{decision_id}")
async def get_decision(decision_id: int):
    """Get specific decision details"""
    # TODO: Implement database query
    return {
        "id": decision_id,
        "timestamp": datetime.now().isoformat(),
        "type": "OUT",
        "subType": "Bowled",
        "confidence": 98.5,
        "requiresReview": False,
        "over": "5.3",
        "cameras": 4,
        "detections": {
            "ball": "Detected",
            "stumps": "Detected",
            "bails": "Dislodged"
        },
        "trajectory": [],
        "videoReferences": []
    }


@app.get("/api/calibration")
async def get_calibration():
    """Get current calibration data"""
    global umpirai_system
    
    if umpirai_system and umpirai_system.calibration:
        return umpirai_system.calibration.get_current_calibration()
    
    return {"calibrated": False}


@app.post("/api/calibration")
async def save_calibration(data: Dict[str, Any]):
    """Save calibration data"""
    global umpirai_system
    
    try:
        if umpirai_system and umpirai_system.calibration:
            # Save calibration
            umpirai_system.calibration.save_calibration("web_calibration")
            return {"success": True, "message": "Calibration saved"}
        
        raise HTTPException(status_code=400, detail="System not initialized")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/calibration/step")
async def complete_calibration_step(step: CalibrationStep):
    """Complete a calibration step"""
    # TODO: Implement calibration step processing
    return {"success": True, "step": step.step}


@app.get("/api/analytics/summary")
async def get_analytics_summary():
    """Get analytics summary"""
    return {
        "totalDecisions": 247,
        "avgConfidence": 94.2,
        "reviewRate": 4.9,
        "accuracy": 95.1,
        "decisionTypes": [
            {"name": "Legal Delivery", "value": 180, "color": "#059669"},
            {"name": "Wide", "value": 35, "color": "#EAB308"},
            {"name": "No Ball", "value": 18, "color": "#F97316"},
            {"name": "Bowled", "value": 8, "color": "#DC2626"},
            {"name": "LBW", "value": 4, "color": "#DC2626"},
            {"name": "Caught", "value": 2, "color": "#DC2626"},
        ]
    }


@app.get("/api/analytics/performance")
async def get_performance_metrics():
    """Get performance metrics over time"""
    return {
        "metrics": [
            {"time": "10:00", "fps": 30, "latency": 0.8, "accuracy": 95},
            {"time": "11:00", "fps": 29, "latency": 0.9, "accuracy": 94},
            {"time": "12:00", "fps": 30, "latency": 0.7, "accuracy": 96},
            {"time": "13:00", "fps": 30, "latency": 0.8, "accuracy": 95},
            {"time": "14:00", "fps": 28, "latency": 1.0, "accuracy": 93},
            {"time": "15:00", "fps": 30, "latency": 0.8, "accuracy": 95},
        ]
    }


@app.get("/api/settings")
async def get_settings():
    """Get current system settings"""
    try:
        config = config_manager.get_config()
        if config:
            return config.to_dict()
        
        # Return default settings
        return {
            "detectionModel": "yolov8m",
            "confidenceThreshold": 0.7,
            "targetFPS": 30,
            "enableGPU": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/settings")
async def update_settings(settings: SettingsUpdate):
    """Update system settings"""
    try:
        # TODO: Update configuration
        config_manager.save_config(settings.settings, 'config.yaml')
        
        # Broadcast settings update
        await manager.broadcast({
            "type": "settings_updated",
            "data": settings.settings
        })
        
        return {"success": True, "message": "Settings updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            
            # Echo back for now
            await websocket.send_json({
                "type": "echo",
                "data": data
            })
            
            # Simulate sending decision updates
            await asyncio.sleep(5)
            await websocket.send_json({
                "type": "decision",
                "data": {
                    "type": "OUT",
                    "subType": "Bowled",
                    "confidence": 98.5,
                    "timestamp": datetime.now().isoformat()
                }
            })
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    print("🚀 UmpirAI API Server starting...")
    print("📡 WebSocket endpoint: ws://localhost:8000/ws")
    print("🌐 API docs: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global umpirai_system
    
    if umpirai_system:
        umpirai_system.shutdown()
    
    print("👋 UmpirAI API Server shutting down...")


if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
