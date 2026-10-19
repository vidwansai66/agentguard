import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import {
  Play,
  RotateCcw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Layers,
  Bot,
  FlaskConical,
  ArrowRight,
  ShieldAlert,
  Sliders,
  Terminal
} from 'lucide-react';
import { api } from '../api/client';
import { Agent, Scenario, TestSuite, TestRun } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const RunExecutionPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [agents, setAgents] = useState<Agent[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [loading, setLoading] = useState(true);

  // Form State
  const [selectedAgentId, setSelectedAgentId] = useState<string>('agent-ticket-sample');
  const [selectedVersion, setSelectedVersion] = useState<string>('1.0.0');
  const [runTarget, setRunTarget] = useState<'scenario' | 'suite'>('scenario');
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('SCEN-03-AMBIGUOUS-OUTCOME');
  const [selectedSuiteId, setSelectedSuiteId] = useState<string>('suite-core-reliability');
  const [customName, setCustomName] = useState<string>('');

  // Execution State
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentRun, setCurrentRun] = useState<TestRun | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const initData = async () => {
    try {
      setLoading(true);
      const [agentList, scenarioList, suiteList] = await Promise.all([
        api.getAgents(),
        api.getScenarios(),
        api.getSuites()
      ]);
      setAgents(agentList);
      setScenarios(scenarioList);
      setSuites(suiteList);

      // Read query params if present
      const qScen = searchParams.get('scenario_id');
      const qSuite = searchParams.get('suite_id');
      const qAgent = searchParams.get('agent_id');
      const qVer = searchParams.get('version');

      if (qAgent) setSelectedAgentId(qAgent);
      if (qVer) setSelectedVersion(qVer);

      if (qScen) {
        setRunTarget('scenario');
        setSelectedScenarioId(qScen);
      } else if (qSuite) {
        setRunTarget('suite');
        setSelectedSuiteId(qSuite);
      }
    } catch (err: any) {
      console.error('Failed to load runner options', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    initData();
  }, []);

  const handleExecute = async () => {
    if (isExecuting) return;
    try {
      setIsExecuting(true);
      setRunError(null);
      setCurrentRun(null);

      const payload: any = {
        name: customName || undefined,
        agent_id: selectedAgentId,
        agent_version: selectedVersion
      };

      if (runTarget === 'scenario') {
        payload.scenario_id = selectedScenarioId;
      } else {
        payload.suite_id = selectedSuiteId;
      }

      const runResult = await api.triggerRun(payload);
      setCurrentRun(runResult);
    } catch (err: any) {
      setRunError(err.message || 'Execution failed');
    } finally {
      setIsExecuting(false);
    }
  };

  const selectedAgent = agents.find((a) => a.id === selectedAgentId);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Test Run Execution</h1>
        <p className="text-xs text-slate-400 mt-1">
          Launch bounded scenario runs against target agents, record structured timeline traces, and evaluate safety assertions.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Run Configuration Launcher */}
        <div className="p-6 rounded-2xl bg-dark-card border border-dark-border space-y-5 shadow-sm">
          <div className="flex items-center gap-2 border-b border-dark-border pb-3">
            <Sliders className="w-4 h-4 text-sky-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">Run Parameters</h2>
          </div>

          <div className="space-y-4 text-xs">
            {/* Agent Selector */}
            <div>
              <label className="block text-slate-300 font-semibold mb-1 flex items-center gap-1.5">
                <Bot className="w-3.5 h-3.5 text-sky-400" />
                <span>Target Agent</span>
              </label>
              <select
                value={selectedAgentId}
                onChange={(e) => {
                  setSelectedAgentId(e.target.value);
                  const ag = agents.find((a) => a.id === e.target.value);
                  if (ag?.current_version) setSelectedVersion(ag.current_version);
                }}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-200 focus:outline-none"
              >
                {agents.map((ag) => (
                  <option key={ag.id} value={ag.id}>
                    {ag.name} ({ag.id})
                  </option>
                ))}
              </select>
            </div>

            {/* Version Selector */}
            <div>
              <label className="block text-slate-300 font-semibold mb-1 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-cyan-400" />
                <span>Agent Version / Strategy</span>
              </label>
              <select
                value={selectedVersion}
                onChange={(e) => setSelectedVersion(e.target.value)}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-200 font-mono focus:outline-none"
              >
                {selectedAgent?.versions.map((ver) => (
                  <option key={ver.id} value={ver.version_tag}>
                    {ver.version_tag} [{ver.strategy}] {ver.is_candidate ? '(Candidate Patch)' : '(Baseline)'}
                  </option>
                ))}
              </select>
            </div>

            {/* Target Mode: Scenario vs Suite */}
            <div>
              <label className="block text-slate-300 font-semibold mb-1.5">Execution Scope</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setRunTarget('scenario')}
                  className={`py-2 px-3 rounded-lg border font-medium text-xs transition-all ${
                    runTarget === 'scenario'
                      ? 'bg-brand-500/15 border-brand-500 text-brand-300 shadow-sm'
                      : 'bg-dark-bg border-dark-border text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Single Scenario
                </button>
                <button
                  type="button"
                  onClick={() => setRunTarget('suite')}
                  className={`py-2 px-3 rounded-lg border font-medium text-xs transition-all ${
                    runTarget === 'suite'
                      ? 'bg-brand-500/15 border-brand-500 text-brand-300 shadow-sm'
                      : 'bg-dark-bg border-dark-border text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Test Suite
                </button>
              </div>
            </div>

            {/* Scenario or Suite Select */}
            {runTarget === 'scenario' ? (
              <div>
                <label className="block text-slate-300 font-semibold mb-1 flex items-center gap-1.5">
                  <FlaskConical className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Choose Scenario</span>
                </label>
                <select
                  value={selectedScenarioId}
                  onChange={(e) => setSelectedScenarioId(e.target.value)}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-200 focus:outline-none"
                >
                  {scenarios.map((sc) => (
                    <option key={sc.id} value={sc.id}>
                      {sc.name} ({sc.failure_type})
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <div>
                <label className="block text-slate-300 font-semibold mb-1 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Choose Test Suite</span>
                </label>
                <select
                  value={selectedSuiteId}
                  onChange={(e) => setSelectedSuiteId(e.target.value)}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-200 focus:outline-none"
                >
                  {suites.map((st) => (
                    <option key={st.id} value={st.id}>
                      {st.name} ({st.scenario_count} scenarios)
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Custom Run Name (Optional) */}
            <div>
              <label className="block text-slate-300 font-semibold mb-1">Run Label (Optional)</label>
              <input
                type="text"
                placeholder="e.g. Baseline Check on Ambiguous Recovery"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-500 focus:outline-none"
              />
            </div>

            {/* Launch Button */}
            <div className="pt-3">
              <button
                onClick={handleExecute}
                disabled={isExecuting}
                className="w-full py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-lg shadow-brand-600/25"
              >
                {isExecuting ? (
                  <>
                    <Clock className="w-4 h-4 animate-spin text-white" />
                    <span>Executing Test Engine...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    <span>Start Controlled Test Run</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Execution Live Status & Results */}
        <div className="lg:col-span-2 space-y-6">
          {isExecuting && (
            <div className="p-8 rounded-2xl bg-dark-card border border-dark-border flex flex-col items-center justify-center text-center space-y-4">
              <div className="relative">
                <div className="w-16 h-16 rounded-full border-4 border-sky-500/20 border-t-sky-400 animate-spin" />
                <Terminal className="w-6 h-6 text-sky-400 absolute inset-0 m-auto" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Running Deterministic Test Engine</h3>
                <p className="text-xs text-slate-400 mt-1 max-w-sm">
                  Simulating tool invocations, injecting faults, recording redacted trace events, and running evaluator rules...
                </p>
              </div>
            </div>
          )}

          {runError && (
            <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-800/50 text-rose-300 text-xs flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
              <div>
                <span className="font-bold">Execution Error: </span>
                <span>{runError}</span>
              </div>
            </div>
          )}

          {!isExecuting && !currentRun && (
            <div className="p-12 rounded-2xl border border-dashed border-dark-border bg-dark-card/30 text-center flex flex-col items-center justify-center">
              <Terminal className="w-10 h-10 text-slate-600 mb-3" />
              <h3 className="text-sm font-semibold text-slate-300">Test Execution Standby</h3>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                Configure your target agent version and scenario scope on the left, then click Start Controlled Test Run.
              </p>
            </div>
          )}

          {currentRun && (
            <div className="space-y-6 animate-fadeIn">
              {/* Completed Run Summary Card */}
              <div className="p-6 rounded-2xl bg-dark-card border border-dark-border space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-dark-border pb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs text-sky-400 font-bold">{currentRun.id}</span>
                      <StatusBadge status={currentRun.status} />
                      <span className="text-[11px] font-mono text-slate-400">
                        {currentRun.total_duration_ms.toFixed(1)}ms total
                      </span>
                    </div>
                    <h2 className="text-base font-bold text-white">{currentRun.name}</h2>
                  </div>

                  <div className="flex items-center gap-2">
                    <Link
                      to={`/runs/${currentRun.id}`}
                      className="px-3.5 py-1.5 rounded-lg bg-dark-bg hover:bg-dark-hover border border-dark-border text-slate-200 text-xs font-semibold flex items-center gap-1.5"
                    >
                      <span>Explore Trace Timeline</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                    <Link
                      to={`/repairs?run_id=${currentRun.id}`}
                      className="px-3.5 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-brand-600/20"
                    >
                      <span>Diagnose Failures</span>
                    </Link>
                  </div>
                </div>

                {/* Scorecards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3 rounded-xl bg-dark-bg border border-dark-border text-center">
                    <div className="text-xs text-slate-500 mb-0.5">Scenarios Passed</div>
                    <div className="text-xl font-bold font-mono text-emerald-400">
                      {currentRun.passed_scenarios} / {currentRun.total_scenarios}
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-dark-bg border border-dark-border text-center">
                    <div className="text-xs text-slate-500 mb-0.5">Failed Scenarios</div>
                    <div className="text-xl font-bold font-mono text-rose-400">
                      {currentRun.failed_scenarios}
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-dark-bg border border-dark-border text-center">
                    <div className="text-xs text-slate-500 mb-0.5">Unsafe Side Effects</div>
                    <div className="text-xl font-bold font-mono text-rose-400">
                      {currentRun.unsafe_side_effects_count}
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-dark-bg border border-dark-border text-center">
                    <div className="text-xs text-slate-500 mb-0.5">Recovered Runs</div>
                    <div className="text-xl font-bold font-mono text-cyan-400">
                      {currentRun.recovered_count} / {currentRun.disrupted_count || 0}
                    </div>
                  </div>
                </div>
              </div>

              {/* Individual Scenario Results List */}
              <div className="rounded-2xl bg-dark-card border border-dark-border overflow-hidden space-y-0">
                <div className="p-4 border-b border-dark-border bg-dark-bg/60 flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 font-mono">
                    Scenario Breakdown ({currentRun.scenario_results?.length || 0})
                  </h3>
                  <span className="text-[11px] text-slate-500 font-mono">Deterministic Evaluator Findings</span>
                </div>

                <div className="divide-y divide-dark-border">
                  {currentRun.scenario_results?.map((res) => (
                    <div key={res.id} className="p-4 space-y-3 hover:bg-dark-hover/20 transition-colors">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center gap-2.5">
                          {res.passed ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                          ) : (
                            <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                          )}
                          <span className="font-semibold text-sm text-slate-100">{res.scenario_name}</span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-dark-bg border border-dark-border text-slate-400">
                            {res.failure_type}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 text-xs font-mono">
                          <span className="text-slate-400">{res.duration_ms}ms</span>
                          <span className="text-slate-400">{res.retry_count} retries</span>
                          <StatusBadge status={res.status} />
                        </div>
                      </div>

                      {/* Evaluator assertions findings */}
                      <div className="grid grid-cols-1 gap-2 pt-1">
                        {res.findings.map((fnd) => (
                          <div
                            key={fnd.id}
                            className={`p-2.5 rounded-lg border text-xs flex items-start justify-between gap-3 ${
                              fnd.status === 'passed'
                                ? 'bg-emerald-950/15 border-emerald-900/40 text-emerald-300'
                                : 'bg-rose-950/20 border-rose-900/40 text-rose-300'
                            }`}
                          >
                            <div>
                              <div className="flex items-center gap-2 mb-0.5">
                                <span className="font-mono font-bold text-[10px]">{fnd.rule_id}</span>
                                <span className="text-slate-400">({fnd.rule_name})</span>
                              </div>
                              <p className="text-[11px] text-slate-300">{fnd.message}</p>
                              {fnd.explanation && (
                                <p className="text-[10px] text-slate-400 mt-0.5 italic">{fnd.explanation}</p>
                              )}
                            </div>

                            <span
                              className={`text-[10px] font-bold uppercase font-mono px-1.5 py-0.5 rounded ${
                                fnd.status === 'passed' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                              }`}
                            >
                              {fnd.status}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
