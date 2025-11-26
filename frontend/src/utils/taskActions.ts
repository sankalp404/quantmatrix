import api from '../services/api';

type TaskName =
  | 'refresh_index_constituents'
  | 'update_tracked_symbol_cache'
  | 'backfill_index_universe'
  | 'backfill_new_tracked'
  | 'backfill_last_200_bars'
  | 'backfill_5m_last_n_days'
  | 'recompute_indicators_universe'
  | 'record_daily_history'
  | 'bootstrap_universe';

const TASK_ENDPOINTS: Record<TaskName, () => Promise<any>> = {
  refresh_index_constituents: () => api.post('/market-data/index/constituents/refresh'),
  update_tracked_symbol_cache: () => api.post('/market-data/tracked/update'),
  backfill_index_universe: () => api.post('/market-data/backfill/index-universe'),
  backfill_new_tracked: () => api.post('/market-data/backfill/tracked-new'),
  backfill_last_200_bars: () => api.post('/market-data/backfill/last-200'),
  backfill_5m_last_n_days: () => api.post('/market-data/backfill/5m'),
  recompute_indicators_universe: () => api.post('/market-data/indicators/recompute-universe'),
  record_daily_history: () => api.post('/market-data/admin/history/record'),
  bootstrap_universe: () => api.post('/market-data/admin/bootstrap'),
};

export const triggerTaskByName = async (taskName: string) => {
  const runner = TASK_ENDPOINTS[taskName as TaskName];
  if (!runner) {
    throw new Error(`Unsupported task: ${taskName}`);
  }
  return runner();
};

