import React from 'react';
import {
  Box,
  Heading,
  Text,
  HStack,
  Badge,
} from '@chakra-ui/react';
import toast from 'react-hot-toast';
import api from '../services/api';
import { useUserPreferences } from '../hooks/useUserPreferences';
import SortableTable, { type Column } from '../components/SortableTable';
import { formatMoney, formatDateTime } from '../utils/format';

const MarketTracked: React.FC = () => {
  const { timezone, currency } = useUserPreferences();
  const [rows, setRows] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState<boolean>(false);

  const load = async () => {
    if (loading) return;
    setLoading(true);
    try {
      const r = await api.get('/market-data/technical/snapshots?limit=5000');
      const out = (r as any)?.data?.rows;
      setRows(Array.isArray(out) ? out : []);
    } catch (err: any) {
      toast.error(err?.message || 'Failed to load tracked snapshot table');
      setRows([]);
    } finally {
      setLoading(false);
    }
  };
  React.useEffect(() => { load(); }, []);

  const columns = React.useMemo<Column<any>[]>(() => {
    const fmtNum = (v: any, digits = 2) =>
      typeof v === 'number' && Number.isFinite(v) ? v.toFixed(digits) : '—';
    const fmtPct = (v: any) =>
      typeof v === 'number' && Number.isFinite(v) ? `${Math.round(v * 10) / 10}%` : '—';
    const fmtX = (v: any) =>
      typeof v === 'number' && Number.isFinite(v) ? `${Math.round(v * 10) / 10}x` : '—';
    const fmtTs = (v: any) => (v ? formatDateTime(String(v), timezone) : '—');

    // Keep default view compact. Level 1–4 fields are still sortable and visible via horizontal scroll.
    return [
      { key: 'symbol', header: 'Symbol', accessor: (r) => r.symbol, sortable: true, sortType: 'string' },
      { key: 'as_of_timestamp', header: 'As of', accessor: (r) => r.as_of_timestamp || r.analysis_timestamp, sortable: true, sortType: 'date', render: (v) => fmtTs(v) },
      { key: 'current_price', header: 'Price', accessor: (r) => r.current_price, sortable: true, sortType: 'number', isNumeric: true, render: (v) => (typeof v === 'number' ? formatMoney(v, currency, { maximumFractionDigits: 2 }) : '—') },
      { key: 'market_cap', header: 'Mkt Cap', accessor: (r) => r.market_cap, sortable: true, sortType: 'number', isNumeric: true, render: (v) => (typeof v === 'number' ? Intl.NumberFormat('en', { notation: 'compact' }).format(v) : '—') },

      // Level 4
      { key: 'stage_label', header: 'Stage', accessor: (r) => r.stage_label, sortable: true, sortType: 'string' },
      { key: 'stage_label_5d_ago', header: 'Stage (5d ago)', accessor: (r) => r.stage_label_5d_ago, sortable: true, sortType: 'string' },

      // Level 3
      { key: 'rs_mansfield_pct', header: 'RS (Mansfield)', accessor: (r) => r.rs_mansfield_pct, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtPct(v) },

      // Level 1 ranges
      { key: 'range_pos_20d', header: 'Range 20d%', accessor: (r) => r.range_pos_20d, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtPct(v) },
      { key: 'range_pos_50d', header: 'Range 50d%', accessor: (r) => r.range_pos_50d, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtPct(v) },
      { key: 'range_pos_52w', header: 'Range 52w%', accessor: (r) => r.range_pos_52w, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtPct(v) },

      // Level 1 SMAs
      { key: 'sma_5', header: 'SMA 5', accessor: (r) => r.sma_5, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtNum(v) },
      { key: 'sma_14', header: 'SMA 14', accessor: (r) => r.sma_14, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtNum(v) },
      { key: 'sma_21', header: 'SMA 21', accessor: (r) => r.sma_21, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtNum(v) },
      { key: 'sma_50', header: 'SMA 50', accessor: (r) => r.sma_50, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtNum(v) },
      { key: 'sma_100', header: 'SMA 100', accessor: (r) => r.sma_100, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtNum(v) },
      { key: 'sma_150', header: 'SMA 150', accessor: (r) => r.sma_150, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtNum(v) },
      { key: 'sma_200', header: 'SMA 200', accessor: (r) => r.sma_200, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtNum(v) },

      // Level 1 EMAs
      { key: 'ema_8', header: 'EMA 8', accessor: (r) => r.ema_8, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtNum(v) },
      { key: 'ema_21', header: 'EMA 21', accessor: (r) => r.ema_21, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtNum(v) },

      // Level 1 ATRs + Level 2 ATR%
      { key: 'atr_14', header: 'ATR 14', accessor: (r) => r.atr_14, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtNum(v) },
      { key: 'atr_30', header: 'ATR 30', accessor: (r) => r.atr_30, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtNum(v) },
      { key: 'atrp_14', header: 'ATR% 14', accessor: (r) => r.atrp_14, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtPct(v) },
      { key: 'atrp_30', header: 'ATR% 30', accessor: (r) => r.atrp_30, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtPct(v) },

      // Level 2 ATR multiples
      { key: 'atrx_sma_21', header: '(P−SMA21)/ATR', accessor: (r) => r.atrx_sma_21, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtX(v) },
      { key: 'atrx_sma_50', header: '(P−SMA50)/ATR', accessor: (r) => r.atrx_sma_50, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtX(v) },
      { key: 'atrx_sma_100', header: '(P−SMA100)/ATR', accessor: (r) => r.atrx_sma_100, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtX(v) },
      { key: 'atrx_sma_150', header: '(P−SMA150)/ATR', accessor: (r) => r.atrx_sma_150, sortable: true, sortType: 'number', isNumeric: true, render: (v) => fmtX(v) },

      // Context
      { key: 'sector', header: 'Sector', accessor: (r) => r.sector, sortable: true, sortType: 'string' },
      { key: 'industry', header: 'Industry', accessor: (r) => r.industry, sortable: true, sortType: 'string' },
    ];
  }, [currency, timezone]);

  return (
    <Box p={4}>
      <HStack justify="space-between" align="end" mb={3} flexWrap="wrap" gap={2}>
        <Box>
          <Heading size="md">Market Tracked</Heading>
          <Text color="fg.muted" fontSize="sm">
            Latest technical snapshot per tracked symbol with Level 1–4 indicators. Click headers to sort.
          </Text>
        </Box>
        <Badge variant="subtle">{rows.length} rows</Badge>
      </HStack>

      <Box w="full" borderWidth="1px" borderColor="border.subtle" borderRadius="xl" bg="bg.card">
        <SortableTable
          data={rows}
          columns={columns}
          defaultSortBy="symbol"
          defaultSortOrder="asc"
          maxHeight="70vh"
          emptyMessage={loading ? 'Loading…' : 'No tracked symbols yet.'}
        />
      </Box>
    </Box>
  );
};

export default MarketTracked;

