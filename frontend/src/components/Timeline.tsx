import React from 'react';
import { format } from 'date-fns';

export interface TimelineEvent {
  timestamp: string;
  title: string;
  description?: string;
  isError?: boolean;
}

export function Timeline({ events }: { events: TimelineEvent[] }) {
  if (!events || events.length === 0) {
    return <div className="text-slate-500 text-sm italic font-mono">No history available</div>;
  }

  return (
    <div className="relative border-l border-slate-700 ml-3 space-y-6">
      {events.map((evt, idx) => (
        <div key={idx} className="relative pl-6">
          <span className={`absolute -left-1.5 top-1.5 h-3 w-3 rounded-full border-2 border-slate-900 ${evt.isError ? 'bg-red-500' : 'bg-blue-500'}`}></span>
          <div className="flex flex-col">
            <span className="text-xs font-mono text-slate-500 mb-1">
              {format(new Date(evt.timestamp), 'yyyy-MM-dd HH:mm:ss')}
            </span>
            <span className={`text-sm font-medium ${evt.isError ? 'text-red-400' : 'text-slate-200'}`}>
              {evt.title}
            </span>
            {evt.description && (
              <span className="text-sm text-slate-400 mt-1 font-mono bg-slate-900 p-2 border border-slate-800 inline-block">
                {evt.description}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
