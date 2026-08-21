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
        <div className="bg-slate-900 border border-slate-800 p-6">
          <h3 className="text-sm font-bold text-slate-400 mb-6 font-mono tracking-wider">LATENCY DISTRIBUTION</h3>
          <div className="space-y-4">
            <div className="flex items-center">
              <span className="w-12 text-xs font-mono text-slate-400">p50</span>
              <div className="flex-1 bg-slate-800 h-6 relative rounded overflow-hidden">
                <div className="bg-green-500/80 h-full transition-all duration-500" style={{ width: `${(metrics.latency_p50 / Math.max(metrics.latency_p99, 1)) * 100}%` }}></div>
                <span className="absolute right-2 top-0 h-full flex items-center text-xs font-mono text-slate-300 font-medium">{(metrics.latency_p50 || 0).toFixed(1)}ms</span>
              </div>
            </div>
            <div className="flex items-center">
              <span className="w-12 text-xs font-mono text-slate-400">p95</span>
              <div className="flex-1 bg-slate-800 h-6 relative rounded overflow-hidden">
                <div className="bg-amber-500/80 h-full transition-all duration-500" style={{ width: `${(metrics.latency_p95 / Math.max(metrics.latency_p99, 1)) * 100}%` }}></div>
                <span className="absolute right-2 top-0 h-full flex items-center text-xs font-mono text-slate-300 font-medium">{(metrics.latency_p95 || 0).toFixed(1)}ms</span>
              </div>
            </div>
            <div className="flex items-center">
              <span className="w-12 text-xs font-mono text-slate-400">p99</span>
              <div className="flex-1 bg-slate-800 h-6 relative rounded overflow-hidden">
                <div className="bg-red-500/80 h-full transition-all duration-500" style={{ width: `${(metrics.latency_p99 / Math.max(metrics.latency_p99, 1)) * 100}%` }}></div>
                <span className="absolute right-2 top-0 h-full flex items-center text-xs font-mono text-slate-300 font-medium">{(metrics.latency_p99 || 0).toFixed(1)}ms</span>
              </div>
            </div>
          </div>
        </div>
        
        <div className="bg-slate-900 border border-slate-800 p-6 flex flex-col">
          <h3 className="text-sm font-bold text-slate-400 mb-2 font-mono tracking-wider">TASK PROCESSING OVERVIEW</h3>
          <div className="flex-1 flex flex-col justify-center">
            <div className="flex justify-between items-end mb-2">
              <div className="text-3xl font-light text-blue-400">{(metrics.throughput || 0).toFixed(1)} <span className="text-sm text-slate-500">/sec</span></div>
              <div className="text-xs font-mono text-slate-400">Active Workers: {metrics.active_workers || 0}</div>
            </div>
            
            <div className="mt-4">
              <div className="flex justify-between text-xs font-mono text-slate-400 mb-1">
                <span>Distribution</span>
                <span>Total: {(metrics.submitted || 0)}</span>
              </div>
              <div className="w-full bg-slate-800 h-4 flex rounded overflow-hidden">
                <div className="bg-blue-500/80 h-full transition-all duration-500" 
                     style={{ width: `${(metrics.submitted ? (Math.max(0, metrics.submitted - (metrics.completed + metrics.failed)) / metrics.submitted) * 100 : 0)}%` }}
                     title={`Pending: ${Math.max(0, metrics.submitted - (metrics.completed + metrics.failed))}`}></div>
                <div className="bg-green-500/80 h-full transition-all duration-500" 
                     style={{ width: `${(metrics.submitted ? (metrics.completed / metrics.submitted) * 100 : 0)}%` }}
                     title={`Completed: ${metrics.completed}`}></div>
                <div className="bg-red-500/80 h-full transition-all duration-500" 
                     style={{ width: `${(metrics.submitted ? (metrics.failed / metrics.submitted) * 100 : 0)}%` }}
                     title={`Failed: ${metrics.failed}`}></div>
              </div>
              <div className="flex justify-between mt-2 text-xs font-mono">
                <div className="flex items-center"><div className="w-2 h-2 rounded-full bg-blue-500 mr-1"></div><span className="text-slate-400">Pending</span></div>
                <div className="flex items-center"><div className="w-2 h-2 rounded-full bg-green-500 mr-1"></div><span className="text-slate-400">Completed ({metrics.completed || 0})</span></div>
                <div className="flex items-center"><div className="w-2 h-2 rounded-full bg-red-500 mr-1"></div><span className="text-slate-400">Failed ({metrics.failed || 0})</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
