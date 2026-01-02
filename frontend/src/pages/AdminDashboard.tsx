import React from 'react';
import { Box, Heading, Button, HStack, Text, useToast, Switch } from '@chakra-ui/react';
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
  const toast = useToast();
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
        toast({
          title: 'Coverage monitor scheduled (hourly)',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        await refreshCoverage();
      } catch (err: any) {
        toast({
          title: 'Failed to schedule monitor',
          description: err?.response?.data?.detail || err?.message || 'Unknown error',
          status: 'error',
          duration: 4000,
          isClosable: true,
        });
      }
      return;
    }
    try {
      await triggerTaskByName(taskName);
      toast({ title: label || taskName, description: 'Task triggered', status: 'success', duration: 3000, isClosable: true });
      await refreshCoverage();
    } catch (err: any) {
      toast({ title: `Failed to run ${label || taskName}`, description: err?.message || 'Unknown error', status: 'error', duration: 4000, isClosable: true });
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
      toast({
        title: `5m backfill ${flag ? 'enabled' : 'disabled'}`,
        status: 'success',
        duration: 2500,
        isClosable: true,
      });
      await refreshCoverage();
    } catch (err: any) {
      toast({
        title: 'Failed to update 5m backfill toggle',
        description: err?.response?.data?.detail || err?.message || 'Unknown error',
        status: 'error',
        duration: 4000,
        isClosable: true,
      });
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
          <HStack spacing={3} mt={3} align="center">
            <Switch
              isChecked={backfill5mEnabled}
              onChange={toggleBackfill5m}
              isDisabled={toggling5m}
              colorScheme="teal"
              size="md"
            />
            <Box>
              <Text fontSize="sm" fontWeight="medium">
                5m Backfill {backfill5mEnabled ? 'Enabled' : 'Disabled'}
              </Text>
              <Text fontSize="xs" color="gray.400">
                Daily backfill always runs. Toggle disables 5m tasks.
              </Text>
            </Box>
          </HStack>
        </CoverageSummaryCard>
      )}

      <Heading size="sm" mb={2}>Quick Actions</Heading>
      <CoverageActionsList
        actions={coverageActions}
        onRun={runNamedTask}
        buttonRenderer={(action, handleClick) => (
          <Button size="sm" onClick={handleClick} isDisabled={action.disabled}>
            {action.label}
          </Button>
        )}
      />
    </Box>
  );
};

export default AdminDashboard;
