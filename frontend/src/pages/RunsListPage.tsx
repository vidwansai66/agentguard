import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Clock, Play, ArrowRight, ShieldCheck, AlertTriangle, Activity } from 'lucide-react';
import { api } from '../api/client';
import { TestRun } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const RunsListPage: React.FC = () => {
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [loading, setLoading] = useState(true);

  const loadRuns = async () => {
    try {
      setLoading(true);
      const data = await api.getRuns(100);
      setRuns(data);
    } catch (err) {
      console.error('Failed to load runs', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  if (loading) {
    return <LoadingSpinner message="Loading historical test runs..." />;
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Historical Test Runs</h1>
          <p className="text-xs text-slate-400 mt-1">
            Persisted execution runs, trace event recordings, and evaluation outcomes.
          </p>
        </div>

        <Link
          to="/execution"
          className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold flex items-center gap-2 shadow-md shadow-brand-600/20 self-start sm:self-auto"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>Launch New Run</span>
        </Link>
      </div>

      <div className="rounded-2xl bg-dark-card border border-dark-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-dark-bg/80 text-slate-400 font-mono text-[11px] uppercase tracking-wider border-b border-dark-border">
              <tr>
                <th className="py-3.5 px-4">Run Identifier & Name</th>
                <th className="py-3.5 px-4">Agent Version</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Passed / Total</th>
                <th className="py-3.5 px-4">Unsafe Effects</th>
                <th className="py-3.5 px-4">Duration</th>
                <th className="py-3.5 px-4">Timestamp</th>
                <th className="py-3.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-border">
              {runs.map((r) => (
                <tr key={r.id} className="hover:bg-dark-hover/30 transition-colors">
                  <td className="py-3.5 px-4 font-mono font-medium text-slate-200">
                    <Link to={`/runs/${r.id}`} className="hover:text-brand-400 hover:underline">
                      {r.id}
                    </Link>
                    <div className="text-[11px] text-slate-500 font-sans truncate max-w-sm">{r.name}</div>
                  </td>
                  <td className="py-3.5 px-4">
                    <div className="font-mono text-xs text-slate-200">{r.agent_id}</div>
                    <div className="flex items-center gap-1.5 mt-1">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-dark-bg border border-dark-border text-sky-400">
                        v{r.agent_version}
                      </span>
                      {r.observability_level && (
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono uppercase font-semibold border ${
                          r.observability_level === 'level_1_result_only'
                            ? 'bg-blue-950/60 text-blue-400 border-blue-800/40'
                            : r.observability_level === 'level_2_structured_events'
                            ? 'bg-purple-950/60 text-purple-400 border-purple-800/40'
                            : 'bg-emerald-950/60 text-emerald-400 border-emerald-800/40'
                        }`}>
                          {r.observability_level === 'level_1_result_only' ? 'L1: Result' : r.observability_level === 'level_2_structured_events' ? 'L2: Events' : 'L3: Inst'}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3.5 px-4">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="py-3.5 px-4 font-mono">
                    <span className="text-emerald-400 font-bold">{r.passed_scenarios}</span>
                    <span className="text-slate-500"> / {r.total_scenarios}</span>
                  </td>
                  <td className="py-3.5 px-4 font-mono">
                    {r.unsafe_side_effects_count > 0 ? (
                      <span className="text-rose-400 font-bold bg-rose-950/40 px-2 py-0.5 rounded border border-rose-800/40">
                        {r.unsafe_side_effects_count} Unsafe
                      </span>
                    ) : (
                      <span className="text-emerald-400">0</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-400">
                    {r.total_duration_ms.toFixed(1)}ms
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                    {r.created_at ? new Date(r.created_at).toLocaleTimeString() : 'N/A'}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <Link
                      to={`/runs/${r.id}`}
                      className="px-2.5 py-1.5 rounded bg-dark-bg hover:bg-dark-card border border-dark-border text-slate-300 hover:text-white text-xs font-medium inline-flex items-center gap-1 transition-all"
                    >
                      <span>Trace & Findings</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
