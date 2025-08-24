import { useEffect, useRef, useCallback } from 'react';
import webSocketService, { WebSocketEvents } from '../services/websocket';

export const useWebSocket = <K extends keyof WebSocketEvents>(
  event: K,
  callback: WebSocketEvents[K],
  deps: React.DependencyList = []
) => {
  const callbackRef = useRef(callback);
  
  // Update callback ref when it changes
  useEffect(() => {
    callbackRef.current = callback;
  });

  useEffect(() => {
    // Create a stable callback that uses the ref
    const stableCallback = (...args: Parameters<WebSocketEvents[K]>) => {
      (callbackRef.current as Function)(...args);
    };

    // Subscribe to the event
    const unsubscribe = webSocketService.on(event, stableCallback as WebSocketEvents[K]);

    // Cleanup on unmount or deps change
    return () => {
      unsubscribe();
    };
  }, [event, ...deps]);
};

export const useWebSocketConnection = () => {
  const connect = useCallback(() => {
    webSocketService.connect();
  }, []);

  const disconnect = useCallback(() => {
    webSocketService.disconnect();
  }, []);

  const isConnected = webSocketService.isConnected();

  useEffect(() => {
    // Auto-connect on mount if not connected
    if (!isConnected) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      // Don't disconnect on unmount as other components might be using it
    };
  }, []);

  return {
    connect,
    disconnect,
    isConnected,
  };
};