import { describe, it, expect } from 'vitest';
import { DashboardStats } from '../types';

export const formatCategory = (cat: string) => {
  const map: Record<string, string> = {
    normal_execution: 'Normal Flow',
    transient_timeout: 'Timeout',
    ambiguous_outcome: 'Ambiguous',
    repeated_action: 'Repeated Action',
    schema_violation: 'Schema Error',
    prompt_injection: 'Prompt Injection'
  };
  return map[cat] || cat.replace(/_/g, ' ');
};

export const getRecoveryRateDisplay = (stats: DashboardStats | null) => {
  const disruptedCount = stats?.disrupted_scenarios_count ?? 0;
  if (!stats || disruptedCount === 0 || stats.recovery_rate === null || stats.recovery_rate === undefined) {
    return 'N/A';
  }
  return `${(stats.recovery_rate * 100).toFixed(1)}%`;
};

export const getSuccessRateDisplay = (stats: DashboardStats | null) => {
  const total = stats?.total_scenarios_count ?? stats?.total_runs ?? 0;
  if (!stats || total === 0) {
    return 'N/A';
  }
  return `${((stats.task_success_rate || 0) * 100).toFixed(1)}%`;
};

describe('Dashboard Metrics Presentation Logic', () => {
  it('formats category names from snake_case to human-readable labels', () => {
    expect(formatCategory('normal_execution')).toBe('Normal Flow');
    expect(formatCategory('transient_timeout')).toBe('Timeout');
    expect(formatCategory('ambiguous_outcome')).toBe('Ambiguous');
    expect(formatCategory('repeated_action')).toBe('Repeated Action');
    expect(formatCategory('unknown_custom_category')).toBe('unknown custom category');
  });

  it('displays N/A for recovery rate when there are zero disruption scenarios tested', () => {
    const statsNoDisruptions: DashboardStats = {
      total_runs: 1,
      total_scenarios_count: 1,
      passed_scenarios_count: 1,
      failed_scenarios_count: 0,
      disrupted_scenarios_count: 0,
      recovered_scenarios_count: 0,
      unsafe_side_effects_count: 0,
      task_success_rate: 1.0,
      recovery_rate: null,
      unsafe_side_effect_rate: 0.0,
      total_failures: 0,
      median_latency_ms: 1.16,
      p95_latency_ms: 1.16,
      cost_per_successful_task: '$0.00 (Local Mock Environment)',
      recent_runs: [],
      failure_type_metrics: [],
      trend_history: [],
      active_regressions_count: 0
    };

    expect(getRecoveryRateDisplay(statsNoDisruptions)).toBe('N/A');
    expect(getSuccessRateDisplay(statsNoDisruptions)).toBe('100.0%');
  });

  it('displays calculated percentage when disruption scenarios exist', () => {
    const statsWithDisruptions: DashboardStats = {
      total_runs: 2,
      total_scenarios_count: 7,
      passed_scenarios_count: 5,
      failed_scenarios_count: 2,
      disrupted_scenarios_count: 4,
      recovered_scenarios_count: 3,
      unsafe_side_effects_count: 0,
      task_success_rate: 0.7143,
      recovery_rate: 0.75,
      unsafe_side_effect_rate: 0.0,
      total_failures: 2,
      median_latency_ms: 0.71,
      p95_latency_ms: 1.16,
      cost_per_successful_task: '$0.00 (Local Mock Environment)',
      recent_runs: [],
      failure_type_metrics: [],
      trend_history: [],
      active_regressions_count: 0
    };

    expect(getRecoveryRateDisplay(statsWithDisruptions)).toBe('75.0%');
    expect(getSuccessRateDisplay(statsWithDisruptions)).toBe('71.4%');
  });

  it('handles empty stats gracefully with N/A displays', () => {
    expect(getRecoveryRateDisplay(null)).toBe('N/A');
    expect(getSuccessRateDisplay(null)).toBe('N/A');
  });
});
