"""
Main FastAPI application for Momentum Lens ETF trading system.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from datetime import datetime, date

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from backend.config.settings import get_settings
from backend.config.config import get_config_manager
from backend.models.base import init_db, get_db_dependency
from backend.routers import market, portfolio, decisions, orders, config as config_router
from backend.core.data_fetcher import get_data_fetcher
from backend.utils.websocket_manager import WebSocketManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# WebSocket manager
ws_manager = WebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting Momentum Lens application...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # Initialize data fetcher
    data_fetcher = get_data_fetcher()
    logger.info("Data fetcher initialized")
    
    # Initialize configuration
    config_manager = get_config_manager()
    logger.info(f"Configuration loaded with preset: {config_manager.config.active_preset}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Momentum Lens application...")
    await ws_manager.disconnect_all()


# Create FastAPI application
app = FastAPI(
    title="Momentum Lens API",
    description="ETF momentum trading system with dynamic strategy configuration",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.application.cors_origins,
    allow_credentials=settings.application.cors_allow_credentials,
    allow_methods=settings.application.cors_allow_methods,
    allow_headers=settings.application.cors_allow_headers,
)

# Include routers with API prefix
api_prefix = f"{settings.application.api_prefix}/{settings.application.api_version}"

app.include_router(market.router, prefix=f"{api_prefix}/market", tags=["Market Data"])
app.include_router(portfolio.router, prefix=f"{api_prefix}/portfolio", tags=["Portfolio"])
app.include_router(decisions.router, prefix=f"{api_prefix}/decisions", tags=["Trading Decisions"])
app.include_router(orders.router, prefix=f"{api_prefix}/orders", tags=["Order Management"])
app.include_router(config_router.router, prefix=f"{api_prefix}/config", tags=["Configuration"])


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Momentum Lens API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "documentation": "/docs",
        "api_prefix": api_prefix
    }


@app.get(f"{api_prefix}/health")
async def health_check():
    """Health check endpoint"""
    from backend.models.base import DatabaseManager
    
    db_status = DatabaseManager.check_connection()
    
    return {
        "status": "healthy" if db_status else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": "connected" if db_status else "disconnected",
        "version": "1.0.0"
    }


@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """
    WebSocket endpoint for real-time price streaming.
    
    Client can subscribe to specific ETF codes by sending:
    {"action": "subscribe", "codes": ["510300", "510500"]}
    
    Client can unsubscribe:
    {"action": "unsubscribe", "codes": ["510300"]}
    """
    await ws_manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            action = data.get("action")
            codes = data.get("codes", [])
            
            if action == "subscribe":
                await ws_manager.subscribe(websocket, codes)
                await websocket.send_json({
                    "type": "subscription",
                    "status": "subscribed",
                    "codes": codes
                })
            
            elif action == "unsubscribe":
                await ws_manager.unsubscribe(websocket, codes)
                await websocket.send_json({
                    "type": "subscription",
                    "status": "unsubscribed",
                    "codes": codes
                })
            
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
            
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


@app.websocket("/ws/signals")
async def websocket_signals(websocket: WebSocket):
    """
    WebSocket endpoint for real-time trading signals.
    
    Broadcasts trading signals as they are generated.
    """
    await ws_manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("Signal WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Signal WebSocket error: {e}")
        ws_manager.disconnect(websocket)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle ValueError exceptions"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": str(exc),
            "status_code": 400,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.application.debug,
        workers=settings.application.workers if not settings.application.debug else 1,
        log_level=settings.application.log_level.lower()
    )