import { useEffect, useRef, useState } from 'react';

interface WebSocketMessage {
  type: string;
  data: any;
}

export function useWebSocket<T = any>(endpoint: string) {
  const [data, setData] = useState<T | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Event | null>(null);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Determine the base WS URL based on current host (handles dev vs prod)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    // Assuming backend runs on 8000 during dev, or same port in prod
    const port = '8000';
    const wsUrl = `${protocol}//${host}:${port}/ws${endpoint}`;

    const connect = () => {
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setIsConnected(true);
        setError(null);
      };

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          if (message.type !== 'ping') {
            setData(message.data);
          }
        } catch (e) {
          console.error("Failed to parse websocket message", e);
        }
      };

      ws.current.onclose = () => {
        setIsConnected(false);
        // Attempt to reconnect after 3 seconds
        setTimeout(connect, 3000);
      };

      ws.current.onerror = (e) => {
        setError(e);
      };
    };

    connect();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [endpoint]);

  return { data, isConnected, error };
}
