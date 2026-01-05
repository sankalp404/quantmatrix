import React from 'react';
import { Box, Heading, Button, Text } from '@chakra-ui/react';
import toast from 'react-hot-toast';
import api from '../services/api';
import { triggerTaskByName } from '../utils/taskActions';
import useCoverageSnapshot from '../hooks/useCoverageSnapshot';
import {
  CoverageActionsList,
  CoverageBucketsGrid,
  CoverageKpiGrid,
  CoverageSummaryCard,
  CoverageTrendGrid,
} from '../components/coverage/CoverageSummaryCard';

const AdminDashboard: React.FC = () => {
  const [backfill5mEnabled, setBackfill5mEnabled] = React.useState<boolean>(true);
  const [toggling5m, setToggling5m] = React.useState<boolean>(false);
  const { snapshot: coverage, refresh: refreshCoverage, sparkline, kpis, actions: coverageActions, hero } = useCoverageSnapshot();

  React.useEffect(() => {
    if (coverage?.meta?.backfill_5m_enabled !== undefined) {
      setBackfill5mEnabled(Boolean(coverage.meta.backfill_5m_enabled));
    }
  }, [coverage]);

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

  return (
    <Box p={4}>
      <Heading size="md" mb={4}>Admin Dashboard</Heading>

      {coverage && (
        <CoverageSummaryCard hero={hero} status={coverage.status}>
          <CoverageKpiGrid kpis={kpis} variant="stat" />
          <CoverageTrendGrid sparkline={sparkline} />
          <CoverageBucketsGrid groups={hero?.buckets || []} />
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
                Daily backfill always runs. Toggle disables 5m tasks.
              </Text>
            </Box>
          </Box>
        </CoverageSummaryCard>
      )}

      <Heading size="sm" mb={2}>Quick Actions</Heading>
      <CoverageActionsList
        actions={coverageActions}
        onRun={runNamedTask}
        buttonRenderer={(action, handleClick) => (
          <Button size="sm" onClick={handleClick} disabled={action.disabled}>
            {action.label}
          </Button>
        )}
      />
    </Box>
  );
};

export default AdminDashboard;
