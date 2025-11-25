import React from 'react';
import { Box, Heading, HStack, Button, Table, Thead, Tbody, Tr, Th, Td, Text, Stack, useToast, Badge } from '@chakra-ui/react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { triggerTaskByName } from '../utils/taskActions';

const AdminTracked: React.FC = () => {
  const [data, setData] = React.useState<any>({ all: [], new: [] });
  const [sortKey, setSortKey] = React.useState<'symbol' | 'market_cap' | 'stage'>('symbol');
  const [sortDir, setSortDir] = React.useState<'asc' | 'desc'>('asc');
  const toast = useToast();
  const { user } = useAuth();
  const canTrigger = user?.role === 'admin';

  const load = async () => {
    try {
      const r = await api.get('/market-data/tracked');
      setData(r.data || { all: [], new: [] });
    } catch { }
  };
  React.useEffect(() => { load(); }, []);

  const toggleSort = (column: 'symbol' | 'market_cap' | 'stage') => {
    if (sortKey === column) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(column);
      setSortDir('asc');
    }
  };

  const detailRows = React.useMemo(() => {
    const rows = (data.all || []).map((sym: string) => ({
      symbol: sym,
      ...(data.details?.[sym] || {}),
    }));
    return rows.sort((a: any, b: any) => {
      const direction = sortDir === 'asc' ? 1 : -1;
      if (sortKey === 'symbol') {
        return a.symbol.localeCompare(b.symbol) * direction;
      }
      if (sortKey === 'market_cap') {
        return ((a.market_cap || 0) - (b.market_cap || 0)) * direction;
      }
      return (a.stage_label || '').localeCompare(b.stage_label || '') * direction;
    });
  }, [data, sortKey, sortDir]);

  const runAction = async (taskName: string, label: string) => {
    try {
      await triggerTaskByName(taskName);
      toast({ title: `${label} triggered`, status: 'success', duration: 3000, isClosable: true });
      load();
    } catch (err: any) {
      toast({ title: `Failed to run ${label}`, description: err?.message || 'Unknown error', status: 'error', duration: 4000, isClosable: true });
    }
  };

  return (
    <Box p={4}>
      <Heading size="md" mb={4}>Tracked Symbols</Heading>
      {data?.meta?.education?.overview && (
        <Box mb={4}>
          <Text color="gray.400">{data.meta.education.overview}</Text>
          {(data.meta.education.details || []).map((line: string) => (
            <Text key={line} color="gray.500" fontSize="sm">• {line}</Text>
          ))}
        </Box>
      )}
      {canTrigger && (
        <>
          <HStack spacing={3} mb={4}>
            {(data?.meta?.actions || []).map((action: any) => (
              <Stack key={action.task_name} spacing={1}>
                <Button size="sm" onClick={() => runAction(action.task_name, action.label)}>{action.label}</Button>
                <Text fontSize="xs" color="gray.400" maxW="220px">{action.description}</Text>
              </Stack>
            ))}
          </HStack>
        </>
      )}
      <Heading size="sm" mb={2}>New</Heading>
      <Table size="sm" mb={6}>
        <Thead><Tr><Th>Symbol</Th></Tr></Thead>
        <Tbody>
          {(data.new || []).map((s: string) => (<Tr key={s}><Td>{s}</Td></Tr>))}
        </Tbody>
      </Table>
      <Heading size="sm" mb={2}>All</Heading>
      <Table size="sm">
        <Thead>
          <Tr>
            <Th cursor="pointer" onClick={() => toggleSort('symbol')}>Symbol</Th>
            <Th>Current Price</Th>
            <Th cursor="pointer" onClick={() => toggleSort('market_cap')}>Market Cap</Th>
            <Th cursor="pointer" onClick={() => toggleSort('stage')}>Stage</Th>
            <Th>ATR</Th>
            <Th>Sector / Industry</Th>
            <Th>Indices</Th>
          </Tr>
        </Thead>
        <Tbody>
          {detailRows.slice(0, 400).map((row: any) => (
            <Tr key={row.symbol}>
              <Td><Badge colorScheme="blue">{row.symbol}</Badge></Td>
              <Td>{row.current_price ? row.current_price.toFixed(2) : '—'}</Td>
              <Td>{row.market_cap ? Intl.NumberFormat('en', { notation: 'compact' }).format(row.market_cap) : '—'}</Td>
              <Td>{row.stage_label || '—'}</Td>
              <Td>{row.atr_value ? row.atr_value.toFixed(2) : '—'}</Td>
              <Td>
                <Text>{row.sector || '—'}</Text>
                <Text fontSize="xs" color="gray.500">{row.industry || ''}</Text>
              </Td>
              <Td>{(row.indices || []).join(', ') || '—'}</Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
      {(!data.all || data.all.length === 0) && <Text color="gray.400">No tracked symbols yet.</Text>}
    </Box>
  );
};

export default AdminTracked;


