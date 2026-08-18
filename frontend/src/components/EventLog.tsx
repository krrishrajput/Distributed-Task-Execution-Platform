import React from 'react';
import { format } from 'date-fns';
import { SystemEvent } from '../types';

export function EventLog({ events }: { events: SystemEvent[] }) {
  return (
    <div className="bg-slate-900 border border-slate-800 h-96 overflow-y-auto font-mono text-xs p-4">
      {events.length === 0 ? (
        <div className="text-slate-500 italic">No recent events...</div>
      ) : (
        events.map((evt) => (
          <div key={evt.event_id} className="mb-1 flex items-start hover:bg-slate-800/50 px-1 py-0.5 transition-colors">
            <span className="text-slate-500 w-32 shrink-0">
              {format(new Date(evt.timestamp), 'HH:mm:ss.SSS')}
            </span>
            <span className={`w-36 shrink-0 font-bold ${getEventTypeColor(evt.event_type)}`}>
              {evt.event_type}
            </span>
            <span className="text-slate-300 ml-2 flex-1 break-all">
              {evt.task_id && <span className="text-blue-400 mr-2">[{evt.task_id.substring(0,8)}]</span>}
              {evt.worker_id && <span className="text-purple-400 mr-2">[{evt.worker_id.substring(0,8)}]</span>}
              {evt.details && <span className="text-slate-500">{JSON.stringify(evt.details)}</span>}
            </span>
          </div>
        ))
      )}
    </div>
  );
}

function getEventTypeColor(type: string) {
  if (type.includes('FAIL') || type.includes('DLQ') || type.includes('OFFLINE')) return 'text-red-400';
  if (type.includes('COMPLETED') || type.includes('JOINED')) return 'text-green-400';
  if (type.includes('STARTED') || type.includes('HEARTBEAT')) return 'text-blue-400';
  if (type.includes('QUEUED')) return 'text-amber-400';
  return 'text-slate-300';
}
