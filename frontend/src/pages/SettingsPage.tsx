import React, { useEffect, useState } from 'react';
import {
  Settings,
  Database,
  Shield,
  BookOpen,
  FileCode,
  RotateCcw,
  CheckCircle2,
  ExternalLink,
  Terminal,
  Activity,
  AlertTriangle
} from 'lucide-react';
import { api } from '../api/client';
import { SystemStatus } from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const SettingsPage: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const data = await api.getSystemStatus();
      setStatus(data);
    } catch (err) {
      console.error('Failed to load system status', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleResetData = async () => {
    if (!window.confirm('Reset all run history and re-seed the 11 baseline demo scenarios?')) return;
    try {
      setResetting(true);
      const res = await api.resetDemoData();
      alert(res.message);
      loadStatus();
    } catch (err: any) {
      alert(`Reset failed: ${err.message}`);
    } finally {
      setResetting(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Checking system diagnostics and database health..." />;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Settings & Architecture Documentation</h1>
        <p className="text-xs text-slate-400 mt-1">
          System health, environment parameters, metric mathematical definitions, and scenario JSON specifications.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* System Diagnostics Card */}
        <div className="p-6 rounded-2xl bg-dark-card border border-dark-border space-y-4">
          <div className="flex items-center gap-2 border-b border-dark-border pb-3">
            <Activity className="w-4 h-4 text-sky-400" />
            <h2 className="text-sm font-bold text-white uppercase font-mono tracking-wider">System Status</h2>
          </div>

          <div className="space-y-3 text-xs font-mono">
            <div className="flex justify-between py-1.5 border-b border-dark-border/60">
              <span className="text-slate-400">Application Version</span>
              <span className="text-slate-200 font-bold">{status?.version || '1.0.0'}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-dark-border/60">
              <span className="text-slate-400">Database Engine</span>
              <span className="text-cyan-400 font-bold capitalize">{status?.database_url_type || 'sqlite'} (Local Store)</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-dark-border/60">
              <span className="text-slate-400">Database Connection</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Healthy & Migrated
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-dark-border/60">
              <span className="text-slate-400">Active Scenarios</span>
              <span className="text-slate-200">{status?.total_scenarios_count}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-dark-border/60">
              <span className="text-slate-400">Persisted Test Runs</span>
              <span className="text-slate-200">{status?.total_runs_count}</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-slate-400">Backend Uptime</span>
              <span className="text-slate-300">{status?.uptime_seconds} seconds</span>
            </div>
          </div>

          <div className="pt-2 flex items-center gap-3">
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-lg bg-dark-bg hover:bg-dark-hover border border-dark-border text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition-all"
            >
              <span>Interactive OpenAPI Docs</span>
              <ExternalLink className="w-3 h-3 text-sky-400" />
            </a>

            <button
              onClick={handleResetData}
              disabled={resetting}
              className="px-3 py-1.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/50 border border-rose-800 text-rose-300 text-xs font-semibold flex items-center gap-1.5 transition-all"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>{resetting ? 'Resetting...' : 'Reset Demo Data'}</span>
            </button>
          </div>
        </div>

        {/* Safety Limitations & Scope */}
        <div className="p-6 rounded-2xl bg-dark-card border border-dark-border space-y-4">
          <div className="flex items-center gap-2 border-b border-dark-border pb-3">
            <Shield className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-bold text-white uppercase font-mono tracking-wider">Safety & Research Scope</h2>
          </div>

          <div className="space-y-3 text-xs text-slate-300 leading-relaxed">
            <p>
              AgentGuard is a controlled AI reliability evaluation harness. It operates under deterministic mock tool sandboxes
              and template-based repair proposals.
            </p>
            <ul className="space-y-2 list-disc list-inside text-slate-400 text-[11px]">
              <li>
                <strong className="text-slate-200">No Unrestricted Execution:</strong> Arbitrary code execution and untrusted Python file uploads are strictly prohibited.
              </li>
              <li>
                <strong className="text-slate-200">Bounded Runtime Limits:</strong> Maximum steps and timeouts are enforced on all tool invocations.
              </li>
              <li>
                <strong className="text-slate-200">Sanitized Traces:</strong> Sensitive tokens, secrets, authorization headers, and credentials are automatically redacted before persistence.
              </li>
              <li>
                <strong className="text-slate-200">No Auto-Deployment:</strong> Candidate patches require explicit verification against regression suites before approval.
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Metric Definitions Card */}
      <div className="p-6 rounded-2xl bg-dark-card border border-dark-border space-y-4">
        <div className="flex items-center gap-2 border-b border-dark-border pb-3">
          <BookOpen className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-white uppercase font-mono tracking-wider">Evaluation Metrics Formulation</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          <div className="p-3.5 rounded-xl bg-dark-bg border border-dark-border space-y-1">
            <span className="font-semibold text-emerald-400 font-mono">Task Success Rate</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Passed runs satisfying all explicit functional assertions divided by total eligible runs. Runs with duplicate side effects are rejected.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-dark-bg border border-dark-border space-y-1">
            <span className="font-semibold text-cyan-400 font-mono">Recovery Rate</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Proportion of initially disrupted scenario runs that safely achieve goal reconciliation under state-aware policies without side effects.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-dark-bg border border-dark-border space-y-1">
            <span className="font-semibold text-rose-400 font-mono">Unsafe Side-Effect Rate</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Share of runs producing duplicate database writes, policy violations, or unauthorized tool executions during retries.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-dark-bg border border-dark-border space-y-1">
            <span className="font-semibold text-amber-400 font-mono">Regression Rate</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Proportion of previously passing baseline scenarios that fail when tested under the candidate repair patch.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-dark-bg border border-dark-border space-y-1">
            <span className="font-semibold text-white font-mono">Monotonic Latency</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Elapsed time per scenario step measured via high-resolution monotonic timer (<code className="text-sky-300">time.perf_counter()</code>).
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-dark-bg border border-dark-border space-y-1">
            <span className="font-semibold text-indigo-400 font-mono">Model Cost Tracking</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Calculated when LLM pricing configurations are provided. For the local mock MVP, recorded as local mock execution.
            </p>
          </div>
        </div>
      </div>

      {/* Scenario JSON Format Schema & Example */}
      <div className="p-6 rounded-2xl bg-dark-card border border-dark-border space-y-4">
        <div className="flex items-center gap-2 border-b border-dark-border pb-3">
          <FileCode className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-bold text-white uppercase font-mono tracking-wider">Scenario JSON Specification</h2>
        </div>

        <p className="text-xs text-slate-400">
          Scenarios can be exported, modified, and re-imported using this standard JSON contract:
        </p>

        <pre className="p-4 rounded-xl bg-dark-bg border border-dark-border text-slate-300 text-[11px] font-mono overflow-x-auto leading-relaxed">
{`{
  "name": "Ambiguous Outcome (Lost Response After Commit)",
  "category": "ticketing",
  "failure_type": "ambiguous_outcome",
  "severity": "high",
  "task_input": {
    "action": "create_ticket",
    "title": "Account Provisioning Order",
    "priority": "high"
  },
  "expected_outcome": {
    "status": "success",
    "max_tickets_created": 1
  },
  "fault_parameters": {
    "fault_type": "ambiguous_outcome",
    "max_fault_count": 1,
    "drop_response_after_action": true
  },
  "allowed_tools": ["ticket_create", "ticket_query", "ticket_get"],
  "policy_constraints": {
    "max_retries": 3,
    "disallowed_tools": ["admin_override"]
  },
  "execution_limits": {
    "max_steps": 10,
    "timeout_seconds": 15
  },
  "expected_assertions": [
    "ASSERT_NO_DUPLICATE_ACTIONS",
    "ASSERT_TASK_OUTCOME",
    "ASSERT_SAFE_RECOVERY"
  ]
}`}
        </pre>
      </div>
    </div>
  );
};
