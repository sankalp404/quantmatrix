import api from '../services/api';

type TaskName =
  | 'refresh_index_constituents'
  | 'update_tracked_symbol_cache'
  | 'backfill_last_bars'
  | 'backfill_5m_last_n_days'
  | 'recompute_indicators_universe'
  | 'record_daily_history'
  | 'monitor_coverage_health'
  | 'restore_daily_coverage_tracked'
  | 'backfill_stale_daily'
  | 'backfill_snapshot_history_200d';

const TASK_ENDPOINTS: Record<TaskName, () => Promise<any>> = {
  refresh_index_constituents: () => api.post('/market-data/index/constituents/refresh'),
  update_tracked_symbol_cache: () => api.post('/market-data/tracked/update'),
  // Default remains ~200d; backend supports ?days=500 etc.
  backfill_last_bars: () => api.post('/market-data/admin/backfill/daily-last-bars?days=200'),
  backfill_5m_last_n_days: () => api.post('/market-data/backfill/5m'),
  recompute_indicators_universe: () => api.post('/market-data/indicators/recompute-universe'),
  record_daily_history: () => api.post('/market-data/admin/history/record'),
  monitor_coverage_health: () => api.post('/market-data/admin/coverage/refresh'),
  restore_daily_coverage_tracked: () => api.post('/market-data/admin/coverage/restore-daily-tracked'),
  backfill_stale_daily: () => api.post('/market-data/admin/coverage/backfill-stale-daily'),
  backfill_snapshot_history_200d: () =>
    api.post('/market-data/admin/snapshots/history/backfill-last-n-days?days=200'),
};

export const triggerTaskByName = async (taskName: string) => {
  const runner = TASK_ENDPOINTS[taskName as TaskName];
  if (!runner) {
    throw new Error(`Unsupported task: ${taskName}`);
  }
  return runner();
};

