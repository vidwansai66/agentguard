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
  Comparison
} from '../types';

const API_BASE = '/api';

class ApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };

    try {
      const response = await fetch(url, { ...options, headers });
      if (!response.ok) {
        let errorData: any = {};
        try {
          errorData = await response.json();
        } catch (_) {
          errorData = { message: response.statusText };
        }
        throw new Error(errorData.message || `API request failed with status ${response.status}`);
      }
      if (response.status === 204) {
        return {} as T;
      }
      return await response.json();
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

  async importScenarios(scenarios: Partial<Scenario>[]): Promise<{ imported_count: number; scenario_ids: string[] }> {
    return this.request<{ imported_count: number; scenario_ids: string[] }>('/scenarios/import', {
      method: 'POST',
      body: JSON.stringify({ scenarios })
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
