import React, { ReactNode } from 'react';
import { clsx } from 'clsx';

interface MetricCardProps {
  title: string;
  value: string | number;
  icon?: ReactNode;
  trend?: string;
  trendUp?: boolean;
  color?: 'default' | 'blue' | 'green' | 'amber' | 'red' | 'purple';
  children?: ReactNode;
}

export function MetricCard({ title, value, icon, trend, trendUp, color = 'default', children }: MetricCardProps) {
  let valueColor = 'text-slate-100';
  if (color === 'blue') valueColor = 'text-blue-500';
  else if (color === 'green') valueColor = 'text-green-500';
  else if (color === 'amber') valueColor = 'text-amber-500';
  else if (color === 'red') valueColor = 'text-red-500';
  else if (color === 'purple') valueColor = 'text-purple-500';

  return (
    <div className="p-4 bg-slate-900 border border-slate-800 flex flex-col justify-between h-full">
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">{title}</h3>
        {icon && <div className="text-slate-500">{icon}</div>}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className={clsx("text-3xl font-mono font-semibold", valueColor)}>{value}</span>
        {trend && (
          <span className={clsx("text-xs font-mono", trendUp ? "text-green-400" : "text-red-400")}>
            {trend}
          </span>
        )}
      </div>
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}
