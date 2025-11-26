import React from 'react';
import { Box, Heading, Table, Thead, Tbody, Tr, Th, Td, Button, HStack, Text, SimpleGrid, Stack, useToast, Badge, Divider } from '@chakra-ui/react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { triggerTaskByName } from '../utils/taskActions';
import Sparkline from '../components/charts/Sparkline';

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

  const coverageHistory = React.useMemo(() => data?.history || data?.meta?.history || [], [data]);
  const recentHistory = React.useMemo(() => [...coverageHistory].slice(-20).reverse(), [coverageHistory]);
  const statusInfo = data?.status || {};
  const statusColor =
    statusInfo.label === 'ok'
      ? 'green'
      : statusInfo.label === 'warning'
        ? 'yellow'
        : statusInfo.label === 'idle'
          ? 'gray'
          : 'orange';

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
      {data && (
        <Box border="1px solid" borderColor="surface.border" bg="surface.card" borderRadius="lg" p={4} mb={6}>
          <HStack justify="space-between" align="flex-start" flexWrap="wrap" gap={3}>
            <Stack spacing={1}>
              <Heading size="sm">Coverage status</Heading>
              <Text fontSize="sm" color="gray.400">{statusInfo.summary || 'No summary yet.'}</Text>
              <Text fontSize="xs" color="gray.500">
                Updated {data.meta?.updated_at ? new Date(data.meta.updated_at).toLocaleString() : '—'} ({data.meta?.source || 'db'})
              </Text>
            </Stack>
            <Badge colorScheme={statusColor} fontSize="sm" px={3} py={1} borderRadius="md">
              {(statusInfo.label || 'unknown').toUpperCase()}
            </Badge>
          </HStack>
          <Divider my={4} borderColor="surface.border" />
          <SimpleGrid columns={[1, 2, 4]} spacing={4}>
            <Box>
              <Text fontSize="sm" color="gray.400">Tracked Symbols</Text>
              <Text fontSize="2xl" fontWeight="bold">{data?.tracked_count ?? '—'}</Text>
              <Text fontSize="xs" color="gray.500">Universe size</Text>
            </Box>
            <Box>
              <Text fontSize="sm" color="gray.400">Daily Coverage %</Text>
              <Text fontSize="2xl" fontWeight="bold">{statusInfo.daily_pct ?? 0}%</Text>
              <Text fontSize="xs" color="gray.500">{data?.daily?.count ?? 0} bars</Text>
            </Box>
            <Box>
              <Text fontSize="sm" color="gray.400">5m Coverage %</Text>
              <Text fontSize="2xl" fontWeight="bold">{statusInfo.m5_pct ?? 0}%</Text>
              <Text fontSize="xs" color="gray.500">{data?.m5?.count ?? 0} bars</Text>
            </Box>
            <Box>
              <Text fontSize="sm" color="gray.400">Stale Symbols</Text>
              <Text fontSize="2xl" fontWeight="bold">{statusInfo.stale_daily ?? 0}</Text>
              <Text fontSize="xs" color="gray.500">{statusInfo.stale_m5 ?? 0} missing 5m</Text>
            </Box>
          </SimpleGrid>
          <SimpleGrid columns={[1, 2]} spacing={4} mt={4}>
            <Box>
              <Text fontSize="sm" color="gray.400" mb={1}>Daily coverage trend</Text>
              <Sparkline values={coverageHistory.map((entry: any) => Number(entry?.daily_pct ?? 0)).slice(-24)} color="green.400" />
            </Box>
            <Box>
              <Text fontSize="sm" color="gray.400" mb={1}>5m coverage trend</Text>
              <Sparkline values={coverageHistory.map((entry: any) => Number(entry?.m5_pct ?? 0)).slice(-24)} color="blue.300" />
            </Box>
          </SimpleGrid>
        </Box>
      )}
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
      {recentHistory.length > 0 && (
        <>
          <Heading size="sm" mb={2}>Recent Coverage Trend</Heading>
          <Table size="sm" mb={6}>
            <Thead>
              <Tr>
                <Th>Sampled</Th>
                <Th>Daily %</Th>
                <Th>5m %</Th>
                <Th>Stale Daily</Th>
                <Th>Stale 5m</Th>
                <Th>Status</Th>
              </Tr>
            </Thead>
            <Tbody>
              {recentHistory.map((entry: any, idx: number) => (
                <Tr key={`${entry.ts}-${idx}`}>
                  <Td>{entry.ts ? new Date(entry.ts).toLocaleString() : '—'}</Td>
                  <Td>{entry.daily_pct ?? '—'}</Td>
                  <Td>{entry.m5_pct ?? '—'}</Td>
                  <Td>{entry.stale_daily ?? 0}</Td>
                  <Td>{entry.stale_m5 ?? 0}</Td>
                  <Td><Badge colorScheme={entry.label === 'ok' ? 'green' : entry.label === 'warning' ? 'yellow' : 'orange'}>{(entry.label || '—').toUpperCase()}</Badge></Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </>
      )}
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


