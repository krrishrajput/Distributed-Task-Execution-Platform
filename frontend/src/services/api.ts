import { TaskCreate, Task, WorkerInfo, Metrics, PaginatedResponse } from '../types';

const API_BASE = '/api/v1';

async function fetchApi<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API Error: ${response.status} ${text}`);
  }
  return response.json();
}

export const api = {
  createTask: (data: TaskCreate) => 
    fetchApi<{task_id: string}>(`${API_BASE}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }),
    
  listTasks: (params?: { status?: string; type?: string; limit?: number; offset?: number; search?: string }) => {
    const qs = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== '') qs.append(k, String(v));
      });
    }
    return fetchApi<PaginatedResponse<Task>>(`${API_BASE}/tasks?${qs.toString()}`);
  },
  
  getTask: (id: string) => fetchApi<Task>(`${API_BASE}/tasks/${id}`),
  
  cancelTask: (id: string) => fetchApi<{status: string}>(`${API_BASE}/tasks/${id}/cancel`, { method: 'POST' }),
  
  retryTask: (id: string) => fetchApi<{status: string}>(`${API_BASE}/tasks/${id}/retry`, { method: 'POST' }),
  
  listDlqTasks: () => fetchApi<Task[]>(`${API_BASE}/tasks/dlq`),
  
  listWorkers: () => fetchApi<WorkerInfo[]>(`${API_BASE}/workers`),
  
  getMetrics: () => fetchApi<Metrics>(`${API_BASE}/metrics`),
};
