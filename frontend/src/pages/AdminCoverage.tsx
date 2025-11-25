import React from 'react';
import { Box, Heading, Table, Thead, Tbody, Tr, Th, Td, Button, HStack, Text, SimpleGrid, Stack, useToast, Badge } from '@chakra-ui/react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { triggerTaskByName } from '../utils/taskActions';

const AdminCoverage: React.FC = () => {
  const [data, setData] = React.useState<any>(null);
  const [scheduling, setScheduling] = React.useState(false);
  const toast = useToast();
  const { user } = useAuth();
  const canTrigger = user?.role === 'admin';

  const load = async () => {
    try {
      const r = await api.get('/market-data/coverage');
      setData(r.data || null);
    } catch { }
  };
  React.useEffect(() => { load(); }, []);

  const runAction = async (taskName: string, label: string) => {
    try {
      await triggerTaskByName(taskName);
      toast({ title: `${label} triggered`, status: 'success', duration: 3000, isClosable: true });
      load();
    } catch (err: any) {
      toast({ title: `Failed to run ${label}`, description: err?.message || 'Unknown error', status: 'error', duration: 4000, isClosable: true });
    }
  };

  const formatTs = (value?: string | null) => (value ? new Date(value).toLocaleString() : '—');

  const staleDailySymbols = React.useMemo(() => {
    if (Array.isArray(data?.daily?.stale)) {
      return data.daily.stale;
    }
    return [];
  }, [data]);

  const scheduleMonitor = async () => {
    if (scheduling) return;
    setScheduling(true);
    try {
      await api.post('/admin/schedules', {
        name: 'monitor-coverage-health',
        task: 'backend.tasks.market_data_tasks.monitor_coverage_health',
        cron: '0 * * * *',
        timezone: 'UTC',
      });
      toast({ title: 'Coverage monitor scheduled (hourly)', status: 'success', duration: 3000, isClosable: true });
      load();
    } catch (err: any) {
      toast({
        title: 'Failed to schedule monitor',
        description: err?.response?.data?.detail || err?.message || 'Unknown error',
        status: 'error',
        duration: 4000,
        isClosable: true,
      });
    } finally {
      setScheduling(false);
    }
  };

  const missingFiveMinute = React.useMemo(() => {
    if (!Array.isArray(data?.m5?.stale)) return [];
    return data.m5.stale.filter((row: any) => row.bucket === 'none');
  }, [data]);

  return (
    <Box p={4}>
      <Heading size="md" mb={4}>Coverage</Heading>
      {data?.meta?.education?.coverage && (
        <Box mb={4}>
          <Text color="gray.400">{data.meta.education.coverage}</Text>
          {(data.meta.education.how_to_fix || []).map((line: string) => (
            <Text key={line} color="gray.500" fontSize="sm">• {line}</Text>
          ))}
        </Box>
      )}
      <SimpleGrid columns={[1, 2, 3]} spacing={4} mb={6}>
        <Box border="1px solid" borderColor="gray.700" borderRadius="md" p={3}>
          <Text fontSize="sm" color="gray.400">Tracked Symbols</Text>
          <Text fontSize="2xl" fontWeight="bold">{data?.tracked_count ?? '—'}</Text>
        </Box>
        <Box border="1px solid" borderColor="gray.700" borderRadius="md" p={3}>
          <Text fontSize="sm" color="gray.400">Daily Coverage</Text>
          <Text fontSize="2xl" fontWeight="bold">{data?.daily?.count ?? '—'}</Text>
          {data?.symbols ? <Text fontSize="xs" color="gray.500">{Math.round((data.daily.count / data.symbols) * 100)}%</Text> : null}
        </Box>
        <Box border="1px solid" borderColor="gray.700" borderRadius="md" p={3}>
          <Text fontSize="sm" color="gray.400">5m Coverage</Text>
          <Text fontSize="2xl" fontWeight="bold">{data?.m5?.count ?? '—'}</Text>
          {data?.symbols ? <Text fontSize="xs" color="gray.500">{Math.round((data.m5.count / data.symbols) * 100)}%</Text> : null}
        </Box>
      </SimpleGrid>
      {canTrigger && (
        <>
          <Heading size="sm" mb={2}>Quick Actions</Heading>
          <Button size="sm" mb={2} onClick={scheduleMonitor} isLoading={scheduling} alignSelf="flex-start">
            Schedule Coverage Monitor
          </Button>
          <HStack spacing={4} mb={6} flexWrap="wrap" align="flex-start">
            {(data?.meta?.actions || []).map((action: any) => (
              <Stack key={action.task_name} spacing={1} maxW="220px">
                <Button size="sm" onClick={() => runAction(action.task_name, action.label)}>
                  {action.label}
                </Button>
                <Text fontSize="xs" color="gray.400">{action.description}</Text>
              </Stack>
            ))}
          </HStack>
        </>
      )}
      <Heading size="sm" mb={1}>Snapshot</Heading>
      <Text color="gray.500" fontSize="xs" mb={4}>
        Refreshed at {data?.generated_at ? new Date(data.generated_at).toLocaleString() : '—'}
      </Text>
      <Heading size="sm" mb={2}>Stale (&gt;48h) Daily Bars</Heading>
      <Table size="sm" mb={6}>
        <Thead>
          <Tr>
            <Th>Symbol</Th>
            <Th>Last Daily</Th>
          </Tr>
        </Thead>
        <Tbody>
          {staleDailySymbols.map((row: any) => (
            <Tr key={`stale-${row.symbol}`}>
              <Td><Badge colorScheme="orange">{row.symbol}</Badge></Td>
              <Td>{formatTs(row.last)}</Td>
            </Tr>
          ))}
          {staleDailySymbols.length === 0 && (
            <Tr><Td colSpan={2}><Text color="gray.500">No stale symbols detected.</Text></Td></Tr>
          )}
        </Tbody>
      </Table>
      <Heading size="sm" mb={2}>Symbols Missing 5m Coverage</Heading>
      <Table size="sm" mb={6}>
        <Thead><Tr><Th>Symbol</Th></Tr></Thead>
        <Tbody>
          {missingFiveMinute.map((row: any) => (
            <Tr key={`m5-${row.symbol}`}><Td>{row.symbol}</Td></Tr>
          ))}
          {missingFiveMinute.length === 0 && (
            <Tr><Td><Text color="gray.500">All tracked samples have recent 5m data.</Text></Td></Tr>
          )}
        </Tbody>
      </Table>
      <Heading size="sm" mb={2}>Raw Snapshot</Heading>
      <Table size="sm">
        <Thead>
          <Tr>
            <Th>Symbol</Th>
            <Th>Last Daily</Th>
            <Th>Last 5m</Th>
          </Tr>
        </Thead>
        <Tbody>
          {Object.keys(data?.daily?.last || {}).slice(0, 150).map((sym) => (
            <Tr key={sym}>
              <Td>{sym}</Td>
              <Td>{formatTs(data.daily.last[sym])}</Td>
              <Td>{formatTs(data.m5.last[sym])}</Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
      {!data && <Text color="gray.400">No coverage yet.</Text>}
    </Box>
  );
};

export default AdminCoverage;


