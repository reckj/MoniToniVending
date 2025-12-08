"""
FastAPI telemetry server for remote monitoring and control.

Provides REST API and WebSocket endpoints for:
- Machine status monitoring
- Log retrieval and export
- Configuration management
- Hardware debug controls (PIN-protected)
"""

from fastapi import FastAPI, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import json

from monitoni.core.config import Config
from monitoni.core.database import DatabaseManager
from monitoni.core.logger import Logger, LogLevel
from monitoni.hardware.manager import HardwareManager


# Pydantic models for request/response
class StatusResponse(BaseModel):
    """Machine status response."""
    machine_id: str
    timestamp: str
    hardware: Dict[str, Any]
    statistics: Dict[str, Any]
    state: str


class LogEntry(BaseModel):
    """Log entry model."""
    id: int
    timestamp: str
    level: str
    message: str
    purchase_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class LogsResponse(BaseModel):
    """Logs response."""
    logs: List[LogEntry]
    total: int
    page: int
    per_page: int


class ConfigUpdateRequest(BaseModel):
    """Configuration update request."""
    section: str
    key: str
    value: Any
    pin: str


class DebugRequest(BaseModel):
    """Debug control request."""
    pin: str
    action: str
    params: Optional[Dict[str, Any]] = None


class RelayControlRequest(BaseModel):
    """Relay control request."""
    pin: str
    channel: int
    state: bool


class LEDControlRequest(BaseModel):
    """LED control request."""
    pin: str
    r: int = 0
    g: int = 0
    b: int = 0
    zone: Optional[int] = None
    animation: Optional[str] = None


class AudioControlRequest(BaseModel):
    """Audio control request."""
    pin: str
    sound: Optional[str] = None
    volume: Optional[float] = None


