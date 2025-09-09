import { useState, useEffect } from 'react';
import { Activity, ArrowDownUp, Zap, ShieldAlert, Cpu } from 'lucide-react';
import MetricCard from '../components/MetricCard';
import TrafficChart from '../components/TrafficChart';
import { clsx } from 'clsx';
import { useMetrics } from '../context/MetricsContext';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

export default function Dashboard() {
  const { history, status, latestMetric, isConnected } = useMetrics();
  const current = latestMetric || history[history.length - 1] || null;

  const [interfaces, setInterfaces] = useState<string[]>([]);
  const [activeInterface, setActiveInterface] = useState<string>('');
  const [switching, setSwitching] = useState(false);

  useEffect(() => {
    // Fetch available interfaces
    axios.get(`${API_BASE}/interfaces`).then(res => {
      setInterfaces((res.data.interfaces || []).map((i: any) => i.name));
    }).catch(e => console.error(e));
    
    // Fetch active setting
    axios.get(`${API_BASE}/settings`).then(res => {
      setActiveInterface(res.data.active_interface || '');
    }).catch(e => console.error(e));
  }, []);
  
  // Keep activeInterface in sync if backend falls back
  useEffect(() => {
    if (status?.interface && !activeInterface) {
       setActiveInterface(status.interface);
    }
  }, [status?.interface, activeInterface]);

  const handleInterfaceChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newIface = e.target.value;
    setActiveInterface(newIface);
    setSwitching(true);
    try {
      await axios.patch(`${API_BASE}/settings`, { active_interface: newIface });
      setTimeout(() => setSwitching(false), 1500); // UI feedback delay
    } catch (err) {
      console.error(err);
      setSwitching(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-dark">Dashboard</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-sm text-slate-600 flex items-center gap-2">
              Interface: 
              <select 
                value={activeInterface || status?.interface || ''}
                onChange={handleInterfaceChange}
                disabled={switching}
                className={clsx(
                  "bg-slate-50 border border-slate-300 text-brand-dark font-medium rounded-md text-xs px-2 py-1 focus:outline-none focus:border-brand-blue cursor-pointer transition-all",
                  switching && "opacity-50"
                )}
              >
                {!interfaces.includes(status?.interface || '') && status?.interface && (
                  <option value={status?.interface}>{status?.interface}</option>
                )}
                {interfaces.map(iface => (
                  <option key={iface} value={iface}>{iface}</option>
                ))}
              </select>
              {switching && <div className="animate-spin rounded-full h-3 w-3 border border-brand-blue border-t-transparent" />}
            </span>
            <span className="text-slate-600">•</span>
            <div className="flex items-center gap-1.5 text-sm">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-brand-blue animate-pulse' : 'bg-rose-500'}`} />
              <span className={isConnected ? 'text-brand-blue' : 'text-rose-500'}>
                {isConnected ? 'Live Stream Active' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Top Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard 
          title="Total Bandwidth" 
          value={current ? current.total_mbps : '0.00'} 
          subtitle="Mbps" 
          icon={ArrowDownUp} 
          color="brand" 
        />
        <MetricCard 
          title="Packet Rate" 
          value={current ? current.total_packets_per_sec : '0'} 
          subtitle="pps" 
          icon={Zap} 
          color="blue" 
        />
        <MetricCard 
          title="Active Flows" 
          value={current ? current.active_flows : '0'} 
          subtitle="connections" 
          icon={Activity} 
          color="amber" 
        />
        <MetricCard 
          title="Recent Anomalies" 
          value={status ? status.anomalies_active : '0'} 
          subtitle="last 5 min" 
          icon={ShieldAlert} 
          color={status?.anomalies_active > 0 ? "rose" : "slate"} 
        />
      </div>

      {/* Main Charts Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Bandwidth Chart */}
        <div className="glass-panel p-6 rounded-xl lg:col-span-2 flex flex-col h-[400px]">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-brand-dark">Network Traffic</h2>
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded bg-brand-cyan/80" />
                <span className="text-slate-600">Download</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded bg-brand-blue/80" />
                <span className="text-slate-600">Upload</span>
              </div>
            </div>
          </div>
          <div className="flex-1 min-h-0">
            <TrafficChart data={history} />
          </div>
        </div>

        {/* Protocol Distribution & Detector Status */}
        <div className="flex flex-col gap-6">
          <div className="glass-panel p-6 rounded-xl flex-1">
            <h2 className="text-lg font-semibold text-brand-dark mb-4">Protocol Distribution</h2>
            {current ? (
              <div className="space-y-4">
                {[
                  { name: 'TCP', value: current.protocols?.tcp, color: 'bg-brand-blue' },
                  { name: 'UDP', value: current.protocols?.udp, color: 'bg-brand-cyan' },
                  { name: 'HTTPS', value: current.protocols?.https, color: 'bg-brand-lime' },
                  { name: 'DNS', value: current.protocols?.dns, color: 'bg-amber-400' },
                ].map(proto => (
                  <div key={proto.name}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-slate-600">{proto.name}</span>
                      <span className="text-slate-600">{proto.value}%</span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className={`h-full ${proto.color}`} style={{ width: `${proto.value}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-slate-600 text-center mt-10">No data</div>
            )}
          </div>

          <div className="glass-panel p-6 rounded-xl">
            <h2 className="text-lg font-semibold text-brand-dark mb-4 flex items-center gap-2">
              <Cpu className="w-5 h-5 text-slate-600" /> 
              Detector Engine
            </h2>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Status</span>
                <span className="text-emerald-500 font-medium">Online (Fitted)</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Algorithm</span>
                <span className="text-brand-dark">Z-Score Statistical</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Current Score</span>
                <span className={clsx(
                  "font-medium",
                  (current?.anomaly_score || 0) > 0.5 ? "text-rose-500" : "text-brand-blue"
                )}>
                  {(current?.anomaly_score || 0).toFixed(3)}
                </span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
