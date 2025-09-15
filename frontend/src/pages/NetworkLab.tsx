import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { RefreshCw, Play, Square, Server, Network } from 'lucide-react';
import { clsx } from 'clsx';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const API_BASE = 'http://localhost:8000/api';

export default function NetworkLab() {
  const [labStatus, setLabStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const fetchLabStatus = useCallback(async () => {
    try {
      // Backend: GET /api/network-lab  →  { active, bridge, nodes, node_count }
      const res = await axios.get(`${API_BASE}/network-lab`);
      const data = res.data;
      setLabStatus(data);

      if (data.active && data.nodes?.length > 0) {
        const flowNodes: any[] = [];
        const flowEdges: any[] = [];

        // Central bridge node
        flowNodes.push({
          id: 'bridge',
          data: { label: `🌉  ${data.bridge ?? 'netwatch-br0'}` },
          position: { x: 300, y: 100 },
          style: {
            background: '#1e3a5f', color: '#93c5fd', border: '1px solid #3b82f6',
            borderRadius: '8px', padding: '10px 16px', fontSize: '13px', fontWeight: 600,
          },
        });

        data.nodes.forEach((node: any, idx: number) => {
          const x = idx * 220 + 100;
          flowNodes.push({
            id: node.name,
            data: { label: `🖥  ${node.name}\n${node.ip_address}` },
            position: { x, y: 300 },
            style: {
              background: '#0f172a', color: '#94a3b8', border: '1px solid #475569',
              borderRadius: '8px', padding: '8px 14px', fontSize: '12px',
            },
          });
          flowEdges.push({
            id: `e-${node.name}`,
            source: node.name,
            target: 'bridge',
            animated: true,
            style: { stroke: '#3b82f6' },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' },
          });
        });

        setNodes(flowNodes);
        setEdges(flowEdges);
      } else {
        setNodes([]);
        setEdges([]);
      }
    } catch (e) {
      console.error('Failed to load lab status', e);
    } finally {
      setLoading(false);
    }
  }, [setNodes, setEdges]);

  useEffect(() => { fetchLabStatus(); }, [fetchLabStatus]);

  const toggleLab = async () => {
    setToggling(true);
    setError(null);
    try {
      if (labStatus?.active) {
        await axios.delete(`${API_BASE}/network-lab`);
      } else {
        await axios.post(`${API_BASE}/network-lab`, {});
      }
      setTimeout(() => { fetchLabStatus(); setToggling(false); }, 1200);
    } catch (e: any) {
      const detail = e?.response?.data?.detail ?? e.message ?? 'Unknown error';
      const isPermission =
        detail.toLowerCase().includes('permission') ||
        detail.toLowerCase().includes('cap_net') ||
        detail.toLowerCase().includes('operation not permitted');
      setError(
        isPermission
          ? 'PERMISSION'
          : detail,
      );
      setToggling(false);
    }
  };

  return (
    <div className="space-y-6 flex flex-col" style={{ height: 'calc(100vh - 100px)' }}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-dark flex items-center gap-2">
            <Server className="w-6 h-6 text-brand-blue" /> Network Lab
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Manage isolated Linux network namespaces for controlled traffic experiments.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => { setLoading(true); fetchLabStatus(); }}
            className="p-2 rounded-lg bg-slate-50 border border-slate-300 text-slate-600 hover:text-brand-dark transition-all"
          >
            <RefreshCw className={clsx('w-5 h-5', loading && 'animate-spin')} />
          </button>
          <button
            onClick={toggleLab}
            disabled={toggling || loading}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 border disabled:opacity-50',
              labStatus?.active
                ? 'bg-rose-500/10 text-rose-600 border-rose-500/20 hover:bg-rose-500/20'
                : 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20 hover:bg-emerald-500/20',
            )}
          >
            {toggling
              ? <div className="animate-spin rounded-full h-4 w-4 border-2 border-current border-t-transparent" />
              : labStatus?.active
                ? <Square className="w-4 h-4 fill-current" />
                : <Play className="w-4 h-4 fill-current" />}
            {toggling ? 'Working...' : labStatus?.active ? 'Teardown Lab' : 'Initialize Lab'}
          </button>
        </div>
      </div>

      {/* Error banners */}
      {error === 'PERMISSION' && (
        <div className="glass-panel rounded-xl border border-amber-500/30 bg-amber-500/5 p-5 space-y-3">
          <div className="flex items-start gap-3">
            <span className="text-2xl">🔒</span>
            <div>
              <p className="text-amber-400 font-semibold">Root privileges required</p>
              <p className="text-slate-600 text-sm mt-1">
                The Network Lab creates real Linux network namespaces, virtual ethernet
                pairs, and bridge devices — all of which require <code className="text-amber-300 bg-amber-500/10 px-1 rounded">CAP_NET_ADMIN</code> (root).
              </p>
            </div>
          </div>
          <div className="border-t border-amber-500/20 pt-3">
            <p className="text-xs text-slate-600 mb-2 font-medium uppercase tracking-wider">To use Network Lab, restart the backend with sudo:</p>
            <div className="bg-slate-900 rounded-lg p-3 font-mono text-sm">
              <p className="text-slate-600"># Stop current backend (Ctrl+C), then run:</p>
              <p className="text-emerald-600">cd ~/Project/netwatch</p>
              <p className="text-emerald-600">source .venv/bin/activate</p>
              <p className="text-emerald-600">make dev-backend-sudo</p>
            </div>
            <p className="text-xs text-slate-600 mt-2">
              ⚠️ Only use sudo in a trusted local dev environment. For experiments without root, use the{' '}
              <span className="text-fuchsia-400">Experiments</span> page instead.
            </p>
          </div>
        </div>
      )}

      {error && error !== 'PERMISSION' && (
        <div className="glass-panel rounded-xl border border-rose-500/30 bg-rose-500/5 p-4 flex items-start gap-3">
          <span className="text-rose-600 text-xl">✗</span>
          <div>
            <p className="text-rose-600 font-semibold">Operation failed</p>
            <p className="text-slate-600 text-sm mt-1 font-mono">{error}</p>
          </div>
        </div>
      )}

      <div className="flex-1 glass-panel rounded-xl overflow-hidden border border-slate-200 relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-brand-500 border-t-transparent" />
          </div>
        ) : !labStatus?.active ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-600 gap-3">
            <Network className="w-16 h-16 opacity-20" />
            <p className="text-lg">Network Lab is offline</p>
            <p className="text-sm">Click "Initialize Lab" to create virtual namespaces.</p>
            <p className="text-xs opacity-60">(Requires root / CAP_NET_ADMIN)</p>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            className="bg-slate-900/50"
          >
            <Controls />
            <MiniMap nodeColor="#3b82f6" maskColor="rgba(15,23,42,0.7)" />
            <Background color="#334155" gap={16} />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
