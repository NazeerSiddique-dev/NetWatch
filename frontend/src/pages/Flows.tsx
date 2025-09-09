import { useState, useEffect } from 'react';
import axios from 'axios';
import { RefreshCw, Search } from 'lucide-react';
import { format } from 'date-fns';
import { clsx } from 'clsx';

const API_BASE = 'http://localhost:8000/api';

export default function Flows() {
  const [flows, setFlows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [limit, setLimit] = useState(50);
  const [protocol, setProtocol] = useState('');
  const [total, setTotal] = useState(0);

  const fetchFlows = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/flows`, {
        params: { page_size: limit, protocol: protocol || undefined }
      });
      // API returns { flows: [...], total: N, ... }
      setFlows(res.data.flows ?? []);
      setTotal(res.data.total ?? 0);
    } catch (e) {
      console.error('Failed to load flows', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { fetchFlows(); }, [limit, protocol]);

  const formatBytes = (bytes: number) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-dark">Network Flows</h1>
          <p className="text-sm text-slate-600 mt-1">Explore historical aggregated 5-tuple conversations.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-600 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter protocol..."
              value={protocol}
              onChange={(e) => setProtocol(e.target.value)}
              className="bg-slate-50 border border-slate-300 text-sm rounded-lg pl-9 pr-4 py-2 text-brand-dark placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors w-48"
            />
          </div>
          <select
            className="bg-slate-50 border border-slate-300 text-sm rounded-lg px-3 py-2 text-brand-dark focus:outline-none focus:border-brand-500 transition-colors"
            value={protocol}
            onChange={(e) => setProtocol(e.target.value)}
          >
            <option value="">All Protocols</option>
            <option value="TCP">TCP</option>
            <option value="UDP">UDP</option>
            <option value="ICMP">ICMP</option>
          </select>
          <button
            onClick={() => fetchFlows(true)}
            disabled={refreshing || loading}
            className="p-2 rounded-lg bg-slate-50 border border-slate-300 text-slate-600 hover:text-brand-dark hover:border-slate-600 transition-all disabled:opacity-50"
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
                <th className="px-4 py-3 font-medium">Time</th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 font-medium">Destination</th>
                <th className="px-4 py-3 font-medium">Protocol</th>
                <th className="px-4 py-3 font-medium">Duration</th>
                <th className="px-4 py-3 font-medium">Packets</th>
                <th className="px-4 py-3 font-medium">Size</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-slate-600">
                    <div className="flex justify-center">
                      <div className="animate-spin rounded-full h-6 w-6 border-2 border-brand-500 border-t-transparent" />
                    </div>
                  </td>
                </tr>
              ) : flows.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-slate-600">
                    No flows recorded yet. The background worker is still collecting data.
                  </td>
                </tr>
              ) : (
                flows.map((flow) => (
                  <tr key={flow.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 text-slate-600">
                      {flow.flow_start ? format(new Date(flow.flow_start), 'HH:mm:ss') : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-slate-800">{flow.src_ip}</span>
                      {flow.src_port && <span className="text-slate-600">:{flow.src_port}</span>}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-slate-800">{flow.dst_ip}</span>
                      {flow.dst_port && <span className="text-slate-600">:{flow.dst_port}</span>}
                    </td>
                    <td className="px-4 py-3">
                      <span className={clsx(
                        'px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wider',
                        flow.protocol === 'TCP' ? 'bg-brand-blue/10 text-brand-blue' :
                        flow.protocol === 'UDP' ? 'bg-blue-500/10 text-blue-600' :
                        'bg-slate-500/10 text-slate-600'
                      )}>
                        {flow.protocol}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {flow.duration_sec != null ? `${(flow.duration_sec * 1000).toFixed(1)} ms` : '-'}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {flow.packet_count ?? 0}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {formatBytes(flow.byte_count ?? 0)}
                    </td>
                    <td className="px-4 py-3">
                      {flow.is_anomalous ? (
                        <span className="px-2 py-0.5 rounded text-xs font-medium bg-rose-500/10 text-rose-600">Anomalous</span>
                      ) : (
                        <span className="text-slate-600 text-xs">Normal</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="bg-slate-50 px-4 py-3 border-t border-slate-200 flex items-center justify-between text-sm text-slate-600">
          <div>
            Showing <span className="text-slate-800 font-medium">{flows.length}</span> of{' '}
            <span className="text-slate-800 font-medium">{total}</span> flows
          </div>
          <div className="flex gap-2 items-center">
            <span>Show:</span>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="bg-transparent text-slate-800 font-medium focus:outline-none cursor-pointer"
            >
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={500}>500</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
