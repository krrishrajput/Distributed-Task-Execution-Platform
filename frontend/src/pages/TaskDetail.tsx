import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { usePolling } from '../hooks/usePolling';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { JsonViewer } from '../components/JsonViewer';
import { Timeline, TimelineEvent } from '../components/Timeline';
import { TaskStatus } from '../types';
import { ArrowLeft, Play, XSquare } from 'lucide-react';

export function TaskDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const { data: task, isLoading, refetch } = usePolling(() => api.getTask(id!), 2000, [id]);

  if (isLoading && !task) return <div className="p-4 font-mono text-slate-400">Loading task {id}...</div>;
  if (!task) return <div className="p-4 font-mono text-red-400">Task not found</div>;

  const handleCancel = async () => {
    try {
      await api.cancelTask(task.id);
      refetch();
    } catch (e) {
      console.error(e);
    }
  };

  const handleRetry = async () => {
    try {
      await api.retryTask(task.id);
      refetch();
    } catch (e) {
      console.error(e);
    }
  };

  // Mock timeline for now (since we don't have a history array in the provided Task model directly)
  // In a real app, this would come from `task.events` or similar if the backend provided it
  const timelineEvents: TimelineEvent[] = [
    { timestamp: task.created_at, title: 'Task Created' }
  ];
  
  if (task.state_history) {
    task.state_history.forEach(sh => {
        timelineEvents.push({
            timestamp: sh.timestamp,
            title: `State: ${sh.to_status}`,
            description: sh.reason || (sh.worker_id ? `Worker: ${sh.worker_id}` : undefined),
            isError: sh.to_status === TaskStatus.FAILED || sh.to_status === TaskStatus.DLQ
        });
    });
  }
  if (task.retry_history) {
    task.retry_history.forEach(rh => {
        timelineEvents.push({
            timestamp: rh.timestamp,
            title: `Retry Attempt ${rh.attempt}`,
            description: rh.error,
            isError: true
        });
    });
  }
  
  // Sort timeline events chronologically
  timelineEvents.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  const isCancelable = [TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING].includes(task.status);
  const isRetryable = [TaskStatus.FAILED, TaskStatus.DLQ].includes(task.status);

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center space-x-4 mb-6">
        <button onClick={() => navigate(-1)} className="p-2 hover:bg-slate-800 text-slate-400 hover:text-slate-200">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h2 className="text-xl font-bold font-mono tracking-wider flex items-center space-x-3">
            <span>TASK: {task.id}</span>
            <StatusBadge status={task.status} />
          </h2>
        </div>
        <div className="flex-1" />
        {isCancelable && (
          <button onClick={handleCancel} className="px-4 py-2 bg-slate-900 border border-slate-700 hover:bg-red-500/20 hover:text-red-400 hover:border-red-500/50 flex items-center text-sm font-mono transition-colors">
            <XSquare className="w-4 h-4 mr-2" /> CANCEL TASK
          </button>
        )}
        {isRetryable && (
          <button onClick={handleRetry} className="px-4 py-2 bg-slate-900 border border-slate-700 hover:bg-amber-500/20 hover:text-amber-400 hover:border-amber-500/50 flex items-center text-sm font-mono transition-colors">
            <Play className="w-4 h-4 mr-2" /> RETRY TASK
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900 border border-slate-800 p-4">
            <h3 className="text-sm font-bold text-slate-400 mb-4 font-mono border-b border-slate-800 pb-2">EXECUTION DETAILS</h3>
            <div className="grid grid-cols-2 gap-y-4 text-sm font-mono">
              <div>
                <span className="text-slate-500 block">Type</span>
                <span className="text-slate-200">{task.task_type}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Worker</span>
                <span className="text-purple-400">{task.worker_id || 'unassigned'}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Attempt</span>
                <span className="text-slate-200">{task.attempt} / {task.max_retries}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Priority</span>
                <span className="text-slate-200">{task.priority}</span>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-bold text-slate-400 font-mono">PAYLOAD</h3>
            <JsonViewer data={task.payload} />
          </div>

          {task.result && (
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-slate-400 font-mono">RESULT</h3>
              <JsonViewer data={task.result} />
            </div>
          )}

          {task.error && (
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-red-400 font-mono">ERROR TRACE</h3>
              <div className="bg-red-950/30 border border-red-900/50 p-4 text-red-400 font-mono text-sm whitespace-pre-wrap overflow-x-auto">
                {task.error}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 p-4">
            <h3 className="text-sm font-bold text-slate-400 mb-4 font-mono border-b border-slate-800 pb-2">LIFECYCLE TIMELINE</h3>
            <Timeline events={timelineEvents} />
          </div>
        </div>
      </div>
    </div>
  );
}
