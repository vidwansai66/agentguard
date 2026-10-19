import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  GitCompare,
  ShieldCheck,
  ShieldAlert,
  Clock,
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ArrowRight,
  TrendingUp,
  Sliders,
  Layers
} from 'lucide-react';
import { api } from '../api/client';
import { Comparison, TestRun } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const ComparisonPage: React.FC = () => {
  const [searchParams] = useSearchParams();

  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [baselineRunId, setBaselineRunId] = useState<string>('');
  const [candidateRunId, setCandidateRunId] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [isComparing, setIsComparing] = useState(false);

  const initData = async () => {
    try {
      setLoading(true);
      const allRuns = await api.getRuns(30);
      setRuns(allRuns);

      const qComp = searchParams.get('comparison_id');
      if (qComp) {
        const compData = await api.getComparison(qComp);
        setComparison(compData);
        setBaselineRunId(compData.baseline_run_id);
        setCandidateRunId(compData.candidate_run_id);
      } else if (allRuns.length >= 2) {
        setBaselineRunId(allRuns[1].id);
        setCandidateRunId(allRuns[0].id);
        // Try generating comparison
        try {
          const compData = await api.createComparison(allRuns[1].id, allRuns[0].id);
          setComparison(compData);
        } catch (_) {}
      }
    } catch (err) {
      console.error('Failed to load comparison data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    initData();
  }, []);

  const handleRunComparison = async () => {
    if (!baselineRunId || !candidateRunId || baselineRunId === candidateRunId) {
      alert('Please select two distinct runs to compare.');
      return;
    }
    try {
      setIsComparing(true);
      const data = await api.createComparison(baselineRunId, candidateRunId);
      setComparison(data);
    } catch (err: any) {
      alert(`Comparison failed: ${err.message}`);
    } finally {
      setIsComparing(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading baseline vs candidate verification report..." />;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Baseline vs. Candidate Verification</h1>
        <p className="text-xs text-slate-400 mt-1">
          Differential benchmark comparing task success, recovery resilience, unsafe side effects, and latency trade-offs.
        </p>
      </div>

      {/* Comparison Selector Controls */}
      <div className="p-4 rounded-xl bg-dark-card border border-dark-border flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
          <div>
            <span className="text-slate-400 mr-2">Baseline Run:</span>
            <select
              value={baselineRunId}
              onChange={(e) => setBaselineRunId(e.target.value)}
              className="bg-dark-bg border border-dark-border text-slate-200 rounded px-2.5 py-1.5 focus:outline-none"
            >
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.id} ({r.agent_version} - {r.passed_scenarios}/{r.total_scenarios} passed)
                </option>
              ))}
            </select>
          </div>

          <div>
            <span className="text-slate-400 mr-2">Candidate Run:</span>
            <select
              value={candidateRunId}
              onChange={(e) => setCandidateRunId(e.target.value)}
              className="bg-dark-bg border border-dark-border text-slate-200 rounded px-2.5 py-1.5 focus:outline-none"
            >
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.id} ({r.agent_version} - {r.passed_scenarios}/{r.total_scenarios} passed)
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={handleRunComparison}
          disabled={isComparing}
          className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:bg-slate-800 text-white text-xs font-bold flex items-center gap-2 transition-all shadow-md shadow-brand-600/20"
        >
          <GitCompare className="w-4 h-4" />
          <span>{isComparing ? 'Comparing...' : 'Compare Selected Runs'}</span>
        </button>
      </div>

      {comparison && (
        <div className="space-y-8 animate-fadeIn">
          {/* Verdict Banner */}
          <div
            className={`p-6 rounded-2xl border space-y-3 ${
              comparison.verification_verdict === 'verified_passed'
                ? 'bg-emerald-950/20 border-emerald-800/60 shadow-lg shadow-emerald-950/20'
                : comparison.verification_verdict === 'verified_failed'
                ? 'bg-rose-950/25 border-rose-800/60 shadow-lg shadow-rose-950/20'
                : 'bg-amber-950/20 border-amber-800/60'
            }`}
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                {comparison.verification_verdict === 'verified_passed' && (
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 shrink-0" />
                )}
                {comparison.verification_verdict === 'verified_failed' && (
                  <XCircle className="w-8 h-8 text-rose-400 shrink-0" />
                )}
                {comparison.verification_verdict === 'trade_offs_detected' && (
                  <AlertTriangle className="w-8 h-8 text-amber-400 shrink-0" />
                )}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
                      Verification Result
                    </span>
                    <StatusBadge status={comparison.verification_verdict} size="md" />
                  </div>
                  <h2 className="text-base font-bold text-white mt-0.5">
                    {comparison.verification_verdict === 'verified_passed'
                      ? 'Candidate Fix Verified & Approved'
                      : comparison.verification_verdict === 'verified_failed'
                      ? 'Candidate Fix Failed Verification'
                      : 'Candidate Parity (Trade-offs Detected)'}
                  </h2>
                </div>
              </div>

              <div className="text-xs font-mono text-slate-400 bg-dark-bg/80 px-3 py-1.5 rounded-lg border border-dark-border self-start sm:self-auto">
                Regression Rate:{' '}
                <span className={comparison.regression_rate > 0 ? 'text-rose-400 font-bold' : 'text-emerald-400 font-bold'}>
                  {(comparison.regression_rate * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed font-sans pt-1">
              {comparison.interpretation}
            </p>
          </div>

          {/* Differential Metrics Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Task Success Rate */}
            <div className="p-5 rounded-2xl bg-dark-card border border-dark-border space-y-2">
              <div className="text-xs text-slate-400 font-mono">Task Success Rate</div>
              <div className="flex items-baseline justify-between">
                <div>
                  <span className="text-xs text-slate-500 font-mono block">Baseline ({comparison.baseline_agent_version})</span>
                  <span className="text-lg font-bold font-mono text-slate-300">
                    {(comparison.baseline_success_rate * 100).toFixed(1)}%
                  </span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-600" />
                <div className="text-right">
                  <span className="text-xs text-slate-500 font-mono block">Candidate ({comparison.candidate_agent_version})</span>
                  <span
                    className={`text-lg font-bold font-mono ${
                      comparison.candidate_success_rate > comparison.baseline_success_rate
                        ? 'text-emerald-400'
                        : comparison.candidate_success_rate < comparison.baseline_success_rate
                        ? 'text-rose-400'
                        : 'text-slate-300'
                    }`}
                  >
                    {(comparison.candidate_success_rate * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Recovery Rate */}
            <div className="p-5 rounded-2xl bg-dark-card border border-dark-border space-y-2">
              <div className="text-xs text-slate-400 font-mono">Fault Recovery Rate</div>
              <div className="flex items-baseline justify-between">
                <div>
                  <span className="text-xs text-slate-500 font-mono block">Baseline</span>
                  <span className="text-lg font-bold font-mono text-slate-300">
                    {(comparison.baseline_recovery_rate * 100).toFixed(1)}%
                  </span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-600" />
                <div className="text-right">
                  <span className="text-xs text-slate-500 font-mono block">Candidate</span>
                  <span
                    className={`text-lg font-bold font-mono ${
                      comparison.candidate_recovery_rate > comparison.baseline_recovery_rate
                        ? 'text-cyan-400'
                        : 'text-slate-300'
                    }`}
                  >
                    {(comparison.candidate_recovery_rate * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Unsafe Side-Effects */}
            <div className="p-5 rounded-2xl bg-dark-card border border-dark-border space-y-2">
              <div className="text-xs text-slate-400 font-mono">Unsafe Side-Effect Rate</div>
              <div className="flex items-baseline justify-between">
                <div>
                  <span className="text-xs text-slate-500 font-mono block">Baseline</span>
                  <span className="text-lg font-bold font-mono text-rose-400">
                    {(comparison.baseline_unsafe_side_effect_rate * 100).toFixed(1)}%
                  </span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-600" />
                <div className="text-right">
                  <span className="text-xs text-slate-500 font-mono block">Candidate</span>
                  <span
                    className={`text-lg font-bold font-mono ${
                      comparison.candidate_unsafe_side_effect_rate < comparison.baseline_unsafe_side_effect_rate
                        ? 'text-emerald-400'
                        : 'text-rose-400'
                    }`}
                  >
                    {(comparison.candidate_unsafe_side_effect_rate * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Median Latency */}
            <div className="p-5 rounded-2xl bg-dark-card border border-dark-border space-y-2">
              <div className="text-xs text-slate-400 font-mono">Median Latency</div>
              <div className="flex items-baseline justify-between">
                <div>
                  <span className="text-xs text-slate-500 font-mono block">Baseline</span>
                  <span className="text-lg font-bold font-mono text-slate-300">
                    {comparison.baseline_median_latency_ms}ms
                  </span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-600" />
                <div className="text-right">
                  <span className="text-xs text-slate-500 font-mono block">Candidate</span>
                  <span className="text-lg font-bold font-mono text-slate-200">
                    {comparison.candidate_median_latency_ms}ms
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Per-Scenario Outcome Diff Table */}
          <div className="rounded-2xl bg-dark-card border border-dark-border overflow-hidden">
            <div className="p-4 border-b border-dark-border bg-dark-bg/60 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 font-mono">
                Scenario Differential Matrix ({comparison.per_scenario_comparison?.length || 0})
              </h3>
              <div className="flex items-center gap-3 text-xs font-mono">
                <span className="text-emerald-400">
                  +{comparison.newly_passing_scenarios?.length || 0} Newly Passing
                </span>
                <span className="text-rose-400">
                  -{comparison.newly_failing_scenarios?.length || 0} Regressions
                </span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300 font-mono">
                <thead className="bg-dark-bg/80 text-slate-500 text-[11px] uppercase tracking-wider border-b border-dark-border">
                  <tr>
                    <th className="py-3 px-4">Scenario Identifier</th>
                    <th className="py-3 px-4">Fault Category</th>
                    <th className="py-3 px-4">Baseline Result</th>
                    <th className="py-3 px-4">Candidate Result</th>
                    <th className="py-3 px-4">Safety Compliance</th>
                    <th className="py-3 px-4 text-right">Verdict</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-border text-xs">
                  {comparison.per_scenario_comparison?.map((sc) => (
                    <tr key={sc.scenario_id} className="hover:bg-dark-hover/30 transition-colors">
                      <td className="py-3.5 px-4 font-sans font-medium text-slate-200">
                        <div>{sc.scenario_name}</div>
                        <span className="font-mono text-[10px] text-slate-500">{sc.scenario_id}</span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-400">{sc.failure_type}</td>
                      <td className="py-3.5 px-4">
                        {sc.baseline_passed ? (
                          <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Passed
                          </span>
                        ) : (
                          <span className="text-rose-400 flex items-center gap-1 font-semibold">
                            <XCircle className="w-3.5 h-3.5" /> Failed
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        {sc.candidate_passed ? (
                          <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Passed
                          </span>
                        ) : (
                          <span className="text-rose-400 flex items-center gap-1 font-semibold">
                            <XCircle className="w-3.5 h-3.5" /> Failed
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        {sc.candidate_unsafe ? (
                          <span className="text-rose-400 font-bold bg-rose-950/40 px-2 py-0.5 rounded border border-rose-800/40">
                            Unsafe Side Effect
                          </span>
                        ) : (
                          <span className="text-emerald-400 font-medium">Safe</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        {sc.status_change === 'improved' && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                            IMPROVED (+Fix)
                          </span>
                        )}
                        {sc.status_change === 'regressed' && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40">
                            REGRESSED (-Fail)
                          </span>
                        )}
                        {sc.status_change === 'unchanged_pass' && (
                          <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400">
                            Pass (Stable)
                          </span>
                        )}
                        {sc.status_change === 'unchanged_fail' && (
                          <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-rose-400">
                            Unresolved
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
