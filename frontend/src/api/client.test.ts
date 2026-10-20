import { describe, it, expect, vi } from 'vitest';
import { getApiBase, api, ApiClient } from './client';

describe('Frontend API Client', () => {
  it('resolves default API base path for local development', () => {
    const base = getApiBase();
    expect(base).toBeDefined();
    expect(typeof base).toBe('string');
  });

  it('exposes essential AgentGuard API methods', () => {
    expect(typeof api.getStats).toBe('function');
    expect(typeof api.getSystemStatus).toBe('function');
    expect(typeof api.getAgents).toBe('function');
    expect(typeof api.getScenarios).toBe('function');
    expect(typeof api.triggerRun).toBe('function');
    expect(typeof api.getRuns).toBe('function');
    expect(typeof api.getRun).toBe('function');
    expect(typeof api.getRunTrace).toBe('function');
    expect(typeof api.testAgentConnection).toBe('function');
    expect(typeof api.validateAgentConfig).toBe('function');
    expect(typeof api.createComparison).toBe('function');
  });

  it('dispatches JSON request with correct headers', async () => {
    const mockData = { status: 'healthy', version: '1.0.0' };
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        text: () => Promise.resolve(JSON.stringify(mockData)),
        json: () => Promise.resolve(mockData),
      } as unknown as Response)
    );

    const client = new ApiClient();
    const result = await client.getSystemStatus();

    expect(fetchSpy).toHaveBeenCalled();
    const [calledUrl, calledOptions] = fetchSpy.mock.calls[0];
    expect(calledUrl).toContain('/system/status');
    expect((calledOptions?.headers as Record<string, string>)['Content-Type']).toBe('application/json');
    expect(result).toEqual(mockData);

    fetchSpy.mockRestore();
  });
});
