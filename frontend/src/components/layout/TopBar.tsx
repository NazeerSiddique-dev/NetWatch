import { Bell, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useMetrics } from '../../context/MetricsContext';

export default function TopBar() {
  const navigate = useNavigate();
  const { status } = useMetrics();
  
  // anomalies_active comes from the status endpoint (alerts in the last 5 minutes)
  const hasActiveAlerts = (status?.anomalies_active || 0) > 0;

  return (
    <header className="h-16 shrink-0 glass-panel border-b border-x-0 border-t-0 z-10 sticky top-0 flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        {/* Mobile menu button would go here */}
      </div>

      <div className="flex items-center gap-4">
        <button 
          onClick={() => navigate('/alerts')}
          className="relative p-2 text-slate-600 hover:text-brand-dark transition-colors rounded-full hover:bg-slate-100"
          title="View Alerts"
        >
          <Bell className="w-5 h-5" />
          {hasActiveAlerts && (
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full border-2 border-white" />
          )}
        </button>
        
        <div className="h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center border border-slate-300 cursor-pointer">
          <User className="w-4 h-4 text-brand-dark" />
        </div>
      </div>
    </header>
  );
}