class TelemetryServer:
    """
    FastAPI-based telemetry server.
    
    Provides REST API and WebSocket for remote monitoring and control.
    """
    
    def __init__(
        self,
        config: Config,
        hardware: HardwareManager,
        database: DatabaseManager,
        logger: Logger
    ):
        """
        Initialize telemetry server.
        
        Args:
            config: System configuration
            hardware: Hardware manager instance
            database: Database manager instance
            logger: Logger instance
        """
        self.config = config
        self.hardware = hardware
        self.database = database
        self.logger = logger
        self.app = FastAPI(
            title="MoniToni Telemetry API",
            description="Remote monitoring and control for MoniToni vending machines",
            version="1.0.0"
        )
        
        # WebSocket connections
        self._ws_connections: List[WebSocket] = []
        self._current_state = "IDLE"
        
        self._setup_middleware()
        self._setup_routes()
        
    def _setup_middleware(self):
        """Configure middleware."""
        # Enable CORS for web dashboard access
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
    def _verify_pin(self, pin: str) -> bool:
        """Verify debug PIN."""
        return pin == str(self.config.debug.pin)
        
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            """Serve simple status page."""
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>MoniToni Telemetry</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background: #1a1a2e; color: #eee; }
                    h1 { color: #00d4ff; }
                    .status { background: #16213e; padding: 20px; border-radius: 10px; margin: 20px 0; }
                    a { color: #00d4ff; }
                </style>
            </head>
            <body>
                <h1>🎰 MoniToni Telemetry Server</h1>
                <div class="status">
                    <h2>API Endpoints</h2>
                    <ul>
                        <li><a href="/api/status">GET /api/status</a> - Machine status</li>
                        <li><a href="/api/logs">GET /api/logs</a> - System logs</li>
                        <li><a href="/docs">API Documentation (Swagger)</a></li>
                    </ul>
                </div>
                <div class="status">
                    <h2>WebSocket</h2>
                    <p>Connect to <code>ws://[host]:8080/ws</code> for real-time updates</p>
                </div>
            </body>
            </html>
            """
        
        @self.app.get("/api/status", response_model=StatusResponse)
        async def get_status():
            """Get current machine status."""
            # Get hardware status
            hw_status = self.hardware.get_status()
            
            # Get statistics from database
            try:
                stats = await self.database.get_statistics()
            except Exception:
                stats = {
                    "completed_purchases": 0,
                    "failed_purchases": 0,
                    "network_incidents": 0,
                    "server_incidents": 0
                }
            
            return StatusResponse(
                machine_id=self.config.machine_id,
                timestamp=datetime.now().isoformat(),
                hardware=hw_status,
                statistics=stats,
                state=self._current_state
            )
        
        @self.app.get("/api/logs", response_model=LogsResponse)
        async def get_logs(
            page: int = Query(1, ge=1),
            per_page: int = Query(50, ge=1, le=500),
            level: Optional[str] = None,
            purchase_id: Optional[str] = None
        ):
            """Get system logs with pagination and filtering."""
            try:
                # Get logs from database
                offset = (page - 1) * per_page
                
                logs_data = await self.database.get_logs(
                    limit=per_page,
                    offset=offset,
                    level=LogLevel[level.upper()] if level else None,
                    purchase_id=purchase_id
                )
                
                logs = [
                    LogEntry(
                        id=log.get("id", 0),
                        timestamp=log.get("timestamp", ""),
                        level=log.get("level", "INFO"),
                        message=log.get("message", ""),
                        purchase_id=log.get("purchase_id"),
                        details=log.get("details")
                    )
                    for log in logs_data
                ]
                
                return LogsResponse(
                    logs=logs,
                    total=len(logs),
                    page=page,
                    per_page=per_page
                )
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/logs/export")
        async def export_logs(
            format: str = Query("json", regex="^(json|csv)$"),
            days: int = Query(7, ge=1, le=365)
        ):
            """Export logs in JSON or CSV format."""
            try:
                logs = await self.database.export_logs_json()
                
                if format == "csv":
                    # Convert to CSV
                    csv_lines = ["timestamp,level,message,purchase_id"]
                    for log in json.loads(logs):
                        ts = log.get("timestamp", "")
                        lvl = log.get("level", "")
                        msg = log.get("message", "").replace('"', '""')
                        pid = log.get("purchase_id", "") or ""
                        csv_lines.append(f'"{ts}","{lvl}","{msg}","{pid}"')
                    return JSONResponse(
                        content={"csv": "\n".join(csv_lines)},
                        media_type="application/json"
                    )
                
                return JSONResponse(content=json.loads(logs))
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/hardware")
        async def get_hardware_status():
            """Get detailed hardware status."""
            return self.hardware.get_status()
        
        @self.app.post("/api/debug/relay")
        async def control_relay(request: RelayControlRequest):
            """Control a specific relay (PIN required)."""
            if not self._verify_pin(request.pin):
                raise HTTPException(status_code=403, detail="Invalid PIN")
            
            if not self.hardware.relay:
                raise HTTPException(status_code=503, detail="Relay controller not available")
            
            success = await self.hardware.relay.set_relay(request.channel, request.state)
            
            if success:
                await self._broadcast({
                    "type": "relay_change",
                    "channel": request.channel,
                    "state": request.state
                })
                return {"success": True, "channel": request.channel, "state": request.state}
            else:
                raise HTTPException(status_code=500, detail="Failed to set relay")
        
        @self.app.post("/api/debug/led")
        async def control_led(request: LEDControlRequest):
            """Control LED strip (PIN required)."""
            if not self._verify_pin(request.pin):
                raise HTTPException(status_code=403, detail="Invalid PIN")
            
            if not self.hardware.led:
                raise HTTPException(status_code=503, detail="LED controller not available")
            
            if request.animation:
                success = await self.hardware.led.play_animation(request.animation)
            elif request.zone is not None:
                success = await self.hardware.led.set_zone_color(
                    request.zone, request.r, request.g, request.b
                )
            else:
                success = await self.hardware.led.set_color(request.r, request.g, request.b)
            
            return {"success": success}
        
        @self.app.post("/api/debug/audio")
        async def control_audio(request: AudioControlRequest):
            """Control audio (PIN required)."""
            if not self._verify_pin(request.pin):
                raise HTTPException(status_code=403, detail="Invalid PIN")
            
            if not self.hardware.audio:
                raise HTTPException(status_code=503, detail="Audio controller not available")
            
            if request.volume is not None:
                await self.hardware.audio.set_volume(request.volume)
            
            if request.sound:
                await self.hardware.audio.play_sound(request.sound)
            
            return {"success": True}
        
        @self.app.post("/api/debug/test-relay-cascade")
        async def test_relay_cascade(pin: str = Query(...)):
            """Test all relays in sequence (PIN required)."""
            if not self._verify_pin(pin):
                raise HTTPException(status_code=403, detail="Invalid PIN")
            
            if not self.hardware.relay:
                raise HTTPException(status_code=503, detail="Relay controller not available")
            
            # Run cascade test in background
            async def cascade():
                for i in range(1, 33):
                    await self.hardware.relay.set_relay(i, True)
                    await asyncio.sleep(0.1)
                    await self.hardware.relay.set_relay(i, False)
            
            asyncio.create_task(cascade())
            
            return {"success": True, "message": "Relay cascade test started"}
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket for real-time updates."""
            await websocket.accept()
            self._ws_connections.append(websocket)
            
            try:
                # Send initial status
                status = await get_status()
                await websocket.send_json({
                    "type": "status",
                    "data": status.model_dump()
                })
                
                # Keep connection alive and listen for messages
                while True:
                    try:
                        data = await asyncio.wait_for(
                            websocket.receive_text(),
                            timeout=30.0
                        )
                        
                        # Handle incoming messages
                        msg = json.loads(data)
                        
                        if msg.get("type") == "ping":
                            await websocket.send_json({"type": "pong"})
                        elif msg.get("type") == "get_status":
                            status = await get_status()
                            await websocket.send_json({
                                "type": "status",
                                "data": status.model_dump()
                            })
                            
                    except asyncio.TimeoutError:
                        # Send heartbeat
                        await websocket.send_json({"type": "heartbeat"})
                        
            except WebSocketDisconnect:
                pass
            finally:
                if websocket in self._ws_connections:
                    self._ws_connections.remove(websocket)
    
    async def _broadcast(self, message: dict):
        """Broadcast message to all connected WebSocket clients."""
        disconnected = []
        
        for ws in self._ws_connections:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        
        # Remove disconnected clients
        for ws in disconnected:
            self._ws_connections.remove(ws)
    
    def set_state(self, state: str):
        """Update current machine state."""
        self._current_state = state
        asyncio.create_task(self._broadcast({
            "type": "state_change",
            "state": state
        }))
    
    async def broadcast_event(self, event_type: str, data: dict):
        """Broadcast an event to all WebSocket clients."""
        await self._broadcast({
            "type": event_type,
            **data
        })


# Global server instance
_telemetry_server: Optional[TelemetryServer] = None


def get_telemetry_server() -> Optional[TelemetryServer]:
    """Get global telemetry server instance."""
    return _telemetry_server


def create_telemetry_server(
    config: Config,
    hardware: HardwareManager,
    database: DatabaseManager,
    logger: Logger
) -> TelemetryServer:
    """Create and return telemetry server instance."""
    global _telemetry_server
    _telemetry_server = TelemetryServer(config, hardware, database, logger)
    return _telemetry_server
