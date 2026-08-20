import React from 'react';
import { MetricCard } from '../components/MetricCard';
import { EventLog } from '../components/EventLog';
import { usePolling } from '../hooks/usePolling';
import { useSSE } from '../hooks/useSSE';
import { api } from '../services/api';
import { Activity, Server, List, CheckCircle, AlertTriangle, XCircle, Clock } from 'lucide-react';

export function Overview() {
  const { data: metrics } = usePolling(api.getMetrics, 5000);
  const { data: workers } = usePolling(api.listWorkers, 5000);
  const { events } = useSSE();

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold font-mono tracking-wider">SYSTEM OVERVIEW</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Throughput" value={(metrics?.throughput || 0).toFixed(1)} trend="/sec" icon={<Activity />} />
        <MetricCard title="Queue Depth" value={metrics?.queue_depth || 0} color="amber" icon={<List />} />
        <MetricCard title="Active Workers" value={workers?.length || 0} color="blue" icon={<Server />} />
        <MetricCard title="Avg Latency" value={`${(metrics?.latency_p50 || 0).toFixed(0)}ms`} icon={<Clock />} />
        
        <MetricCard title="Failure Rate" value={`${(metrics?.failure_rate || 0).toFixed(2)}%`} color={metrics?.failure_rate && metrics.failure_rate > 5 ? 'red' : 'default'} icon={<XCircle />} />
        <MetricCard title="Retry Rate" value={`${(metrics?.retry_rate || 0).toFixed(2)}%`} color="amber" icon={<AlertTriangle />} />
        <MetricCard title="Recovery Count" value={metrics?.recovery_count || 0} color="green" icon={<CheckCircle />} />
        <MetricCard title="DLQ Count" value={metrics?.dlq_count || 0} color="purple" icon={<AlertTriangle />} />
      </div>

      <div className="mt-8">
        <h3 className="text-sm font-bold text-slate-400 mb-3 font-mono border-b border-slate-800 pb-2">LIVE EVENT STREAM</h3>
        <EventLog events={events} />
      </div>
    </div>
  );
}
