import React from 'react';
import { Box, Heading, SimpleGrid, Stat, StatLabel, StatNumber, StatHelpText, Button, HStack, Text, Stack, useToast, Badge, Divider } from '@chakra-ui/react';
import api from '../services/api';
import { triggerTaskByName } from '../utils/taskActions';
import Sparkline from '../components/charts/Sparkline';

const AdminDashboard: React.FC = () => {
  const [statuses, setStatuses] = React.useState<any>({});
  const [coverage, setCoverage] = React.useState<any>(null);
  const toast = useToast();

  const load = async () => {
    try {
      const s = await api.get('/market-data/admin/tasks/status');
      setStatuses(s.data || {});
    } catch { }
    try {
      const c = await api.get('/market-data/coverage');
      setCoverage(c.data || null);
    } catch { }
  };

  React.useEffect(() => {
    load();
  }, []);

  const k = (key: string) => statuses?.[`taskstatus:${key}:last`];

  const coverageHistory = React.useMemo(() => {
    const list = coverage?.history || coverage?.meta?.history || [];
    return {
      daily: list.map((entry: any) => Number(entry?.daily_pct ?? 0)).slice(-24),
      m5: list.map((entry: any) => Number(entry?.m5_pct ?? 0)).slice(-24),
      labels: list.map((entry: any) => entry?.ts),
    };
  }, [coverage]);

  const coverageStatus = coverage?.status || {};
  const statusLabel = (coverageStatus.label || 'unknown').toUpperCase();
  const statusColor =
    coverageStatus.label === 'ok'
      ? 'green'
      : coverageStatus.label === 'warning'
        ? 'yellow'
        : coverageStatus.label === 'idle'
          ? 'gray'
          : 'orange';
  const updatedAt = coverage?.meta?.updated_at;

  const tile = (title: string, val: string | number | undefined, help?: string) => (
    <Stat p={4} border="1px solid" borderColor="surface.border" borderRadius="lg" bg="surface.card">
      <StatLabel>{title}</StatLabel>
      <StatNumber>{val ?? '—'}</StatNumber>
      {help ? <StatHelpText>{help}</StatHelpText> : null}
    </Stat>
  );

  const coverageActions = React.useMemo(() => {
    const base = coverage?.meta?.actions || [];
    const extras = [
      { label: 'Bootstrap Universe', task_name: 'bootstrap_universe', description: 'Runs refresh → tracked → backfills → recompute.' },
      { label: 'Recompute Indicators', task_name: 'recompute_indicators_universe', description: 'Builds DB snapshots for the tracked universe.' },
      { label: 'Record History', task_name: 'record_daily_history', description: 'Writes immutable MarketSnapshotHistory rows.' },
    ];
    return [...base, ...extras];
  }, [coverage]);

  const runNamedTask = async (taskName: string, label?: string) => {
    try {
      await triggerTaskByName(taskName);
      toast({ title: label || taskName, description: 'Task triggered', status: 'success', duration: 3000, isClosable: true });
      load();
    } catch (err: any) {
      toast({ title: `Failed to run ${label || taskName}`, description: err?.message || 'Unknown error', status: 'error', duration: 4000, isClosable: true });
    }
  };

  return (
    <Box p={4}>
      <Heading size="md" mb={4}>Admin Dashboard</Heading>

      {coverage && (
        <Box border="1px solid" borderColor="surface.border" bg="surface.card" borderRadius="lg" p={4} mb={6}>
          <HStack justify="space-between" align="flex-start" flexWrap="wrap" gap={3}>
            <Stack spacing={1}>
              <Heading size="sm">Coverage status</Heading>
              <Text fontSize="sm" color="gray.400">{coverageStatus.summary || 'No summary yet.'}</Text>
              <Text fontSize="xs" color="gray.500">
                Updated {updatedAt ? new Date(updatedAt).toLocaleString() : '—'} ({coverage?.meta?.source || 'db'})
              </Text>
            </Stack>
            <Badge colorScheme={statusColor} fontSize="sm" px={3} py={1} borderRadius="md">
              {statusLabel}
            </Badge>
          </HStack>
          <Divider my={4} borderColor="surface.border" />
          <SimpleGrid columns={[1, 2, 4]} spacing={4}>
            {tile('Tracked Symbols', coverage?.tracked_count, 'Universe size')}
            {tile('Daily Coverage %', `${coverageStatus.daily_pct ?? 0}%`, `Total bars: ${coverage?.daily?.count ?? 0}`)}
            {tile('5m Coverage %', `${coverageStatus.m5_pct ?? 0}%`, `Total bars: ${coverage?.m5?.count ?? 0}`)}
            {tile('Stale (>48h)', coverageStatus.stale_daily || 0, `${coverageStatus.stale_m5 || 0} missing 5m`)}
          </SimpleGrid>
          <SimpleGrid columns={[1, 2]} spacing={4} mt={4}>
            <Box>
              <Text fontSize="sm" color="gray.400" mb={1}>Daily coverage trend</Text>
              <Sparkline values={coverageHistory.daily} color="green.400" />
            </Box>
            <Box>
              <Text fontSize="sm" color="gray.400" mb={1}>5m coverage trend</Text>
              <Sparkline values={coverageHistory.m5} color="blue.300" />
            </Box>
          </SimpleGrid>
        </Box>
      )}

      <Heading size="sm" mb={2}>Quick Actions</Heading>
      <HStack spacing={4} align="flex-start" flexWrap="wrap" mb={6}>
        {coverageActions.map((action) => (
          <Stack key={`qa-${action.task_name}`} spacing={1} maxW="200px">
            <Button size="sm" onClick={() => runNamedTask(action.task_name, action.label)}>
              {action.label}
            </Button>
            <Text fontSize="xs" color="gray.400">{action.description}</Text>
          </Stack>
        ))}
      </HStack>

      <Heading size="sm" mb={2}>Last Task Runs</Heading>
      <Box p={4} border="1px solid" borderColor="gray.700" borderRadius="lg">
        {Object.entries(statuses || {}).map(([key, v]: any) => (
          <Box key={key} mb={3}>
            <Text fontSize="sm" color="gray.400">{key}</Text>
            <Text>{v?.status} at {v?.ts}</Text>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default AdminDashboard;


