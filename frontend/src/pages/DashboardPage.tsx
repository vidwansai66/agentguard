import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  AlertTriangle,
  RotateCcw,
  Clock,
  Coins,
  ArrowRight,
  Play,
  Plus,
  RefreshCw,
  BarChart3,
  TrendingUp,
  Activity
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell
} from 'recharts';
import { api } from '../api/client';
import { DashboardStats } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { EmptyState } from '../components/common/EmptyState';

export const DashboardPage: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getStats();
      setStats(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return <LoadingSpinner message="Calculating reliability metrics from execution database..." />;
  }

  if (error) {
    return (
      <div className="p-6 rounded-xl bg-rose-950/20 border border-rose-800/40 text-rose-300">
        <h3 className="font-semibold text-sm mb-1">Backend Connection Error</h3>
        <p className="text-xs text-rose-400 mb-4">{error}</p>
        <button
          onClick={loadData}
          className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const hasRuns = (stats?.total_runs || 0) > 0;

  return (
    <div className="space-y-8">
      {/* Top Banner & Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">System Reliability & Verification</h1>
          <p className="text-xs text-slate-400 mt-1">
            Empirical measurements from controlled agent execution, fault injection, and candidate verification.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            className="p-2 rounded-lg bg-dark-card border border-dark-border text-slate-400 hover:text-white transition-all text-xs flex items-center gap-1.5"
            title="Refresh metrics"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <Link
            to="/scenarios"
            className="btn-uiverse text-xs font-semibold flex items-center gap-2"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Manage Scenarios</span>
          </Link>
          <Link
            to="/execution"
            className="btn-tactile-brand flex items-center gap-2"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Run Test Suite</span>
          </Link>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Total Runs */}
        <div className="p-4 rounded-xl bg-dark-card border border-dark-border shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Total Runs</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">{stats?.total_runs || 0}</div>
          <p className="text-[11px] text-slate-500 mt-1">Across all test suites</p>
        </div>

        {/* Task Success Rate */}
        <div className="p-4 rounded-xl bg-dark-card border border-dark-border shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Success Rate</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            {((stats?.task_success_rate || 0) * 100).toFixed(1)}%
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Explicit pass criteria</p>
        </div>

        {/* Recovery Rate */}
        <div className="p-4 rounded-xl bg-dark-card border border-dark-border shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Recovery Rate</span>
            <RotateCcw className="w-4 h-4 text-teal-400" />
          </div>
          <div className="text-2xl font-bold text-teal-400 font-mono">
            {((stats?.recovery_rate || 0) * 100).toFixed(1)}%
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Under tool disruption</p>
        </div>

        {/* Unsafe Side-Effect Rate */}
        <div className="p-4 rounded-xl bg-dark-card border border-dark-border shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Unsafe Side Effects</span>
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-rose-400 font-mono">
            {((stats?.unsafe_side_effect_rate || 0) * 100).toFixed(1)}%
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Duplicate / policy breach</p>
        </div>

        {/* Median Latency */}
        <div className="p-4 rounded-xl bg-dark-card border border-dark-border shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Median Latency</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {stats?.median_latency_ms || 0}
            <span className="text-xs font-normal text-slate-400 ml-1">ms</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">p95: {stats?.p95_latency_ms || 0}ms</p>
        </div>

        {/* Cost Per Task */}
        <div className="p-4 rounded-xl bg-dark-card border border-dark-border shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Model Cost</span>
            <Coins className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-xs font-semibold text-slate-300 font-mono truncate" title={stats?.cost_per_successful_task}>
            Local Mocks
          </div>
          <p className="text-[11px] text-slate-500 mt-1 truncate" title="External LLM cost input inactive">
            Zero external cost
          </p>
        </div>
      </div>

      {!hasRuns ? (
        <EmptyState
          icon={BarChart3}
          title="No execution data recorded yet"
          description="The database has not executed any test runs yet. Run your first scenario or full test suite to generate empirical reliability benchmarks."
          actionText="Launch First Test Run"
          onAction={() => navigate('/execution')}
        />
      ) : (
        <>
          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Reliability Trend History */}
            <div className="p-5 rounded-2xl bg-dark-card border border-dark-border space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                    <span>Run Success & Safety Trends</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">Chronological succession of recent test runs</p>
                </div>
              </div>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={stats?.trend_history || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="successGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                      </linearGradient>
                      <linearGradient id="unsafeGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="timestamp" stroke="#64748b" fontSize={11} />
                    <YAxis stroke="#64748b" fontSize={11} domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#111827', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                      formatter={(val: any) => [`${(Number(val) * 100).toFixed(1)}%`]}
                    />
                    <Area type="monotone" dataKey="success_rate" name="Success Rate" stroke="#10b981" fill="url(#successGrad)" strokeWidth={2} />
                    <Area type="monotone" dataKey="unsafe_side_effect_rate" name="Unsafe Side Effects" stroke="#f43f5e" fill="url(#unsafeGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Failure Type Distribution */}
            <div className="p-5 rounded-2xl bg-dark-card border border-dark-border space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-emerald-400" />
                  <span>Outcomes by Failure Category</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">Distribution across the 6 fault injection categories</p>
              </div>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stats?.failure_type_metrics || []} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                    <XAxis
                      dataKey="category"
                      stroke="#64748b"
                      fontSize={10}
                      interval={0}
                      angle={-25}
                      textAnchor="end"
                    />
                    <YAxis stroke="#64748b" fontSize={11} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#111827', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                    />
                    <Bar dataKey="passed" name="Passed" fill="#10b981" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="failed" name="Failed" fill="#f43f5e" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Recent Test Runs Table */}
          <div className="rounded-2xl bg-dark-card border border-dark-border overflow-hidden">
            <div className="p-5 border-b border-dark-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white">Recent Execution Runs</h3>
                <p className="text-xs text-slate-400 mt-0.5">Historical executions stored in local database</p>
              </div>
              <Link
                to="/runs"
                className="text-xs text-brand-400 hover:text-brand-300 font-medium flex items-center gap-1"
              >
                <span>View all runs</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-dark-bg/60 text-slate-400 font-mono text-[11px] uppercase tracking-wider border-b border-dark-border">
                  <tr>
                    <th className="py-3 px-4">Run Identifier</th>
                    <th className="py-3 px-4">Agent / Version</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Passed / Total</th>
                    <th className="py-3 px-4">Unsafe Effects</th>
                    <th className="py-3 px-4">Duration</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-border">
                  {stats?.recent_runs.map((run) => (
                    <tr key={run.id} className="hover:bg-dark-hover/40 transition-colors">
                      <td className="py-3.5 px-4 font-mono font-medium text-slate-200">
                        <Link to={`/runs/${run.id}`} className="hover:text-brand-400 hover:underline">
                          {run.id}
                        </Link>
                        <div className="text-[11px] text-slate-500 font-sans truncate max-w-xs">{run.name}</div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="font-mono text-slate-300">{run.agent_id}</span>
                        <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] bg-emerald-950/60 text-emerald-400 border border-emerald-800/40 font-mono">
                          {run.agent_version}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <StatusBadge status={run.status} />
                      </td>
                      <td className="py-3.5 px-4 font-mono">
                        <span className="text-emerald-400 font-semibold">{run.passed_scenarios}</span>
                        <span className="text-slate-500"> / {run.total_scenarios}</span>
                      </td>
                      <td className="py-3.5 px-4 font-mono">
                        {run.unsafe_side_effects_count > 0 ? (
                          <span className="text-rose-400 font-bold bg-rose-950/40 px-2 py-0.5 rounded border border-rose-800/50">
                            {run.unsafe_side_effects_count} Unsafe
                          </span>
                        ) : (
                          <span className="text-emerald-400">0</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-400">
                        {run.duration_ms.toFixed(1)}ms
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Link
                          to={`/runs/${run.id}`}
                          className="px-2.5 py-1.5 rounded bg-dark-bg hover:bg-dark-card border border-dark-border text-slate-300 hover:text-white text-xs font-medium inline-flex items-center gap-1 transition-all"
                        >
                          <span>Trace & Results</span>
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
