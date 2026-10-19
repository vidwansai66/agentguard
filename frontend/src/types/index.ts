export interface AgentVersion {
  id: string;
  agent_id: string;
  version_tag: string;
  strategy: string;
  config: Record<string, any>;
  description?: string;
  is_candidate: boolean;
  created_at?: string;
}

export type ObservabilityLevel = 'level_1_result_only' | 'level_2_structured_events' | 'level_3_instrumented_tools';

export interface Agent {
  id: string;
  name: string;
  description?: string;
  agent_type: string;
  adapter_type?: 'python' | 'http' | 'python_sdk_wrapper';
  registration_source?: 'built_in' | 'custom' | 'connected_existing';
  status: string;
  observability_level?: ObservabilityLevel;
  current_version: string;
  supported_tools: string[];
  declared_capabilities?: string[];
  adapter_config?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
  versions: AgentVersion[];
}

export interface HttpConnectionConfig {
  base_url: string;
  health_endpoint?: string;
  invocation_endpoint?: string;
  auth_type?: string;
  auth_header_name?: string;
  secret_env_var?: string;
  connect_timeout_seconds?: number;
  read_timeout_seconds?: number;
  allow_local_dev?: boolean;
  observability_level?: ObservabilityLevel;
  event_format?: string;
  request_mapping?: Record<string, any>;
  response_mapping?: Record<string, any>;
}

export interface SdkWrapperConfig {
  wrapper_type: string;
  target_name?: string;
  observability_level?: ObservabilityLevel;
  input_parameter_name?: string;
}

export interface FrameworkConnectionConfig {
  framework: string;
  graph_target: string;
  max_steps?: number;
}

export interface ModelBackedConnectionConfig {
  provider: string;
  model: string;
  base_url: string;
  secret_env_var: string;
  request_timeout_seconds?: number;
  max_model_calls?: number;
  max_tool_calls?: number;
  temperature?: number;
  system_prompt?: string;
}

export interface FrameworkCatalogItem {
  framework: string;
  status: 'supported' | 'planned';
  installed_version?: string;
  description: string;
  example_target?: string;
}

export interface ExistingAgentConnectRequest {
  id: string;
  name: string;
  description?: string;
  connection_method: 'http_endpoint' | 'python_sdk_wrapper' | 'agent_framework' | 'model_backed';
  observability_level: ObservabilityLevel;
  version: string;
  supported_tools: string[];
  declared_capabilities: string[];
  http_config?: HttpConnectionConfig;
  sdk_config?: SdkWrapperConfig;
  framework_config?: FrameworkConnectionConfig;
  llm_config?: ModelBackedConnectionConfig;
}


export interface Scenario {
  id: string;
  name: string;
  description?: string;
  category: string;
  failure_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  is_enabled: boolean;
  is_seeded: boolean;
  version: number;
  task_input: Record<string, any>;
  expected_outcome: Record<string, any>;
  fault_parameters: Record<string, any>;
  allowed_tools: string[];
  policy_constraints: Record<string, any>;
  execution_limits: Record<string, any>;
  expected_assertions: string[];
  required_capabilities?: string[];
  created_at?: string;
  updated_at?: string;
}

export interface TestSuite {
  id: string;
  name: string;
  description?: string;
  is_regression_suite: boolean;
  scenario_ids: string[];
  scenario_count: number;
  created_at?: string;
  updated_at?: string;
}

export interface EvaluationFinding {
  id: string;
  run_id: string;
  scenario_result_id: string;
  scenario_id: string;
  rule_id: string;
  rule_name: string;
  status: 'passed' | 'failed' | 'warning';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  explanation?: string;
  trace_event_ids: string[];
  evidence: Record<string, any>;
  created_at?: string;
}

export interface TraceEvent {
  id: string;
  run_id: string;
  scenario_result_id: string;
  scenario_id: string;
  step_index: number;
  event_type: 'agent_decision' | 'tool_call' | 'tool_response' | 'fault_injected' | 'retry' | 'policy_check' | 'error' | 'system';
  severity: 'info' | 'warning' | 'error' | 'critical';
  action_name?: string;
  tool_name?: string;
  sanitized_input: Record<string, any>;
  sanitized_output: Record<string, any>;
  fault_details: Record<string, any>;
  retry_count: number;
  duration_ms: number;
  error_message?: string;
  timestamp?: string;
}

export interface ScenarioResult {
  id: string;
  run_id: string;
  scenario_id: string;
  scenario_name: string;
  scenario_version: number;
  failure_type: string;
  status: 'passed' | 'failed' | 'unsupported' | 'error' | 'cancelled';
  passed: boolean;
  disrupted: boolean;
  recovered: boolean;
  has_unsafe_side_effect: boolean;
  duration_ms: number;
  retry_count: number;
  step_count: number;
  error_message?: string;
  execution_output: Record<string, any>;
  findings: EvaluationFinding[];
  created_at?: string;
}

export interface TestRun {
  id: string;
  name: string;
  agent_id: string;
  agent_version: string;
  suite_id?: string;
  scenario_id?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  observability_level?: ObservabilityLevel;
  trigger_type: string;
  total_scenarios: number;
  passed_scenarios: number;
  failed_scenarios: number;
  unsupported_scenarios?: number;
  unsafe_side_effects_count: number;
  disrupted_count: number;
  recovered_count: number;
  total_duration_ms: number;
  started_at?: string;
  completed_at?: string;
  created_at?: string;
  scenario_results?: ScenarioResult[];
}

