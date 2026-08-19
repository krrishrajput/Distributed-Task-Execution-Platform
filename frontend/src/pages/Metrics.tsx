import React from 'react';
import { usePolling } from '../hooks/usePolling';
import { api } from '../services/api';
import { MetricCard } from '../components/MetricCard';
import { Activity, Clock, Server, AlertTriangle } from 'lucide-react';

export function Metrics() {
  const { data: metrics } = usePolling(api.getMetrics, 5000);

  if (!metrics) return <div className="text-slate-400 font-mono p-4">Loading metrics...</div>;

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold font-mono tracking-wider mb-6">SYSTEM METRICS</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Row 1 */}
        <MetricCard title="Throughput" value={(metrics?.throughput || 0).toFixed(1)} trend="/sec" icon={<Activity />} color="blue" />
        <MetricCard title="Avg Execution" value={`${(metrics?.avg_execution_duration || 0).toFixed(1)}ms`} icon={<Clock />} />
        <MetricCard title="Recovery Count" value={metrics?.recovery_count || 0} icon={<Activity />} />
        <MetricCard title="DLQ Size" value={metrics?.dlq_count || 0} color={metrics?.dlq_count ? 'purple' : 'default'} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard title="p50 Latency" value={`${(metrics?.latency_p50 || 0).toFixed(1)}ms`} />
        <MetricCard title="p95 Latency" value={`${(metrics?.latency_p95 || 0).toFixed(1)}ms`} color="amber" />
        <MetricCard title="p99 Latency" value={`${(metrics?.latency_p99 || 0).toFixed(1)}ms`} color="red" />
        <MetricCard title="Fail/Retry" value={`${(metrics?.failure_rate || 0).toFixed(1)}%`} color={(metrics?.failure_rate || 0) > 10 ? 'red' : 'amber'} icon={<AlertTriangle />} />
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-900 border border-slate-800 p-6 h-64 flex flex-col items-center justify-center text-slate-500 font-mono text-sm border-dashed">
          [ Latency Timeseries Chart Placeholder ]
        </div>
        <div className="bg-slate-900 border border-slate-800 p-6 h-64 flex flex-col items-center justify-center text-slate-500 font-mono text-sm border-dashed">
          [ Throughput Timeseries Chart Placeholder ]
        </div>
      </div>
    </div>
  );
}
