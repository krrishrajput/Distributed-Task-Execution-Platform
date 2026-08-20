import React, { useState } from 'react';
import { api } from '../services/api';
import { Play } from 'lucide-react';

export function Simulate() {
  const [result, setResult] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const submitTask = async (type: string, payload: any, count = 1) => {
    setLoading(true);
    try {
      if (count === 1) {
        const res = await api.createTask({ task_type: type, payload }) as any;
        setResult(`Success: Task ${res.id} created.`);
      } else {
        const ids = [];
        for (let i = 0; i < count; i++) {
          const res = await api.createTask({ task_type: type, payload }) as any;
          ids.push(res.id);
        }
        setResult(`Success: Created ${count} tasks. IDs: \n${ids.join('\n')}`);
      }
    } catch (err: any) {
      setResult(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const simulateButtons = [
    { label: "Submit Sleep Task", type: "sleep", payload: { duration: 5 } },
    { label: "Submit Random Failure", type: "random_failure", payload: { failure_rate: 0.8 } },
    { label: "Submit Deterministic Failure", type: "deterministic_failure", payload: { message: "Simulated deterministic failure" } },
    { label: "Submit Lease Expiration Task", type: "sleep", payload: { duration: 60 } }, // Takes longer than lease
    { label: "Submit Eventual Success", type: "eventual_success", payload: { failures_before_success: 2 } },
    { label: "Submit CPU Simulation", type: "cpu_simulation", payload: { iterations: 10000000 } },
  ];

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold font-mono tracking-wider">FAILURE SIMULATION SUITE</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {simulateButtons.map((btn, idx) => (
          <div key={idx} className="bg-slate-900 border border-slate-800 p-4 flex flex-col justify-between">
            <div>
              <h3 className="font-mono text-slate-200 mb-2">{btn.label}</h3>
              <pre className="text-xs text-slate-500 bg-slate-950 p-2 border border-slate-800 mb-4 overflow-x-auto">
                {JSON.stringify({ type: btn.type, payload: btn.payload }, null, 2)}
              </pre>
            </div>
            <button
              disabled={loading}
              onClick={() => submitTask(btn.type, btn.payload)}
              className="mt-2 w-full py-2 bg-slate-800 hover:bg-blue-500/20 hover:text-blue-400 border border-slate-700 hover:border-blue-500/50 text-sm font-mono transition-colors flex items-center justify-center disabled:opacity-50"
            >
              <Play className="w-4 h-4 mr-2" /> SUBMIT 1X
            </button>
          </div>
        ))}

        <div className="bg-slate-900 border border-slate-800 p-4 flex flex-col justify-between md:col-span-2">
          <div>
            <h3 className="font-mono text-slate-200 mb-2">Bulk Submit</h3>
            <p className="text-xs text-slate-400 mb-4">Submit a large batch of small sleep tasks to test throughput.</p>
          </div>
          <button
            disabled={loading}
            onClick={() => submitTask("sleep", { duration: 0.1 }, 50)}
            className="w-full py-2 bg-slate-800 hover:bg-blue-500/20 hover:text-blue-400 border border-slate-700 hover:border-blue-500/50 text-sm font-mono transition-colors flex items-center justify-center disabled:opacity-50"
          >
            <Play className="w-4 h-4 mr-2" /> SUBMIT 50X BATCH
          </button>
        </div>
      </div>

      {result && (
        <div className="mt-8">
          <h3 className="text-sm font-bold text-slate-400 mb-2 font-mono">SUBMISSION RESULT</h3>
          <pre className="bg-slate-900 border border-slate-800 p-4 text-sm font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap">
            {result}
          </pre>
        </div>
      )}
    </div>
  );
}
