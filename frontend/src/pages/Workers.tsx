import React from 'react';
import { DataTable } from '../components/DataTable';
import { StatusBadge } from '../components/StatusBadge';
import { usePolling } from '../hooks/usePolling';
import { api } from '../services/api';
import { WorkerInfo } from '../types';
import { formatDistanceToNow } from 'date-fns';
import { Server, Activity, CheckCircle, XCircle } from 'lucide-react';

export function Workers() {
  const { data, isLoading } = usePolling(() => api.listWorkers(), 5000);

  if (isLoading && !data) return <div className="text-slate-400 font-mono">Loading workers...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold font-mono tracking-wider">WORKER FLEET</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data?.map(worker => (
          <div key={worker.worker_id} className="bg-slate-900 border border-slate-800 p-4">
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center space-x-2">
                <Server className="w-5 h-5 text-slate-500" />
                <span className="font-mono font-bold">{worker?.worker_id?.substring(0,12) || 'unknown'}</span>
              </div>
              <StatusBadge status={worker.status} />
            </div>
            
            <div className="space-y-3 font-mono text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Uptime</span>
                <span className="text-slate-300">
                  {formatDistanceToNow(new Date(worker.started_at))}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Last Heartbeat</span>
                <span className="text-slate-300">
                  {formatDistanceToNow(new Date(worker.last_heartbeat))} ago
                </span>
              </div>
              
              <div className="mt-4 pt-4 border-t border-slate-800">
                <div className="flex justify-between mb-1">
                  <span className="text-slate-500 flex items-center"><Activity className="w-3 h-3 mr-1"/> Active / Max</span>
                  <span className="text-blue-400">{worker.active_tasks} / {worker.concurrency}</span>
                </div>
                {/* Progress bar */}
                <div className="w-full bg-slate-800 h-1.5 mb-4">
                  <div 
                    className="bg-blue-500 h-1.5" 
                    style={{ width: `${Math.min(100, (worker.active_tasks / worker.concurrency) * 100)}%` }}
                  ></div>
                </div>

                <div className="flex justify-between">
                  <span className="text-slate-500 flex items-center"><CheckCircle className="w-3 h-3 mr-1"/> Completed</span>
                  <span className="text-green-400">{worker.completed_tasks}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 flex items-center"><XCircle className="w-3 h-3 mr-1"/> Failed</span>
                  <span className="text-red-400">{worker.failed_tasks}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      {data?.length === 0 && (
        <div className="text-center p-12 bg-slate-900 border border-slate-800 border-dashed text-slate-500 font-mono">
          NO ACTIVE WORKERS FOUND
        </div>
      )}
    </div>
  );
}
