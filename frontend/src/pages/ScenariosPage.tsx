import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FlaskConical,
  Search,
  Filter,
  Plus,
  Download,
  Upload,
  Copy,
  Trash2,
  Play,
  CheckCircle2,
  XCircle,
  Eye,
  Sliders,
  AlertTriangle
} from 'lucide-react';
import { api } from '../api/client';
import { Scenario } from '../types';
import { SeverityBadge } from '../components/common/SeverityBadge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const ScenariosPage: React.FC = () => {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [failureTypeFilter, setFailureTypeFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');

  // Selected scenario for detail view
  const [inspectScenario, setInspectScenario] = useState<Scenario | null>(null);

  // Modal for Create/Edit
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newScenario, setNewScenario] = useState<Partial<Scenario>>({
    name: '',
    description: '',
    category: 'ticketing',
    failure_type: 'transient_timeout',
    severity: 'medium',
    is_enabled: true,
    task_input: { action: 'create_ticket', title: 'Example Ticket', priority: 'medium' },
    expected_outcome: { status: 'success', max_tickets_created: 1 },
    fault_parameters: { fault_type: 'transient_timeout', max_fault_count: 1 },
    allowed_tools: ['ticket_create', 'ticket_query', 'ticket_get'],
    policy_constraints: { max_retries: 3 }
  });

  const navigate = useNavigate();

  const loadScenarios = async () => {
    try {
      setLoading(true);
      const data = await api.getScenarios({
        search: search || undefined,
        failure_type: failureTypeFilter || undefined,
        severity: severityFilter || undefined
      });
      setScenarios(data);
    } catch (err) {
      console.error('Failed to load scenarios', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadScenarios();
  }, [search, failureTypeFilter, severityFilter]);

  const handleDuplicate = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const dup = await api.duplicateScenario(id);
      loadScenarios();
    } catch (err: any) {
      alert(`Duplication failed: ${err.message}`);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete scenario ${id}?`)) return;
    try {
      await api.deleteScenario(id);
      if (inspectScenario?.id === id) setInspectScenario(null);
      loadScenarios();
    } catch (err: any) {
      alert(`Deletion failed: ${err.message}`);
    }
  };

  const handleExport = async () => {
    try {
      const data = await api.exportScenarios();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `agentguard-scenarios-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      if (!text.trim()) {
        alert('Import failed: The selected JSON file is empty.');
        return;
      }

      let parsed: any;
      try {
        parsed = JSON.parse(text);
      } catch (jsonErr: any) {
        alert(`Import failed: Malformed JSON file (${jsonErr.message})`);
        return;
      }

      // Format normalization: single scenario, scenario array, or export bundle
      let payloadToSend: any = parsed;
      if (Array.isArray(parsed)) {
        if (parsed.length === 0) {
          alert('Import failed: JSON file contains an empty array of scenarios.');
          return;
        }
        payloadToSend = parsed;
      } else if (parsed && typeof parsed === 'object') {
        if (Array.isArray(parsed.scenarios)) {
          if (parsed.scenarios.length === 0) {
            alert('Import failed: Export bundle contains 0 scenarios.');
            return;
          }
          payloadToSend = parsed;
        } else if (parsed.name || parsed.failure_type || parsed.id) {
          // Single scenario object
          payloadToSend = parsed;
        } else {
          alert('Import failed: Unsupported JSON format. Expected a scenario object, an array of scenarios, or an export bundle with a "scenarios" list.');
          return;
        }
      } else {
        alert('Import failed: Invalid JSON structure. Expected an object or array.');
        return;
      }

      const res = await api.importScenarios(payloadToSend);
      if (res.imported_count > 0) {
        alert(`Successfully imported ${res.imported_count} scenario${res.imported_count === 1 ? '' : 's'}!`);
        await loadScenarios();
      } else {
        alert('Import completed, but 0 scenarios were saved.');
      }
    } catch (err: any) {
      alert(`Import failed: ${err.message}`);
    } finally {
      if (e.target) {
        e.target.value = '';
      }
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newScenario.name) return;
    try {
      await api.createScenario(newScenario);
      setShowCreateModal(false);
      loadScenarios();
    } catch (err: any) {
      alert(`Failed to create scenario: ${err.message}`);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Test Scenarios Library</h1>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic evaluation scenarios, fault injection matrices, and safety assertions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="px-3 py-2 rounded-lg bg-dark-card border border-dark-border hover:bg-dark-hover text-slate-300 text-xs font-semibold flex items-center gap-2 cursor-pointer transition-all">
            <Upload className="w-3.5 h-3.5" />
            <span>Import JSON</span>
            <input type="file" accept=".json" onChange={handleImport} className="hidden" />
          </label>

          <button
            onClick={handleExport}
            className="px-3 py-2 rounded-lg bg-dark-card border border-dark-border hover:bg-dark-hover text-slate-300 text-xs font-semibold flex items-center gap-2 transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export</span>
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="px-3.5 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold flex items-center gap-2 transition-all shadow-md shadow-brand-600/20"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Scenario</span>
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="p-4 rounded-xl bg-dark-card border border-dark-border flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-slate-500 ml-1" />
          <input
            type="text"
            placeholder="Search scenario name, description, or fault type..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-transparent border-0 focus:outline-none text-xs text-slate-200 placeholder:text-slate-500 w-full"
          />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
            <Filter className="w-3.5 h-3.5 text-emerald-400" />
            <span>Fault Category:</span>
            <select
              value={failureTypeFilter}
              onChange={(e) => setFailureTypeFilter(e.target.value)}
              className="bg-dark-bg border border-dark-border text-slate-200 rounded px-2.5 py-1 text-xs focus:outline-none"
            >
              <option value="">All Categories</option>
              <option value="normal_execution">Normal Execution</option>
              <option value="transient_timeout">Transient Timeout</option>
              <option value="ambiguous_outcome">Ambiguous Outcome</option>
              <option value="repeated_action">Repeated Action</option>
              <option value="malformed_output">Malformed Output</option>
              <option value="prompt_injection">Prompt Injection</option>
              <option value="policy_violation">Policy Violation</option>
            </select>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
            <span>Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-dark-bg border border-dark-border text-slate-200 rounded px-2.5 py-1 text-xs focus:outline-none"
            >
              <option value="">All Severities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Grid: Scenarios Cards */}
      {loading ? (
        <LoadingSpinner message="Filtering test scenarios..." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {scenarios.map((scen) => (
            <div
              key={scen.id}
              onClick={() => setInspectScenario(scen)}
              className="p-5 rounded-2xl bg-dark-card border border-dark-border hover:border-slate-700 hover:bg-dark-card/90 transition-all cursor-pointer flex flex-col justify-between group shadow-sm"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <span className="font-mono text-[11px] text-emerald-400 font-semibold bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
                    {scen.id}
                  </span>
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={scen.severity} />
                    {scen.is_seeded && (
                      <span className="text-[10px] font-mono text-slate-500 bg-slate-800/80 px-1.5 py-0.5 rounded">
                        Seed
                      </span>
                    )}
                  </div>
                </div>

                <h3 className="text-sm font-semibold text-white group-hover:text-brand-400 transition-colors line-clamp-1">
                  {scen.name}
                </h3>

                <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                  {scen.description}
                </p>

                <div className="pt-2 flex flex-wrap gap-1.5">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-dark-bg border border-dark-border text-slate-300">
                    Fault: {scen.failure_type}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-dark-bg border border-dark-border text-slate-300">
                    Tools: {scen.allowed_tools.length}
                  </span>
                </div>
              </div>

              <div className="mt-5 pt-3.5 border-t border-dark-border flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 text-slate-500">
                  <button
                    onClick={(e) => handleDuplicate(scen.id, e)}
                    className="p-1.5 rounded hover:bg-dark-bg hover:text-slate-200 transition-colors"
                    title="Duplicate scenario"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={(e) => handleDelete(scen.id, e)}
                    className="p-1.5 rounded hover:bg-dark-bg hover:text-rose-400 transition-colors"
                    title="Delete scenario"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/execution?scenario_id=${scen.id}`);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-brand-600/20 hover:bg-brand-600 text-brand-300 hover:text-white border border-brand-500/30 text-xs font-semibold flex items-center gap-1.5 transition-all"
                >
                  <Play className="w-3 h-3 fill-current" />
                  <span>Execute</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Scenario Detail / Inspector Modal */}
      {inspectScenario && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-dark-card border border-dark-border rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6 space-y-6 shadow-2xl">
            <div className="flex items-start justify-between border-b border-dark-border pb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs text-emerald-400 font-semibold">{inspectScenario.id}</span>
                  <SeverityBadge severity={inspectScenario.severity} />
                  <span className="text-xs font-mono text-slate-400">v{inspectScenario.version}</span>
                </div>
                <h2 className="text-base font-bold text-white">{inspectScenario.name}</h2>
              </div>
              <button
                onClick={() => setInspectScenario(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                &times;
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <h4 className="font-semibold text-slate-300 mb-1">Description</h4>
                <p className="text-slate-400 leading-relaxed">{inspectScenario.description}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 rounded-lg bg-dark-bg border border-dark-border space-y-1">
                  <span className="text-slate-500 font-mono">Fault Injection Category</span>
                  <div className="font-semibold text-teal-400 font-mono">{inspectScenario.failure_type}</div>
                </div>
                <div className="p-3 rounded-lg bg-dark-bg border border-dark-border space-y-1">
                  <span className="text-slate-500 font-mono">Execution Limits</span>
                  <div className="font-semibold text-slate-200 font-mono">
                    Max Steps: {inspectScenario.execution_limits?.max_steps || 10}
                  </div>
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-slate-300 mb-1 font-mono">Task Input Payload</h4>
                <pre className="p-3 rounded-lg bg-dark-bg border border-dark-border font-mono text-[11px] text-slate-300 overflow-x-auto">
                  {JSON.stringify(inspectScenario.task_input, null, 2)}
                </pre>
              </div>

              <div>
                <h4 className="font-semibold text-slate-300 mb-1 font-mono">Fault Parameters</h4>
                <pre className="p-3 rounded-lg bg-dark-bg border border-dark-border font-mono text-[11px] text-teal-300 overflow-x-auto">
                  {JSON.stringify(inspectScenario.fault_parameters, null, 2)}
                </pre>
              </div>

              <div>
                <h4 className="font-semibold text-slate-300 mb-1 font-mono">Expected Outcome & Assertions</h4>
                <div className="p-3 rounded-lg bg-dark-bg border border-dark-border space-y-2">
                  <pre className="font-mono text-[11px] text-emerald-400">
                    {JSON.stringify(inspectScenario.expected_outcome, null, 2)}
                  </pre>
                  <div className="flex flex-wrap gap-1.5 pt-2 border-t border-dark-border/60">
                    {inspectScenario.expected_assertions.map((a) => (
                      <span key={a} className="px-2 py-0.5 rounded text-[10px] font-mono bg-dark-card text-slate-300 border border-slate-700">
                        {a}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-dark-border flex items-center justify-between">
              <button
                onClick={() => setInspectScenario(null)}
                className="px-4 py-2 rounded-lg bg-dark-bg hover:bg-dark-hover border border-dark-border text-slate-300 text-xs font-medium"
              >
                Close
              </button>

              <button
                onClick={() => {
                  navigate(`/execution?scenario_id=${inspectScenario.id}`);
                }}
                className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold flex items-center gap-2 shadow-md shadow-brand-600/20"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Execute This Scenario</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Scenario Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form
            onSubmit={handleCreateSubmit}
            className="bg-dark-card border border-dark-border rounded-2xl max-w-xl w-full max-h-[85vh] overflow-y-auto p-6 space-y-5 shadow-2xl text-xs"
          >
            <div className="border-b border-dark-border pb-3 flex items-center justify-between">
              <h3 className="text-base font-bold text-white">Create Test Scenario</h3>
              <button type="button" onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-white">
                &times;
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Scenario Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Gateway Timeout on Ticket Submission"
                  value={newScenario.name}
                  onChange={(e) => setNewScenario({ ...newScenario, name: e.target.value })}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Description</label>
                <textarea
                  rows={2}
                  placeholder="Detailed explanation of the test conditions..."
                  value={newScenario.description}
                  onChange={(e) => setNewScenario({ ...newScenario, description: e.target.value })}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-brand-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Fault Type</label>
                  <select
                    value={newScenario.failure_type}
                    onChange={(e) => setNewScenario({ ...newScenario, failure_type: e.target.value })}
                    className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-100 focus:outline-none"
                  >
                    <option value="normal_execution">Normal Execution</option>
                    <option value="transient_timeout">Transient Timeout</option>
                    <option value="ambiguous_outcome">Ambiguous Outcome</option>
                    <option value="repeated_action">Repeated Action</option>
                    <option value="malformed_output">Malformed Output</option>
                    <option value="prompt_injection">Prompt Injection</option>
                    <option value="policy_violation">Policy Violation</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Severity</label>
                  <select
                    value={newScenario.severity}
                    onChange={(e) => setNewScenario({ ...newScenario, severity: e.target.value as any })}
                    className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-100 focus:outline-none"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1 font-mono">Task Input JSON</label>
                <textarea
                  rows={3}
                  value={JSON.stringify(newScenario.task_input, null, 2)}
                  onChange={(e) => {
                    try {
                      setNewScenario({ ...newScenario, task_input: JSON.parse(e.target.value) });
                    } catch (_) {}
                  }}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg p-2.5 font-mono text-[11px] text-slate-200 focus:outline-none font-mono"
                />
              </div>
            </div>

            <div className="pt-4 border-t border-dark-border flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 rounded-lg bg-dark-bg hover:bg-dark-hover border border-dark-border text-slate-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white font-semibold shadow-md shadow-brand-600/20"
              >
                Save Scenario
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
