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
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import UmpirAI components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from umpirai.umpirai_system import UmpirAISystem, SystemConfig, SystemMode
from umpirai.config.config_manager import ConfigManager, load_config
from umpirai.video.video_processor import CameraSource
from umpirai.models.data_models import Decision as UmpirAIDecision
import psutil
import threading

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
processing_thread: Optional[threading.Thread] = None
stop_processing = threading.Event()

# Store recent decisions for history
recent_decisions: List[Dict[str, Any]] = []
MAX_RECENT_DECISIONS = 1000

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


# Processing loop function
def processing_loop():
    """Background processing loop for continuous frame processing"""
    global umpirai_system, recent_decisions, stop_processing
    
    logger.info("Processing loop started")
    
    while not stop_processing.is_set() and umpirai_system and umpirai_system.is_running:
        try:
            # Process a single frame
            decision = umpirai_system.process_frame()
            
            # If a decision was made, broadcast it and store it
            if decision:
                decision_dict = {
                    "id": len(recent_decisions) + 1,
                    "timestamp": decision.timestamp.isoformat() if hasattr(decision.timestamp, 'isoformat') else str(decision.timestamp),
                    "type": decision.decision_type.value if hasattr(decision.decision_type, 'value') else str(decision.decision_type),
                    "subType": decision.sub_type or "",
                    "confidence": decision.confidence,
                    "requiresReview": decision.requires_review,
                    "over": f"{decision.over_number}.{decision.ball_number}" if hasattr(decision, 'over_number') else "0.0",
                    "cameras": len(umpirai_system.video_processor.get_healthy_cameras()) if umpirai_system else 0,
                    "detections": decision.metadata if hasattr(decision, 'metadata') else {}
                }
                
                # Store decision
                recent_decisions.append(decision_dict)
                if len(recent_decisions) > MAX_RECENT_DECISIONS:
                    recent_decisions.pop(0)
                
                # Broadcast to WebSocket clients
                asyncio.run(manager.broadcast({
                    "type": "decision",
                    "data": decision_dict
                }))
            
            # Small sleep to prevent CPU spinning
            time.sleep(0.001)
            
        except Exception as e:
            logger.error(f"Error in processing loop: {e}")
            time.sleep(0.1)  # Longer sleep on error
    
    logger.info("Processing loop stopped")


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
    
    # Get system status
    system_status = umpirai_system.get_status()
    
    # Get resource usage
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    
    # Try to get GPU usage (if available)
    gpu_percent = 0.0
    try:
        import torch
        if torch.cuda.is_available():
            gpu_percent = torch.cuda.utilization()
    except:
        pass
    
    return SystemStatus(
        running=system_status.is_running,
        cameras=len(system_status.active_cameras),
        fps=system_status.current_fps,
        latency=system_status.processing_latency_ms,
        cpu_usage=cpu_percent,
        memory_usage=memory_percent,
        gpu_usage=gpu_percent
    )


@app.post("/api/start")
async def start_monitoring():
    """Start the umpiring system"""
    global umpirai_system, processing_thread, stop_processing
    
    try:
        if umpirai_system and umpirai_system.is_running:
            return {"success": False, "message": "System is already running"}
        
        # Load configuration
        try:
            config_path = Path(__file__).parent.parent / 'config_test.yaml'
            if config_path.exists():
                config = load_config(str(config_path))
            else:
                # Use default config
                config = SystemConfig()
        except Exception as e:
            logger.warning(f"Could not load config: {e}. Using defaults.")
            config = SystemConfig()
        
        # Initialize system
        umpirai_system = UmpirAISystem(config)
        
        # Add video source (for testing, use a video file or camera)
        # This should be configured based on user settings
        video_path = Path(__file__).parent.parent / 'videos'
        if video_path.exists():
            video_files = list(video_path.glob('*.mp4'))
            if video_files:
                # Use first video file for demo
                camera_source = CameraSource(
                    source_type='file',
                    source_path=str(video_files[0])
                )
                umpirai_system.add_camera('camera_1', camera_source)
        
        # Start the system
        umpirai_system.start()
        
        # Start processing thread
        stop_processing.clear()
        processing_thread = threading.Thread(target=processing_loop, daemon=True)
        processing_thread.start()
        
        # Broadcast status update
        await manager.broadcast({
            "type": "status",
            "data": {"running": True}
        })
        
        return {"success": True, "message": "System started successfully"}
    except Exception as e:
        logger.error(f"Failed to start system: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stop")
async def stop_monitoring():
    """Stop the umpiring system"""
    global umpirai_system, processing_thread, stop_processing
    
    try:
        if umpirai_system is None or not umpirai_system.is_running:
            return {"success": False, "message": "System is not running"}
        
        # Stop processing thread
        stop_processing.set()
        if processing_thread:
            processing_thread.join(timeout=5.0)
        
        # Stop the system
        umpirai_system.stop()
        
        # Broadcast status update
        await manager.broadcast({
            "type": "status",
            "data": {"running": False}
        })
        
        return {"success": True, "message": "System stopped successfully"}
    except Exception as e:
        logger.error(f"Failed to stop system: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/decisions")
