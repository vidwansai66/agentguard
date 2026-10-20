import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Clock,
  Filter,
  Download,
  Copy,
  ChevronDown,
  ChevronRight,
  Shield,
  Bot,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileCode,
  ArrowLeft,
  Wrench,
  Activity
} from 'lucide-react';
import { api } from '../api/client';
import { TestRun, TraceEvent, EvaluationFinding } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const RunDetailsPage: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();

  const [run, setRun] = useState<TestRun | null>(null);
  const [traces, setTraces] = useState<TraceEvent[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [filterType, setFilterType] = useState<string>('');
  const [filterSeverity, setFilterSeverity] = useState<string>('');
  const [filterScenario, setFilterScenario] = useState<string>('');

  // Expandable trace items
  const [expandedEvents, setExpandedEvents] = useState<Record<string, boolean>>({});

  const loadRunDetails = async () => {
    if (!runId) return;
    try {
      setLoading(true);
      const [runData, traceData] = await Promise.all([
        api.getRun(runId),
        api.getRunTrace(runId, {
          event_type: filterType || undefined,
          severity: filterSeverity || undefined,
          scenario_id: filterScenario || undefined
        })
      ]);
      setRun(runData);
      setTraces(traceData);
    } catch (err) {
      console.error('Failed to load run details or trace', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRunDetails();
  }, [runId, filterType, filterSeverity, filterScenario]);

  const toggleExpand = (id: string) => {
    setExpandedEvents((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleCopyTrace = () => {
    navigator.clipboard.writeText(JSON.stringify(traces, null, 2));
    alert('Sanitized trace timeline JSON copied to clipboard!');
  };

  const handleExportRun = async () => {
    if (!runId) return;
    try {
      const data = await api.getRun(runId);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `agentguard-run-${runId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    }
  };

  if (loading && !run) {
    return <LoadingSpinner message="Loading chronological execution trace..." />;
  }

  if (!run) {
    return (
      <div className="p-8 text-center text-slate-400">
        Run '{runId}' not found.
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Top Breadcrumb & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <Link to="/runs" className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 mb-1">
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to All Runs</span>
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">{run.name}</h1>
            <StatusBadge status={run.status} />
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase ${
              run.observability_level === 'level_1_result_only'
                ? 'bg-teal-500/10 text-teal-400 border border-teal-500/30'
                : run.observability_level === 'level_2_structured_events'
                ? 'bg-purple-500/10 text-purple-400 border border-purple-500/30'
                : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
            }`}>
              {run.observability_level === 'level_1_result_only'
                ? 'Level 1: Result-Only'
                : run.observability_level === 'level_2_structured_events'
                ? 'Level 2: Structured-Events'
                : 'Level 3: Instrumented'}
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Run ID: {run.id} | Agent: {run.agent_id} ({run.agent_version})
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleCopyTrace}
            className="px-3 py-2 rounded-lg bg-dark-card border border-dark-border hover:bg-dark-hover text-slate-300 text-xs font-semibold flex items-center gap-2 transition-all"
          >
            <Copy className="w-3.5 h-3.5" />
            <span>Copy Trace JSON</span>
          </button>

          <button
            onClick={handleExportRun}
            className="px-3 py-2 rounded-lg bg-dark-card border border-dark-border hover:bg-dark-hover text-slate-300 text-xs font-semibold flex items-center gap-2 transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Results</span>
          </button>

          <Link
            to={`/repairs?run_id=${run.id}`}
            className="px-3.5 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold flex items-center gap-2 transition-all shadow-md shadow-brand-600/20"
          >
            <Wrench className="w-3.5 h-3.5" />
            <span>Diagnose & Propose Fix</span>
          </Link>
        </div>
      </div>

      {/* Metrics Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-dark-card border border-dark-border">
          <span className="text-slate-400 text-xs">Total Duration</span>
          <div className="text-xl font-bold font-mono text-white mt-1">
            {run.total_duration_ms.toFixed(1)}ms
          </div>
        </div>

        <div className="p-4 rounded-xl bg-dark-card border border-dark-border">
          <span className="text-slate-400 text-xs">Scenario Success</span>
          <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
            {run.passed_scenarios} / {run.total_scenarios}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-dark-card border border-dark-border">
          <span className="text-slate-400 text-xs">Unsafe Side Effects</span>
          <div className={`text-xl font-bold font-mono mt-1 ${run.unsafe_side_effects_count > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
            {run.unsafe_side_effects_count}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-dark-card border border-dark-border">
          <span className="text-slate-400 text-xs">Recovered Runs</span>
          <div className="text-xl font-bold font-mono text-teal-400 mt-1">
            {run.recovered_count} / {run.disrupted_count || 0}
          </div>
        </div>
      </div>

      {/* Filter Ribbon */}
      <div className="p-4 rounded-xl bg-dark-card border border-dark-border flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
          <Filter className="w-3.5 h-3.5 text-emerald-400" />
          <span>Event Type:</span>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="bg-dark-bg border border-dark-border text-slate-200 rounded px-2.5 py-1 text-xs focus:outline-none"
          >
            <option value="">All Events ({traces.length})</option>
            <option value="agent_decision">Agent Decision</option>
            <option value="tool_call">Tool Call</option>
            <option value="tool_response">Tool Response</option>
            <option value="fault_injected">Fault Injected</option>
            <option value="error">Error</option>
          </select>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
          <span>Severity:</span>
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="bg-dark-bg border border-dark-border text-slate-200 rounded px-2.5 py-1 text-xs focus:outline-none"
          >
            <option value="">All Severities</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>
        </div>

        <div className="ml-auto text-xs text-slate-500 font-mono flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5 text-emerald-400" />
          <span>Sensitive Tokens Redacted</span>
        </div>
      </div>

      {/* Chronological Trace Timeline */}
      <div className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
          <Activity className="w-4 h-4 text-brand-400" />
          <span>Execution Timeline Events ({traces.length})</span>
        </h2>

        {traces.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500 rounded-xl bg-dark-card border border-dark-border">
            No trace events match the current filter selection.
          </div>
        ) : (
          <div className="space-y-3">
            {traces.map((event) => {
              const isExpanded = expandedEvents[event.id];

              let badgeColor = 'bg-slate-800 text-slate-300 border-slate-700';
              if (event.event_type === 'fault_injected') badgeColor = 'bg-rose-500/20 text-rose-300 border-rose-500/40';
              if (event.event_type === 'tool_call') badgeColor = 'bg-teal-500/20 text-teal-300 border-teal-500/40';
              if (event.event_type === 'tool_response') badgeColor = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
              if (event.event_type === 'agent_decision') badgeColor = 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40';

              return (
                <div
                  key={event.id}
                  className="rounded-xl border border-dark-border bg-dark-card overflow-hidden hover:border-slate-700 transition-all"
                >
                  <div
                    onClick={() => toggleExpand(event.id)}
                    className="p-4 flex items-center justify-between cursor-pointer select-none hover:bg-dark-hover/30 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <button className="text-slate-500 hover:text-white">
                        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </button>

                      <span className="font-mono text-xs text-slate-500 w-12">
                        #{event.step_index.toString().padStart(2, '0')}
                      </span>

                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${badgeColor}`}>
                        {event.event_type}
                      </span>

                      <span className="font-semibold text-xs text-slate-200">
                        {event.action_name || event.tool_name || 'System Step'}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
                      {event.duration_ms > 0 && <span>{event.duration_ms.toFixed(1)}ms</span>}
                      {event.retry_count > 0 && <span className="text-amber-400 font-bold">Retry {event.retry_count}</span>}
                      <SeverityBadge severity={event.severity} />
                    </div>
                  </div>

                  {/* Expanded Structured Data Inspection */}
                  {isExpanded && (
                    <div className="p-4 border-t border-dark-border bg-[#070A10] space-y-3 font-mono text-xs">
                      {event.error_message && (
                        <div className="p-2.5 rounded bg-rose-950/40 border border-rose-900/50 text-rose-300">
                          <span className="font-bold">Error: </span>
                          <span>{event.error_message}</span>
                        </div>
                      )}

                      {event.fault_details && Object.keys(event.fault_details).length > 0 && (
                        <div>
                          <div className="text-[11px] text-rose-400 font-bold mb-1">Injected Fault Details:</div>
                          <pre className="p-2.5 rounded bg-dark-bg border border-rose-900/40 text-rose-300 text-[11px] overflow-x-auto">
                            {JSON.stringify(event.fault_details, null, 2)}
                          </pre>
                        </div>
                      )}

                      {event.sanitized_input && Object.keys(event.sanitized_input).length > 0 && (
                        <div>
                          <div className="text-[11px] text-slate-400 mb-1">Sanitized Input / Params:</div>
                          <pre className="p-2.5 rounded bg-dark-bg border border-dark-border text-slate-300 text-[11px] overflow-x-auto">
                            {JSON.stringify(event.sanitized_input, null, 2)}
                          </pre>
                        </div>
                      )}

                      {event.sanitized_output && Object.keys(event.sanitized_output).length > 0 && (
                        <div>
                          <div className="text-[11px] text-slate-400 mb-1">Sanitized Output / Response:</div>
                          <pre className="p-2.5 rounded bg-dark-bg border border-dark-border text-emerald-400 text-[11px] overflow-x-auto">
                            {JSON.stringify(event.sanitized_output, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
