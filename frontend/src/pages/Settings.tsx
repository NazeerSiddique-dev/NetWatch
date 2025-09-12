import { useState, useEffect } from 'react';
import axios from 'axios';
import { Settings as SettingsIcon, Save, AlertCircle, CheckCircle2 } from 'lucide-react';
import { clsx } from 'clsx';

const API_BASE = 'http://localhost:8000/api';

export default function Settings() {
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notification, setNotification] = useState<{ type: 'success' | 'error', message: string } | null>(null);

  // Form states
  const [anomalyThreshold, setAnomalyThreshold] = useState<number>(3.0);
  const [alertCooldown, setAlertCooldown] = useState<number>(60);

  const [interfaces, setInterfaces] = useState<string[]>([]);
  const [activeInterface, setActiveInterface] = useState<string>('');

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await axios.get(`${API_BASE}/settings`);
        setConfig(res.data);
        setAnomalyThreshold(res.data.anomaly_threshold || 3.0);
        setAlertCooldown(res.data.alert_cooldown_seconds || 60);
        setActiveInterface(res.data.active_interface || '');
      } catch (e) {
        console.error('Failed to fetch settings', e);
      } finally {
        setLoading(false);
      }
    };
    fetchConfig();
    
    axios.get(`${API_BASE}/interfaces`).then(res => {
      setInterfaces((res.data.interfaces || []).map((i: any) => i.name));
    }).catch(e => console.error(e));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setNotification(null);
    try {
      await axios.patch(`${API_BASE}/settings`, {
        anomaly_threshold: anomalyThreshold,
        alert_cooldown_seconds: alertCooldown,
        active_interface: activeInterface || null,
      });
      setNotification({ type: 'success', message: 'Settings saved successfully! The detection engine has been updated.' });
      
      // Clear notification after 3 seconds
      setTimeout(() => setNotification(null), 3000);
    } catch (e: any) {
      setNotification({ type: 'error', message: e.response?.data?.detail || 'Failed to save settings.' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-dark flex items-center gap-2">
            <SettingsIcon className="w-6 h-6 text-slate-600" /> System Settings
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Dynamically configure NetWatch behavior in real-time.
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-blue text-brand-dark rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-brand-500/20"
        >
          {saving ? <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" /> : <Save className="w-4 h-4" />}
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {notification && (
        <div className={clsx("flex items-center gap-3 p-4 rounded-lg border", 
          notification.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600' : 'bg-rose-500/10 border-rose-500/20 text-rose-600'
        )}>
          {notification.type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
          <p className="font-medium text-sm">{notification.message}</p>
        </div>
      )}

      <div className="glass-panel p-6 rounded-xl space-y-8">
        
        {/* Detection Engine Configuration */}
        <div>
          <h3 className="text-lg font-medium text-brand-dark mb-4 border-b border-slate-200 pb-2">Detection Engine</h3>
          
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 text-sm mb-6 flex justify-between items-center">
            <div>
              <p className="text-slate-600 mb-1">Active algorithm</p>
              <p className="font-medium text-brand-dark uppercase">{config?.detector_type || 'Statistical'}</p>
            </div>
            <div className="text-right">
              <p className="text-slate-600 mb-1">Data Source</p>
              <select
                value={activeInterface}
                onChange={(e) => setActiveInterface(e.target.value)}
                className="bg-slate-200 text-slate-500 font-semibold rounded text-xs px-2 py-1 focus:outline-none focus:border-brand-blue cursor-pointer"
              >
                <option value="">AUTO (System Default)</option>
                {interfaces.map(iface => (
                  <option key={iface} value={iface}>{iface}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="block text-sm font-medium text-slate-600">
                  Anomaly Sensitivity Threshold (Z-Score)
                </label>
                <span className="text-brand-blue font-mono bg-brand-blue/10 px-2 py-1 rounded text-sm">{anomalyThreshold.toFixed(1)}</span>
              </div>
              <p className="text-xs text-slate-600 mb-4">
                Lower values make the detector more sensitive to smaller spikes. Higher values reduce false positives. Default is 3.0.
              </p>
              <input 
                type="range" 
                min="1.0" 
                max="10.0" 
                step="0.1" 
                value={anomalyThreshold} 
                onChange={(e) => setAnomalyThreshold(parseFloat(e.target.value))}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand-blue"
              />
              <div className="flex justify-between text-xs text-slate-600 mt-2">
                <span>Highly Sensitive (1.0)</span>
                <span>Strict (10.0)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Alerting Configuration */}
        <div>
          <h3 className="text-lg font-medium text-brand-dark mb-4 border-b border-slate-200 pb-2">Alert Configuration</h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-2">
                Alert Cooldown Period (seconds)
              </label>
              <p className="text-xs text-slate-600 mb-3">
                Minimum time to wait before triggering another alert for the same type of anomaly to prevent alert fatigue.
              </p>
              <input 
                type="number" 
                min="10" 
                max="3600"
                value={alertCooldown}
                onChange={(e) => setAlertCooldown(parseInt(e.target.value))}
                className="bg-slate-100 border border-slate-300 text-brand-dark text-sm rounded-lg focus:ring-brand-500 focus:border-brand-500 block w-full sm:w-64 p-2.5 outline-none"
              />
            </div>
          </div>
        </div>

        {/* Data Retention Configuration (Read-only for now) */}
        <div>
          <h3 className="text-lg font-medium text-brand-dark mb-4 border-b border-slate-200 pb-2">Data Retention Policy</h3>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
              <p className="text-slate-600 text-xs mb-1">1-Second Metrics</p>
              <p className="font-medium text-brand-dark">{config?.retention_metrics_1s_hours || 24} hours</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
              <p className="text-slate-600 text-xs mb-1">1-Minute Aggregates</p>
              <p className="font-medium text-brand-dark">{config?.retention_metrics_1m_days || 30} days</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
              <p className="text-slate-600 text-xs mb-1">Raw Flow Data</p>
              <p className="font-medium text-brand-dark">{config?.retention_raw_flows_hours || 24} hours</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
              <p className="text-slate-600 text-xs mb-1">Alert History</p>
              <p className="font-medium text-brand-dark">{config?.retention_alerts_days || 90} days</p>
            </div>
          </div>
          <p className="text-xs text-slate-600 mt-3">
            Note: Data retention periods are currently enforced via background cron jobs and require a backend restart to update.
          </p>
        </div>

      </div>
    </div>
  );
}
