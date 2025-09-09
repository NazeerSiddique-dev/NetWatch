import { useState, useEffect } from 'react';
import axios from 'axios';
import { ShieldAlert, CheckCircle2, AlertTriangle, Info, RefreshCw } from 'lucide-react';
import { format } from 'date-fns';
import { clsx } from 'clsx';

const API_BASE = 'http://localhost:8000/api';

export default function Alerts() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState<any | null>(null);

  const fetchAlerts = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/alerts`, { params: { page_size: 100 } });
      // API returns { alerts: [...], total: N, ... }
      setAlerts(res.data.alerts ?? []);
      setTotal(res.data.total ?? 0);
    } catch (e) {
      console.error('Failed to load alerts', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
    // Poll for new alerts every 5 seconds
    const id = setInterval(() => fetchAlerts(true), 5000);
    return () => clearInterval(id);
  }, []);

  const updateAlertStatus = async (id: string, status: string) => {
    try {
      await axios.patch(`${API_BASE}/alerts/${id}`, { status });
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, status } : a)));
    } catch (e) {
      console.error(`Failed to update alert`, e);
    }
  };

  const resolveAllAlerts = async () => {
    try {
      setLoading(true);
      await axios.post(`${API_BASE}/alerts/resolve-all`);
      await fetchAlerts();
    } catch (e) {
      console.error('Failed to resolve all alerts', e);
      setLoading(false);
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return <ShieldAlert className="w-4 h-4 text-rose-500" />;
      case 'HIGH':     return <AlertTriangle className="w-4 h-4 text-orange-500" />;
      case 'MEDIUM':   return <AlertTriangle className="w-4 h-4 text-amber-500" />;
      default:         return <Info className="w-4 h-4 text-blue-500" />;
    }
  };

  const severityColor = (s: string) =>
    s === 'CRITICAL' ? 'text-rose-600' :
    s === 'HIGH'     ? 'text-orange-400' :
    s === 'MEDIUM'   ? 'text-amber-400'  : 'text-blue-600';

  const statusBadge = (s: string) =>
    s === 'NEW'          ? 'bg-rose-500/20 text-rose-600 border border-rose-500/30' :
    s === 'ACKNOWLEDGED' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                           'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20';

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-dark flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-rose-500" /> Alert Center
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Real-time anomalies detected by the Z-Score engine. Auto-refreshes every 5s.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-slate-600 text-sm">{total} total alerts</span>
          <button
            onClick={resolveAllAlerts}
            disabled={loading || alerts.every(a => a.status === 'RESOLVED')}
            className="px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 hover:bg-emerald-500/20 transition-all disabled:opacity-50 text-sm font-medium flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4" /> Resolve All
          </button>
          <button
            onClick={() => fetchAlerts(true)}
            disabled={refreshing}
            className="p-1.5 rounded-lg bg-slate-50 border border-slate-300 text-slate-600 hover:text-brand-dark transition-all disabled:opacity-50"
          >
            <RefreshCw className={clsx('w-5 h-5', refreshing && 'animate-spin')} />
          </button>
        </div>
      </div>

      <div className="glass-panel rounded-xl overflow-hidden border border-slate-200">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th className="px-4 py-3 font-medium">Severity</th>
                <th className="px-4 py-3 font-medium">Time</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Score</th>
                <th className="px-4 py-3 font-medium">Interface</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center">
                    <div className="flex justify-center">
                      <div className="animate-spin rounded-full h-6 w-6 border-2 border-brand-500 border-t-transparent" />
                    </div>
                  </td>
                </tr>
              ) : alerts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-slate-600">
                    No anomalies detected in the last 24 hours. The detector is running.
                  </td>
                </tr>
              ) : (
                alerts.map((alert) => (
                  <tr
                    key={alert.id}
                    className={clsx(
                      'transition-colors',
                      alert.status === 'NEW'
                        ? 'bg-rose-500/5 hover:bg-rose-500/10'
                        : 'hover:bg-slate-50'
                    )}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {getSeverityIcon(alert.severity)}
                        <span className={clsx('font-medium', severityColor(alert.severity))}>
                          {alert.severity}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {format(new Date(alert.created_at), 'MMM d, HH:mm:ss')}
                    </td>
                    <td className="px-4 py-3 text-slate-800 font-medium">
                      {alert.alert_type}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-600">
                      {alert.anomaly_score != null ? alert.anomaly_score.toFixed(3) : '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {alert.interface ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={clsx('px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wider', statusBadge(alert.status))}>
                        {alert.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <button
                        onClick={() => setSelectedAlert(alert)}
                        className="text-xs px-3 py-1 bg-blue-500/10 text-blue-600 hover:bg-blue-500/20 rounded transition-colors inline-flex items-center gap-1"
                      >
                        <Info className="w-3 h-3" /> View
                      </button>
                      {alert.status === 'NEW' && (
                        <button
                          onClick={() => updateAlertStatus(alert.id, 'ACKNOWLEDGED')}
                          className="text-xs px-3 py-1 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 rounded transition-colors"
                        >
                          Acknowledge
                        </button>
                      )}
                      {alert.status !== 'RESOLVED' && (
                        <button
                          onClick={() => updateAlertStatus(alert.id, 'RESOLVED')}
                          className="text-xs px-3 py-1 bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 rounded transition-colors inline-flex items-center gap-1"
                        >
                          <CheckCircle2 className="w-3 h-3" /> Resolve
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* View Alert Modal */}
      {selectedAlert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-300 rounded-xl max-w-lg w-full p-6 shadow-2xl">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-lg font-bold text-brand-dark flex items-center gap-2">
                {getSeverityIcon(selectedAlert.severity)}
                Alert Details
              </h2>
              <button onClick={() => setSelectedAlert(null)} className="text-slate-600 hover:text-brand-dark">✕</button>
            </div>
            
            <div className="space-y-4">
              <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
                <p className="text-slate-800">{selectedAlert.message}</p>
                <p className="text-xs text-slate-600 mt-2">
                  Detected at {format(new Date(selectedAlert.created_at), 'MMM d, yyyy HH:mm:ss')}
                </p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="glass-panel p-3 rounded-lg border border-slate-300/30">
                  <p className="text-xs text-slate-600 uppercase tracking-wider">Metric</p>
                  <p className="font-mono text-fuchsia-400 mt-1">{selectedAlert.metric_name || 'N/A'}</p>
                </div>
                <div className="glass-panel p-3 rounded-lg border border-slate-300/30">
                  <p className="text-xs text-slate-600 uppercase tracking-wider">Interface</p>
                  <p className="font-mono text-blue-600 mt-1">{selectedAlert.interface || 'N/A'}</p>
                </div>
                
                <div className="glass-panel p-3 rounded-lg border border-slate-300/30">
                  <p className="text-xs text-slate-600 uppercase tracking-wider">Observed Value</p>
                  <p className="font-mono text-rose-600 mt-1 text-lg">
                    {selectedAlert.observed_value != null ? selectedAlert.observed_value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : 'N/A'}
                  </p>
                </div>
                <div className="glass-panel p-3 rounded-lg border border-slate-300/30">
                  <p className="text-xs text-slate-600 uppercase tracking-wider">Baseline (Normal)</p>
                  <p className="font-mono text-emerald-600 mt-1 text-lg">
                    {selectedAlert.baseline_value != null ? selectedAlert.baseline_value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : 'N/A'}
                  </p>
                </div>
                
                <div className="glass-panel p-4 rounded-lg border border-slate-300/30 col-span-2 flex justify-between items-center bg-slate-50">
                  <div>
                    <p className="text-xs text-slate-600 uppercase tracking-wider">Deviation (Z-Score)</p>
                    <p className="font-mono text-amber-400 mt-1 text-xl font-semibold">
                      {selectedAlert.deviation_sigma != null ? `${selectedAlert.deviation_sigma.toFixed(2)}σ` : 'N/A'}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-600 uppercase tracking-wider">Algorithm Score</p>
                    <p className="font-mono text-brand-dark mt-1 text-xl">
                      {selectedAlert.anomaly_score != null ? selectedAlert.anomaly_score.toFixed(3) : 'N/A'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="mt-6 pt-4 border-t border-slate-200 flex justify-end gap-3">
              <button
                onClick={() => setSelectedAlert(null)}
                className="px-4 py-2 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors text-sm font-medium"
              >
                Close
              </button>
              {selectedAlert.status !== 'RESOLVED' && (
                <button
                  onClick={() => {
                    updateAlertStatus(selectedAlert.id, 'RESOLVED');
                    setSelectedAlert(null);
                  }}
                  className="px-4 py-2 rounded-lg bg-emerald-500/20 border border-emerald-500/30 text-emerald-600 hover:bg-emerald-500/30 transition-all text-sm font-medium flex items-center gap-2 shadow-lg shadow-emerald-900/20"
                >
                  <CheckCircle2 className="w-4 h-4" /> Resolve Alert
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
