import React from 'react';
import { Box, Heading, Button, Text, HStack, VStack, Badge } from '@chakra-ui/react';
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
      const staleCandidates = res?.data?.stale_candidates;
      toast.success(
        typeof staleCandidates === 'number'
          ? `Queued stale-only backfill (${staleCandidates} symbols)`
          : 'Queued stale-only backfill',
      );
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

  const dailyFillSeries = (coverage as any)?.daily?.fill_by_date as
    | Array<{ date: string; symbol_count: number; pct_of_universe: number }>
    | undefined;
  const snapshotFillSeries = (coverage as any)?.daily?.snapshot_fill_by_date as
    | Array<{ date: string; symbol_count: number; pct_of_universe: number }>
    | undefined;

  const totalSymbols = Number((coverage as any)?.symbols ?? (coverage as any)?.tracked_count ?? 0);

  const dailyFillDist = React.useMemo(() => {
    const rows = (dailyFillSeries || [])
      .filter((r) => r && r.date)
      .slice()
      .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0)); // newest-first
    const newestDate = rows.length ? rows[0].date : null;
    const newestCount = rows.length ? Number(rows[0].symbol_count || 0) : 0;
    const newestPct = rows.length ? Number(rows[0].pct_of_universe || 0) : 0;
    return { newestDate, newestCount, newestPct, total: totalSymbols || 0, rows };
  }, [dailyFillSeries, totalSymbols]);

  const heroEffective = React.useMemo(() => {
    if (!hero) return hero;
    // When 5m is disabled, suppress noisy “missing 5m data” messaging in the hero.
    if (!backfill5mEnabled && hero?.staleCounts?.daily === 0 && hero?.staleCounts?.m5 > 0) {
      return {
        ...hero,
        summary: 'Daily coverage is green. 5m is disabled (ignored for status).',
      };
    }
    return hero;
  }, [hero, backfill5mEnabled]);

  const dailyHistogram = React.useMemo(() => {
    const { rows, newestDate, total } = dailyFillDist;
    if (!rows.length || !newestDate || !total) return null;

    const pctFor = (row: { pct_of_universe: number }) => Number(row?.pct_of_universe || 0);
    const colorForPct = (pct: number) => {
      // HSL: red(0) -> green(120), driven by % (height)
      const t = Math.max(0, Math.min(1, pct / 100));
      const hue = 0 + 120 * t;
      return `hsl(${hue}, 70%, 45%)`;
    };

    const barMaxH = 36;
    const fillMap = new Map(rows.map((r) => [r.date, r]));
    const snapshotPctByDate = new Map((snapshotFillSeries || []).map((r) => [r.date, Number(r.pct_of_universe || 0)]));

    // Trading-day series: use the last N observed dates in fill_by_date.
    // This naturally excludes weekends/holidays (no OHLCV rows expected) and avoids confusing gaps.
    const windowDays = 50;
    const bars: Array<{ date: string; symbol_count: number; pct_of_universe: number }> = rows
      .slice() // newest-first
      .reverse() // oldest-first
      .slice(-windowDays) // keep last N trading days
      .map((r) => ({
        date: r.date,
        symbol_count: Number(r.symbol_count || 0),
        pct_of_universe: Number(r.pct_of_universe || 0),
      }));

    return (
      <Box mt={2}>
        <Box
          borderRadius="md"
          borderWidth="1px"
          borderColor="border.subtle"
          bg="bg.card"
          px={2}
          py={2}
          overflowX="auto"
          overflowY="hidden"
        >
          <HStack align="end" gap={1} h={`${barMaxH}px`} minW="max-content">
            {bars.map((r) => {
              const pct = pctFor(r);
              const h = Math.max(2, Math.round((pct / 100) * barMaxH));
              const snapPct = snapshotPctByDate.get(r.date);
              const snapOk = typeof snapPct === 'number' && snapPct >= 95;
              const snapNone = typeof snapPct !== 'number';
              // Dot thresholds: green = basically complete, orange = partial, red = low coverage, gray = no snapshot run recorded.
              const dotBg =
                snapNone
                  ? 'gray.400'
                  : snapOk
                    ? 'green.500'
                    : (snapPct || 0) >= 50
                      ? 'orange.500'
                      : 'red.500';
              return (
                <Box key={r.date} w="10px" title={`${r.date}: ${r.symbol_count}/${total} (${Math.round(pct * 10) / 10}%)`}>
                  <Box w="10px" h={`${h}px`} borderRadius="sm" bg={colorForPct(pct)} />
                  <Box
                    mt="2px"
                    mx="auto"
                    w="6px"
                    h="6px"
                    borderRadius="full"
                    bg={dotBg}
                    title={
                      snapNone
                        ? `${r.date}: snapshots —`
                        : `${r.date}: snapshots ${Math.round((snapPct || 0) * 10) / 10}%`
                    }
                  />
                </Box>
              );
            })}
          </HStack>
        </Box>
        <Text mt={1} fontSize="xs" color="fg.muted">
          Histogram bars (daily, last {windowDays} trading days): height + color represent % of symbols with a stored 1d OHLCV bar on that date.
          Dot under each bar indicates technical snapshot coverage for that date (green ≥95%, orange ≥50%, red &lt;50%, gray = no snapshot run recorded).
        </Text>
      </Box>
    );
  }, [dailyFillDist, snapshotFillSeries]);

  return (
    <Box p={4}>
      <Heading size="md" mb={4}>Admin Dashboard</Heading>

      {coverage && (
        <CoverageSummaryCard hero={heroEffective} status={coverage.status}>
          <CoverageKpiGrid kpis={kpis} variant="stat" />
          <CoverageTrendGrid sparkline={sparkline} />
          <CoverageBucketsGrid groups={hero?.buckets || []} />
          {dailyFillDist.total > 0 ? (
            <Box mt={3} borderWidth="1px" borderColor="border.subtle" borderRadius="lg" p={3} bg="bg.muted">
              <HStack justify="space-between" align="start" flexWrap="wrap" gap={3}>
                <Box>
                  <Text fontSize="sm" fontWeight="semibold" color="fg.default">
                    Daily fill by date (1d OHLCV)
                  </Text>
                  <Text fontSize="xs" color="fg.muted">
                    {dailyFillDist.newestDate
                      ? `Newest date: ${dailyFillDist.newestDate} • ${dailyFillDist.newestCount}/${dailyFillDist.total} symbols`
                      : 'No daily bars found'}
                  </Text>
                </Box>
                <Badge variant="subtle" colorScheme="green">
                  {dailyFillDist.total > 0
                    ? `${Math.round((dailyFillDist.newestPct || 0) * 10) / 10}% filled on newest`
                    : '—'}
                </Badge>
              </HStack>
              {dailyHistogram}
              <Text mt={2} fontSize="xs" color="fg.muted">
                Hover a bar to see date, filled symbols, fill %, and snapshot %.
              </Text>
            </Box>
          ) : null}
          <Box mt={3} display="flex" alignItems="center" justifyContent="space-between" gap={3} flexWrap="wrap">
            <Box>
              <HStack gap={2} flexWrap="wrap">
                <Badge variant="subtle">Source: {String(coverage?.meta?.source || '—')}</Badge>
                <Badge variant="subtle">Last refresh: {formatDateTime(coverage?.meta?.updated_at, timezone)}</Badge>
                <Badge variant="subtle">Monitor: {fmtLastRun('monitor_coverage_health')}</Badge>
                <Badge variant="subtle">Restore: {fmtLastRun('bootstrap_daily_coverage_tracked')}</Badge>
              </HStack>
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
