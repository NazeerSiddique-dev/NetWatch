import { Activity } from 'lucide-react';
import { clsx } from 'clsx';

export default function DataSourceBadge({ mode = 'REAL' }: { mode?: string }) {
  const isReal = mode === 'REAL';
  const isLab = mode === 'LAB';
  
  return (
    <div className={clsx(
      "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border",
      isReal ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20" :
      isLab ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
      "bg-blue-500/10 text-blue-600 border-blue-500/20"
    )}>
      <div className={clsx(
        "w-2 h-2 rounded-full animate-pulse-slow",
        isReal ? "bg-emerald-400" :
        isLab ? "bg-amber-400" :
        "bg-blue-400"
      )} />
      {mode === 'REAL' ? 'REAL DATA' : mode === 'LAB' ? 'LAB DATA' : 'SYNTHETIC'}
    </div>
  );
}
