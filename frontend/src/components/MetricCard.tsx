import { LucideIcon } from 'lucide-react';
import { clsx } from 'clsx';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  color?: 'brand' | 'blue' | 'amber' | 'rose' | 'slate';
}

export default function MetricCard({ 
  title, value, subtitle, icon: Icon, trend, trendValue, color = 'brand' 
}: MetricCardProps) {
  const colors = {
    brand: 'text-brand-blue bg-brand-blue/10 border-brand-blue/20',
    blue: 'text-brand-cyan bg-brand-cyan/20 border-brand-cyan/30',
    amber: 'text-amber-600 bg-amber-500/10 border-amber-500/20',
    rose: 'text-rose-500 bg-rose-500/10 border-rose-500/20',
    slate: 'text-slate-600 bg-slate-200 border-slate-300',
  };

  return (
    <div className="glass-panel p-5 rounded-xl flex flex-col justify-between group hover:border-brand-blue/40 transition-colors">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-600">{title}</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight text-brand-dark">{value}</span>
            {subtitle && <span className="text-sm text-slate-600">{subtitle}</span>}
          </div>
        </div>
        <div className={clsx("p-2 rounded-lg border", colors[color])}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      
      {trendValue && (
        <div className="mt-4 flex items-center text-sm">
          <span className={clsx(
            "font-medium",
            trend === 'up' ? "text-emerald-500" : trend === 'down' ? "text-rose-500" : "text-slate-600"
          )}>
            {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'} {trendValue}
          </span>
          <span className="text-slate-600 ml-2">vs last 5m</span>
        </div>
      )}
    </div>
  );
}
