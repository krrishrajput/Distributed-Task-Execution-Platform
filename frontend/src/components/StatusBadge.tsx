import React from 'react';
import { clsx } from 'clsx';
import { TaskStatus, WorkerStatus } from '../types';

interface StatusBadgeProps {
  status: TaskStatus | WorkerStatus | string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  let colorClass = 'bg-slate-800 text-slate-300 border-slate-700'; // Default gray
  
  if (status === TaskStatus.COMPLETED || status === WorkerStatus.HEALTHY) {
    colorClass = 'bg-green-500/10 text-green-400 border-green-500/20';
  } else if (status === TaskStatus.RUNNING || status === WorkerStatus.UNHEALTHY) {
    colorClass = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
  } else if (status === TaskStatus.FAILED || status === WorkerStatus.OFFLINE) {
    colorClass = 'bg-red-500/10 text-red-400 border-red-500/20';
  } else if (status === TaskStatus.DLQ) {
    colorClass = 'bg-purple-500/10 text-purple-400 border-purple-500/20';
  } else if (status === WorkerStatus.DRAINING) {
    colorClass = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
  }

  return (
    <span className={clsx('px-2 py-0.5 text-xs font-mono font-medium border rounded-none', colorClass, className)}>
      {status}
    </span>
  );
}
