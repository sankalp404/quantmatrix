import React from 'react';
import { Box, Heading, Table, Thead, Tbody, Tr, Th, Td, Text, useToast, Badge } from '@chakra-ui/react';
import api from '../services/api';

const MarketTracked: React.FC = () => {
  const [data, setData] = React.useState<any>({ all: [], details: {}, meta: {} });
  const [sortKey, setSortKey] = React.useState<'symbol' | 'market_cap' | 'stage'>('symbol');
  const [sortDir, setSortDir] = React.useState<'asc' | 'desc'>('asc');
  const toast = useToast();

  const load = async () => {
    try {
      const r = await api.get('/market-data/tracked');
      setData(r.data || { all: [], details: {}, meta: {} });
    } catch (err: any) {
      toast({ title: 'Failed to load tracked symbols', description: err?.message || 'Unknown error', status: 'error', duration: 3000, isClosable: true });
    }
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

  const sortArrow = (column: 'symbol' | 'market_cap' | 'stage') => {
    if (sortKey !== column) return '';
    return sortDir === 'asc' ? ' ▲' : ' ▼';
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

  const fmtNumber = (val: any, fraction = 2) => (typeof val === 'number' ? val.toFixed(fraction) : '—');
  const fmtCompact = (val: any) => (typeof val === 'number' ? Intl.NumberFormat('en', { notation: 'compact' }).format(val) : '—');

  return (
    <Box p={4}>
      <Heading size="md" mb={4}>Market Tracked</Heading>
      {data?.meta?.education?.overview && (
        <Box mb={4}>
          <Text color="gray.400" fontSize="sm">
            {data.meta.education.overview}
          </Text>
        </Box>
      )}
      <Table size="sm">
        <Thead>
          <Tr>
            <Th cursor="pointer" onClick={() => toggleSort('symbol')}>Symbol{sortArrow('symbol')}</Th>
            <Th>Current Price</Th>
            <Th cursor="pointer" onClick={() => toggleSort('market_cap')}>Market Cap{sortArrow('market_cap')}</Th>
            <Th cursor="pointer" onClick={() => toggleSort('stage')}>Stage{sortArrow('stage')}</Th>
            <Th>ATR</Th>
            <Th>Last Snapshot</Th>
            <Th>Sector / Industry</Th>
            <Th>Indices</Th>
          </Tr>
        </Thead>
        <Tbody>
          {detailRows.slice(0, 400).map((row: any) => (
            <Tr key={row.symbol}>
              <Td><Badge colorScheme="blue">{row.symbol}</Badge></Td>
              <Td>{fmtNumber(row.current_price)}</Td>
              <Td>{fmtCompact(row.market_cap)}</Td>
              <Td>{row.stage_label || '—'}</Td>
              <Td>{row.atr_value ? row.atr_value.toFixed(2) : '—'}</Td>
              <Td>{row.last_snapshot_at ? new Date(row.last_snapshot_at).toLocaleString() : '—'}</Td>
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

export default MarketTracked;

