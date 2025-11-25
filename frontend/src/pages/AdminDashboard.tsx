import React from 'react';
import { Box, Heading, SimpleGrid, Stat, StatLabel, StatNumber, StatHelpText, Button, HStack, Text, Stack, useToast } from '@chakra-ui/react';
import api from '../services/api';
import { triggerTaskByName } from '../utils/taskActions';

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

  const tile = (title: string, val: string | number | undefined, help?: string) => (
    <Stat p={4} border="1px solid" borderColor="gray.700" borderRadius="lg">
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

      {/* SLA banners */}
      {coverage && (
        <Box mb={4}>
          {(() => {
            const symCount = coverage.symbols || 0;
            const dailyCount = coverage.daily?.count || 0;
            const m5Count = coverage.m5?.count || 0;
            const dailyPct = symCount ? Math.round((dailyCount / symCount) * 100) : 0;
            const m5Pct = symCount ? Math.round((m5Count / symCount) * 100) : 0;
            const dailyOld = coverage.daily?.freshness?.['>48h'] || 0;
            const needsFix = symCount > 0 && (dailyPct < 90 || dailyOld > 0 || m5Pct === 0);
            if (!needsFix) return null;
            return (
              <Box p={3} border="1px solid" borderColor="yellow.700" borderRadius="md" bg="yellow.900" color="yellow.200">
                <HStack justify="space-between">
                  <Box>
                    <Heading size="sm">Action needed</Heading>
                    <Text fontSize="sm">Coverage/freshness below SLA. Daily {dailyPct}%, 5m {m5Pct}%. {dailyOld > 0 ? `${dailyOld} symbols >48h stale.` : ''}</Text>
                  </Box>
                  <HStack spacing={3} flexWrap="wrap">
                    {coverageActions.map((action) => (
                      <Stack key={action.task_name} spacing={1} align="flex-start">
                        <Button size="sm" onClick={() => runNamedTask(action.task_name, action.label)}>
                          {action.label}
                        </Button>
                        <Text fontSize="xs" color="gray.300" maxW="180px">{action.description}</Text>
                      </Stack>
                    ))}
                  </HStack>
                </HStack>
              </Box>
            );
          })()}
        </Box>
      )}

      <SimpleGrid columns={[1, 2, 3]} spacing={4} mb={6}>
        {tile('Tracked Symbols', coverage?.tracked_count, 'Universe size')}
        {tile('Daily Covered', coverage?.daily?.count, coverage?.symbols ? `${Math.round((coverage.daily.count / coverage.symbols) * 100)}%` : undefined)}
        {tile('5m Covered', coverage?.m5?.count, coverage?.symbols ? `${Math.round((coverage.m5.count / coverage.symbols) * 100)}%` : undefined)}
      </SimpleGrid>
      {coverage?.indices ? (
        <SimpleGrid columns={[1, 3, 3]} spacing={4} mb={6}>
          {tile('SP500 Members', coverage.indices.SP500)}
          {tile('NASDAQ100 Members', coverage.indices.NASDAQ100)}
          {tile('DOW30 Members', coverage.indices.DOW30)}
        </SimpleGrid>
      ) : null}

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


