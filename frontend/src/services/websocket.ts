import { io, Socket } from 'socket.io-client';
import { PriceUpdate, Alert, Decision, MarketIndicator } from '../types';

const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

export type WebSocketEvents = {
  price_update: (data: PriceUpdate) => void;
  alert: (alert: Alert) => void;
  decision_update: (decision: Decision) => void;
  market_update: (indicators: MarketIndicator) => void;
  rebalance_required: (data: { deviation: number; etfs: string[] }) => void;
  trade_executed: (trade: any) => void;
  connection_status: (status: 'connected' | 'disconnected' | 'error') => void;
};

class WebSocketService {
  private socket: Socket | null = null;
  private listeners: Map<keyof WebSocketEvents, Set<Function>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  connect(): void {
    if (this.socket?.connected) {
      console.log('WebSocket already connected');
      return;
    }

    this.socket = io(WS_URL, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: this.reconnectDelay,
      reconnectionAttempts: this.maxReconnectAttempts,
    });

    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.emit('connection_status', 'connected');
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      this.emit('connection_status', 'disconnected');
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;
      
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        this.emit('connection_status', 'error');
      }
    });

    // Subscribe to real-time events
    this.socket.on('price_update', (data: PriceUpdate) => {
      this.emit('price_update', data);
    });

    this.socket.on('alert', (alert: Alert) => {
      this.emit('alert', alert);
    });

    this.socket.on('decision_update', (decision: Decision) => {
      this.emit('decision_update', decision);
    });

    this.socket.on('market_update', (indicators: MarketIndicator) => {
      this.emit('market_update', indicators);
    });

    this.socket.on('rebalance_required', (data: any) => {
      this.emit('rebalance_required', data);
    });

    this.socket.on('trade_executed', (trade: any) => {
      this.emit('trade_executed', trade);
    });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  on<K extends keyof WebSocketEvents>(
    event: K,
    callback: WebSocketEvents[K]
  ): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    
    this.listeners.get(event)!.add(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = this.listeners.get(event);
      if (callbacks) {
        callbacks.delete(callback);
      }
    };
  }

  off<K extends keyof WebSocketEvents>(
    event: K,
    callback?: WebSocketEvents[K]
  ): void {
    if (!callback) {
      this.listeners.delete(event);
    } else {
      const callbacks = this.listeners.get(event);
      if (callbacks) {
        callbacks.delete(callback);
      }
    }
  }

  private emit<K extends keyof WebSocketEvents>(
    event: K,
    ...args: Parameters<WebSocketEvents[K]>
  ): void {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          (callback as Function)(...args);
        } catch (error) {
          console.error(`Error in WebSocket event handler for ${event}:`, error);
        }
      });
    }
  }

  // Subscribe to specific ETF price updates
  subscribeToETF(code: string): void {
    if (this.socket?.connected) {
      this.socket.emit('subscribe_etf', { code });
    }
  }

  unsubscribeFromETF(code: string): void {
    if (this.socket?.connected) {
      this.socket.emit('unsubscribe_etf', { code });
    }
  }

  // Request immediate update
  requestUpdate(type: 'prices' | 'indicators' | 'decision'): void {
    if (this.socket?.connected) {
      this.socket.emit('request_update', { type });
    }
  }

  isConnected(): boolean {
    return this.socket?.connected || false;
  }
}

// Export singleton instance
export const webSocketService = new WebSocketService();

export default webSocketService;