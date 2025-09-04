import { useMemo } from 'react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from 'recharts';
import { format } from 'date-fns';

interface TrafficChartProps {
  data: any[];
}

export default function TrafficChart({ data }: TrafficChartProps) {
  // Use a stable, formatted dataset for recharts
  const chartData = useMemo(() => {
    return data.map(d => ({
      ...d,
      timeLabel: format(new Date(d.timestamp), 'HH:mm:ss'),
      rx: d.rx_mbps || 0,
      tx: d.tx_mbps || 0,
    }));
  }, [data]);

  if (chartData.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center text-slate-600">
        Waiting for data...
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={chartData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="colorRx" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#0891B2" stopOpacity={0.4}/>
            <stop offset="95%" stopColor="#0891B2" stopOpacity={0}/>
          </linearGradient>
          <linearGradient id="colorTx" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#0284C7" stopOpacity={0.4}/>
            <stop offset="95%" stopColor="#0284C7" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
        <XAxis 
          dataKey="timeLabel" 
          stroke="#94a3b8" 
          fontSize={12} 
          tickLine={false}
          axisLine={false}
          minTickGap={30}
        />
        <YAxis 
          stroke="#94a3b8" 
          fontSize={12} 
          tickLine={false}
          axisLine={false}
          tickFormatter={(value) => `${value} Mbps`}
        />
        <Tooltip 
          contentStyle={{ backgroundColor: '#FFFFFF', borderColor: '#E2E8F0', color: '#0F172A' }}
          itemStyle={{ color: '#0F172A' }}
        />
        <Area 
          type="monotone" 
          dataKey="rx" 
          name="Download"
          stroke="#0891B2" 
          strokeWidth={2}
          fillOpacity={1} 
          fill="url(#colorRx)" 
          isAnimationActive={false}
        />
        <Area 
          type="monotone" 
          dataKey="tx" 
          name="Upload"
          stroke="#0284C7" 
          strokeWidth={2}
          fillOpacity={1} 
          fill="url(#colorTx)" 
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
