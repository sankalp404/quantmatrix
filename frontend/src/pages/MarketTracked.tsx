import React from 'react';
import {
  Box,
  Heading,
  Text,
  Badge,
  TableScrollArea,
  TableRoot,
  TableHeader,
  TableBody,
  TableRow,
  TableColumnHeader,
  TableCell,
} from '@chakra-ui/react';
import toast from 'react-hot-toast';
import api from '../services/api';
import { useUserPreferences } from '../hooks/useUserPreferences';
import { formatDateTime } from '../utils/format';

const MarketTracked: React.FC = () => {
  const { timezone } = useUserPreferences();
  const [data, setData] = React.useState<any>({ all: [], details: {}, meta: {} });
  const [sortKey, setSortKey] = React.useState<'symbol' | 'market_cap' | 'stage'>('symbol');
  const [sortDir, setSortDir] = React.useState<'asc' | 'desc'>('asc');

  const load = async () => {
    try {
      const r = await api.get('/market-data/tracked');
      setData(r.data || { all: [], details: {}, meta: {} });
    } catch (err: any) {
      toast.error(err?.message || 'Failed to load tracked symbols');
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
      <TableScrollArea>
        <TableRoot size="sm" variant="line">
          <TableHeader>
            <TableRow>
              <TableColumnHeader cursor="pointer" onClick={() => toggleSort('symbol')}>Symbol{sortArrow('symbol')}</TableColumnHeader>
              <TableColumnHeader>Current Price</TableColumnHeader>
              <TableColumnHeader cursor="pointer" onClick={() => toggleSort('market_cap')}>Market Cap{sortArrow('market_cap')}</TableColumnHeader>
              <TableColumnHeader cursor="pointer" onClick={() => toggleSort('stage')}>Stage{sortArrow('stage')}</TableColumnHeader>
              <TableColumnHeader>ATR</TableColumnHeader>
              <TableColumnHeader>Last Snapshot</TableColumnHeader>
              <TableColumnHeader>Sector / Industry</TableColumnHeader>
              <TableColumnHeader>Indices</TableColumnHeader>
            </TableRow>
          </TableHeader>
          <TableBody>
            {detailRows.slice(0, 400).map((row: any) => (
              <TableRow key={row.symbol}>
                <TableCell><Badge colorScheme="blue">{row.symbol}</Badge></TableCell>
                <TableCell>{fmtNumber(row.current_price)}</TableCell>
                <TableCell>{fmtCompact(row.market_cap)}</TableCell>
                <TableCell>{row.stage_label || '—'}</TableCell>
                <TableCell>{row.atr_value ? row.atr_value.toFixed(2) : '—'}</TableCell>
                <TableCell>{formatDateTime(row.last_snapshot_at, timezone)}</TableCell>
                <TableCell>
                  <Text>{row.sector || '—'}</Text>
                  <Text fontSize="xs" color="gray.500">{row.industry || ''}</Text>
                </TableCell>
                <TableCell>{(row.indices || []).join(', ') || '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </TableRoot>
      </TableScrollArea>
      {(!data.all || data.all.length === 0) && <Text color="gray.400">No tracked symbols yet.</Text>}
    </Box>
  );
};

export default MarketTracked;

