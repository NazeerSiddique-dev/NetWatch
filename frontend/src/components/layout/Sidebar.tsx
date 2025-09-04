import { NavLink } from 'react-router-dom';
import { 
  Activity, 
  Network, 
  ListTree, 
  LineChart, 
  Bell, 
  ServerCog, 
  FlaskConical, 
  Cpu, 
  Settings 
} from 'lucide-react';
import { clsx } from 'clsx';

const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: Activity },
  { name: 'Interfaces', path: '/interfaces', icon: Network },
  { name: 'Flows', path: '/flows', icon: ListTree },
  { name: 'Analytics', path: '/analytics', icon: LineChart },
  { name: 'Alerts', path: '/alerts', icon: Bell },
  { name: 'Network Lab', path: '/lab', icon: ServerCog },
  { name: 'Experiments', path: '/experiments', icon: FlaskConical },
  { name: 'System', path: '/system', icon: Cpu },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="w-64 glass-panel border-r border-y-0 border-l-0 z-20 hidden md:flex flex-col">
      <div className="h-16 flex items-center px-6 border-b border-slate-200">
        <div className="flex items-center gap-2 text-brand-blue font-bold text-xl tracking-tight">
          <Activity className="w-6 h-6" />
          <span>NetWatch</span>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto py-6 px-3">
        <nav className="space-y-1.5">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 group font-medium",
                  isActive 
                    ? "bg-brand-blue/10 text-brand-blue shadow-sm" 
                    : "text-slate-600 hover:text-brand-dark hover:bg-slate-100"
                )
              }
            >
              <item.icon className="w-5 h-5 shrink-0" />
              {item.name}
            </NavLink>
          ))}
        </nav>
      </div>
    </aside>
  );
}
