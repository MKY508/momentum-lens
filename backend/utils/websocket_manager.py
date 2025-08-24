"""
WebSocket connection manager for real-time data streaming.
"""

import asyncio
import json
import logging
from typing import Dict, List, Set
from datetime import datetime
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and subscriptions"""
    
    def __init__(self):
        # Store active connections
        self.active_connections: List[WebSocket] = []
        
        # Store subscriptions: {websocket: set(codes)}
        self.subscriptions: Dict[WebSocket, Set[str]] = {}
        
        # Store reverse mapping: {code: set(websockets)}
        self.code_subscribers: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = set()
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Clean up subscriptions
        if websocket in self.subscriptions:
            codes = self.subscriptions[websocket]
            for code in codes:
                if code in self.code_subscribers:
                    self.code_subscribers[code].discard(websocket)
                    if not self.code_subscribers[code]:
                        del self.code_subscribers[code]
            del self.subscriptions[websocket]
        
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def disconnect_all(self):
        """Disconnect all WebSocket connections"""
        for connection in self.active_connections.copy():
            try:
                await connection.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
            self.disconnect(connection)
    
    async def subscribe(self, websocket: WebSocket, codes: List[str]):
        """Subscribe a WebSocket to specific ETF codes"""
        if websocket not in self.subscriptions:
            self.subscriptions[websocket] = set()
        
        for code in codes:
            self.subscriptions[websocket].add(code)
            
            if code not in self.code_subscribers:
                self.code_subscribers[code] = set()
            self.code_subscribers[code].add(websocket)
        
        logger.info(f"WebSocket subscribed to {codes}")
    
    async def unsubscribe(self, websocket: WebSocket, codes: List[str]):
        """Unsubscribe a WebSocket from specific ETF codes"""
        if websocket not in self.subscriptions:
            return
        
        for code in codes:
            self.subscriptions[websocket].discard(code)
            
            if code in self.code_subscribers:
                self.code_subscribers[code].discard(websocket)
                if not self.code_subscribers[code]:
                    del self.code_subscribers[code]
        
        logger.info(f"WebSocket unsubscribed from {codes}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            self.disconnect(websocket)
    
    async def send_json_to_client(self, data: dict, websocket: WebSocket):
        """Send JSON data to a specific WebSocket"""
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.error(f"Error sending JSON to WebSocket: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all connected WebSockets"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_json(self, data: dict):
        """Broadcast JSON data to all connected WebSockets"""
        message = json.dumps(data)
        await self.broadcast(message)
    
    async def broadcast_price_update(self, code: str, price_data: dict):
        """Broadcast price update to subscribers of a specific ETF"""
        if code not in self.code_subscribers:
            return
        
        message = {
            "type": "price_update",
            "code": code,
            "data": price_data,
            "timestamp": datetime.now().isoformat()
        }
        
        disconnected = []
        for websocket in self.code_subscribers[code]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending price update: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_signal(self, signal_data: dict):
        """Broadcast trading signal to all connected clients"""
        message = {
            "type": "trading_signal",
            "data": signal_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_json(message)
    
    async def broadcast_alert(self, alert_data: dict):
        """Broadcast risk alert to all connected clients"""
        message = {
            "type": "risk_alert",
            "data": alert_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_json(message)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)
    
    def get_subscription_stats(self) -> Dict[str, int]:
        """Get statistics about subscriptions"""
        stats = {
            "total_connections": len(self.active_connections),
            "total_subscriptions": sum(len(subs) for subs in self.subscriptions.values()),
            "unique_codes": len(self.code_subscribers),
            "codes": {}
        }
        
        for code, subscribers in self.code_subscribers.items():
            stats["codes"][code] = len(subscribers)
        
        return stats