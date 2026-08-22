import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { DataTable } from '../components/DataTable';
import { StatusBadge } from '../components/StatusBadge';
import { usePolling } from '../hooks/usePolling';
import { useGlobalSSE } from '../context/SSEContext';
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
  const [searchParams, setSearchParams] = useSearchParams();
  const initialStatus = searchParams.get('status') || '';
  const initialPage = parseInt(searchParams.get('page') || '1', 10);
  
  const [statusFilter, setStatusFilter] = useState(initialStatus);
  const [page, setPage] = useState(initialPage);
  const navigate = useNavigate();
  
  // Sync state to URL
  useEffect(() => {
    const params = new URLSearchParams();
    if (statusFilter) params.set('status', statusFilter);
    if (page > 1) params.set('page', page.toString());
    setSearchParams(params, { replace: true });
  }, [statusFilter, page, setSearchParams]);

  const { data: polledData, isLoading } = usePolling(
    () => api.listTasks({ limit: 50, offset: (page - 1) * 50, status: statusFilter }),
    5000,
    [page, statusFilter]
  );
  
  const { events } = useGlobalSSE();
  const [tasks, setTasks] = useState<Task[]>([]);

  // Overwrite completely on new page data, don't accumulate across pages
  useEffect(() => {
    if (!polledData?.items) return;
    setTasks(polledData.items);
  }, [polledData]);

  // Apply SSE mutations instantly only to tasks currently in view
  useEffect(() => {
    if (events.length === 0) return;
    const latestEvent = events[0]; // because events are unshifted in SSE context? Wait, the context pushes them.
    
    // Process all new events since last render
    setTasks(prev => {
        let updated = [...prev];
        let changed = false;
        
        events.forEach(event => {
            if (!event.task_id) return;
            const idx = updated.findIndex(t => t.id === event.task_id);
            if (idx !== -1) {
                const newStatus = mapEventToStatus(event.event_type);
                if (newStatus && updated[idx].status !== newStatus) {
                    updated[idx] = { ...updated[idx], status: newStatus, updated_at: event.timestamp };
                    changed = true;
                }
            }
        });
        
        return changed ? updated : prev;
    });
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
