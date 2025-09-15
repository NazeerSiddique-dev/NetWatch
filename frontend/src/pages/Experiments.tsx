import { useState, useEffect } from 'react';
import axios from 'axios';
import { FlaskConical, Play, CheckCircle, XCircle, BarChart2, Zap, Clock } from 'lucide-react';
import { clsx } from 'clsx';
import { format } from 'date-fns';

const API_BASE = 'http://localhost:8000/api';

const ATTACK_OPTIONS = [
  { id: 'syn_flood',  label: 'TCP SYN Flood',       description: 'Floods target with SYN packets, exhausting connection table', color: 'text-rose-600',    bg: 'bg-rose-500/10',    border: 'border-rose-500/20' },
  { id: 'udp_flood',  label: 'UDP Flood',             description: 'Overwhelms target with high-volume UDP datagrams',           color: 'text-orange-400',  bg: 'bg-orange-500/10',  border: 'border-orange-500/20' },
  { id: 'port_scan',  label: 'Port Scan',             description: 'Probes many ports sequentially to discover open services',   color: 'text-amber-400',   bg: 'bg-amber-500/10',   border: 'border-amber-500/20' },
  { id: 'data_exfil', label: 'Data Exfiltration',    description: 'Abnormally high outbound traffic simulating data theft',     color: 'text-purple-400',  bg: 'bg-purple-500/10',  border: 'border-purple-500/20' },
  { id: 'icmp_flood', label: 'ICMP Ping Flood',       description: 'Sends massive ICMP echo requests to saturate bandwidth',     color: 'text-blue-600',    bg: 'bg-blue-500/10',    border: 'border-blue-500/20' },
];

