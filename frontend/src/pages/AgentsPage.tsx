import React, { useEffect, useState } from 'react';
import { Bot, Check, Shield, Wrench, Layers, Tag, Play, Clock, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { Agent, TestRun } from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { StatusBadge } from '../components/common/StatusBadge';

export const AgentsPage: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [loading, setLoading] = useState(true);

  const loadAgents = async () => {
    try {
      setLoading(true);
      const data = await api.getAgents();
      setAgents(data);
      if (data.length > 0) {
        setSelectedAgent(data[0]);
        const agentRuns = await api.getRuns(20);
        setRuns(agentRuns.filter((r) => r.agent_id === data[0].id));
      }
    } catch (err) {
      console.error('Failed to load agents', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAgents();
  }, []);

  if (loading) {
    return <LoadingSpinner message="Loading registered agent adapters..." />;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Agent Adapter Registry</h1>
        <p className="text-xs text-slate-400 mt-1">
          Registered agent execution adapters, version snapshots, recovery policies, and tool capability definitions.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Registered Agents List */}
        <div className="space-y-4">
          <h2 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">
            Registered Agents ({agents.length})
          </h2>

          <div className="space-y-3">
            {agents.map((agent) => {
              const isSelected = selectedAgent?.id === agent.id;
              return (
                <div
                  key={agent.id}
                  onClick={() => setSelectedAgent(agent)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-dark-card border-brand-500/50 shadow-md shadow-brand-500/10'
                      : 'bg-dark-card/60 border-dark-border hover:bg-dark-card hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-sky-950/80 border border-sky-800/60 flex items-center justify-center text-sky-400">
                        <Bot className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-white">{agent.name}</h3>
                        <p className="text-[11px] font-mono text-slate-400">{agent.id}</p>
                      </div>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      {agent.status}
                    </span>
                  </div>

                  <p className="text-xs text-slate-400 mt-3 line-clamp-2 leading-relaxed">
                    {agent.description}
                  </p>

                  <div className="mt-4 pt-3 border-t border-dark-border flex items-center justify-between text-[11px] text-slate-400 font-mono">
                    <span>Active Version:</span>
                    <span className="text-sky-400 font-semibold">{agent.current_version}</span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="p-4 rounded-xl bg-dark-bg/60 border border-dark-border/80 text-xs text-slate-400 space-y-2">
            <h4 className="font-semibold text-slate-300 flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-sky-400" />
              <span>Adapter Architecture</span>
            </h4>
            <p className="text-[11px] leading-relaxed">
              AgentGuard executes agents strictly inside controlled adapter boundaries. Third-party agents connect via
              deterministic tool invokers with automated fault interception and trace redaction.
            </p>
          </div>
        </div>

        {/* Right Column: Agent Details & Versions */}
        {selectedAgent && (
          <div className="lg:col-span-2 space-y-6">
            {/* Header Card */}
            <div className="p-6 rounded-2xl bg-dark-card border border-dark-border space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-white">{selectedAgent.name}</h2>
                    <span className="px-2 py-0.5 rounded-full text-xs font-mono bg-sky-950 text-sky-300 border border-sky-800">
                      {selectedAgent.agent_type}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{selectedAgent.description}</p>
                </div>
                <Link
                  to={`/execution?agent_id=${selectedAgent.id}`}
                  className="px-3.5 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold flex items-center gap-2 self-start sm:self-auto transition-all shadow-md shadow-brand-600/20"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Execute Test on Agent</span>
                </Link>
              </div>

              {/* Supported Tools List */}
              <div className="pt-4 border-t border-dark-border space-y-2">
                <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-1.5">
                  <Wrench className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Allowed Mock Tools</span>
                </h4>
                <div className="flex flex-wrap gap-2">
                  {selectedAgent.supported_tools.map((tool) => (
                    <span
                      key={tool}
                      className="px-2.5 py-1 rounded-lg text-xs font-mono bg-dark-bg border border-dark-border text-slate-300 flex items-center gap-1.5"
                    >
                      <Check className="w-3 h-3 text-emerald-400" />
                      <span>{tool}</span>
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Version Registry & Recovery Strategy Comparison */}
            <div className="p-6 rounded-2xl bg-dark-card border border-dark-border space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Layers className="w-4 h-4 text-brand-400" />
                  <span>Version Snapshots & Recovery Strategies</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Compare baseline vs candidate patch configurations and fault recovery policies.
                </p>
              </div>

              <div className="space-y-3">
                {selectedAgent.versions.map((ver) => (
                  <div
                    key={ver.id}
                    className={`p-4 rounded-xl border transition-all ${
                      ver.is_candidate
                        ? 'bg-sky-950/20 border-sky-800/60'
                        : 'bg-dark-bg/60 border-dark-border'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <Tag className="w-4 h-4 text-sky-400" />
                        <span className="font-mono text-sm font-bold text-white">{ver.version_tag}</span>
                        {ver.is_candidate ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-500/20 text-sky-300 border border-sky-500/40">
                            Candidate Fix
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-400 border border-slate-700">
                            Baseline
                          </span>
                        )}
                      </div>
                      <div className="text-xs font-mono text-slate-400">
                        Strategy: <span className="text-cyan-400 font-semibold">{ver.strategy}</span>
                      </div>
                    </div>

                    <p className="text-xs text-slate-400 mt-2">{ver.description}</p>

                    <div className="mt-3 bg-dark-card/90 p-2.5 rounded-lg border border-dark-border font-mono text-[11px] text-slate-300 overflow-x-auto">
                      <span className="text-slate-500">// Active Policy Config:</span>
                      <pre className="mt-1">{JSON.stringify(ver.config, null, 2)}</pre>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Agent Run History */}
            <div className="rounded-2xl bg-dark-card border border-dark-border overflow-hidden">
              <div className="p-4 border-b border-dark-border flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Clock className="w-4 h-4 text-amber-400" />
                  <span>Execution History for {selectedAgent.name}</span>
                </h3>
                <span className="text-xs text-slate-400">{runs.length} runs</span>
              </div>

              {runs.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500">
                  No runs executed on this agent yet. Launch a test scenario to begin.
                </div>
              ) : (
                <div className="divide-y divide-dark-border">
                  {runs.map((r) => (
                    <div key={r.id} className="p-4 flex items-center justify-between hover:bg-dark-hover/30 transition-colors">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <Link to={`/runs/${r.id}`} className="font-mono text-xs font-semibold text-white hover:text-brand-400">
                            {r.id}
                          </Link>
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 font-mono text-sky-400">
                            {r.agent_version}
                          </span>
                          <StatusBadge status={r.status} />
                        </div>
                        <p className="text-xs text-slate-400">{r.name}</p>
                      </div>

                      <div className="flex items-center gap-4 text-xs font-mono">
                        <div>
                          <span className="text-emerald-400 font-semibold">{r.passed_scenarios}</span>
                          <span className="text-slate-500"> / {r.total_scenarios} passed</span>
                        </div>
                        <Link
                          to={`/runs/${r.id}`}
                          className="p-1.5 rounded bg-dark-bg border border-dark-border hover:bg-dark-card text-slate-300"
                        >
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
