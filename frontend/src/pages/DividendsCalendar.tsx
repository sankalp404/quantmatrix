import React from 'react';
import { Box, HStack, Text, Button, CardRoot, CardBody, Badge } from '@chakra-ui/react';
import { FiRefreshCw } from 'react-icons/fi';
import { useQuery } from 'react-query';
import SortableTable, { type Column } from '../components/SortableTable';
import { portfolioApi } from '../services/api';
import { useUserPreferences } from '../hooks/useUserPreferences';
import { formatMoney } from '../utils/format';

type DividendRow = any;

const DividendsCalendar: React.FC = () => {
  const { currency } = useUserPreferences();
  const q = useQuery(['dividends', 365], () => portfolioApi.getDividends(undefined, 365), {
    staleTime: 60_000,
    refetchInterval: 300_000,
  });

  const dividends: DividendRow[] = (q.data as any)?.data?.dividends || (q.data as any)?.dividends || [];

  const columns: Column<DividendRow>[] = [
    {
      key: 'symbol',
      header: 'Symbol',
      accessor: (d) => String(d?.symbol || d?.underlying_symbol || ''),
      sortable: true,
      sortType: 'string',
      render: (v) => (
        <Text fontFamily="mono" fontSize="12px">
          {String(v || '—')}
        </Text>
      ),
      width: '140px',
    },
    {
      key: 'ex_date',
      header: 'Ex-date',
      accessor: (d) => String(d?.ex_date || d?.exDate || ''),
      sortable: true,
      sortType: 'string',
      width: '160px',
    },
    {
      key: 'amount',
      header: 'Amount',
      accessor: (d) => Number(d?.amount ?? d?.cash_amount ?? 0),
      sortable: true,
      sortType: 'number',
      isNumeric: true,
      render: (v) => (
        <Text fontSize="12px" color="fg.muted">
          {formatMoney(Number(v || 0), currency, { maximumFractionDigits: 2 })}
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
            Dividends
          </Text>
          <Text fontSize="sm" color="fg.muted">
            v3-safe view
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
            <Text fontWeight="semibold">Rows</Text>
            <Badge colorPalette="gray">{dividends.length}</Badge>
          </HStack>
        </CardBody>
      </CardRoot>

      <Box w="full" borderWidth="1px" borderColor="border.subtle" borderRadius="xl" bg="bg.card">
        <SortableTable
          data={dividends}
          columns={columns}
          defaultSortBy="ex_date"
          defaultSortOrder="desc"
          size="sm"
          maxHeight="70vh"
          emptyMessage={q.isLoading ? 'Loading…' : 'No dividends found.'}
        />
      </Box>
    </Box>
  );
};

export default DividendsCalendar;