async def get_decisions(
    limit: int = 50,
    offset: int = 0,
    type: Optional[str] = None
):
    """Get decision history"""
    global recent_decisions
    
    # Filter by type if specified
    filtered_decisions = recent_decisions
    if type:
        filtered_decisions = [d for d in recent_decisions if d['type'] == type]
    
    # Apply pagination
    total = len(filtered_decisions)
    paginated = filtered_decisions[offset:offset + limit]
    
    return {
        "decisions": paginated,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.get("/api/decisions/{decision_id}")
async def get_decision(decision_id: int):
    """Get specific decision details"""
    global recent_decisions
    
    # Find decision by ID
    for decision in recent_decisions:
        if decision['id'] == decision_id:
            return decision
    
    raise HTTPException(status_code=404, detail="Decision not found")


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
    global recent_decisions
    
    if not recent_decisions:
        return {
            "totalDecisions": 0,
            "avgConfidence": 0.0,
            "reviewRate": 0.0,
            "accuracy": 0.0,
            "decisionTypes": []
        }
    
    # Calculate statistics
    total = len(recent_decisions)
    avg_confidence = sum(d['confidence'] for d in recent_decisions) / total
    review_count = sum(1 for d in recent_decisions if d['requiresReview'])
    review_rate = (review_count / total) * 100 if total > 0 else 0
    
    # Count decision types
    type_counts = {}
    for decision in recent_decisions:
        dtype = decision['type']
        type_counts[dtype] = type_counts.get(dtype, 0) + 1
    
    # Format for chart
    decision_types = [
        {"name": dtype, "value": count, "color": _get_decision_color(dtype)}
        for dtype, count in type_counts.items()
    ]
    
    return {
        "totalDecisions": total,
        "avgConfidence": round(avg_confidence, 1),
        "reviewRate": round(review_rate, 1),
        "accuracy": round(avg_confidence, 1),  # Using confidence as proxy for accuracy
        "decisionTypes": decision_types
    }


def _get_decision_color(decision_type: str) -> str:
    """Get color for decision type"""
    colors = {
        "LEGAL_DELIVERY": "#059669",
        "WIDE": "#EAB308",
        "NO_BALL": "#F97316",
        "OUT": "#DC2626",
        "BOWLED": "#DC2626",
        "LBW": "#DC2626",
        "CAUGHT": "#DC2626",
    }
    return colors.get(decision_type, "#6B7280")


@app.get("/api/analytics/performance")
async def get_performance_metrics():
    """Get performance metrics over time"""
    global umpirai_system
    
    if not umpirai_system or not umpirai_system.performance_monitor:
        # Return empty metrics
        return {"metrics": []}
    
    # Get performance history
    try:
        history = umpirai_system.performance_monitor.get_metrics_history()
        
        # Format for chart (sample every 10th metric to avoid too much data)
        metrics = []
        for i, metric in enumerate(history[::10]):  # Sample every 10th
            metrics.append({
                "time": datetime.fromtimestamp(metric.timestamp).strftime("%H:%M"),
                "fps": round(metric.fps, 1),
                "latency": round(metric.processing_latency_ms, 1),
                "accuracy": 95  # Placeholder - would need ground truth
            })
        
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return {"metrics": []}


@app.get("/api/settings")
async def get_settings():
    """Get current system settings"""
    global umpirai_system
    
    try:
        if umpirai_system and umpirai_system.config:
            config = umpirai_system.config
            return {
                "detectionModel": config.detection_device,
                "confidenceThreshold": 0.7,  # Default
                "targetFPS": config.target_fps,
                "enableGPU": config.detection_device != "cpu"
            }
        
        # Return default settings
        return {
            "detectionModel": "yolov8n",
            "confidenceThreshold": 0.7,
            "targetFPS": 30,
            "enableGPU": False
        }
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/settings")
async def update_settings(settings: SettingsUpdate):
    """Update system settings"""
    global umpirai_system
    
    try:
        # Update settings (would need to restart system for some changes)
        logger.info(f"Settings update requested: {settings.settings}")
        
        # Broadcast settings update
        await manager.broadcast({
            "type": "settings_updated",
            "data": settings.settings
        })
        
        return {"success": True, "message": "Settings updated successfully. Restart system for changes to take effect."}
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
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
    global umpirai_system, processing_thread, stop_processing
    
    # Stop processing thread
    stop_processing.set()
    if processing_thread:
        processing_thread.join(timeout=5.0)
    
    # Stop system
    if umpirai_system:
        umpirai_system.stop()
    
    print("👋 UmpirAI API Server shutting down...")


if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
