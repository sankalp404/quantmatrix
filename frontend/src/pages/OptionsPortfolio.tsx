import React from 'react';
import { Box, HStack, Text, Button, Badge, CardRoot, CardBody } from '@chakra-ui/react';
import { FiRefreshCw } from 'react-icons/fi';
import { usePortfolio } from '../hooks/usePortfolio';
import SortableTable, { type Column } from '../components/SortableTable';
import { useUserPreferences } from '../hooks/useUserPreferences';
import { formatMoney } from '../utils/format';

type AnyPos = any;

function isOptionPosition(p: AnyPos): boolean {
  const t = String(p?.instrument_type || p?.asset_class || p?.type || '').toLowerCase();
  return t.includes('option') || t.includes('opt');
}

const OptionsPortfolio: React.FC = () => {
  const q = usePortfolio();
  const data = (q.data as any) || {};
  const accounts = Object.values<any>(data?.accounts || {});
  const all: AnyPos[] = accounts.flatMap((a: any) => a?.all_positions || []);
  const options = all.filter(isOptionPosition);
  const { currency } = useUserPreferences();

  const columns: Column<AnyPos>[] = [
    {
      key: 'symbol',
      header: 'Symbol',
      accessor: (p) => String(p?.symbol || p?.underlying_symbol || p?.instrument?.symbol || ''),
      sortable: true,
      sortType: 'string',
      render: (v) => (
        <Text fontFamily="mono" fontSize="12px">
          {String(v || '—')}
        </Text>
      ),
      width: '160px',
    },
    {
      key: 'qty',
      header: 'Qty',
      accessor: (p) => Number(p?.quantity ?? p?.qty ?? 0),
      sortable: true,
      sortType: 'number',
      isNumeric: true,
      width: '90px',
    },
    {
      key: 'value',
      header: 'Value',
      accessor: (p) => Number(p?.market_value ?? p?.marketValue ?? p?.value ?? 0),
      sortable: true,
      sortType: 'number',
      isNumeric: true,
      render: (v) => (
        <Text fontSize="12px" color="fg.muted">
          {formatMoney(Number(v || 0), currency, { maximumFractionDigits: 0 })}
        </Text>
      ),
      width: '160px',
    },
    {
      key: 'pnl',
      header: 'P&L',
      accessor: (p) => Number(p?.unrealized_pnl ?? p?.unrealizedPnL ?? p?.pnl ?? 0),
      sortable: true,
      sortType: 'number',
      isNumeric: true,
      render: (v) => (
        <Text fontSize="12px" color={Number(v || 0) >= 0 ? 'green.500' : 'red.500'}>
          {formatMoney(Number(v || 0), currency, { maximumFractionDigits: 0 })}
        </Text>
      ),
      width: '160px',
    },
  ];

  return (
    <Box>
      <HStack justify="space-between" mb={3}>
        <Box>
          <Text fontSize="lg" fontWeight="semibold" color="fg.default">
            Options
          </Text>
          <Text fontSize="sm" color="fg.muted">
            v3-safe view (tables + paging standardized elsewhere)
          </Text>
        </Box>
        <Button size="sm" variant="outline" onClick={() => q.refetch()} loading={q.isFetching}>
          <FiRefreshCw />
          <Box as="span" ml={2}>
            Reload
          </Box>
        </Button>
      </HStack>

      <CardRoot bg="bg.card" borderWidth="1px" borderColor="border.subtle" borderRadius="xl" mb={3}>
        <CardBody>
          <HStack justify="space-between">
            <Text fontWeight="semibold">Positions</Text>
            <Badge colorPalette="gray">{options.length}</Badge>
          </HStack>
        </CardBody>
      </CardRoot>

      <Box w="full" borderWidth="1px" borderColor="border.subtle" borderRadius="xl" bg="bg.card">
        <SortableTable
          data={options}
          columns={columns}
          defaultSortBy="value"
          defaultSortOrder="desc"
          size="sm"
          maxHeight="70vh"
          emptyMessage={q.isLoading ? 'Loading…' : 'No option positions found.'}
        />
      </Box>
    </Box>
  );
};

export default OptionsPortfolio;


