import React, { useEffect, useState } from 'react';
import {
  Bot,
  Check,
  Shield,
  Wrench,
  Layers,
  ArrowRight,
  Plus,
  Radio,
  Server,
  Code,
  AlertCircle,
  CheckCircle2,
  X,
  Power,
  Link2,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  FileText,
  Terminal,
  Info,
  Cpu,
  Sparkles,
  Workflow,
  FileCode
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import {
  Agent,
  TestRun,
  CustomAgentRegisterPayload,
  ExistingAgentConnectRequest,
  ValidateConfigResponse,
  TestConnectionResponse,
  ObservabilityLevel,
  Scenario,
  FrameworkCatalogItem
} from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { StatusBadge } from '../components/common/StatusBadge';


const ALL_CAPABILITIES = [
  { id: 'ticket_create', label: 'Ticket Creation', desc: 'Can invoke ticket creation mock tool' },
  { id: 'ticket_query', label: 'Ticket Query', desc: 'Can search and query existing tickets' },
  { id: 'ticket_get', label: 'Ticket Get', desc: 'Can retrieve ticket details by ID' },
  { id: 'state_inspection', label: 'State Inspection', desc: 'Inspects state before retrying on ambiguous outcome' },
  { id: 'handle_structured_errors', label: 'Structured Error Recovery', desc: 'Recovers gracefully from timeouts and 5xx errors' },
  { id: 'untrusted_text_handling', label: 'Prompt Injection Defense', desc: 'Safely sanitizes untrusted tool outputs' },
  { id: 'policy_compliance', label: 'Policy Guardrails', desc: 'Enforces tool access policy authorization' },
];

export const AgentsPage: React.FC = () => {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [frameworkCatalog, setFrameworkCatalog] = useState<FrameworkCatalogItem[]>([]);

  // Universal Agent Connection Wizard State
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [wizardStep, setWizardStep] = useState<number>(1);
  const [connType, setConnType] = useState<'python' | 'http' | 'framework' | 'model_backed' | 'contract'>('http');
  const [connId, setConnId] = useState('');
  const [connName, setConnName] = useState('');
  const [connDesc, setConnDesc] = useState('');
  const [connVersion, setConnVersion] = useState('1.0.0');
  const [connObsLevel, setConnObsLevel] = useState<ObservabilityLevel>('level_3_instrumented_tools');
  const [connCaps, setConnCaps] = useState<string[]>([
    'ticket_create',
    'ticket_query',
    'ticket_get',
    'state_inspection',
    'handle_structured_errors'
  ]);

  // 1. Python connection state
  const [connPythonMode, setConnPythonMode] = useState<'sdk_wrapper' | 'trusted_class'>('sdk_wrapper');
  const [connSdkTarget, setConnSdkTarget] = useState('existing_ticket_solver');
  const [connSdkInputParam, setConnSdkInputParam] = useState('prompt');

  // 2. HTTP connection state
  const [connHttpBaseUrl, setConnHttpBaseUrl] = useState('http://127.0.0.1:8080');
  const [connHttpInvocationEndpoint, setConnHttpInvocationEndpoint] = useState('/run');
  const [connHttpHealthEndpoint, setConnHttpHealthEndpoint] = useState('/health');
  const [connHttpSecretEnv, setConnHttpSecretEnv] = useState('');
  const [connHttpAuthType, setConnHttpAuthType] = useState('Bearer');
  const [connHttpAuthHeader, setConnHttpAuthHeader] = useState('Authorization');
  const [connHttpConnectTimeout, setConnHttpConnectTimeout] = useState('5.0');
  const [connHttpReadTimeout, setConnHttpReadTimeout] = useState('15.0');
  const [connHttpRequestMap, setConnHttpRequestMap] = useState('{\n  "query": "prompt",\n  "session_id": "run_id"\n}');
  const [connHttpResponseMap, setConnHttpResponseMap] = useState('{\n  "result_path": "output",\n  "status_path": "status"\n}');
  const [showAdvancedHttp, setShowAdvancedHttp] = useState(false);

  // 3. Framework connection state
  const [connFramework, setConnFramework] = useState('langgraph');
  const [connGraphTarget, setConnGraphTarget] = useState('customer_support_graph');

  // 4. Model-Backed agent state
  const [connLlmModel, setConnLlmModel] = useState('gpt-4o-mini');
  const [connLlmBaseUrl, setConnLlmBaseUrl] = useState('https://api.openai.com/v1');
  const [connLlmSecretEnv, setConnLlmSecretEnv] = useState('OPENAI_API_KEY');
  const [connLlmMaxCalls, setConnLlmMaxCalls] = useState('5');
  const [connLlmMaxTools, setConnLlmMaxTools] = useState('5');
  const [connLlmTemp, setConnLlmTemp] = useState('0.0');
  const [connLlmPrompt, setConnLlmPrompt] = useState('You are an AI support agent. Inspect existing tickets and use create_ticket with idempotency keys.');

  // Step 3 & 4 Validation and Handshake State
  const [isConnectValidating, setIsConnectValidating] = useState(false);
  const [connectValidationResult, setConnectValidationResult] = useState<ValidateConfigResponse | null>(null);
  const [isTestingHandshake, setIsTestingHandshake] = useState(false);
  const [handshakeResult, setHandshakeResult] = useState<TestConnectionResponse | null>(null);
  const [selectedCompatScenarioId, setSelectedCompatScenarioId] = useState<string>('');
  const [isConnectSubmitting, setIsConnectSubmitting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [connectedAgentSuccess, setConnectedAgentSuccess] = useState<Agent | null>(null);

  // Register Custom Agent Modal State (Legacy)
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [regId, setRegId] = useState('');
  const [regName, setRegName] = useState('');
  const [regDesc, setRegDesc] = useState('');
  const [regAdapterType, setRegAdapterType] = useState<'python' | 'http'>('python');
  const [regVersion, setRegVersion] = useState('1.0.0');
  const [regStrategy, setRegStrategy] = useState('baseline');
  const [regCaps, setRegCaps] = useState<string[]>([
    'ticket_create',
    'ticket_query',
    'ticket_get',
    'state_inspection',
    'handle_structured_errors'
  ]);
  const [regPythonClass, setRegPythonClass] = useState('CustomTestAgent');
  const [regHttpUrl, setRegHttpUrl] = useState('http://127.0.0.1:8080');
  const [regHttpConnectTimeout, setRegHttpConnectTimeout] = useState('5.0');
  const [regHttpReadTimeout, setRegHttpReadTimeout] = useState('15.0');
  const [regHttpSecretEnv, setRegHttpSecretEnv] = useState('');

  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidateConfigResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [registerError, setRegisterError] = useState<string | null>(null);

  // Live Connection Test State on details card
  const [isTestingConn, setIsTestingConn] = useState(false);
  const [connTestResult, setConnTestResult] = useState<TestConnectionResponse | null>(null);

  const loadAgents = async () => {
    try {
      setLoading(true);
      const [agentList, scenarioList, fwCatalog] = await Promise.all([
        api.getAgents(),
        api.getScenarios(),
        api.getFrameworkCatalog().catch(() => [])
      ]);
      setAgents(agentList);
      setScenarios(scenarioList);
      setFrameworkCatalog(fwCatalog);
      if (scenarioList.length > 0 && !selectedCompatScenarioId) {
        setSelectedCompatScenarioId(scenarioList[0].id);
      }
      if (agentList.length > 0) {
        const current = selectedAgent ? agentList.find((a) => a.id === selectedAgent.id) || agentList[0] : agentList[0];
        setSelectedAgent(current);
        const agentRuns = await api.getRuns(20);
        setRuns(agentRuns.filter((r) => r.agent_id === current.id));
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

  const handleSelectAgent = async (ag: Agent) => {
    setSelectedAgent(ag);
    setConnTestResult(null);
    try {
      const agentRuns = await api.getAgentRuns(ag.id);
      setRuns(agentRuns);
    } catch (err) {
      console.error('Failed to load agent runs', err);
    }
  };

  const handleToggleCapability = (capId: string, isConnect: boolean = false) => {
    if (isConnect) {
      setConnCaps((prev) =>
        prev.includes(capId) ? prev.filter((c) => c !== capId) : [...prev, capId]
      );
    } else {
      setRegCaps((prev) =>
        prev.includes(capId) ? prev.filter((c) => c !== capId) : [...prev, capId]
      );
    }
  };

  // Connect Existing Agent Handler
  const handleConnectExisting = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!connId.trim() || !connName.trim()) {
      setConnectError('Agent Identifier and Name are required.');
      return;
    }

    try {
      setIsConnectSubmitting(true);
      setConnectError(null);

      let parsedReqMap: any = {};
      let parsedRespMap: any = {};
      if (connType === 'http' && connHttpRequestMap.trim()) {
        try {
          parsedReqMap = JSON.parse(connHttpRequestMap);
        } catch (_) {
          throw new Error('Request mapping must be valid JSON.');
        }
      }
      if (connType === 'http' && connHttpResponseMap.trim()) {
        try {
          parsedRespMap = JSON.parse(connHttpResponseMap);
        } catch (_) {
          throw new Error('Response mapping must be valid JSON.');
        }
      }

      let connection_method: 'http_endpoint' | 'python_sdk_wrapper' | 'agent_framework' | 'model_backed' = 'http_endpoint';
      if (connType === 'http') connection_method = 'http_endpoint';
      else if (connType === 'python') connection_method = 'python_sdk_wrapper';
      else if (connType === 'framework') connection_method = 'agent_framework';
      else if (connType === 'model_backed') connection_method = 'model_backed';

      const payload: ExistingAgentConnectRequest = {
        id: connId.trim(),
        name: connName.trim(),
        description: connDesc.trim() || undefined,
        connection_method,
        observability_level: connObsLevel,
        version: connVersion.trim() || '1.0.0',
        supported_tools: ['ticket_create', 'ticket_query', 'ticket_get'],
        declared_capabilities: connCaps,
        http_config: connType === 'http' ? {
          base_url: connHttpBaseUrl.trim(),
          health_endpoint: connHttpHealthEndpoint.trim() || undefined,
          invocation_endpoint: connHttpInvocationEndpoint.trim() || '/run',
          auth_type: connHttpAuthType,
          auth_header_name: connHttpAuthHeader.trim() || 'Authorization',
          secret_env_var: connHttpSecretEnv.trim() || undefined,
          connect_timeout_seconds: parseFloat(connHttpConnectTimeout) || 5.0,
          read_timeout_seconds: parseFloat(connHttpReadTimeout) || 15.0,
          allow_local_dev: true,
          observability_level: connObsLevel,
          request_mapping: parsedReqMap,
          response_mapping: parsedRespMap
        } : undefined,
        sdk_config: connType === 'python' ? {
          wrapper_type: 'callable',
          target_name: connSdkTarget,
          observability_level: connObsLevel,
          input_parameter_name: connSdkInputParam.trim() || 'prompt'
        } : undefined,
        framework_config: connType === 'framework' ? {
          framework: connFramework,
          graph_target: connGraphTarget,
          max_steps: 10
        } : undefined,
        llm_config: connType === 'model_backed' ? {
          provider: 'openai_compatible',
          model: connLlmModel.trim(),
          base_url: connLlmBaseUrl.trim(),
          secret_env_var: connLlmSecretEnv.trim() || 'OPENAI_API_KEY',
          max_model_calls: parseInt(connLlmMaxCalls) || 5,
          max_tool_calls: parseInt(connLlmMaxTools) || 5,
          temperature: parseFloat(connLlmTemp) || 0.0,
          system_prompt: connLlmPrompt.trim()
        } : undefined
      };

      const newAgent = await api.connectExistingAgent(payload);
      await loadAgents();
      setSelectedAgent(newAgent);
      setConnectedAgentSuccess(newAgent);
      setWizardStep(5);
    } catch (err: any) {
      setConnectError(err.message || 'Failed to connect existing agent');
    } finally {
      setIsConnectSubmitting(false);
    }
  };

  const handleValidateConnectConfig = async () => {
    try {
      setIsConnectValidating(true);
      setConnectError(null);
      let adapter_type = 'python_sdk_wrapper';
      const cfg: any = {
        observability_level: connObsLevel
      };

      if (connType === 'http') {
        adapter_type = 'http';
        cfg.base_url = connHttpBaseUrl.trim();
        cfg.invocation_endpoint = connHttpInvocationEndpoint.trim();
        cfg.allow_local_dev = true;
        if (connHttpRequestMap.trim()) {
          try { cfg.request_mapping = JSON.parse(connHttpRequestMap); } catch (e) { throw new Error('Request mapping must be valid JSON'); }
        }
        if (connHttpResponseMap.trim()) {
          try { cfg.response_mapping = JSON.parse(connHttpResponseMap); } catch (e) { throw new Error('Response mapping must be valid JSON'); }
        }
      } else if (connType === 'python') {
        adapter_type = connPythonMode === 'trusted_class' ? 'python' : 'python_sdk_wrapper';
        cfg.target_name = connSdkTarget;
      } else if (connType === 'framework') {
        adapter_type = 'langgraph';
        cfg.framework = connFramework;
        cfg.graph_target = connGraphTarget;
      } else if (connType === 'model_backed') {
        adapter_type = 'model_backed';
        cfg.provider = 'openai_compatible';
        cfg.model = connLlmModel.trim();
        cfg.base_url = connLlmBaseUrl.trim();
        cfg.secret_env_var = connLlmSecretEnv.trim();
        cfg.max_model_calls = parseInt(connLlmMaxCalls) || 5;
      }

      const res = await api.validateAgentConfig(adapter_type, cfg);
      setConnectValidationResult(res);
    } catch (err: any) {
      setConnectValidationResult({
        valid: false,
        error: err.message || 'Validation failed',
        adapter_type: connType,
        details: {}
      });
    } finally {
      setIsConnectValidating(false);
    }
  };

  const handleTestConnectHandshake = async () => {
    try {
      setIsTestingHandshake(true);
      setConnectError(null);
      let adapter_type = 'python_sdk_wrapper';
      const cfg: any = { observability_level: connObsLevel };

      if (connType === 'http') {
        adapter_type = 'http';
        cfg.base_url = connHttpBaseUrl.trim();
        cfg.invocation_endpoint = connHttpInvocationEndpoint.trim();
        cfg.health_endpoint = connHttpHealthEndpoint.trim();
        cfg.allow_local_dev = true;
      } else if (connType === 'python') {
        adapter_type = 'python_sdk_wrapper';
        cfg.target_name = connSdkTarget;
      } else if (connType === 'framework') {
        adapter_type = 'langgraph';
        cfg.graph_name = connGraphTarget;
      } else if (connType === 'model_backed') {
        adapter_type = 'model_backed';
        cfg.model = connLlmModel.trim();
        cfg.base_url = connLlmBaseUrl.trim();
        cfg.secret_env_var = connLlmSecretEnv.trim();
      }

      const res = await api.testAgentConnection(connId || 'probe-check', adapter_type, cfg);
      setHandshakeResult(res);
    } catch (err: any) {
      setHandshakeResult({
        status: 'error',
        message: err.message || 'Handshake failed',
        adapter_type: connType,
        declared_capabilities: connCaps,
        details: { error: String(err) }
      });
    } finally {
      setIsTestingHandshake(false);
    }
  };


  // Register Custom Agent Handler
  const handleValidateConfig = async () => {
    try {
      setIsValidating(true);
      setRegisterError(null);
      const cfg: any = {};
      if (regAdapterType === 'python') {
        cfg.class_name = regPythonClass;
      } else {
        cfg.base_url = regHttpUrl.trim();
        cfg.connect_timeout_seconds = parseFloat(regHttpConnectTimeout) || 5.0;
        cfg.read_timeout_seconds = parseFloat(regHttpReadTimeout) || 15.0;
        cfg.secret_env_var = regHttpSecretEnv.trim() || undefined;
        cfg.allow_local_dev = true;
      }

      const res = await api.validateAgentConfig(regAdapterType, cfg);
      setValidationResult(res);
    } catch (err: any) {
      setValidationResult({
        valid: false,
        error: err.message || 'Validation failed',
        adapter_type: regAdapterType,
        details: {}
      });
    } finally {
      setIsValidating(false);
    }
  };

  const handleRegisterAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regId.trim() || !regName.trim()) {
      setRegisterError('Agent Identifier and Name are required.');
      return;
    }

    try {
      setIsSubmitting(true);
      setRegisterError(null);

      const adapter_config: any = {};
      if (regAdapterType === 'python') {
        adapter_config.class_name = regPythonClass;
      } else {
        adapter_config.base_url = regHttpUrl.trim();
        adapter_config.connect_timeout_seconds = parseFloat(regHttpConnectTimeout) || 5.0;
        adapter_config.read_timeout_seconds = parseFloat(regHttpReadTimeout) || 15.0;
        adapter_config.secret_env_var = regHttpSecretEnv.trim() || undefined;
        adapter_config.allow_local_dev = true;
      }

      const payload: CustomAgentRegisterPayload = {
        id: regId.trim(),
        name: regName.trim(),
        description: regDesc.trim() || undefined,
        adapter_type: regAdapterType,
        version: regVersion.trim() || '1.0.0',
        strategy: regStrategy,
        supported_tools: ['ticket_create', 'ticket_query', 'ticket_get'],
        declared_capabilities: regCaps,
        adapter_config
      };

      const newAgent = await api.registerCustomAgent(payload);
      setShowRegisterModal(false);
      await loadAgents();
      setSelectedAgent(newAgent);
    } catch (err: any) {
      setRegisterError(err.message || 'Failed to register custom agent');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTestConnection = async () => {
    if (!selectedAgent) return;
    try {
      setIsTestingConn(true);
      setConnTestResult(null);
      const res = await api.testAgentConnection(
        selectedAgent.id,
        selectedAgent.adapter_type,
        selectedAgent.adapter_config
      );
      setConnTestResult(res);
    } catch (err: any) {
      setConnTestResult({
        status: 'error',
        message: err.message || 'Connection test failed',
        adapter_type: selectedAgent.adapter_type || 'python',
        declared_capabilities: selectedAgent.declared_capabilities || [],
        details: {}
      });
    } finally {
      setIsTestingConn(false);
    }
  };

  const handleToggleStatus = async () => {
    if (!selectedAgent) return;
    const newStatus = selectedAgent.status === 'active' ? 'disabled' : 'active';
    try {
      const updated = await api.updateAgent(selectedAgent.id, { status: newStatus });
      setSelectedAgent(updated);
      setAgents(agents.map((a) => (a.id === updated.id ? updated : a)));
    } catch (err) {
      console.error('Failed to toggle status', err);
    }
  };

  const renderObservabilityBadge = (level?: string) => {
    switch (level) {
      case 'level_1_result_only':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-blue-500/10 text-blue-400 border border-blue-500/30 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
            Level 1: Result-Only
          </span>
        );
      case 'level_2_structured_events':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-purple-500/10 text-purple-400 border border-purple-500/30 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
            Level 2: Structured-Events
          </span>
        );
      case 'level_3_instrumented_tools':
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            Level 3: Instrumented-Tools
          </span>
        );
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading registered agent adapters..." />;
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Agent Adapter Registry</h1>
          <p className="text-xs text-slate-400 mt-1">
            Connect existing AI agents or register custom Python and HTTP adapters for controlled reliability testing.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            id="btn-connect-existing-agent"
            onClick={() => {
              setConnectValidationResult(null);
              setConnectError(null);
              setShowConnectModal(true);
            }}
            className="px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold text-xs flex items-center gap-2 transition-all shadow-md shadow-brand-600/25"
          >
            <Link2 className="w-4 h-4" />
            <span>Connect Existing Agent</span>
          </button>
          <button
            id="btn-register-custom-agent"
            onClick={() => {
              setValidationResult(null);
              setRegisterError(null);
              setShowRegisterModal(true);
            }}
            className="px-4 py-2.5 rounded-xl bg-dark-card border border-dark-border hover:bg-dark-hover text-slate-200 font-semibold text-xs flex items-center gap-2 transition-all"
          >
            <Plus className="w-4 h-4 text-brand-400" />
            <span>Register Custom Agent</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Registered Agents List */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">
              Registered Agents ({agents.length})
            </h2>
          </div>

          <div className="space-y-3">
            {agents.map((agent) => {
              const isSelected = selectedAgent?.id === agent.id;
              const isHttp = agent.adapter_type === 'http';
              const isSdk = agent.adapter_type === 'python_sdk_wrapper';
              const isConnected = agent.registration_source === 'connected_existing';
              return (
                <div
                  key={agent.id}
                  onClick={() => handleSelectAgent(agent)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-dark-card border-brand-500/50 shadow-md shadow-brand-500/10'
                      : 'bg-dark-card/60 border-dark-border hover:bg-dark-card hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          isHttp
                            ? 'bg-amber-950/80 border border-amber-800/60 text-amber-400'
                            : isSdk
                            ? 'bg-purple-950/80 border border-purple-800/60 text-purple-400'
                            : 'bg-sky-950/80 border border-sky-800/60 text-sky-400'
                        }`}
                      >
                        {isHttp ? <Server className="w-5 h-5" /> : isSdk ? <Link2 className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-white">{agent.name}</h3>
                        <p className="text-[11px] font-mono text-slate-400">{agent.id}</p>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                          agent.status === 'active'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                        }`}
                      >
                        {agent.status}
                      </span>
                      <span
                        className={`px-1.5 py-0.2 rounded text-[9px] font-mono font-semibold uppercase ${
                          isConnected
                            ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                            : agent.registration_source === 'custom'
                            ? 'bg-indigo-950 text-indigo-300 border border-indigo-800'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {isConnected ? 'connected' : agent.registration_source || 'built_in'}
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-400 mt-3 line-clamp-2 leading-relaxed">
                    {agent.description}
                  </p>

                  <div className="mt-3 pt-2.5 border-t border-dark-border/80 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400 font-mono">
                    {renderObservabilityBadge(agent.observability_level)}
                    <span className="text-sky-400 font-semibold">{agent.current_version}</span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="p-4 rounded-xl bg-dark-bg/60 border border-dark-border/80 text-xs text-slate-400 space-y-2">
            <h4 className="font-semibold text-slate-300 flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-sky-400" />
              <span>Observability Levels</span>
            </h4>
            <div className="text-[11px] space-y-1.5 leading-relaxed">
              <p><strong className="text-blue-300">Level 1 (Result-Only):</strong> Evaluates final answer & prompt defense. Tool-level fault injection is not supported.</p>
              <p><strong className="text-purple-300">Level 2 (Structured-Events):</strong> External agent returns execution steps & timings for timeline inspection.</p>
              <p><strong className="text-emerald-300">Level 3 (Instrumented-Tools):</strong> Tool calls are intercepted by AgentGuard for controlled fault injection.</p>
            </div>
          </div>
        </div>

        {/* Right Column: Selected Agent Details, Test Tool & History */}
        {selectedAgent && (
          <div className="lg:col-span-2 space-y-6">
            {/* Header Card */}
            <div className="p-6 rounded-2xl bg-dark-card border border-dark-border space-y-4 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-lg font-bold text-white">{selectedAgent.name}</h2>
                    <span className="px-2 py-0.5 rounded-full text-xs font-mono bg-sky-950 text-sky-300 border border-sky-800">
                      {selectedAgent.adapter_type || 'python'} adapter
                    </span>
                    {renderObservabilityBadge(selectedAgent.observability_level)}
                  </div>
                  <p className="text-xs text-slate-400 font-mono mt-1">ID: {selectedAgent.id}</p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleToggleStatus}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                      selectedAgent.status === 'active'
                        ? 'bg-rose-950/40 text-rose-300 border border-rose-800/60 hover:bg-rose-900/60'
                        : 'bg-emerald-950/40 text-emerald-300 border border-emerald-800/60 hover:bg-emerald-900/60'
                    }`}
                  >
                    <Power className="w-3.5 h-3.5" />
                    <span>{selectedAgent.status === 'active' ? 'Disable Agent' : 'Enable Agent'}</span>
                  </button>

                  <button
                    onClick={handleTestConnection}
                    disabled={isTestingConn}
                    className="px-3.5 py-1.5 rounded-lg bg-dark-bg border border-dark-border hover:bg-slate-800 text-sky-300 text-xs font-semibold flex items-center gap-1.5 transition-all"
                  >
                    <Radio className="w-3.5 h-3.5 text-sky-400 animate-pulse" />
                    <span>{isTestingConn ? 'Testing...' : 'Test Connectivity'}</span>
                  </button>

                  <Link
                    to={`/runs/new?agent_id=${selectedAgent.id}&version=${selectedAgent.current_version}`}
                    className="px-3.5 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-all shadow-md shadow-brand-600/20"
                  >
                    <span>Launch Run</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                {selectedAgent.description || 'No description provided.'}
              </p>

              {/* Observability Level Info Banner */}
              <div className="p-3.5 rounded-xl bg-dark-bg border border-dark-border flex items-start gap-3">
                <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <div className="flex items-center gap-2 font-semibold text-white">
                    <span>Integration Observability Level:</span>
                    {renderObservabilityBadge(selectedAgent.observability_level)}
                  </div>
                  <p className="text-slate-400 text-[11px]">
                    {selectedAgent.observability_level === 'level_1_result_only'
                      ? 'This agent is connected via Result-Only observability. AgentGuard can test prompt injection resistance, input formatting, and final task success. Scenarios requiring intermediate tool fault injection will be marked unsupported.'
                      : selectedAgent.observability_level === 'level_2_structured_events'
                      ? 'This agent provides structured execution events (timings, intermediate steps, and tool names) for timeline inspection. Intermediate tool faults cannot be injected unless tools are delegated.'
                      : 'Full tool-level instrumentation active. Agent tool calls are intercepted by AgentGuard mock tools, exercising fault injection, duplicate detection, and policy enforcement.'}
                  </p>
                </div>
              </div>

              {/* Live Connectivity Test Result */}
              {connTestResult && (
                <div
                  className={`p-3.5 rounded-xl border text-xs flex items-start gap-2.5 transition-all ${
                    connTestResult.status === 'healthy'
                      ? 'bg-emerald-950/30 border-emerald-800/80 text-emerald-300'
                      : connTestResult.status === 'warning'
                      ? 'bg-amber-950/30 border-amber-800/80 text-amber-300'
                      : 'bg-rose-950/30 border-rose-800/80 text-rose-300'
                  }`}
                >
                  {connTestResult.status === 'healthy' ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                  )}
                  <div className="space-y-1 flex-1">
                    <p className="font-semibold">{connTestResult.message}</p>
                    {connTestResult.declared_capabilities?.length > 0 && (
                      <p className="text-[11px] font-mono opacity-80">
                        Capabilities verified: {connTestResult.declared_capabilities.join(', ')}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => setConnTestResult(null)}
                    className="text-slate-400 hover:text-slate-200"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}

              {/* Declared Capabilities */}
              <div className="pt-4 border-t border-dark-border space-y-2">
                <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-brand-400" />
                  <span>Declared Adapter Capabilities</span>
                </h4>
                <div className="flex flex-wrap gap-2">
                  {(selectedAgent.declared_capabilities || [
                    'ticket_create',
                    'ticket_query',
                    'ticket_get'
                  ]).map((cap) => (
                    <span
                      key={cap}
                      className="px-2.5 py-1 rounded-lg text-xs font-mono bg-dark-bg border border-brand-500/30 text-brand-300 flex items-center gap-1.5"
                    >
                      <Check className="w-3 h-3 text-brand-400" />
                      <span>{cap}</span>
                    </span>
                  ))}
                </div>
              </div>

              {/* Supported Tools List */}
              <div className="pt-3 border-t border-dark-border/60 space-y-2">
                <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-1.5">
                  <Wrench className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Approved Mock Tools</span>
                </h4>
                <div className="flex flex-wrap gap-2">
                  {(selectedAgent.supported_tools || ['ticket_create', 'ticket_query', 'ticket_get']).map((tool) => (
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

              {/* Adapter Configuration */}
              {selectedAgent.adapter_config && Object.keys(selectedAgent.adapter_config).length > 0 && (
                <div className="pt-3 border-t border-dark-border/60 space-y-2">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-1.5">
                    <Code className="w-3.5 h-3.5 text-amber-400" />
                    <span>Active Adapter Configuration</span>
                  </h4>
                  <pre className="p-3 rounded-xl bg-dark-bg border border-dark-border font-mono text-[11px] text-slate-300 overflow-x-auto">
                    {JSON.stringify(selectedAgent.adapter_config, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            {/* Version Registry & Recovery Strategy Comparison */}
            <div className="p-6 rounded-2xl bg-dark-card border border-dark-border space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Layers className="w-4 h-4 text-brand-400" />
                  <span>Version Snapshots & Recovery Strategies</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Snapshots of baseline vs candidate configurations and fault recovery policies.
                </p>
              </div>

              <div className="space-y-3">
                {selectedAgent.versions.map((ver) => (
                  <div
                    key={ver.id}
                    className="p-4 rounded-xl bg-dark-bg/60 border border-dark-border flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-white">v{ver.version_tag}</span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase ${
                            ver.strategy === 'safe_idempotent'
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                              : ver.strategy === 'bounded_backoff'
                              ? 'bg-blue-950 text-blue-300 border border-blue-800'
                              : ver.strategy === 'strict_policy'
                              ? 'bg-purple-950 text-purple-300 border border-purple-800'
                              : 'bg-slate-800 text-slate-300 border border-slate-700'
                          }`}
                        >
                          {ver.strategy}
                        </span>
                        {ver.is_candidate && (
                          <span className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-amber-950 text-amber-300 border border-amber-800 uppercase">
                            Candidate
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400">{ver.description || 'Config snapshot'}</p>
                    </div>

                    <Link
                      to={`/runs/new?agent_id=${selectedAgent.id}&version=${ver.version_tag}`}
                      className="px-3 py-1.5 rounded-lg bg-dark-card border border-dark-border hover:bg-dark-hover text-slate-300 text-xs font-semibold flex items-center gap-1.5 self-start sm:self-auto"
                    >
                      <span>Run Version</span>
                      <ArrowRight className="w-3 h-3 text-sky-400" />
                    </Link>
                  </div>
                ))}
              </div>
            </div>

            {/* Execution History */}
            <div className="p-6 rounded-2xl bg-dark-card border border-dark-border space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">Previous Execution Runs</h3>
                  <p className="text-xs text-slate-400">Chronological runs executed on this agent.</p>
                </div>
                <Link to={`/runs?agent_id=${selectedAgent.id}`} className="text-xs text-brand-400 hover:text-brand-300">
                  View All Runs
                </Link>
              </div>

              {runs.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-xs border border-dashed border-dark-border rounded-xl">
                  No execution runs recorded for this agent yet.
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
                            v{r.agent_version}
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

      {/* Universal Agent Connection Wizard Modal */}
      {showConnectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-4xl bg-dark-card border border-dark-border rounded-2xl p-6 space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-dark-border pb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-xl bg-brand-500/20 border border-brand-500/40 flex items-center justify-center text-brand-400">
                  <Sparkles className="w-5 h-5 text-brand-400" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Universal AI Agent Connection Wizard</h3>
                  <p className="text-xs text-slate-400">
                    Connect existing Python agents, HTTP microservices, Framework graphs, or Model-backed agents.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setConnType('contract')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                    connType === 'contract'
                      ? 'bg-sky-950 border border-sky-700 text-sky-300'
                      : 'bg-dark-bg border border-dark-border text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5 text-sky-400" />
                  <span>Integration Contract</span>
                </button>
                <button
                  onClick={() => {
                    setShowConnectModal(false);
                    setConnectedAgentSuccess(null);
                  }}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {connType === 'contract' ? (
              <div className="space-y-4 text-xs text-slate-300">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-white text-sm">Universal Integration Contract Specification</h4>
                  <button
                    onClick={() => setConnType('http')}
                    className="text-xs text-brand-400 hover:text-brand-300 font-semibold"
                  >
                    ← Back to Wizard
                  </button>
                </div>

                <div className="p-4 rounded-xl bg-dark-bg border border-dark-border space-y-4 font-mono text-[11px]">
                  <div>
                    <h5 className="font-sans font-bold text-sky-400 text-xs mb-1">Supported Connection Architecture:</h5>
                    <p className="text-slate-400 font-sans leading-relaxed">
                      All integrations map through AgentGuard's common lifecycle operations: 
                      <code className="text-amber-300"> validate_config</code>, <code className="text-amber-300">initialize</code>, <code className="text-amber-300">test_connection</code>, <code className="text-amber-300">run_task</code>, <code className="text-amber-300">cancel</code>, <code className="text-amber-300">dispose</code>.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-slate-300 font-sans">
                    <div className="p-3 rounded-lg bg-dark-card border border-dark-border space-y-1">
                      <p className="font-bold text-blue-300">1. Python Projects (A1 / A2)</p>
                      <p className="text-slate-400 text-[11px]">CallableAgentWrapper wraps existing Python functions or classes without modifying agent code.</p>
                    </div>
                    <div className="p-3 rounded-lg bg-dark-card border border-dark-border space-y-1">
                      <p className="font-bold text-amber-300">2. HTTP Microservices (B)</p>
                      <p className="text-slate-400 text-[11px]">REST endpoints with dot-notation path extraction, health checks, SSRF filtering, and token redaction.</p>
                    </div>
                    <div className="p-3 rounded-lg bg-dark-card border border-dark-border space-y-1">
                      <p className="font-bold text-purple-300">3. Agent Frameworks (C)</p>
                      <p className="text-slate-400 text-[11px]">LangGraph compiled StateGraphs supported with node-level event capture. CrewAI and AutoGen planned.</p>
                    </div>
                    <div className="p-3 rounded-lg bg-dark-card border border-dark-border space-y-1">
                      <p className="font-bold text-emerald-300">4. Model-Backed Agents (D)</p>
                      <p className="text-slate-400 text-[11px]">OpenAI-compatible models with tool calling routed through AgentGuard's controlled fault injector.</p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {/* 5-Step Wizard Progress Stepper */}
                <div className="flex items-center justify-between border-b border-dark-border/80 pb-3 text-xs">
                  {[
                    { step: 1, label: '1. Connection Type' },
                    { step: 2, label: '2. Configuration' },
                    { step: 3, label: '3. Validation & Handshake' },
                    { step: 4, label: '4. Scenario Compatibility' },
                    { step: 5, label: '5. Register & Launch' }
                  ].map((s) => (
                    <button
                      key={s.step}
                      type="button"
                      onClick={() => !connectedAgentSuccess && setWizardStep(s.step)}
                      disabled={!!connectedAgentSuccess}
                      className={`flex items-center gap-1.5 font-semibold transition-colors ${
                        wizardStep === s.step
                          ? 'text-brand-400'
                          : wizardStep > s.step
                          ? 'text-emerald-400'
                          : 'text-slate-500'
                      }`}
                    >
                      <span
                        className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                          wizardStep === s.step
                            ? 'bg-brand-500 text-white'
                            : wizardStep > s.step
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                            : 'bg-slate-800 text-slate-500'
                        }`}
                      >
                        {wizardStep > s.step ? '✓' : s.step}
                      </span>
                      <span className="hidden sm:inline">{s.label}</span>
                    </button>
                  ))}
                </div>

                {/* STEP 1: Choose Connection Type */}
                {wizardStep === 1 && (
                  <div className="space-y-4 animate-fadeIn">
                    <div className="space-y-1">
                      <h4 className="font-bold text-white text-sm">Step 1 — Choose Connection Architecture</h4>
                      <p className="text-xs text-slate-400">Select how your existing AI agent is packaged or hosted:</p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-1">
                      {/* Option 1: Existing Python Project */}
                      <div
                        onClick={() => {
                          setConnType('python');
                          setConnObsLevel('level_3_instrumented_tools');
                        }}
                        className={`p-4 rounded-xl border cursor-pointer transition-all space-y-2 ${
                          connType === 'python'
                            ? 'bg-purple-950/40 border-purple-500 shadow-md shadow-purple-500/10'
                            : 'bg-dark-bg/60 border-dark-border hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 text-purple-400 font-bold text-xs">
                            <Code className="w-4 h-4" />
                            <span>1. Existing Python Project</span>
                          </div>
                          <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-purple-950 text-purple-300 border border-purple-800">
                            SDK Wrapper
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">
                          Integrate standalone Python functions, LangChain chains, or custom classes using <strong className="text-white">CallableAgentWrapper</strong> with zero changes to agent source code.
                        </p>
                      </div>

                      {/* Option 2: HTTP/API Endpoint */}
                      <div
                        onClick={() => {
                          setConnType('http');
                          setConnObsLevel('level_1_result_only');
                        }}
                        className={`p-4 rounded-xl border cursor-pointer transition-all space-y-2 ${
                          connType === 'http'
                            ? 'bg-amber-950/40 border-amber-500 shadow-md shadow-amber-500/10'
                            : 'bg-dark-bg/60 border-dark-border hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 text-amber-400 font-bold text-xs">
                            <Server className="w-4 h-4" />
                            <span>2. HTTP / REST API Agent</span>
                          </div>
                          <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-amber-950 text-amber-300 border border-amber-800">
                            Microservice
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">
                          Connect any remote agent running over HTTP/REST. Configurable health checks, dot-notation JSON mappings, timeouts, and SSRF security defense.
                        </p>
                      </div>

                      {/* Option 3: Agent Framework */}
                      <div
                        onClick={() => {
                          setConnType('framework');
                          setConnObsLevel('level_3_instrumented_tools');
                        }}
                        className={`p-4 rounded-xl border cursor-pointer transition-all space-y-2 ${
                          connType === 'framework'
                            ? 'bg-sky-950/40 border-sky-500 shadow-md shadow-sky-500/10'
                            : 'bg-dark-bg/60 border-dark-border hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 text-sky-400 font-bold text-xs">
                            <Workflow className="w-4 h-4" />
                            <span>3. Agent Framework</span>
                          </div>
                          <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-sky-950 text-sky-300 border border-sky-800">
                            LangGraph v1.2+
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">
                          Execute compiled StateGraph workflows. Captures node transitions as structured timeline events with tool-call fault injection.
                        </p>
                      </div>

                      {/* Option 4: Model-Backed Agent */}
                      <div
                        onClick={() => {
                          setConnType('model_backed');
                          setConnObsLevel('level_3_instrumented_tools');
                        }}
                        className={`p-4 rounded-xl border cursor-pointer transition-all space-y-2 ${
                          connType === 'model_backed'
                            ? 'bg-emerald-950/40 border-emerald-500 shadow-md shadow-emerald-500/10'
                            : 'bg-dark-bg/60 border-dark-border hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs">
                            <Cpu className="w-4 h-4" />
                            <span>4. Model-Backed Agent</span>
                          </div>
                          <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-emerald-950 text-emerald-300 border border-emerald-800">
                            OpenAI API
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">
                          Orchestrate an OpenAI-compatible LLM with tool calling. Enforces an explicit tool allowlist and routes all tools through AgentGuard's Fault Injector.
                        </p>
                      </div>
                    </div>

                    <div className="pt-4 flex justify-end">
                      <button
                        type="button"
                        onClick={() => {
                          if (!connId) {
                            if (connType === 'python') setConnId('agent-python-ext');
                            else if (connType === 'http') setConnId('agent-http-ext');
                            else if (connType === 'framework') setConnId('agent-langgraph-ext');
                            else if (connType === 'model_backed') setConnId('agent-llm-ext');
                          }
                          if (!connName) {
                            if (connType === 'python') setConnName('Existing Python Ticket Agent');
                            else if (connType === 'http') setConnName('External Support Microservice');
                            else if (connType === 'framework') setConnName('Customer Support LangGraph Agent');
                            else if (connType === 'model_backed') setConnName('Support Assistant (GPT-4o-Mini)');
                          }
                          setWizardStep(2);
                        }}
                        className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold text-xs flex items-center gap-2 transition-all shadow-md shadow-brand-600/20"
                      >
                        <span>Continue to Configuration</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}

                {/* STEP 2: Configure Connection */}
                {wizardStep === 2 && (
                  <div className="space-y-4 animate-fadeIn text-xs">
                    <div className="space-y-1">
                      <h4 className="font-bold text-white text-sm">Step 2 — Configure Agent & Connection Details</h4>
                      <p className="text-slate-400">Specify agent identifiers and connection endpoints:</p>
                    </div>

                    {/* Identifiers */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div>
                        <label className="block text-slate-300 font-semibold mb-1">Agent Identifier *</label>
                        <input
                          type="text"
                          required
                          value={connId}
                          onChange={(e) => setConnId(e.target.value)}
                          className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-200 font-mono focus:outline-none focus:border-brand-500"
                        />
                      </div>
                      <div>
                        <label className="block text-slate-300 font-semibold mb-1">Display Name *</label>
                        <input
                          type="text"
                          required
                          value={connName}
                          onChange={(e) => setConnName(e.target.value)}
                          className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-brand-500"
                        />
                      </div>
                      <div>
                        <label className="block text-slate-300 font-semibold mb-1">Version</label>
                        <input
                          type="text"
                          value={connVersion}
                          onChange={(e) => setConnVersion(e.target.value)}
                          className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-200 font-mono focus:outline-none focus:border-brand-500"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-slate-300 font-semibold mb-1">Description</label>
                      <input
                        type="text"
                        value={connDesc}
                        onChange={(e) => setConnDesc(e.target.value)}
                        placeholder="Brief summary of agent function"
                        className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-brand-500"
                      />
                    </div>

                    {/* Observability Level Selection Cards */}
                    <div>
                      <label className="block text-slate-300 font-semibold mb-1.5 flex items-center justify-between">
                        <span>Execution Observability Level</span>
                        <span className="text-[10px] text-slate-400 font-normal">Controls how tests and traces observe the agent</span>
                      </label>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                        <div
                          onClick={() => setConnObsLevel('level_1_result_only')}
                          className={`p-3 rounded-xl border cursor-pointer transition-all ${
                            connObsLevel === 'level_1_result_only'
                              ? 'bg-blue-950/40 border-blue-500/80 shadow-md shadow-blue-500/10'
                              : 'bg-dark-bg/60 border-dark-border hover:border-slate-700'
                          }`}
                        >
                          <div className="flex items-center gap-1.5 text-blue-300 font-semibold text-xs">
                            <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                            <span>Level 1: Result-Only</span>
                          </div>
                          <p className="text-[10px] text-slate-400 mt-1 leading-relaxed">
                            Evaluates final outputs and prompt defense. Tool-level fault injection is not supported.
                          </p>
                        </div>

                        <div
                          onClick={() => setConnObsLevel('level_2_structured_events')}
                          className={`p-3 rounded-xl border cursor-pointer transition-all ${
                            connObsLevel === 'level_2_structured_events'
                              ? 'bg-purple-950/40 border-purple-500/80 shadow-md shadow-purple-500/10'
                              : 'bg-dark-bg/60 border-dark-border hover:border-slate-700'
                          }`}
                        >
                          <div className="flex items-center gap-1.5 text-purple-300 font-semibold text-xs">
                            <span className="w-2 h-2 rounded-full bg-purple-400"></span>
                            <span>Level 2: Structured-Events</span>
                          </div>
                          <p className="text-[10px] text-slate-400 mt-1 leading-relaxed">
                            External agent returns execution events, tool calls, and step timings in response payload.
                          </p>
                        </div>

                        <div
                          onClick={() => setConnObsLevel('level_3_instrumented_tools')}
                          className={`p-3 rounded-xl border cursor-pointer transition-all ${
                            connObsLevel === 'level_3_instrumented_tools'
                              ? 'bg-emerald-950/40 border-emerald-500/80 shadow-md shadow-emerald-500/10'
                              : 'bg-dark-bg/60 border-dark-border hover:border-slate-700'
                          }`}
                        >
                          <div className="flex items-center gap-1.5 text-emerald-300 font-semibold text-xs">
                            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                            <span>Level 3: Instrumented-Tools</span>
                          </div>
                          <p className="text-[10px] text-slate-400 mt-1 leading-relaxed">
                            Tool calls pass through AgentGuard. Enables full fault injection, duplicate detection, and policy checks.
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Specific Config: 1. Python */}
                    {connType === 'python' && (
                      <div className="p-4 rounded-xl bg-dark-bg border border-dark-border space-y-3">
                        <h5 className="font-semibold text-purple-400 flex items-center gap-1.5">
                          <Code className="w-4 h-4" />
                          <span>Python Project Adapter Settings</span>
                        </h5>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-slate-300 font-medium mb-1">Integration Mode</label>
                            <select
                              value={connPythonMode}
                              onChange={(e: any) => setConnPythonMode(e.target.value)}
                              className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-slate-200"
                            >
                              <option value="sdk_wrapper">Python SDK Wrapper (CallableAgentWrapper)</option>
                              <option value="trusted_class">Trusted AgentAdapter Class</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-slate-300 font-medium mb-1">Target Callable / Module</label>
                            <select
                              value={connSdkTarget}
                              onChange={(e) => setConnSdkTarget(e.target.value)}
                              className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-slate-200 font-mono"
                            >
                              <option value="existing_ticket_solver">existing_ticket_solver (Standalone function)</option>
                              <option value="ExistingCustomerSupportAgent">ExistingCustomerSupportAgent (Custom class)</option>
                              <option value="legacy_support_handler">legacy_support_handler</option>
                            </select>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Specific Config: 2. HTTP */}
                    {connType === 'http' && (
                      <div className="p-4 rounded-xl bg-dark-bg border border-dark-border space-y-3">
                        <h5 className="font-semibold text-amber-400 flex items-center gap-1.5">
                          <Server className="w-4 h-4" />
                          <span>HTTP Microservice Settings</span>
                        </h5>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                          <div className="sm:col-span-2">
                            <label className="block text-slate-300 font-medium mb-1">Base URL *</label>
                            <input
                              type="url"
                              required
                              value={connHttpBaseUrl}
                              onChange={(e) => setConnHttpBaseUrl(e.target.value)}
                              className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-slate-200 font-mono"
                            />
                          </div>
                          <div>
                            <label className="block text-slate-300 font-medium mb-1">Invocation Endpoint</label>
                            <input
                              type="text"
                              value={connHttpInvocationEndpoint}
                              onChange={(e) => setConnHttpInvocationEndpoint(e.target.value)}
                              className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-slate-200 font-mono"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-slate-300 font-medium mb-1">Health Endpoint</label>
                            <input
                              type="text"
                              value={connHttpHealthEndpoint}
                              onChange={(e) => setConnHttpHealthEndpoint(e.target.value)}
                              className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-slate-200 font-mono"
                            />
                          </div>
                          <div>
                            <label className="block text-slate-300 font-medium mb-1">Secret Env Var</label>
                            <input
                              type="text"
                              value={connHttpSecretEnv}
                              onChange={(e) => setConnHttpSecretEnv(e.target.value)}
                              placeholder="e.g. AGENT_API_KEY (never plain text)"
                              className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-slate-200 font-mono"
                            />
                          </div>
                        </div>

                        {/* Advanced HTTP Accordion */}
                        <div className="pt-2 border-t border-dark-border/80">
                          <button
                            type="button"
                            onClick={() => setShowAdvancedHttp(!showAdvancedHttp)}
                            className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 font-semibold"
                          >
                            {showAdvancedHttp ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                            <span>Advanced Payload Mappings & Timeouts</span>
                          </button>
                          {showAdvancedHttp && (
                            <div className="mt-2.5 space-y-2.5 pt-1">
                              <div className="grid grid-cols-2 gap-3">
                                <div>
                                  <label className="block text-slate-300 font-medium mb-1">Request Mapping (JSON)</label>
                                  <textarea
                                    rows={2}
                                    value={connHttpRequestMap}
                                    onChange={(e) => setConnHttpRequestMap(e.target.value)}
                                    className="w-full bg-dark-card border border-dark-border rounded p-1.5 font-mono text-[11px] text-slate-200"
                                  />
                                </div>
                                <div>
                                  <label className="block text-slate-300 font-medium mb-1">Response Mapping (JSON)</label>
                                  <textarea
                                    rows={2}
                                    value={connHttpResponseMap}
                                    onChange={(e) => setConnHttpResponseMap(e.target.value)}
                                    className="w-full bg-dark-card border border-dark-border rounded p-1.5 font-mono text-[11px] text-slate-200"
                                  />
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Specific Config: 3. Framework */}
                    {connType === 'framework' && (
                      <div className="p-4 rounded-xl bg-dark-bg border border-dark-border space-y-3">
                        <h5 className="font-semibold text-sky-400 flex items-center gap-1.5">
                          <Workflow className="w-4 h-4" />
                          <span>Agent Framework Settings</span>
                        </h5>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-slate-300 font-medium mb-1">Framework Integration</label>
                            <select
                              value={connFramework}
                              onChange={(e) => setConnFramework(e.target.value)}
                              className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-slate-200"
                            >
                              <option value="langgraph">LangGraph (Installed v1.2+ Supported)</option>
                              <option value="crewai" disabled>CrewAI (Planned Integration)</option>
                              <option value="autogen" disabled>Microsoft AutoGen (Planned Integration)</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-slate-300 font-medium mb-1">Compiled Graph Target</label>
                            <select
                              value={connGraphTarget}
                              onChange={(e) => setConnGraphTarget(e.target.value)}
                              className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-slate-200 font-mono"
                            >
                              <option value="customer_support_graph">customer_support_graph (StateGraph with 4 nodes)</option>
                              <option value="langgraph_ticket_graph">langgraph_ticket_graph</option>
                            </select>
                          </div>
                        </div>
                        <p className="text-[11px] text-slate-400">
                          StateGraph transitions are captured as timeline events. Node tool requests route to AgentGuard's Fault Injector.
                        </p>
                      </div>
                    )}

                    {/* Specific Config: 4. Model-Backed */}
                    {connType === 'model_backed' && (
                      <div className="p-4 rounded-xl bg-dark-bg border border-dark-border space-y-3">
                        <h5 className="font-semibold text-emerald-400 flex items-center gap-1.5">
                          <Cpu className="w-4 h-4" />
                          <span>OpenAI-Compatible Model Settings</span>
                        </h5>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                          <div>
                            <label className="block text-slate-300 font-medium mb-1">Model Identifier</label>
                            <input
                              type="text"
                              value={connLlmModel}
                              onChange={(e) => setConnLlmModel(e.target.value)}
                              placeholder="gpt-4o-mini"
                              className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-slate-200 font-mono"
                            />
                          </div>
                          <div>
                            <label className="block text-slate-300 font-medium mb-1">Base URL</label>
                            <input
                              type="url"
                              value={connLlmBaseUrl}
                              onChange={(e) => setConnLlmBaseUrl(e.target.value)}
                              className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-slate-200 font-mono"
                            />
                          </div>
                          <div>
                            <label className="block text-slate-300 font-medium mb-1">Secret Env Var</label>
                            <input
                              type="text"
                              value={connLlmSecretEnv}
                              onChange={(e) => setConnLlmSecretEnv(e.target.value)}
                              placeholder="OPENAI_API_KEY"
                              className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-slate-200 font-mono"
                            />
                          </div>
                        </div>
                        <div className="p-2.5 rounded bg-dark-card/80 border border-dark-border text-[11px] text-emerald-300">
                          <strong>Tool Call Safety Guarantee:</strong> All model tool calls are validated against an allowlist and routed through AgentGuard's Fault Injector. Secrets are scrubbed from traces.
                        </div>
                      </div>
                    )}

                    {/* Declared Capabilities Checklist */}
                    <div>
                      <label className="block text-slate-300 font-semibold mb-2">Supported Capabilities</label>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {ALL_CAPABILITIES.map((cap) => {
                          const isChecked = connCaps.includes(cap.id);
                          return (
                            <div
                              key={cap.id}
                              onClick={() => handleToggleCapability(cap.id, true)}
                              className={`p-2.5 rounded-lg border cursor-pointer transition-all flex items-start gap-2.5 ${
                                isChecked
                                  ? 'bg-brand-950/30 border-brand-500/50 text-white'
                                  : 'bg-dark-bg/60 border-dark-border text-slate-400 hover:border-slate-700'
                              }`}
                            >
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={() => {}}
                                className="mt-0.5 rounded border-slate-700 bg-dark-card text-brand-500"
                              />
                              <div>
                                <p className="font-semibold text-xs leading-none">{cap.label}</p>
                                <p className="text-[10px] text-slate-400 mt-1">{cap.desc}</p>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <div className="pt-3 flex items-center justify-between border-t border-dark-border">
                      <button
                        type="button"
                        onClick={() => setWizardStep(1)}
                        className="px-4 py-2 rounded-xl bg-dark-bg border border-dark-border text-slate-400 hover:text-white"
                      >
                        ← Back
                      </button>
                      <button
                        type="button"
                        onClick={() => setWizardStep(3)}
                        className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold flex items-center gap-2"
                      >
                        <span>Continue to Validation & Handshake</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}

                {/* STEP 3: Validate & Test Connection */}
                {wizardStep === 3 && (
                  <div className="space-y-4 animate-fadeIn text-xs">
                    <div className="space-y-1">
                      <h4 className="font-bold text-white text-sm">Step 3 — Validate Configuration & Test Handshake</h4>
                      <p className="text-slate-400">Run security checks, schema verification, and live connectivity probes:</p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* Sub-step A: Schema Validation */}
                      <div className="p-4 rounded-xl bg-dark-bg border border-dark-border space-y-3">
                        <div className="flex items-center justify-between">
                          <h5 className="font-semibold text-white flex items-center gap-1.5">
                            <Shield className="w-4 h-4 text-sky-400" />
                            <span>Configuration Schema Check</span>
                          </h5>
                          <button
                            type="button"
                            onClick={handleValidateConnectConfig}
                            disabled={isConnectValidating}
                            className="px-3 py-1.5 rounded-lg bg-sky-950/60 hover:bg-sky-900 border border-sky-800 text-sky-300 font-semibold text-[11px]"
                          >
                            {isConnectValidating ? 'Validating...' : 'Run Validation'}
                          </button>
                        </div>
                        <p className="text-[11px] text-slate-400">
                          Checks URL schemes, timeout boundaries, SSRF private IP rules, and payload mapping schemas.
                        </p>
                        {connectValidationResult && (
                          <div
                            className={`p-3 rounded-lg border text-xs flex items-start gap-2 ${
                              connectValidationResult.valid
                                ? 'bg-emerald-950/30 border-emerald-800 text-emerald-300'
                                : 'bg-rose-950/30 border-rose-800 text-rose-300'
                            }`}
                          >
                            {connectValidationResult.valid ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                            ) : (
                              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                            )}
                            <div>
                              <p className="font-semibold">
                                {connectValidationResult.valid ? 'Schema Valid' : 'Schema Invalid'}
                              </p>
                              <p className="text-[11px] mt-0.5">
                                {connectValidationResult.valid
                                  ? `Validated for ${connType} adapter (${connObsLevel}).`
                                  : connectValidationResult.error}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Sub-step B: Connectivity Handshake */}
                      <div className="p-4 rounded-xl bg-dark-bg border border-dark-border space-y-3">
                        <div className="flex items-center justify-between">
                          <h5 className="font-semibold text-white flex items-center gap-1.5">
                            <Radio className="w-4 h-4 text-emerald-400" />
                            <span>Live Connectivity Handshake</span>
                          </h5>
                          <button
                            type="button"
                            onClick={handleTestConnectHandshake}
                            disabled={isTestingHandshake}
                            className="px-3 py-1.5 rounded-lg bg-emerald-950/60 hover:bg-emerald-900 border border-emerald-800 text-emerald-300 font-semibold text-[11px]"
                          >
                            {isTestingHandshake ? 'Testing...' : 'Test Handshake'}
                          </button>
                        </div>
                        <p className="text-[11px] text-slate-400">
                          Initiates connection probe, verifies reachability, signature, and environment secret availability.
                        </p>
                        {handshakeResult && (
                          <div
                            className={`p-3 rounded-lg border text-xs flex items-start gap-2 ${
                              handshakeResult.status === 'healthy'
                                ? 'bg-emerald-950/30 border-emerald-800 text-emerald-300'
                                : handshakeResult.status === 'unconfigured'
                                ? 'bg-amber-950/30 border-amber-800 text-amber-300'
                                : 'bg-rose-950/30 border-rose-800 text-rose-300'
                            }`}
                          >
                            <div>
                              <p className="font-semibold uppercase tracking-wider text-[10px]">
                                Status: {handshakeResult.status}
                              </p>
                              <p className="text-[11px] mt-0.5">{handshakeResult.message}</p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="pt-3 flex items-center justify-between border-t border-dark-border">
                      <button
                        type="button"
                        onClick={() => setWizardStep(2)}
                        className="px-4 py-2 rounded-xl bg-dark-bg border border-dark-border text-slate-400 hover:text-white"
                      >
                        ← Back
                      </button>
                      <button
                        type="button"
                        onClick={() => setWizardStep(4)}
                        className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold flex items-center gap-2"
                      >
                        <span>Continue to Compatibility Check</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}

                {/* STEP 4: Test Compatibility */}
                {wizardStep === 4 && (
                  <div className="space-y-4 animate-fadeIn text-xs">
                    <div className="space-y-1">
                      <h4 className="font-bold text-white text-sm">Step 4 — Test Scenario Compatibility</h4>
                      <p className="text-slate-400">Pre-flight evaluation check before launching test runs:</p>
                    </div>

                    {/* Scenario Picker */}
                    <div className="p-4 rounded-xl bg-dark-bg border border-dark-border space-y-3">
                      <div>
                        <label className="block text-slate-300 font-semibold mb-1">Target Scenario to Evaluate</label>
                        <select
                          value={selectedCompatScenarioId}
                          onChange={(e) => setSelectedCompatScenarioId(e.target.value)}
                          className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-2 text-slate-200"
                        >
                          {scenarios.map((s) => (
                            <option key={s.id} value={s.id}>
                              [{s.failure_type}] {s.name} ({s.severity})
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Compatibility Evaluation Breakdown */}
                      {(() => {
                        const activeScen = scenarios.find((s) => s.id === selectedCompatScenarioId);
                        if (!activeScen) return null;

                        const reqCaps: string[] = activeScen.task_input?.required_capabilities || (activeScen as any).required_capabilities || [];
                        const missingCaps = reqCaps.filter((c) => !connCaps.includes(c));
                        const isToolFaultScen = ['ambiguous_outcome', 'transient_timeout', 'repeated_action', 'malformed_output', 'policy_violation'].includes(activeScen.failure_type);
                        const isLevel1Mismatched = isToolFaultScen && connObsLevel === 'level_1_result_only';

                        const isCompatible = missingCaps.length === 0 && !isLevel1Mismatched;

                        return (
                          <div className="p-3.5 rounded-lg bg-dark-card border border-dark-border space-y-3">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-slate-300">Compatibility Verdict:</span>
                              <span
                                className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                                  isCompatible
                                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                    : isLevel1Mismatched
                                    ? 'bg-amber-950 text-amber-300 border border-amber-800'
                                    : 'bg-rose-950 text-rose-300 border border-rose-800'
                                }`}
                              >
                                {isCompatible ? '100% Compatible' : isLevel1Mismatched ? 'Partially Observable' : 'Incompatible'}
                              </span>
                            </div>

                            <div className="space-y-1.5 text-[11px] leading-relaxed">
                              <p className="text-slate-300">
                                <strong>Tool Interception & Fault Injection: </strong>
                                {isToolFaultScen ? (
                                  connObsLevel === 'level_3_instrumented_tools' ? (
                                    <span className="text-emerald-400">Supported (Level 3 Instrumented Tools will apply '{activeScen.failure_type}').</span>
                                  ) : (
                                    <span className="text-amber-400">Blocked (Requires Level 3 Instrumented Tools, but agent provides {connObsLevel}).</span>
                                  )
                                ) : (
                                  <span className="text-blue-400">Non-tool scenario. Evaluated on output and policy compliance.</span>
                                )}
                              </p>

                              <p className="text-slate-300">
                                <strong>Missing Capabilities: </strong>
                                {missingCaps.length === 0 ? (
                                  <span className="text-emerald-400">None. All declared.</span>
                                ) : (
                                  <span className="text-rose-400 font-mono">{missingCaps.join(', ')}</span>
                                )}
                              </p>
                            </div>
                          </div>
                        );
                      })()}
                    </div>

                    <div className="pt-3 flex items-center justify-between border-t border-dark-border">
                      <button
                        type="button"
                        onClick={() => setWizardStep(3)}
                        className="px-4 py-2 rounded-xl bg-dark-bg border border-dark-border text-slate-400 hover:text-white"
                      >
                        ← Back
                      </button>
                      <button
                        type="button"
                        onClick={() => setWizardStep(5)}
                        className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold flex items-center gap-2"
                      >
                        <span>Continue to Register & Launch</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}

                {/* STEP 5: Register & Execute */}
                {wizardStep === 5 && (
                  <div className="space-y-4 animate-fadeIn text-xs">
                    <div className="space-y-1">
                      <h4 className="font-bold text-white text-sm">Step 5 — Complete Registration & Launch Run</h4>
                      <p className="text-slate-400">Review parameters and persist connection into AgentGuard:</p>
                    </div>

                    {connectedAgentSuccess ? (
                      <div className="p-5 rounded-2xl bg-emerald-950/30 border border-emerald-800 space-y-4 text-center">
                        <div className="w-12 h-12 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 mx-auto">
                          <CheckCircle2 className="w-6 h-6" />
                        </div>
                        <div>
                          <h4 className="text-sm font-bold text-white">Agent Connected Successfully!</h4>
                          <p className="text-slate-400 text-xs mt-1">
                            '{connectedAgentSuccess.name}' is now registered and ready for reliability testing.
                          </p>
                        </div>

                        <div className="flex items-center justify-center gap-3 pt-2">
                          <button
                            type="button"
                            onClick={() => {
                              setShowConnectModal(false);
                              setConnectedAgentSuccess(null);
                            }}
                            className="px-4 py-2 rounded-xl bg-dark-bg border border-dark-border text-slate-300 font-semibold text-xs"
                          >
                            Close Wizard
                          </button>
                          <Link
                            to={`/runs/new?agent_id=${connectedAgentSuccess.id}&scenario_id=${selectedCompatScenarioId}`}
                            className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold text-xs flex items-center gap-2 shadow-lg shadow-brand-600/30"
                          >
                            <span>Launch Test Run Now</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </Link>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <div className="p-4 rounded-xl bg-dark-bg border border-dark-border space-y-2">
                          <div className="grid grid-cols-2 gap-2 text-[11px]">
                            <div><span className="text-slate-400">Agent ID:</span> <span className="font-mono text-white">{connId}</span></div>
                            <div><span className="text-slate-400">Name:</span> <span className="text-white font-semibold">{connName}</span></div>
                            <div><span className="text-slate-400">Adapter Type:</span> <span className="font-mono text-sky-400">{connType}</span></div>
                            <div><span className="text-slate-400">Observability Level:</span> <span className="font-mono text-emerald-400">{connObsLevel}</span></div>
                          </div>
                        </div>

                        {connectError && (
                          <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
                            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                            <span>{connectError}</span>
                          </div>
                        )}

                        <div className="pt-3 flex items-center justify-between border-t border-dark-border">
                          <button
                            type="button"
                            onClick={() => setWizardStep(4)}
                            className="px-4 py-2 rounded-xl bg-dark-bg border border-dark-border text-slate-400 hover:text-white"
                          >
                            ← Back
                          </button>
                          <button
                            type="button"
                            onClick={() => handleConnectExisting()}
                            disabled={isConnectSubmitting}
                            className="px-6 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold flex items-center gap-2 shadow-md shadow-brand-600/20"
                          >
                            <Link2 className="w-4 h-4" />
                            <span>{isConnectSubmitting ? 'Registering...' : 'Register Agent'}</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}


      {/* Modal 2: Register Custom Agent */}
      {showRegisterModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="w-full max-w-2xl bg-dark-card border border-dark-border rounded-2xl p-6 space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-dark-border pb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-brand-500/20 border border-brand-500/40 flex items-center justify-center text-brand-400">
                  <Bot className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Register Custom Agent Adapter</h3>
                  <p className="text-xs text-slate-400">
                    Connect an external AI agent using the documented Python or HTTP adapter contract.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowRegisterModal(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleRegisterAgent} className="space-y-5 text-xs">
              {/* Adapter Mode Selector */}
              <div>
                <label className="block text-slate-300 font-semibold mb-2">Integration Adapter Mode</label>
                <div className="grid grid-cols-2 gap-3">
                  <div
                    onClick={() => {
                      setRegAdapterType('python');
                      setValidationResult(null);
                    }}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                      regAdapterType === 'python'
                        ? 'bg-sky-950/40 border-sky-500/80 shadow-md shadow-sky-500/10'
                        : 'bg-dark-bg/60 border-dark-border hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-2 text-white font-semibold">
                      <Code className="w-4 h-4 text-sky-400" />
                      <span>Mode A — Python Adapter</span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">
                      Trusted Python module or class implementing the AgentAdapter contract in process.
                    </p>
                  </div>

                  <div
                    onClick={() => {
                      setRegAdapterType('http');
                      setValidationResult(null);
                    }}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                      regAdapterType === 'http'
                        ? 'bg-amber-950/40 border-amber-500/80 shadow-md shadow-amber-500/10'
                        : 'bg-dark-bg/60 border-dark-border hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-2 text-white font-semibold">
                      <Server className="w-4 h-4 text-amber-400" />
                      <span>Mode B — HTTP Adapter</span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">
                      External agent microservice reachable over HTTP/HTTPS with strict SSRF controls.
                    </p>
                  </div>
                </div>
              </div>

              {/* Agent Identifiers */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Agent Identifier *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. agent-custom-billing"
                    value={regId}
                    onChange={(e) => setRegId(e.target.value)}
                    className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-200 font-mono focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Display Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Billing Disputes Agent"
                    value={regName}
                    onChange={(e) => setRegName(e.target.value)}
                    className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-brand-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Description</label>
                <input
                  type="text"
                  placeholder="Describes the agent purpose and task scope"
                  value={regDesc}
                  onChange={(e) => setRegDesc(e.target.value)}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-brand-500"
                />
              </div>

              {/* Adapter Specific Configuration */}
              {regAdapterType === 'python' ? (
                <div className="p-4 rounded-xl bg-dark-bg border border-dark-border space-y-3">
                  <h4 className="font-semibold text-sky-400 flex items-center gap-1.5">
                    <Code className="w-4 h-4" />
                    <span>Python Adapter Configuration</span>
                  </h4>
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Trusted Adapter Class</label>
                    <select
                      value={regPythonClass}
                      onChange={(e) => setRegPythonClass(e.target.value)}
                      className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-2 text-slate-200 font-mono focus:outline-none"
                    >
                      <option value="CustomTestAgent">CustomTestAgent (app.agents.custom_test_agent)</option>
                      <option value="SampleTicketAgent">SampleTicketAgent (app.agents.sample_ticket_agent)</option>
                    </select>
                    <p className="text-[10px] text-slate-500 mt-1">
                      Arbitrary script execution is restricted. Only verified classes in the registered application registry can be instantiated.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-dark-bg border border-dark-border space-y-3">
                  <h4 className="font-semibold text-amber-400 flex items-center gap-1.5">
                    <Server className="w-4 h-4" />
                    <span>HTTP Microservice Configuration</span>
                  </h4>
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Service Base URL *</label>
                    <input
                      type="url"
                      required
                      placeholder="http://127.0.0.1:8080"
                      value={regHttpUrl}
                      onChange={(e) => setRegHttpUrl(e.target.value)}
                      className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-2 text-slate-200 font-mono focus:outline-none"
                    />
                    <p className="text-[10px] text-slate-500 mt-1">
                      SSRF protection active: Cloud metadata endpoints (169.254.169.254), multicast, and invalid schemes are blocked.
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-slate-300 font-medium mb-1">Connect Timeout (s)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={regHttpConnectTimeout}
                        onChange={(e) => setRegHttpConnectTimeout(e.target.value)}
                        className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-slate-200 font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-slate-300 font-medium mb-1">Read Timeout (s)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={regHttpReadTimeout}
                        onChange={(e) => setRegHttpReadTimeout(e.target.value)}
                        className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-slate-200 font-mono"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Secret Reference (Optional)</label>
                    <input
                      type="text"
                      placeholder="Environment variable name, e.g. TICKET_AGENT_API_KEY"
                      value={regHttpSecretEnv}
                      onChange={(e) => setRegHttpSecretEnv(e.target.value)}
                      className="w-full bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-slate-200 font-mono"
                    />
                    <p className="text-[10px] text-slate-500 mt-1">
                      API credentials are never stored in database records; values are read from server environment variables.
                    </p>
                  </div>
                </div>
              )}

              {/* Declared Capabilities Checklist */}
              <div>
                <label className="block text-slate-300 font-semibold mb-2">Declared Capabilities</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {ALL_CAPABILITIES.map((cap) => {
                    const isChecked = regCaps.includes(cap.id);
                    return (
                      <div
                        key={cap.id}
                        onClick={() => handleToggleCapability(cap.id, false)}
                        className={`p-2.5 rounded-lg border cursor-pointer transition-all flex items-start gap-2.5 ${
                          isChecked
                            ? 'bg-brand-950/30 border-brand-500/50 text-white'
                            : 'bg-dark-bg/60 border-dark-border text-slate-400 hover:border-slate-700'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {}}
                          className="mt-0.5 rounded border-slate-700 bg-dark-card text-brand-500"
                        />
                        <div>
                          <p className="font-semibold text-xs leading-none">{cap.label}</p>
                          <p className="text-[10px] text-slate-400 mt-1">{cap.desc}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Validation Status Box */}
              {validationResult && (
                <div
                  className={`p-3 rounded-xl border text-xs flex items-start gap-2 ${
                    validationResult.valid
                      ? 'bg-emerald-950/30 border-emerald-800 text-emerald-300'
                      : 'bg-rose-950/30 border-rose-800 text-rose-300'
                  }`}
                >
                  {validationResult.valid ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <p className="font-semibold">
                      {validationResult.valid ? 'Configuration Validated Successfully' : 'Validation Failed'}
                    </p>
                    <p className="text-[11px] opacity-90 mt-0.5">
                      {validationResult.valid
                        ? `Adapter passed boundary and schema checks (${validationResult.adapter_type}).`
                        : validationResult.error}
                    </p>
                  </div>
                </div>
              )}

              {registerError && (
                <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span>{registerError}</span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="pt-2 flex items-center justify-end gap-3 border-t border-dark-border">
                <button
                  type="button"
                  onClick={handleValidateConfig}
                  disabled={isValidating}
                  className="px-4 py-2 rounded-xl bg-dark-bg border border-dark-border hover:bg-slate-800 text-slate-200 font-semibold text-xs transition-all flex items-center gap-1.5"
                >
                  <Shield className="w-3.5 h-3.5 text-sky-400" />
                  <span>{isValidating ? 'Validating...' : 'Validate Config'}</span>
                </button>

                <button
                  type="button"
                  onClick={() => setShowRegisterModal(false)}
                  className="px-4 py-2 rounded-xl bg-dark-bg border border-dark-border text-slate-400 hover:text-white text-xs font-semibold"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:bg-slate-800 text-white font-semibold text-xs shadow-md shadow-brand-600/20 transition-all"
                >
                  {isSubmitting ? 'Registering...' : 'Register Agent'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
