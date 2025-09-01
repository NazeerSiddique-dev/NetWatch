import React, { createContext, useContext, useEffect, useState } from 'react';
import axios from 'axios';
import { useWebSocket } from '../hooks/useWebSocket';

const API_BASE = 'http://localhost:8000/api';

interface MetricsContextType {
  history: any[];
  status: any;
  latestMetric: any;
  isConnected: boolean;
}

const MetricsContext = createContext<MetricsContextType | undefined>(undefined);

export function MetricsProvider({ children }: { children: React.ReactNode }) {
  const { data: latestMetric, isConnected } = useWebSocket('/metrics');
  const [history, setHistory] = useState<any[]>([]);
  const [status, setStatus] = useState<any>(null);

  // ── Initial history backfill (run ONCE on mount) ─────────────────────────
  useEffect(() => {
    const fetchInitData = async () => {
      try {
        const histRes = await axios.get(`${API_BASE}/metrics/history?minutes=10&granularity=1s`);
        const points = histRes.data.data || [];
        // Only seed history if there is no live data yet
        setHistory(prev => prev.length === 0 ? points : prev);
      } catch (e) {
        console.error('Failed to load initial history', e);
      }
    };
    fetchInitData();
  }, []);

  // ── Status card poll (lightweight, every 15s, does NOT touch chart data) ──
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await axios.get(`${API_BASE}/metrics/status`);
        setStatus(res.data);
      } catch (_) {}
    };
    fetchStatus();
    const id = setInterval(fetchStatus, 15000);
    return () => clearInterval(id);
  }, []);

  // ── Append real-time WebSocket metrics to history (sliding 10-min window) ─
  useEffect(() => {
    if (latestMetric) {
      setHistory(prev => {
        const newHist = [...prev, latestMetric];
        if (newHist.length > 600) newHist.shift(); // Keep last 10 mins (600s)
        return newHist;
      });
    }
  }, [latestMetric]);

  return (
    <MetricsContext.Provider value={{ history, status, latestMetric, isConnected }}>
      {children}
    </MetricsContext.Provider>
  );
}

export function useMetrics() {
  const context = useContext(MetricsContext);
  if (context === undefined) {
    throw new Error('useMetrics must be used within a MetricsProvider');
  }
  return context;
}
