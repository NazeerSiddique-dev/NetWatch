import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { format } from 'date-fns';
import { clsx } from 'clsx';
import { Activity, Clock, Wifi } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';

export default function Analytics() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('60'); // minutes

  useEffect(() => {
    const fetchAnalytics = async () => {
      setLoading(true);
      try {
        // Use 1s granularity for ≤15m, 1m otherwise
        const granularity = parseInt(timeRange) <= 15 ? '1s' : '1m';
        const res = await axios.get(`${API_BASE}/metrics/history`, {
          params: { minutes: timeRange, granularity },
        });
        setData(res.data.data ?? []);
      } catch (e) {
        console.error('Failed to load analytics', e);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, [timeRange]);

  // Normalise field names: 1s rows use rx_mbps, 1m rows use avg_rx_mbps
  const chartData = useMemo(() => {
    return data.map((d) => {
      const rx   = d.rx_mbps      ?? d.avg_rx_mbps      ?? 0;
      const tx   = d.tx_mbps      ?? d.avg_tx_mbps      ?? 0;
      const pps  = d.total_packets_per_sec ?? d.avg_packets_per_sec ?? 0;
      const lat  = d.avg_latency_ms ?? null;
      return {
        ...d,
        rx_mbps: rx,
        tx_mbps: tx,
        total_packets_per_sec: pps,
        avg_latency_ms: lat,
        timeLabel: format(
          new Date(d.timestamp),
          parseInt(timeRange) > 60 ? 'HH:mm' : 'HH:mm:ss',
        ),
      };
    });
  }, [data, timeRange]);

  const ranges = [
    { label: '15m', value: '15' },
    { label: '1h',  value: '60' },
    { label: '6h',  value: '360' },
    { label: '24h', value: '1440' },
  ];

  const tooltipStyle = { backgroundColor: '#FFFFFF', borderColor: '#E2E8F0', color: '#0F172A' };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-dark">Historical Analytics</h1>
          <p className="text-sm text-slate-600 mt-1">Review past network performance and detect trends.</p>
        </div>
        <div className="flex items-center gap-2 glass-panel p-1 rounded-lg">
          {ranges.map((r) => (
            <button
              key={r.value}
              onClick={() => setTimeRange(r.value)}
              className={clsx(
                'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                timeRange === r.value
                  ? 'bg-brand-blue text-white shadow-sm'
                  : 'text-slate-600 hover:text-brand-dark hover:bg-slate-100',
              )}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="h-96 glass-panel rounded-xl flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-brand-500 border-t-transparent" />
        </div>
      ) : chartData.length === 0 ? (
        <div className="h-96 glass-panel rounded-xl flex flex-col items-center justify-center text-slate-600 gap-3">
          <Wifi className="w-12 h-12 opacity-20" />
          <p>No historical data yet. Keep the backend running and data will accumulate here.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Bandwidth */}
          <div className="glass-panel p-6 rounded-xl flex flex-col h-[350px] lg:col-span-2">
            <div className="flex items-center gap-2 mb-6">
              <Wifi className="w-5 h-5 text-brand-blue" />
              <h2 className="text-lg font-semibold text-brand-dark">Bandwidth (Mbps)</h2>
            </div>
            <div className="flex-1 min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis dataKey="timeLabel" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} minTickGap={40} />
                  <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(v: any) => `${Number(v).toFixed(3)} Mbps`} />
                  <Legend iconType="circle" />
                  <Line type="monotone" dataKey="rx_mbps" name="Download" stroke="#0891B2" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="tx_mbps" name="Upload"   stroke="#0284C7" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Packet Rate */}
          <div className="glass-panel p-6 rounded-xl flex flex-col h-[350px]">
            <div className="flex items-center gap-2 mb-6">
              <Activity className="w-5 h-5 text-brand-cyan" />
              <h2 className="text-lg font-semibold text-brand-dark">Packet Rate (pps)</h2>
            </div>
            <div className="flex-1 min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis dataKey="timeLabel" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} minTickGap={30} />
                  <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend iconType="circle" />
                  <Line type="monotone" dataKey="total_packets_per_sec" name="Packets/sec" stroke="#0284C7" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Latency */}
          <div className="glass-panel p-6 rounded-xl flex flex-col h-[350px]">
            <div className="flex items-center gap-2 mb-6">
              <Clock className="w-5 h-5 text-amber-500" />
              <h2 className="text-lg font-semibold text-brand-dark">Avg Latency (ms)</h2>
            </div>
            <div className="flex-1 min-h-0">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis dataKey="timeLabel" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} minTickGap={30} />
                  <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(v: any) => `${Number(v).toFixed(2)} ms`} />
                  <Legend iconType="circle" />
                  <Line type="monotone" dataKey="avg_latency_ms" name="Avg Latency" stroke="#f59e0b" strokeWidth={2} dot={false} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
