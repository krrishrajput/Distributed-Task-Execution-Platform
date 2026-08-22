import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { DataTable } from '../components/DataTable';
import { StatusBadge } from '../components/StatusBadge';
import { usePolling } from '../hooks/usePolling';
import { useSSE } from '../hooks/useSSE';
import { api } from '../services/api';
import { Task, TaskStatus } from '../types';
import { format } from 'date-fns';

const mapEventToStatus = (eventType: string): TaskStatus | undefined => {
  const map: Record<string, TaskStatus> = {
    'TASK_QUEUED': TaskStatus.QUEUED,
    'TASK_STARTED': TaskStatus.RUNNING,
    'TASK_COMPLETED': TaskStatus.COMPLETED,
    'TASK_FAILED': TaskStatus.FAILED,
    'TASK_RETRYING': TaskStatus.RETRYING,
    'TASK_DLQ': TaskStatus.DLQ,
    'TASK_CANCELLED': TaskStatus.CANCELLED,
  };
  return map[eventType];
};

export function Tasks() {
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const navigate = useNavigate();
  
  const { data: polledData, isLoading } = usePolling(
    () => api.listTasks({ limit: 50, offset: (page - 1) * 50, status: statusFilter }),
    5000,
    [page, statusFilter]
  );
  
  const { events } = useSSE();
  const [tasks, setTasks] = useState<Task[]>([]);

  // Safely merge polled data with real-time SSE updates using timestamp reconciliation
  useEffect(() => {
    if (!polledData?.items) return;
    
    setTasks(prevTasks => {
      const merged = new Map(prevTasks.map(t => [t.id, t]));
      
      polledData.items.forEach(polledTask => {
        const existing = merged.get(polledTask.id);
        // CRITICAL FIX: Only accept the polled payload if its updated_at is STRICTLY NEWER
        // than what we currently have in local state (which may have been mutated by SSE)
        if (!existing || new Date(polledTask.updated_at).getTime() >= new Date(existing.updated_at).getTime()) {
          merged.set(polledTask.id, polledTask);
        }
      });
      return Array.from(merged.values());
    });
  }, [polledData]);

  // Apply SSE mutations instantly
  useEffect(() => {
    if (events.length === 0) return;
    const latestEvent = events[0];
    
    if (latestEvent.task_id) {
      setTasks(prev => prev.map(t => {
        if (t.id === latestEvent.task_id) {
            const newStatus = mapEventToStatus(latestEvent.event_type);
            return { 
                ...t, 
                status: newStatus || t.status, 
                updated_at: latestEvent.timestamp 
            };
        }
        return t;
      }));
    }
  }, [events]);

  const columns = [
    { key: 'id', header: 'Task ID', render: (t: Task) => <span className="font-mono">{t.id.substring(0,8)}</span> },
    { key: 'type', header: 'Type', render: (t: Task) => <span className="font-mono">{t.task_type}</span> },
    { key: 'status', header: 'Status', render: (t: Task) => <StatusBadge status={t.status} /> },
    { key: 'priority', header: 'Priority', render: (t: Task) => <span className="font-mono">{t.priority}</span> },
    { key: 'worker', header: 'Worker', render: (t: Task) => t.worker_id ? <span className="font-mono text-purple-400">{t.worker_id.substring(0,8)}</span> : <span className="text-slate-600">-</span> },
    { key: 'attempt', header: 'Attempt', render: (t: Task) => <span className="font-mono">{t.attempt}/{t.max_retries}</span> },
    { key: 'created', header: 'Created', render: (t: Task) => <span className="font-mono text-slate-400">{format(new Date(t.created_at), 'HH:mm:ss')}</span> }
  ];

  return (
    <div className="space-y-4 h-full flex flex-col">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold font-mono tracking-wider">TASKS</h2>
        <div className="flex space-x-2">
          <select 
            className="bg-slate-900 border border-slate-700 text-slate-300 text-sm p-2 font-mono outline-none focus:border-blue-500 rounded-none"
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
          >
            <option value="">ALL STATUSES</option>
            <option value="PENDING">PENDING</option>
            <option value="QUEUED">QUEUED</option>
            <option value="RUNNING">RUNNING</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="FAILED">FAILED</option>
            <option value="DLQ">DLQ</option>
            <option value="CANCELLED">CANCELLED</option>
          </select>
        </div>
      </div>
      
      <div className="flex-1 overflow-hidden flex flex-col">
        <DataTable 
          columns={columns} 
          data={tasks} 
          isLoading={isLoading && tasks.length === 0}
          onRowClick={(task) => navigate(`/tasks/${task.id}`)}
        />
        <div className="mt-4 flex justify-between items-center text-sm font-mono text-slate-400">
          <div>Showing page {page} of {polledData?.pages || 1}</div>
          <div className="space-x-2">
            <button 
              className="px-3 py-1 bg-slate-800 border border-slate-700 hover:bg-slate-700 disabled:opacity-50"
              disabled={page === 1}
              onClick={() => setPage(p => p - 1)}
            >
              PREV
            </button>
            <button 
              className="px-3 py-1 bg-slate-800 border border-slate-700 hover:bg-slate-700 disabled:opacity-50"
              disabled={!polledData || page >= polledData.pages}
              onClick={() => setPage(p => p + 1)}
            >
              NEXT
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
