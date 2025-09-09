import { useState, useEffect } from 'react';
import axios from 'axios';
import { RefreshCw, Wifi, WifiOff, ArrowDown, ArrowUp } from 'lucide-react';
import { clsx } from 'clsx';

const API_BASE = 'http://localhost:8000/api';

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B/s';
  const k = 1024;
  const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

function StatBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-600 mb-1">
        <span>{label}</span>
        <span>{pct.toFixed(1)}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-slate-200 overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function Interfaces() {
  const [interfaces, setInterfaces] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchInterfaces = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/interfaces`);
      setInterfaces(res.data.interfaces ?? []);
    } catch (e) {
      console.error('Failed to load interfaces', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchInterfaces();
    const id = setInterval(() => fetchInterfaces(true), 3000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-dark">Network Interfaces</h1>
          <p className="text-sm text-slate-600 mt-1">
            Live statistics for all host network interfaces. Auto-refreshes every 3 seconds.
          </p>
        </div>
        <button
          onClick={() => fetchInterfaces(true)}
          disabled={refreshing}
          className="self-start p-2 rounded-lg bg-slate-50 border border-slate-300 text-slate-600 hover:text-brand-dark transition-all disabled:opacity-50"
        >
          <RefreshCw className={clsx('w-5 h-5', refreshing && 'animate-spin')} />
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-brand-500 border-t-transparent" />
        </div>
      ) : interfaces.length === 0 ? (
        <div className="glass-panel p-10 rounded-xl flex flex-col items-center text-slate-600 gap-3">
          <WifiOff className="w-12 h-12 opacity-30" />
          <p>No interfaces found.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {interfaces.map((iface) => (
            <div
              key={iface.name}
              className={clsx(
                'glass-panel rounded-xl p-5 border transition-all',
                iface.is_up
                  ? 'border-slate-200 hover:border-slate-300'
                  : 'border-slate-100 opacity-60',
              )}
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  {iface.is_up
                    ? <Wifi className="w-5 h-5 text-emerald-600" />
                    : <WifiOff className="w-5 h-5 text-slate-600" />}
                  <div>
                    <p className="font-bold text-brand-dark text-lg leading-none">{iface.name}</p>
                    {iface.mac_address && (
                      <p className="text-xs text-slate-600 mt-0.5 font-mono">{iface.mac_address}</p>
                    )}
                  </div>
                </div>
                <span className={clsx(
                  'text-xs font-medium px-2 py-1 rounded-full tracking-wide',
                  iface.is_up
                    ? 'bg-emerald-500/10 text-emerald-600'
                    : 'bg-slate-200 text-slate-500',
                )}>
                  {iface.is_up ? 'UP' : 'DOWN'}
                </span>
              </div>

              {/* IP addresses */}
              {iface.addresses?.length > 0 && (
                <div className="mb-4 space-y-1">
                  {iface.addresses.slice(0, 3).map((addr: any, i: number) => (
                    <p key={i} className="text-xs font-mono text-slate-600">
                      <span className="text-slate-600">{addr.family ?? 'inet'}: </span>
                      {addr.address}
                      {addr.netmask && <span className="text-slate-600"> / {addr.netmask}</span>}
                    </p>
                  ))}
                </div>
              )}

              {/* Traffic stats */}
              {iface.is_up && (
                <div className="space-y-3 pt-3 border-t border-slate-200">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="flex items-center gap-1.5 text-slate-600">
                      <ArrowDown className="w-3.5 h-3.5 text-emerald-600" />
                      <span>{formatBytes(iface.rx_bytes_per_sec ?? 0)}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-slate-600">
                      <ArrowUp className="w-3.5 h-3.5 text-blue-600" />
                      <span>{formatBytes(iface.tx_bytes_per_sec ?? 0)}</span>
                    </div>
                  </div>

                  <StatBar
                    label="RX Packets/s"
                    value={iface.rx_packets_per_sec ?? 0}
                    max={Math.max(iface.rx_packets_per_sec ?? 0, iface.tx_packets_per_sec ?? 0, 100)}
                    color="bg-emerald-500"
                  />
                  <StatBar
                    label="TX Packets/s"
                    value={iface.tx_packets_per_sec ?? 0}
                    max={Math.max(iface.rx_packets_per_sec ?? 0, iface.tx_packets_per_sec ?? 0, 100)}
                    color="bg-blue-500"
                  />

                  {/* Totals */}
                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 pt-1 border-t border-slate-200">
                    <div>
                      <p>RX Total</p>
                      <p className="text-slate-600 font-mono">{((iface.rx_bytes ?? 0) / 1e6).toFixed(1)} MB</p>
                    </div>
                    <div>
                      <p>TX Total</p>
                      <p className="text-slate-600 font-mono">{((iface.tx_bytes ?? 0) / 1e6).toFixed(1)} MB</p>
                    </div>
                    {iface.mtu && (
                      <div>
                        <p>MTU</p>
                        <p className="text-slate-600">{iface.mtu}</p>
                      </div>
                    )}
                    {iface.speed_mbps && (
                      <div>
                        <p>Speed</p>
                        <p className="text-slate-600">{iface.speed_mbps} Mbps</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