export default function Experiments() {
  const [experiments, setExperiments] = useState<any[]>([]);
  const [evaluation, setEvaluation] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Inject form state
  const [selectedAttack, setSelectedAttack] = useState('syn_flood');
  const [duration, setDuration] = useState(15);
  const [intensity, setIntensity] = useState(1.0);
  const [injecting, setInjecting] = useState(false);
  const [injectResult, setInjectResult] = useState<string | null>(null);
  const [countdown, setCountdown] = useState(0);

  const fetchData = async () => {
    try {
      const [expRes, evalRes] = await Promise.all([
        axios.get(`${API_BASE}/experiments`),
        axios.get(`${API_BASE}/experiments/evaluation`),
      ]);
      setExperiments(expRes.data.experiments ?? []);
      setEvaluation(evalRes.data);
    } catch (e) {
      console.error('Failed to load experiments', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Refresh experiment list every 3s to pick up status changes
    const id = setInterval(fetchData, 3000);
    return () => clearInterval(id);
  }, []);

  // Countdown timer while injection is running
  useEffect(() => {
    if (countdown <= 0) return;
    const t = setInterval(() => setCountdown(c => {
      if (c <= 1) { clearInterval(t); return 0; }
      return c - 1;
    }), 1000);
    return () => clearInterval(t);
  }, [countdown]);

  const runInjection = async () => {
    setInjecting(true);
    setInjectResult(null);
    try {
      const res = await axios.post(`${API_BASE}/experiments/inject`, {
        attack_type: selectedAttack,
        duration_sec: duration,
        intensity,
      });
      setInjectResult(`✅ ${res.data.message}`);
      setCountdown(duration);
    } catch (e: any) {
      setInjectResult(`❌ ${e?.response?.data?.detail ?? e.message}`);
    } finally {
      setInjecting(false);
    }
  };

  const statusColor = (s: string) =>
    s === 'RUNNING'   ? 'text-brand-blue animate-pulse' :
    s === 'COMPLETED' ? 'text-emerald-600' :
    s === 'FAILED'    ? 'text-rose-600' : 'text-slate-600';

  const selectedProfile = ATTACK_OPTIONS.find(a => a.id === selectedAttack)!;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-brand-dark flex items-center gap-2">
          <FlaskConical className="w-6 h-6 text-fuchsia-500" /> Experiments & Evaluation
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          Inject simulated attacks directly into the detection pipeline — <span className="text-emerald-600 font-medium">no sudo required</span>.
        </p>
      </div>

      {/* Evaluation metrics */}
      {evaluation && evaluation.total_experiments > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Precision',    value: evaluation.precision    != null ? `${evaluation.precision}%`    : '—' },
            { label: 'Recall',       value: evaluation.recall       != null ? `${evaluation.recall}%`       : '—' },
            { label: 'F1 Score',     value: evaluation.f1_score     != null ? `${evaluation.f1_score}%`     : '—' },
            { label: 'Avg Latency',  value: evaluation.avg_detection_latency_ms != null ? `${evaluation.avg_detection_latency_ms} ms` : '—' },
          ].map(m => (
            <div key={m.label} className="glass-panel p-4 rounded-xl">
              <p className="text-xs text-slate-600 uppercase tracking-wider">{m.label}</p>
              <p className="text-2xl font-bold text-brand-dark mt-1">{m.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

        {/* Attack type selector */}
        <div className="lg:col-span-2 space-y-3">
          <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wider">Select Attack Type</h2>
          {ATTACK_OPTIONS.map(attack => (
            <button
              key={attack.id}
              onClick={() => setSelectedAttack(attack.id)}
              className={clsx(
                'w-full text-left p-4 rounded-xl border transition-all',
                selectedAttack === attack.id
                  ? `${attack.bg} ${attack.border} ring-1 ring-inset ring-current`
                  : 'glass-panel border-slate-200 hover:border-slate-600',
              )}
            >
              <p className={clsx('font-semibold text-sm', selectedAttack === attack.id ? attack.color : 'text-slate-800')}>
                {attack.label}
              </p>
              <p className="text-xs text-slate-600 mt-0.5">{attack.description}</p>
            </button>
          ))}
        </div>

        {/* Injection control panel */}
        <div className="lg:col-span-3 flex flex-col gap-4">

          <div className={clsx('glass-panel p-6 rounded-xl border', selectedProfile.border)}>
            <div className="flex items-center gap-3 mb-5">
              <div className={clsx('p-2 rounded-lg', selectedProfile.bg)}>
                <Zap className={clsx('w-5 h-5', selectedProfile.color)} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-brand-dark">{selectedProfile.label}</h2>
                <p className="text-xs text-slate-600">{selectedProfile.description}</p>
              </div>
            </div>

            <div className="space-y-5">
              {/* Duration slider */}
              <div>
                <div className="flex justify-between mb-1">
                  <label className="text-sm font-medium text-slate-600">Duration</label>
                  <span className={clsx('text-sm font-bold', selectedProfile.color)}>{duration}s</span>
                </div>
                <input
                  type="range" min={5} max={60} step={5}
                  value={duration}
                  onChange={e => setDuration(Number(e.target.value))}
                  className="w-full accent-fuchsia-500"
                />
                <div className="flex justify-between text-xs text-slate-600 mt-0.5">
                  <span>5s</span><span>30s</span><span>60s</span>
                </div>
              </div>

              {/* Intensity slider */}
              <div>
                <div className="flex justify-between mb-1">
                  <label className="text-sm font-medium text-slate-600">Intensity</label>
                  <span className={clsx('text-sm font-bold', selectedProfile.color)}>
                    {intensity === 1.0 ? 'Maximum' : intensity >= 0.7 ? 'High' : intensity >= 0.4 ? 'Medium' : 'Low'}
                    {' '}({Math.round(intensity * 100)}%)
                  </span>
                </div>
                <input
                  type="range" min={0.1} max={1.0} step={0.1}
                  value={intensity}
                  onChange={e => setIntensity(Number(e.target.value))}
                  className="w-full accent-fuchsia-500"
                />
                <div className="flex justify-between text-xs text-slate-600 mt-0.5">
                  <span>Low</span><span>Medium</span><span>Max</span>
                </div>
              </div>

              {/* Launch button */}
              <button
                onClick={runInjection}
                disabled={injecting || countdown > 0}
                className={clsx(
                  'w-full flex items-center justify-center gap-3 py-3 px-6 rounded-xl font-bold text-brand-dark text-base transition-all',
                  injecting || countdown > 0
                    ? 'bg-slate-700 cursor-not-allowed opacity-60'
                    : `bg-gradient-to-r from-fuchsia-600 to-purple-600 hover:from-fuchsia-500 hover:to-purple-500 shadow-lg shadow-fuchsia-900/30`,
                )}
              >
                {injecting ? (
                  <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
                ) : countdown > 0 ? (
                  <><Clock className="w-5 h-5" /> Running… {countdown}s remaining</>
                ) : (
                  <><Zap className="w-5 h-5 fill-current" /> Launch {selectedProfile.label}</>
                )}
              </button>

              {injectResult && (
                <div className={clsx(
                  'p-3 rounded-lg text-sm font-medium',
                  injectResult.startsWith('✅') ? 'bg-emerald-500/10 text-emerald-600' : 'bg-rose-500/10 text-rose-600',
                )}>
                  {injectResult}
                  {injectResult.startsWith('✅') && (
                    <p className="text-xs text-slate-600 mt-1 font-normal">
                      Open the Dashboard and Alerts pages to see the spike and alert in real-time.
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Experiment log table */}
          <div className="glass-panel rounded-xl overflow-hidden border border-slate-200 flex flex-col" style={{ maxHeight: 320 }}>
            <div className="p-4 border-b border-slate-200 flex items-center justify-between shrink-0">
              <h2 className="text-sm font-semibold text-brand-dark flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-fuchsia-400" /> Experiment Log
              </h2>
              <span className="text-xs text-slate-600">{experiments.length} total</span>
            </div>
            <div className="flex-1 overflow-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-slate-50 text-slate-600 text-xs border-b border-slate-200 sticky top-0">
                  <tr>
                    <th className="px-3 py-2 font-medium">Time</th>
                    <th className="px-3 py-2 font-medium">Attack</th>
                    <th className="px-3 py-2 font-medium">Status</th>
                    <th className="px-3 py-2 font-medium">Detected</th>
                    <th className="px-3 py-2 font-medium">Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {loading ? (
                    <tr><td colSpan={5} className="px-3 py-8 text-center text-slate-600">Loading…</td></tr>
                  ) : experiments.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-3 py-8 text-center text-slate-600">
                        No experiments yet. Launch an attack above.
                      </td>
                    </tr>
                  ) : (
                    experiments.map(exp => (
                      <tr key={exp.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-3 py-2 text-slate-600 text-xs">
                          {format(new Date(exp.created_at), 'HH:mm:ss')}
                        </td>
                        <td className="px-3 py-2 text-slate-800 font-medium text-xs">{exp.traffic_type}</td>
                        <td className={clsx('px-3 py-2 text-xs font-semibold', statusColor(exp.status))}>
                          {exp.status}
                        </td>
                        <td className="px-3 py-2">
                          {exp.anomaly_detected == null
                            ? <span className="text-slate-600">—</span>
                            : exp.anomaly_detected
                              ? <CheckCircle className="w-4 h-4 text-emerald-600" />
                              : <XCircle className="w-4 h-4 text-rose-600" />}
                        </td>
                        <td className="px-3 py-2 text-slate-600 text-xs">
                          {exp.detection_time_ms != null ? `${Math.round(exp.detection_time_ms)} ms` : '—'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
