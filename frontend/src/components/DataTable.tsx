import React from 'react';

interface Column<T> {
  key: string;
  header: string;
  render: (item: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (item: T) => void;
  isLoading?: boolean;
}

export function DataTable<T>({ columns, data, onRowClick, isLoading }: DataTableProps<T>) {
  return (
    <div className="w-full overflow-x-auto border border-slate-800 bg-slate-900">
      <table className="w-full text-sm text-left text-slate-300">
        <thead className="text-xs text-slate-400 uppercase bg-slate-900/50 border-b border-slate-800 font-mono">
          <tr>
            {columns.map((col) => (
              <th key={col.key} className="px-4 py-3 font-medium">
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-slate-500 font-mono">
                Loading data...
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-slate-500 font-mono">
                No items found
              </td>
            </tr>
          ) : (
            data.map((item, idx) => (
              <tr 
                key={idx} 
                onClick={() => onRowClick && onRowClick(item)}
                className={`border-b border-slate-800 last:border-0 hover:bg-slate-800/50 transition-colors ${onRowClick ? 'cursor-pointer' : ''}`}
              >
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3 whitespace-nowrap">
                    {col.render(item)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
