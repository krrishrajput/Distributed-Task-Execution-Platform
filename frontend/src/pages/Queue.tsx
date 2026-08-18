import React from 'react';
import { usePolling } from '../hooks/usePolling';
import { api } from '../services/api';

export function Queue() {
  const { data: metrics } = usePolling(api.getMetrics, 5000);
  
  if (!metrics) return <div className="text-slate-400 font-mono">Loading queue metrics...</div>;

  const totalCapacity = 10000; // arbitrary max scale for visual
  const qDepthPercent = Math.min(100, (metrics.queue_depth / totalCapacity) * 100);

  return (
    <div className="space-y-8 max-w-5xl">
      <h2 className="text-xl font-bold font-mono tracking-wider">QUEUE DIAGNOSTICS</h2>

      <div className="bg-slate-900 border border-slate-800 p-6">
        <h3 className="text-sm font-bold text-slate-400 mb-4 font-mono">GLOBAL QUEUE DEPTH</h3>
        <div className="flex items-end mb-2">
          <span className="text-4xl font-mono text-amber-500 mr-2">{metrics.queue_depth}</span>
          <span className="text-slate-500 font-mono mb-1">tasks waiting</span>
        </div>
        <div className="w-full bg-slate-800 h-4 border border-slate-700">
          <div 
            className="bg-amber-500 h-full transition-all duration-500" 
            style={{ width: `${qDepthPercent}%` }}
          ></div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-900 border border-slate-800 p-6">
          <h3 className="text-sm font-bold text-slate-400 mb-4 font-mono">SCHEDULED & DELAYED</h3>
          <span className="text-3xl font-mono text-blue-400">{metrics.scheduled_count}</span>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-6">
          <h3 className="text-sm font-bold text-slate-400 mb-4 font-mono">RETRY QUEUE</h3>
          <span className="text-3xl font-mono text-amber-400">{metrics.retry_queue_count}</span>
        </div>
        <div className="bg-slate-900 border border-red-900/50 p-6 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-red-400 mb-4 font-mono">DEAD LETTER QUEUE (DLQ)</h3>
            <span className="text-3xl font-mono text-purple-400">{metrics.dlq_count}</span>
          </div>
          <a href="/tasks?status=DLQ" className="text-xs font-mono text-slate-400 hover:text-white underline mt-4">
            VIEW DLQ TASKS &rarr;
          </a>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 p-6">
        <h3 className="text-sm font-bold text-slate-400 mb-4 font-mono">PRIORITY BREAKDOWN</h3>
        <div className="space-y-4">
          {Object.entries(metrics.priority_breakdown || {}).map(([prio, count]) => (
            <div key={prio}>
              <div className="flex justify-between text-xs font-mono mb-1 text-slate-300">
                <span>Priority {prio}</span>
                <span>{count} tasks</span>
              </div>
              <div className="w-full bg-slate-800 h-2 border border-slate-700">
                <div 
                  className="bg-blue-500 h-full" 
                  style={{ width: `${Math.min(100, (Number(count) / Math.max(1, metrics.queue_depth)) * 100)}%` }}
                ></div>
              </div>
            </div>
          ))}
          {Object.keys(metrics.priority_breakdown || {}).length === 0 && (
            <div className="text-slate-500 text-sm font-mono">No tasks in queue</div>
          )}
        </div>
      </div>
    </div>
  );
}
