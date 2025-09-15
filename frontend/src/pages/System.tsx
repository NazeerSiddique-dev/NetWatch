import { useState, useEffect } from 'react';
import axios from 'axios';
import { Cpu, Server, Database, MemoryStick } from 'lucide-react';
import { clsx } from 'clsx';

const API_BASE = 'http://localhost:8000/api';

export default function System() {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await axios.get(`${API_BASE}/system/health`);
        setHealth(res.data);
      } catch (e) {
        console.error("Failed to load system health", e);
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!health) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  const { resources, services, worker } = health;
  
  const dbService = services.find((s: any) => s.name.includes('SQL'))?.status || 'unknown';
  const redisService = services.find((s: any) => s.name === 'Redis')?.status || 'unknown';

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight text-brand-dark flex items-center gap-2">
        <Cpu className="w-6 h-6 text-slate-600" /> System Health
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Core Services */}
        <div className="glass-panel p-6 rounded-xl">
          <h2 className="text-lg font-semibold text-brand-dark mb-4 flex items-center gap-2">
            <Server className="w-5 h-5 text-brand-blue" /> Services
          </h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-slate-600">Database</span>
              <span className={clsx("px-2 py-1 rounded text-xs font-medium uppercase", dbService === 'healthy' ? 'bg-emerald-500/10 text-emerald-600' : 'bg-rose-500/10 text-rose-600')}>
                {dbService}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-600">Redis</span>
              <span className={clsx("px-2 py-1 rounded text-xs font-medium uppercase", redisService === 'healthy' ? 'bg-emerald-500/10 text-emerald-600' : 'bg-amber-500/10 text-amber-400')}>
                {redisService}
              </span>
            </div>
          </div>
        </div>

        {/* Resources */}
        <div className="glass-panel p-6 rounded-xl">
          <h2 className="text-lg font-semibold text-brand-dark mb-4 flex items-center gap-2">
            <MemoryStick className="w-5 h-5 text-blue-600" /> Resources
          </h2>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-600">CPU Usage</span>
                <span className="text-slate-800">{resources.cpu_percent}%</span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500" style={{ width: `${resources.cpu_percent}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-600">Memory Usage</span>
                <span className="text-slate-800">{resources.memory_percent}%</span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-purple-500" style={{ width: `${resources.memory_percent}%` }} />
              </div>
            </div>
          </div>
        </div>

        {/* Stream Worker */}
        <div className="glass-panel p-6 rounded-xl">
          <h2 className="text-lg font-semibold text-brand-dark mb-4 flex items-center gap-2">
            <Database className="w-5 h-5 text-amber-400" /> Background Worker
          </h2>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-slate-600">Packets Processed</span>
              <span className="text-slate-800 font-medium">{worker?.packets_processed || 0}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-600">Flows Persisted</span>
              <span className="text-slate-800 font-medium">{worker?.flows_processed || 0}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-600">Metrics Persisted</span>
              <span className="text-slate-800 font-medium">{worker?.metrics_published || 0}</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
