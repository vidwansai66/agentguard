import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import {
  Wrench,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  RotateCcw,
  ShieldAlert,
  GitCompare,
  ArrowRight,
  ThumbsUp,
  ThumbsDown,
  Layers,
  FileCode
} from 'lucide-react';
import { api } from '../api/client';
import { Diagnosis, RepairProposal, TestRun } from '../types';
import { DiffView } from '../components/common/DiffView';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const DiagnosisPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [runs, setRuns] = useState<TestRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [diagnoses, setDiagnoses] = useState<Diagnosis[]>([]);
  const [patches, setPatches] = useState<RepairProposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const initData = async () => {
    try {
      setLoading(true);
      const allRuns = await api.getRuns(30);
      setRuns(allRuns);

      const qRun = searchParams.get('run_id');
      const targetRunId = qRun || (allRuns.length > 0 ? allRuns[0].id : '');
      setSelectedRunId(targetRunId);

      if (targetRunId) {
        await loadRunDiagnoses(targetRunId);
      }
    } catch (err) {
      console.error('Failed to load diagnosis data', err);
    } finally {
      setLoading(false);
    }
  };

  const loadRunDiagnoses = async (runId: string) => {
    try {
      const [diagList, patchList] = await Promise.all([
        api.getRunDiagnoses(runId),
        api.getPatches()
      ]);

      // If diagnoses empty for this run, auto-generate them!
      if (diagList.length === 0) {
        const generated = await api.diagnoseRun(runId);
        setDiagnoses(generated);
      } else {
        setDiagnoses(diagList);
      }

      const freshPatches = await api.getPatches();
      setPatches(freshPatches.filter((p) => p.run_id === runId));
    } catch (err) {
      console.error('Error loading diagnoses', err);
    }
  };

  useEffect(() => {
    initData();
  }, []);

  const handleSelectRun = (id: string) => {
    setSelectedRunId(id);
    loadRunDiagnoses(id);
  };

  const handleApprove = async (patchId: string) => {
    try {
      setActionLoading(patchId);
      await api.approvePatch(patchId);
      if (selectedRunId) await loadRunDiagnoses(selectedRunId);
    } catch (err: any) {
      alert(`Approval failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (patchId: string) => {
    try {
      setActionLoading(patchId);
      await api.rejectPatch(patchId, 'Rejected by operator');
      if (selectedRunId) await loadRunDiagnoses(selectedRunId);
    } catch (err: any) {
      alert(`Rejection failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleVerify = async (patchId: string) => {
    try {
      setActionLoading(patchId);
      const comparison = await api.verifyPatch(patchId);
      if (selectedRunId) await loadRunDiagnoses(selectedRunId);
      navigate(`/comparison?comparison_id=${comparison.id}`);
    } catch (err: any) {
      alert(`Verification run failed: ${err.message}`);
      if (selectedRunId) await loadRunDiagnoses(selectedRunId);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Synthesizing rule-based diagnoses from execution trace evidence..." />;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Diagnosis & Repair Engine</h1>
        <p className="text-xs text-slate-400 mt-1">
          Evidence-linked failure analysis, deterministic root cause identification, and verified candidate repair templates.
        </p>
      </div>

      {/* Select Run Selector Bar */}
      <div className="p-4 rounded-xl bg-dark-card border border-dark-border flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono uppercase text-slate-400 font-semibold">Active Run:</span>
          <select
            value={selectedRunId}
            onChange={(e) => handleSelectRun(e.target.value)}
            className="bg-dark-bg border border-dark-border text-slate-200 rounded px-3 py-1.5 text-xs font-mono focus:outline-none"
          >
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {r.id} — {r.name} ({r.failed_scenarios} fails, {r.unsafe_side_effects_count} unsafe)
              </option>
            ))}
          </select>
        </div>

        {selectedRunId && (
          <Link
            to={`/runs/${selectedRunId}`}
            className="text-xs text-brand-400 hover:text-brand-300 font-medium flex items-center gap-1 font-mono"
          >
            <span>View execution trace</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        )}
      </div>

      {/* Main Diagnosis & Repair List */}
      {diagnoses.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-dark-card border border-dark-border space-y-3">
          <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
          <h3 className="text-sm font-semibold text-white">No Failure Symptoms Detected</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            All assertions in this test run passed without safety violations or side effects. No repair proposals needed.
          </p>
        </div>
      ) : (
        <div className="space-y-8">
          {diagnoses.map((diag, idx) => {
            const correspondingPatch = patches.find((p) => p.diagnosis_id === diag.id) || patches[idx];

            return (
              <div
                key={diag.id}
                className="p-6 rounded-2xl bg-dark-card border border-dark-border space-y-6 shadow-md"
              >
                {/* Diagnosis Header */}
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-dark-border pb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="px-2 py-0.5 rounded font-mono text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                        Diagnosis #{idx + 1}
                      </span>
                      <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-sky-950 text-sky-400 border border-sky-800">
                        Confidence: {diag.confidence}
                      </span>
                      <span className="text-[11px] font-mono text-slate-500">{diag.id}</span>
                    </div>
                    <h2 className="text-base font-bold text-white">{diag.title}</h2>
                  </div>

                  <div className="text-xs font-mono text-slate-400 bg-dark-bg px-3 py-1.5 rounded-lg border border-dark-border">
                    Recommended: <span className="text-cyan-400 font-semibold">{diag.recommended_strategy}</span>
                  </div>
                </div>

                {/* Evidence & Explanation Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="p-4 rounded-xl bg-dark-bg/60 border border-dark-border space-y-2">
                    <h4 className="font-semibold text-slate-300 flex items-center gap-2 font-mono">
                      <AlertTriangle className="w-4 h-4 text-rose-400" />
                      <span>Likely Root Cause</span>
                    </h4>
                    <p className="text-slate-300 font-medium">{diag.likely_cause}</p>
                    <p className="text-slate-400 leading-relaxed text-[11px] pt-1 border-t border-dark-border/40">
                      {diag.explanation}
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-dark-bg/60 border border-dark-border space-y-2">
                    <h4 className="font-semibold text-slate-300 flex items-center gap-2 font-mono">
                      <ShieldAlert className="w-4 h-4 text-cyan-400" />
                      <span>Empirical Evidence References</span>
                    </h4>
                    <pre className="p-2.5 rounded bg-dark-card border border-dark-border text-slate-300 text-[11px] overflow-x-auto font-mono">
                      {JSON.stringify(diag.supporting_evidence, null, 2)}
                    </pre>
                    {diag.limitations && (
                      <p className="text-[10px] text-slate-500 italic mt-1">
                        Limitations: {diag.limitations}
                      </p>
                    )}
                  </div>
                </div>

                {/* Proposed Repair Patch Section */}
                {correspondingPatch && (
                  <div className="p-5 rounded-xl bg-dark-bg/90 border border-brand-500/30 space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-mono text-xs font-bold text-brand-400">
                            {correspondingPatch.template_id}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold bg-slate-800 text-slate-300">
                            Status: {correspondingPatch.approval_status}
                          </span>
                          {correspondingPatch.verification_status !== 'unverified' && (
                            <StatusBadge status={correspondingPatch.verification_status} />
                          )}
                        </div>
                        <h3 className="text-sm font-bold text-white">{correspondingPatch.title}</h3>
                      </div>

                      {/* Approval / Verify Action Buttons */}
                      <div className="flex items-center gap-2">
                        {correspondingPatch.approval_status === 'pending' && (
                          <>
                            <button
                              onClick={() => handleReject(correspondingPatch.id)}
                              disabled={actionLoading === correspondingPatch.id}
                              className="px-3 py-1.5 rounded-lg bg-dark-card hover:bg-dark-hover border border-dark-border text-slate-300 hover:text-rose-400 text-xs font-semibold flex items-center gap-1.5 transition-all"
                            >
                              <ThumbsDown className="w-3.5 h-3.5" />
                              <span>Reject</span>
                            </button>
                            <button
                              onClick={() => handleApprove(correspondingPatch.id)}
                              disabled={actionLoading === correspondingPatch.id}
                              className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-all shadow-md shadow-emerald-600/20"
                            >
                              <ThumbsUp className="w-3.5 h-3.5" />
                              <span>Approve Candidate Fix</span>
                            </button>
                          </>
                        )}

                        {correspondingPatch.approval_status === 'approved' && (
                          <button
                            onClick={() => handleVerify(correspondingPatch.id)}
                            disabled={actionLoading === correspondingPatch.id}
                            className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-bold flex items-center gap-2 transition-all shadow-md shadow-brand-600/25"
                          >
                            <GitCompare className="w-4 h-4" />
                            <span>
                              {actionLoading === correspondingPatch.id
                                ? 'Executing Verification...'
                                : 'Run Candidate Verification'}
                            </span>
                          </button>
                        )}

                        {correspondingPatch.comparison_id && (
                          <Link
                            to={`/comparison?comparison_id=${correspondingPatch.comparison_id}`}
                            className="px-3 py-1.5 rounded-lg bg-dark-card hover:bg-dark-hover border border-dark-border text-sky-400 text-xs font-semibold flex items-center gap-1.5"
                          >
                            <span>View Comparison Report</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </Link>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="p-3 rounded-lg bg-dark-card border border-dark-border">
                        <span className="text-emerald-400 font-semibold block mb-0.5">Expected Benefit:</span>
                        <p className="text-slate-300 text-[11px]">{correspondingPatch.expected_benefit}</p>
                      </div>
                      <div className="p-3 rounded-lg bg-dark-card border border-dark-border">
                        <span className="text-amber-400 font-semibold block mb-0.5">Potential Trade-offs & Risks:</span>
                        <p className="text-slate-300 text-[11px]">{correspondingPatch.potential_risks}</p>
                      </div>
                    </div>

                    {/* Diff View */}
                    <div>
                      <DiffView diff={correspondingPatch.patch_diff} />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
