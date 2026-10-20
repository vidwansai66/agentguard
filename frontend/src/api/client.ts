import {
  DashboardStats,
  SystemStatus,
  Agent,
  Scenario,
  TestSuite,
  TestRun,
  TraceEvent,
  ScenarioResult,
  Diagnosis,
  RepairProposal,
  Comparison,
  CustomAgentRegisterPayload,
  ExistingAgentConnectRequest,
  ValidateConfigResponse,
  TestConnectionResponse,
  CompatibilityResponse,
  FrameworkCatalogItem
} from '../types';

export const getApiBase = (): string => {
  const meta = import.meta as any;
  const envUrl = (meta?.env?.VITE_API_URL || meta?.env?.VITE_API_BASE_URL || '').trim();

  if (envUrl) {
    const cleaned = envUrl.replace(/\/+$/, '');
    return cleaned.endsWith('/api') ? cleaned : `${cleaned}/api`;
  }

  // If running in production on Vercel without a custom env var configured,
  // target the live Render backend directly
  if (typeof window !== 'undefined' && window.location && window.location.hostname.endsWith('vercel.app')) {
    return 'https://agentguard-p14p.onrender.com/api';
  }

  return '/api';
};

export const API_BASE = getApiBase();

export class ApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };

    try {
      const response = await fetch(url, { ...options, headers });
      const contentType = response.headers.get('content-type') || '';

      if (!response.ok) {
        let errorMessage = `API request failed with status ${response.status} (${response.statusText || 'Error'})`;
        try {
          if (contentType.includes('application/json')) {
            const errorData = await response.json();
            if (errorData?.message) {
              errorMessage = errorData.message;
            } else if (errorData?.detail) {
              errorMessage = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
            }
          } else {
            const errorText = await response.text();
            if (errorText.trim().startsWith('<')) {
              errorMessage = `Server returned HTTP ${response.status} (${response.statusText}). Endpoint ${url} returned an HTML document.`;
            } else if (errorText.trim()) {
              errorMessage = errorText.slice(0, 200);
            }
          }
        } catch (_) {
          // Fall back to status message
        }
        throw new Error(errorMessage);
      }

      if (response.status === 204) {
        return {} as T;
      }

      const rawText = await response.text();
      if (!rawText || !rawText.trim()) {
        return {} as T;
      }

      try {
        return JSON.parse(rawText) as T;
      } catch (parseErr: any) {
        if (rawText.trim().startsWith('<') || contentType.includes('text/html')) {
          throw new Error(
            `API endpoint ${url} returned an HTML page instead of JSON. Ensure your API URL is configured correctly and pointing to the backend service.`
          );
        }
        throw new Error(`Failed to parse API response as JSON: ${parseErr.message}`);
      }
    } catch (err: any) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  }

  // Health & Stats
  async getStats(): Promise<DashboardStats> {
    return this.request<DashboardStats>('/stats');
  }

  async getSystemStatus(): Promise<SystemStatus> {
    return this.request<SystemStatus>('/system/status');
  }

  async resetDemoData(): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>('/system/reset-demo-data', {
      method: 'POST'
    });
  }

  // Agents
  async getAgents(): Promise<Agent[]> {
    return this.request<Agent[]>('/agents');
  }

  async getAgent(id: string): Promise<Agent> {
    return this.request<Agent>(`/agents/${id}`);
  }

  async registerCustomAgent(payload: CustomAgentRegisterPayload): Promise<Agent> {
    return this.request<Agent>('/agents/custom', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async connectExistingAgent(payload: ExistingAgentConnectRequest): Promise<Agent> {
    return this.request<Agent>('/agents/connect-existing', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async getFrameworkCatalog(): Promise<FrameworkCatalogItem[]> {
    return this.request<FrameworkCatalogItem[]>('/agents/frameworks/catalog');
  }


  async validateAgentConfig(adapter_type: string, adapter_config: Record<string, any>): Promise<ValidateConfigResponse> {
    return this.request<ValidateConfigResponse>('/agents/validate-config', {
      method: 'POST',
      body: JSON.stringify({ adapter_type, adapter_config })
    });
  }

  async testAgentConnection(agentId: string, adapter_type?: string, adapter_config?: Record<string, any>): Promise<TestConnectionResponse> {
    return this.request<TestConnectionResponse>(`/agents/${agentId}/test-connection`, {
      method: 'POST',
      body: JSON.stringify({ adapter_type, adapter_config })
    });
  }

  async getAgentRuns(agentId: string): Promise<TestRun[]> {
    return this.request<TestRun[]>(`/agents/${agentId}/runs`);
  }

  async updateAgent(agentId: string, payload: Partial<Agent>): Promise<Agent> {
    return this.request<Agent>(`/agents/${agentId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    });
  }

  async checkScenarioCompatibility(agentId: string, scenarioIds: string[], suiteId?: string): Promise<CompatibilityResponse> {
    return this.request<CompatibilityResponse>('/scenarios/compatibility', {
      method: 'POST',
      body: JSON.stringify({ agent_id: agentId, scenario_ids: scenarioIds, suite_id: suiteId })
    });
  }

  // Scenarios
  async getScenarios(params?: { failure_type?: string; severity?: string; search?: string }): Promise<Scenario[]> {
    const query = new URLSearchParams();
    if (params?.failure_type) query.set('failure_type', params.failure_type);
    if (params?.severity) query.set('severity', params.severity);
    if (params?.search) query.set('search', params.search);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<Scenario[]>(`/scenarios${qs}`);
  }

  async getScenario(id: string): Promise<Scenario> {
    return this.request<Scenario>(`/scenarios/${id}`);
  }

  async createScenario(scenario: Partial<Scenario>): Promise<Scenario> {
    return this.request<Scenario>('/scenarios', {
      method: 'POST',
      body: JSON.stringify(scenario)
    });
  }

  async updateScenario(id: string, scenario: Partial<Scenario>): Promise<Scenario> {
    return this.request<Scenario>(`/scenarios/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(scenario)
    });
  }

  async deleteScenario(id: string): Promise<void> {
    return this.request<void>(`/scenarios/${id}`, {
      method: 'DELETE'
    });
  }

  async duplicateScenario(id: string): Promise<Scenario> {
    return this.request<Scenario>(`/scenarios/${id}/duplicate`, {
      method: 'POST'
    });
  }

  async exportScenarios(): Promise<{ version: string; scenarios: Scenario[] }> {
    return this.request<{ version: string; scenarios: Scenario[] }>('/scenarios/export');
  }

  async importScenarios(payload: any): Promise<{ imported_count: number; scenario_ids: string[] }> {
    return this.request<{ imported_count: number; scenario_ids: string[] }>('/scenarios/import', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  // Test Suites
  async getSuites(): Promise<TestSuite[]> {
    return this.request<TestSuite[]>('/suites');
  }

  async getSuite(id: string): Promise<TestSuite> {
    return this.request<TestSuite>(`/suites/${id}`);
  }

  async createSuite(suite: { name: string; description?: string; scenario_ids: string[] }): Promise<TestSuite> {
    return this.request<TestSuite>('/suites', {
      method: 'POST',
      body: JSON.stringify(suite)
    });
  }

  // Runs
  async getRuns(limit: number = 50): Promise<TestRun[]> {
    return this.request<TestRun[]>(`/runs?limit=${limit}`);
  }

  async getRun(id: string): Promise<TestRun> {
    return this.request<TestRun>(`/runs/${id}`);
  }

  async getRunTrace(id: string, params?: { scenario_id?: string; event_type?: string; severity?: string }): Promise<TraceEvent[]> {
    const query = new URLSearchParams();
    if (params?.scenario_id) query.set('scenario_id', params.scenario_id);
    if (params?.event_type) query.set('event_type', params.event_type);
    if (params?.severity) query.set('severity', params.severity);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<TraceEvent[]>(`/runs/${id}/trace${qs}`);
  }

  async triggerRun(params: {
    name?: string;
    agent_id: string;
    agent_version: string;
    suite_id?: string;
    scenario_id?: string;
    custom_config?: Record<string, any>;
  }): Promise<TestRun> {
    return this.request<TestRun>('/runs', {
      method: 'POST',
      body: JSON.stringify(params)
    });
  }

  async cancelRun(id: string): Promise<{ id: string; status: string; message: string }> {
    return this.request<{ id: string; status: string; message: string }>(`/runs/${id}/cancel`, {
      method: 'POST'
    });
  }

  // Diagnosis & Repairs
  async diagnoseRun(runId: string): Promise<Diagnosis[]> {
    return this.request<Diagnosis[]>(`/runs/${runId}/diagnose`, {
      method: 'POST'
    });
  }

  async getRunDiagnoses(runId: string): Promise<Diagnosis[]> {
    return this.request<Diagnosis[]>(`/runs/${runId}/diagnoses`);
  }

  async getPatches(): Promise<RepairProposal[]> {
    return this.request<RepairProposal[]>('/patches');
  }

  async getPatch(id: string): Promise<RepairProposal> {
    return this.request<RepairProposal>(`/patches/${id}`);
  }

  async approvePatch(id: string, notes?: string): Promise<RepairProposal> {
    return this.request<RepairProposal>(`/patches/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ notes })
    });
  }

  async rejectPatch(id: string, reason?: string): Promise<RepairProposal> {
    return this.request<RepairProposal>(`/patches/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason })
    });
  }

  async verifyPatch(id: string): Promise<Comparison> {
    return this.request<Comparison>(`/patches/${id}/verify`, {
      method: 'POST'
    });
  }

  // Comparisons
  async createComparison(baselineRunId: string, candidateRunId: string): Promise<Comparison> {
    return this.request<Comparison>('/comparisons', {
      method: 'POST',
      body: JSON.stringify({
        baseline_run_id: baselineRunId,
        candidate_run_id: candidateRunId
      })
    });
  }

  async getComparison(id: string): Promise<Comparison> {
    return this.request<Comparison>(`/comparisons/${id}`);
  }
}

export const api = new ApiClient();
