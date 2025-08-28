import { Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import TopBar from './components/layout/TopBar';
import Dashboard from './pages/Dashboard';
import Interfaces from './pages/Interfaces';
import Flows from './pages/Flows';
import Analytics from './pages/Analytics';
import Alerts from './pages/Alerts';
import NetworkLab from './pages/NetworkLab';
import Experiments from './pages/Experiments';
import System from './pages/System';
import Settings from './pages/Settings';
import { MetricsProvider } from './context/MetricsContext';

function App() {
  return (
    <MetricsProvider>
      <div className="flex h-screen overflow-hidden bg-dark-900">
        <Sidebar />
        <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
          <TopBar />
          <main className="w-full grow p-6">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/interfaces" element={<Interfaces />} />
              <Route path="/flows" element={<Flows />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/lab" element={<NetworkLab />} />
              <Route path="/network-lab" element={<NetworkLab />} />
              <Route path="/experiments" element={<Experiments />} />
              <Route path="/system" element={<System />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </div>
    </MetricsProvider>
  );
}

export default App;
