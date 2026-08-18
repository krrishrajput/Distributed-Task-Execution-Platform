import React from 'react';

interface JsonViewerProps {
  data: any;
  className?: string;
}

export function JsonViewer({ data, className = '' }: JsonViewerProps) {
  if (data === undefined || data === null) {
    return <div className={`text-slate-500 italic font-mono text-sm ${className}`}>null</div>;
  }
  
  return (
    <pre className={`bg-slate-900 border border-slate-800 p-4 overflow-x-auto text-sm font-mono text-slate-300 ${className}`}>
      <code>{JSON.stringify(data, null, 2)}</code>
    </pre>
  );
}