export interface CustomAgentRegisterPayload {
  id: string;
  name: string;
  description?: string;
  adapter_type: 'python' | 'http';
  version: string;
  strategy: string;
  observability_level?: ObservabilityLevel;
  supported_tools: string[];
  declared_capabilities: string[];
  adapter_config: Record<string, any>;
}

export interface ValidateConfigResponse {
  valid: boolean;
  error?: string;
  adapter_type: string;
  observability_level?: ObservabilityLevel;
  details: Record<string, any>;
}

export interface TestConnectionResponse {
  status: 'healthy' | 'warning' | 'error' | 'unconfigured';
  message: string;
  adapter_type: string;
  observability_level?: ObservabilityLevel;
  declared_capabilities: string[];
  details: Record<string, any>;
}

export interface CompatibilityScenarioDetail {
  scenario_id: string;
  scenario_name: string;
  failure_type?: string;
  required_capabilities: string[];
  missing_capabilities: string[];
  observability_level?: ObservabilityLevel;
  observability_compatible?: boolean;
  compatible: boolean;
  explanation: string;
}

export interface CompatibilityResponse {
  agent_id: string;
  observability_level?: ObservabilityLevel;
  declared_capabilities: string[];
  compatible: boolean;
  scenarios: CompatibilityScenarioDetail[];
}

export interface Diagnosis {
  id: string;
  run_id: string;
  scenario_result_id: string;
  scenario_id: string;
  title: string;
  likely_cause: string;
  confidence: string;
  explanation: string;
  supporting_evidence: Record<string, any>;
  relevant_trace_event_ids: string[];
  recommended_strategy: string;
  recommended_patch_template_id?: string;
  limitations?: string;
  created_at?: string;
}

export interface RepairProposal {
  id: string;
  diagnosis_id: string;
  run_id: string;
  template_id: string;
  title: string;
  proposed_change: string;
  rationale: string;
  expected_benefit: string;
  potential_risks: string;
  patch_diff: string;
  target_agent_id: string;
  base_version: string;
  candidate_version_tag: string;
  candidate_strategy: string;
  candidate_config: Record<string, any>;
  approval_status: 'pending' | 'approved' | 'rejected';
  approved_at?: string;
  rejected_at?: string;
  verification_status: 'unverified' | 'verifying' | 'verified_passed' | 'verified_failed' | 'trade_offs_detected';
  candidate_run_id?: string;
  comparison_id?: string;
  verification_summary: Record<string, any>;
  created_at?: string;
}

export interface PerScenarioComparison {
  scenario_id: string;
  scenario_name: string;
  failure_type: string;
  baseline_passed: boolean;
  candidate_passed: boolean;
  baseline_unsafe: boolean;
  candidate_unsafe: boolean;
  baseline_duration_ms: number;
  candidate_duration_ms: number;
  status_change: 'improved' | 'regressed' | 'unchanged_pass' | 'unchanged_fail';
}

export interface Comparison {
  id: string;
  baseline_run_id: string;
  candidate_run_id: string;
  baseline_agent_version: string;
  candidate_agent_version: string;
  baseline_success_rate: number;
  candidate_success_rate: number;
  baseline_recovery_rate: number;
  candidate_recovery_rate: number;
  baseline_unsafe_side_effect_rate: number;
  candidate_unsafe_side_effect_rate: number;
  baseline_median_latency_ms: number;
  candidate_median_latency_ms: number;
  baseline_p95_latency_ms: number;
  candidate_p95_latency_ms: number;
  regression_rate: number;
  newly_passing_scenarios: string[];
  newly_failing_scenarios: string[];
  safety_regressions: string[];
  per_scenario_comparison: PerScenarioComparison[];
  interpretation: string;
  verification_verdict: 'verified_passed' | 'verified_failed' | 'trade_offs_detected' | 'undetermined';
  created_at?: string;
}

export interface CategoryMetric {
  category: string;
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
}

export interface TrendPoint {
  run_id: string;
  run_name: string;
  timestamp: string;
  success_rate: number;
  unsafe_side_effect_rate: number;
  duration_ms: number;
}

export interface DashboardStats {
  total_runs: number;
  task_success_rate: number;
  recovery_rate: number;
  unsafe_side_effect_rate: number;
  total_failures: number;
  median_latency_ms: number;
  p95_latency_ms: number;
  cost_per_successful_task: string;
  recent_runs: Array<{
    id: string;
    name: string;
    agent_id: string;
    agent_version: string;
    status: string;
    passed_scenarios: number;
    total_scenarios: number;
    unsafe_side_effects_count: number;
    duration_ms: number;
    created_at?: string;
  }>;
  failure_type_metrics: CategoryMetric[];
  trend_history: TrendPoint[];
  active_regressions_count: number;
}

export interface SystemStatus {
  status: string;
  version: string;
  database_connected: boolean;
  database_url_type: string;
  registered_agents_count: number;
  total_scenarios_count: number;
  total_runs_count: number;
  uptime_seconds: number;
}
