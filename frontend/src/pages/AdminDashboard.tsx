import React from 'react';
import { Box, Heading, Button, Text } from '@chakra-ui/react';
import toast from 'react-hot-toast';
import api from '../services/api';
import { triggerTaskByName } from '../utils/taskActions';
import useCoverageSnapshot from '../hooks/useCoverageSnapshot';
import { useUserPreferences } from '../hooks/useUserPreferences';
import { formatDateTime } from '../utils/format';
import {
  CoverageBucketsGrid,
  CoverageKpiGrid,
  CoverageSummaryCard,
  CoverageTrendGrid,
} from '../components/coverage/CoverageSummaryCard';

const AdminDashboard: React.FC = () => {
  const { timezone } = useUserPreferences();
  const [backfill5mEnabled, setBackfill5mEnabled] = React.useState<boolean>(true);
  const [toggling5m, setToggling5m] = React.useState<boolean>(false);
  const [refreshingCoverage, setRefreshingCoverage] = React.useState<boolean>(false);
  const [restoringDaily, setRestoringDaily] = React.useState<boolean>(false);
  const [backfillingStale, setBackfillingStale] = React.useState<boolean>(false);
  const [advancedOpen, setAdvancedOpen] = React.useState<boolean>(false);
  const [taskStatus, setTaskStatus] = React.useState<Record<string, any> | null>(null);
  const { snapshot: coverage, refresh: refreshCoverage, sparkline, kpis, actions: coverageActions, hero } = useCoverageSnapshot();
  const autoRefreshAttemptedRef = React.useRef(false);

  React.useEffect(() => {
    if (coverage?.meta?.backfill_5m_enabled !== undefined) {
      setBackfill5mEnabled(Boolean(coverage.meta.backfill_5m_enabled));
    }
  }, [coverage]);

  const loadTaskStatus = async () => {
    try {
      const res = await api.get('/market-data/admin/tasks/status');
      setTaskStatus(res?.data || null);
    } catch {
      setTaskStatus(null);
    }
  };

  React.useEffect(() => {
    void loadTaskStatus();
  }, []);

  const refreshCoverageNow = async (origin: 'manual' | 'auto') => {
    if (refreshingCoverage) return;
    setRefreshingCoverage(true);
    try {
      const res = await api.post('/market-data/admin/coverage/refresh');
      const taskId = res?.data?.task_id;
      toast.success(origin === 'auto' ? 'Coverage refresh queued (auto)' : 'Coverage refresh queued');
      // Task may take a moment; do a couple of lightweight refreshes.
      setTimeout(() => void refreshCoverage(), 1500);
      setTimeout(() => void refreshCoverage(), 4500);
      void taskId;
      void loadTaskStatus();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || 'Failed to refresh coverage');
    } finally {
      setRefreshingCoverage(false);
    }
  };

  const restoreDailyCoverageTracked = async () => {
    if (restoringDaily) return;
    setRestoringDaily(true);
    try {
      // Guided orchestrator (daily only, tracked universe)
      await triggerTaskByName('restore_daily_coverage_tracked');
      toast.success('Daily coverage restore queued');
      setTimeout(() => void refreshCoverage(), 1500);
      setTimeout(() => void refreshCoverage(), 4500);
      void loadTaskStatus();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || 'Failed to queue daily coverage restore');
    } finally {
      setRestoringDaily(false);
    }
  };

  const backfillStaleDailyOnly = async () => {
    if (backfillingStale) return;
    setBackfillingStale(true);
    try {
      const res = await api.post('/market-data/admin/coverage/backfill-stale-daily');
      const backfilled = res?.data?.backfilled;
      toast.success(typeof backfilled === 'number' ? `Queued stale-only backfill (${backfilled})` : 'Queued stale-only backfill');
      setTimeout(() => void refreshCoverage(), 1500);
      setTimeout(() => void refreshCoverage(), 4500);
      void loadTaskStatus();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || 'Failed to backfill stale daily');
    } finally {
      setBackfillingStale(false);
    }
  };

  const runNamedTask = async (taskName: string, label?: string) => {
    // Special-case: schedule coverage monitor as an hourly beat entry
    if (taskName === 'schedule_coverage_monitor') {
      try {
        await api.post('/admin/schedules', {
          name: 'monitor-coverage-health',
          task: 'backend.tasks.market_data_tasks.monitor_coverage_health',
          cron: '0 * * * *',
          timezone: 'UTC',
        });
        toast.success('Coverage monitor scheduled (hourly)');
        await refreshCoverage();
      } catch (err: any) {
        toast.error(err?.response?.data?.detail || err?.message || 'Failed to schedule monitor');
      }
      return;
    }
    try {
      await triggerTaskByName(taskName);
      toast.success(label || taskName);
      await refreshCoverage();
      void loadTaskStatus();
    } catch (err: any) {
      toast.error(err?.message || `Failed to run ${label || taskName}`);
    }
  };

  const toggleBackfill5m = async () => {
    if (toggling5m) return;
    setToggling5m(true);
    const next = !backfill5mEnabled;
    try {
      const res = await api.post('/market-data/admin/coverage/backfill-5m-toggle', { enabled: next });
      const flag = res?.data?.backfill_5m_enabled ?? next;
      setBackfill5mEnabled(Boolean(flag));
      toast.success(`5m backfill ${flag ? 'enabled' : 'disabled'}`);
      await refreshCoverage();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || 'Failed to update 5m backfill toggle');
    } finally {
      setToggling5m(false);
    }
  };

  // Auto-trigger coverage monitor when cache is missing/stale.
  React.useEffect(() => {
    if (!coverage || autoRefreshAttemptedRef.current) return;
    const age = Number(coverage?.meta?.snapshot_age_seconds ?? NaN);
    const source = String(coverage?.meta?.source || '');
    const stale = !Number.isFinite(age) || age > 15 * 60 || source !== 'cache';
    if (stale) {
      autoRefreshAttemptedRef.current = true;
      void refreshCoverageNow('auto');
    }
  }, [coverage]);

  const fmtLastRun = (key: string) => {
    const raw = (taskStatus || {})[key];
    const ts = raw?.ts;
    return formatDateTime(ts, timezone);
  };

  return (
    <Box p={4}>
      <Heading size="md" mb={4}>Admin Dashboard</Heading>

      {coverage && (
        <CoverageSummaryCard hero={hero} status={coverage.status}>
          <CoverageKpiGrid kpis={kpis} variant="stat" />
          <CoverageTrendGrid sparkline={sparkline} />
          <CoverageBucketsGrid groups={hero?.buckets || []} />
          <Box mt={3} display="flex" alignItems="center" justifyContent="space-between" gap={3} flexWrap="wrap">
            <Box>
              <Text fontSize="xs" color="gray.400">
                Source: <Text as="span" color="gray.200">{String(coverage?.meta?.source || '—')}</Text> •{' '}
                Last refresh: <Text as="span" color="gray.200">{formatDateTime(coverage?.meta?.updated_at, timezone)}</Text>
                {' '}• Monitor last run:{' '}
                <Text as="span" color="gray.200">{fmtLastRun('taskstatus:monitor_coverage_health:last')}</Text>
              </Text>
            </Box>
            <Button size="sm" variant="outline" loading={refreshingCoverage} onClick={() => void refreshCoverageNow('manual')}>
              Refresh coverage now
            </Button>
          </Box>
          <Box mt={3} display="flex" alignItems="center" gap={3}>
            <input
              type="checkbox"
              checked={backfill5mEnabled}
              onChange={() => void toggleBackfill5m()}
              disabled={toggling5m}
            />
            <Box>
              <Text fontSize="sm" fontWeight="medium">
                5m Backfill {backfill5mEnabled ? 'Enabled' : 'Disabled'}
              </Text>
              <Text fontSize="xs" color="gray.400">
                Daily coverage is the primary SLA. When disabled, 5m is informational-only (ignored for status).
              </Text>
            </Box>
          </Box>
          <Box mt={4} display="flex" flexDirection="column" gap={2}>
            <Text fontSize="sm" fontWeight="semibold">Guided Actions</Text>
            <Box display="flex" gap={2} flexWrap="wrap">
              <Button colorScheme="brand" size="sm" loading={restoringDaily} onClick={() => void restoreDailyCoverageTracked()}>
                Restore Daily Coverage (Tracked)
              </Button>
              <Button variant="outline" size="sm" loading={backfillingStale} onClick={() => void backfillStaleDailyOnly()}>
                Backfill Daily (Stale Only)
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setAdvancedOpen(!advancedOpen)}>
                {advancedOpen ? 'Hide Advanced' : 'Show Advanced'}
              </Button>
            </Box>
            {advancedOpen ? (
              <Box mt={2} borderWidth="1px" borderColor="border.subtle" borderRadius="lg" p={3} bg="bg.muted">
                <Text fontSize="xs" color="fg.muted" mb={2}>
                  Advanced controls (use when debugging). These are more granular and may be slower/noisier.
                </Text>
                <Box display="flex" gap={2} flexWrap="wrap">
                  <Button size="xs" variant="outline" onClick={() => void runNamedTask('refresh_index_constituents', 'Refresh constituents')}>
                    Refresh Constituents
                  </Button>
                  <Button size="xs" variant="outline" onClick={() => void runNamedTask('update_tracked_symbol_cache', 'Update tracked')}>
                    Update Tracked
                  </Button>
                  <Button size="xs" variant="outline" onClick={() => void runNamedTask('backfill_index_universe', 'Backfill indices (batch=20 default)')}>
                    Backfill Indices (Daily)
                  </Button>
                  <Button size="xs" variant="outline" onClick={() => void runNamedTask('backfill_last_200_bars', 'Backfill last-200 (tracked)')}>
                    Backfill Last-200 (Tracked)
                  </Button>
                  <Button size="xs" variant="outline" onClick={() => void runNamedTask('recompute_indicators_universe', 'Recompute indicators')}>
                    Recompute Indicators
                  </Button>
                  <Button size="xs" variant="outline" onClick={() => void runNamedTask('record_daily_history', 'Record history')}>
                    Record History
                  </Button>
                </Box>
              </Box>
            ) : null}
          </Box>
        </CoverageSummaryCard>
      )}
    </Box>
  );
};

export default AdminDashboard;
