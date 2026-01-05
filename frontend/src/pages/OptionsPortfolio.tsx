import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Container,
  Heading,
  VStack,
  HStack,
  Text,
  Card,
  CardBody,
  CardHeader,
  SimpleGrid,
  Badge,
  Button,
  Select,
  Input,
  InputGroup,
  InputElement,
  TabsRoot,
  TabsList,
  TabsTrigger,
  TabsContent,
  StatRoot,
  StatLabel,
  StatHelpText,
  StatValueText,
  StatUpIndicator,
  StatDownIndicator,
  Spinner,
  AlertRoot,
  AlertIndicator,
  Flex,
  Icon,
  Tooltip,
  Progress,
  MenuRoot,
  MenuTrigger,
  MenuContent,
  MenuItem,
  IconButton,
  TableScrollArea,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Avatar,
  Stack,
  Tag,
  TagLabel,
  TagCloseButton,
} from '@chakra-ui/react';
import AppDivider from '../components/ui/AppDivider';
import toast from 'react-hot-toast';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  LineChart,
  Line,
} from 'recharts';
import {
  FiCalendar,
  FiChevronDown,
  FiDownload,
  FiInfo,
  FiRefreshCw,
  FiSearch,
  FiSettings,
} from 'react-icons/fi';
import {
  FiTrendingUp,
  FiTrendingDown,
  FiDollarSign,
  FiPercent,
  FiClock,
  FiTarget,
  FiFilter,
  FiArrowUp,
  FiArrowDown,
} from 'react-icons/fi';
import { portfolioApi } from '../services/api';
import useFlexQuery from '../hooks/useFlexQuery';
import SortableTable, { Column } from '../components/SortableTable';
import AccountFilterWrapper from '../components/AccountFilterWrapper';
import { transformPortfolioToAccounts } from '../hooks/useAccountFilter';
import EmptyState from '../components/ui/EmptyState';
import { useAccountContext } from '../context/AccountContext';

interface OptionPosition {
  id: string;
  symbol: string;
  underlying_symbol: string;
  strike_price: number;
  expiration_date: string;
  option_type: 'call' | 'put';
  quantity: number;
  average_open_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  day_pnl: number;
  account_number: string;
  days_to_expiration: number;
  multiplier: number;
  last_updated: string;
}

interface OptionsSummary {
  total_positions: number;
  total_market_value: number;
  total_unrealized_pnl: number;
  total_unrealized_pnl_pct: number;
  total_day_pnl: number;
  total_day_pnl_pct: number;
  calls_count: number;
  puts_count: number;
  expiring_this_week: number;
  expiring_this_month: number;
  underlyings_count: number;
  avg_days_to_expiration: number;
  underlyings: string[];
}

interface UnderlyingGroup {
  calls: OptionPosition[];
  puts: OptionPosition[];
  total_value: number;
  total_pnl: number;
}

// Enhanced Underlying Card Component
const UnderlyingCard: React.FC<{
  symbol: string;
  data: UnderlyingGroup;
  isExpanded?: boolean;
  onToggle?: () => void;
}> = ({ symbol, data, isExpanded = false, onToggle }) => {
  const cardBg = 'gray.800';
  const borderColor = 'gray.600';
  const profitColor = data.total_pnl >= 0 ? 'green.500' : 'red.500';

  // Calculate additional metrics
  const totalPositions = data.calls.length + data.puts.length;
  const callsValue = data.calls.reduce((sum, call) => sum + call.market_value, 0);
  const putsValue = data.puts.reduce((sum, put) => sum + put.market_value, 0);
  const callsPnL = data.calls.reduce((sum, call) => sum + call.unrealized_pnl, 0);
  const putsPnL = data.puts.reduce((sum, put) => sum + put.unrealized_pnl, 0);

  // Average days to expiration
  const avgDaysToExp = totalPositions > 0
    ? Math.round([...data.calls, ...data.puts].reduce((sum, pos) => sum + pos.days_to_expiration, 0) / totalPositions)
    : 0;

  // Get most significant positions
  const significantCalls = data.calls
    .sort((a, b) => Math.abs(b.unrealized_pnl) - Math.abs(a.unrealized_pnl))
    .slice(0, 3);

  const significantPuts = data.puts
    .sort((a, b) => Math.abs(b.unrealized_pnl) - Math.abs(a.unrealized_pnl))
    .slice(0, 3);

  return (
    <Card
      bg={cardBg}
      borderColor={borderColor}
      p={4}
      transition="all 0.2s"
      _hover={{ shadow: 'md', transform: 'translateY(-1px)' }}
      cursor={onToggle ? "pointer" : "default"}
      onClick={onToggle}
    >
      <CardBody p={0}>
        <VStack spacing={4} align="stretch">
          {/* Header */}
          <Flex justify="space-between" align="center">
            <HStack spacing={3}>
              <Avatar
                size="sm"
                name={symbol}
                bg="blue.500"
                color="white"
                fontWeight="bold"
              />
              <VStack align="start" spacing={0}>
                <Text fontSize="lg" fontWeight="bold">{symbol}</Text>
                <HStack spacing={2}>
                  <Badge colorScheme="blue" size="sm">{totalPositions} positions</Badge>
                  <Badge variant="outline" size="sm">
                    <Icon as={FiClock} mr={1} />
                    {avgDaysToExp}d avg
                  </Badge>
                </HStack>
              </VStack>
            </HStack>

            <VStack align="end" spacing={1}>
              <Text fontSize="xl" fontWeight="bold">
                ${data.total_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </Text>
              <Text
                fontSize="sm"
                fontWeight="bold"
                color={profitColor}
              >
                {data.total_pnl >= 0 ? '+' : ''}${data.total_pnl.toFixed(2)}
              </Text>
              <Text fontSize="xs" color="gray.500">P&L</Text>
            </VStack>
          </Flex>

          {/* Calls vs Puts Overview */}
          <SimpleGrid columns={2} spacing={4}>
            {/* Calls Section */}
            <Box
              p={3}
              bg={'green.900'}
              borderRadius="md"
              border="1px solid"
              borderColor={'green.700'}
            >
              <VStack align="start" spacing={2}>
                <HStack justify="space-between" width="full">
                  <Text fontSize="sm" fontWeight="bold" color="green.600">
                    <Icon as={FiArrowUp} mr={1} />
                    CALLS ({data.calls.length})
                  </Text>
                  <Text fontSize="sm" fontWeight="medium">
                    ${callsValue.toFixed(2)}
                  </Text>
                </HStack>

                {data.calls.length > 0 && (
                  <VStack spacing={1} align="stretch" width="full">
                    {significantCalls.map((call) => (
                      <HStack key={call.id} justify="space-between" fontSize="xs">
                        <Text>
                          ${call.strike_price} • {call.days_to_expiration}d
                        </Text>
                        <Text
                          color={call.unrealized_pnl >= 0 ? 'green.600' : 'red.500'}
                          fontWeight="medium"
                        >
                          {call.unrealized_pnl >= 0 ? '+' : ''}${call.unrealized_pnl.toFixed(0)}
                        </Text>
                      </HStack>
                    ))}
                    {data.calls.length > 3 && (
                      <Text fontSize="xs" color="gray.500" textAlign="center">
                        +{data.calls.length - 3} more calls
                      </Text>
                    )}
                  </VStack>
                )}

                {data.calls.length === 0 && (
                  <Text fontSize="xs" color="gray.500" fontStyle="italic">
                    No call positions
                  </Text>
                )}

                <Text
                  fontSize="xs"
                  fontWeight="bold"
                  color={callsPnL >= 0 ? 'green.600' : 'red.500'}
                >
                  Total: {callsPnL >= 0 ? '+' : ''}${callsPnL.toFixed(2)}
                </Text>
              </VStack>
            </Box>

            {/* Puts Section */}
            <Box
              p={3}
              bg={'red.900'}
              borderRadius="md"
              border="1px solid"
              borderColor={'red.700'}
            >
              <VStack align="start" spacing={2}>
                <HStack justify="space-between" width="full">
                  <Text fontSize="sm" fontWeight="bold" color="red.600">
                    <Icon as={FiArrowDown} mr={1} />
                    PUTS ({data.puts.length})
                  </Text>
                  <Text fontSize="sm" fontWeight="medium">
                    ${putsValue.toFixed(2)}
                  </Text>
                </HStack>

                {data.puts.length > 0 && (
                  <VStack spacing={1} align="stretch" width="full">
                    {significantPuts.map((put) => (
                      <HStack key={put.id} justify="space-between" fontSize="xs">
                        <Text>
                          ${put.strike_price} • {put.days_to_expiration}d
                        </Text>
                        <Text
                          color={put.unrealized_pnl >= 0 ? 'green.600' : 'red.500'}
                          fontWeight="medium"
                        >
                          {put.unrealized_pnl >= 0 ? '+' : ''}${put.unrealized_pnl.toFixed(0)}
                        </Text>
                      </HStack>
                    ))}
                    {data.puts.length > 3 && (
                      <Text fontSize="xs" color="gray.500" textAlign="center">
                        +{data.puts.length - 3} more puts
                      </Text>
                    )}
                  </VStack>
                )}

                {data.puts.length === 0 && (
                  <Text fontSize="xs" color="gray.500" fontStyle="italic">
                    No put positions
                  </Text>
                )}

                <Text
                  fontSize="xs"
                  fontWeight="bold"
                  color={putsPnL >= 0 ? 'green.600' : 'red.500'}
                >
                  Total: {putsPnL >= 0 ? '+' : ''}${putsPnL.toFixed(2)}
                </Text>
              </VStack>
            </Box>
          </SimpleGrid>

          {/* Expanded Details */}
          {isExpanded && (
            <Box mt={4}>
              <AppDivider mb={4} />
              <Text fontSize="sm" fontWeight="semibold" mb={3}>All Positions</Text>

              <TableScrollArea>
                <Table size="sm">
                  <Thead>
                    <Tr>
                      <Th>Type</Th>
                      <Th>Strike</Th>
                      <Th>Exp</Th>
                      <Th>Qty</Th>
                      <Th isNumeric>Value</Th>
                      <Th isNumeric>P&L</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {[...data.calls, ...data.puts]
                      .sort((a, b) => a.days_to_expiration - b.days_to_expiration)
                      .map((position) => (
                        <Tr key={position.id}>
                          <Td>
                            <Badge
                              size="sm"
                              colorScheme={position.option_type === 'call' ? 'green' : 'red'}
                            >
                              {position.option_type.toUpperCase()}
                            </Badge>
                          </Td>
                          <Td>${position.strike_price}</Td>
                          <Td>
                            <Text fontSize="xs">
                              {position.days_to_expiration}d
                            </Text>
                          </Td>
                          <Td>{position.quantity}</Td>
                          <Td isNumeric>${position.market_value.toFixed(2)}</Td>
                          <Td isNumeric>
                            <Text color={position.unrealized_pnl >= 0 ? 'green.500' : 'red.500'}>
                              {position.unrealized_pnl >= 0 ? '+' : ''}${position.unrealized_pnl.toFixed(2)}
                            </Text>
                          </Td>
                        </Tr>
                      ))}
                  </Tbody>
                </Table>
              </TableScrollArea>
            </Box>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
};

const OptionsPortfolio: React.FC = () => {
  const { selected, setSelected } = useAccountContext();
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [positions, setPositions] = useState<OptionPosition[]>([]);
  const [summary, setSummary] = useState<OptionsSummary | null>(null);
  const [underlyings, setUnderlyings] = useState<Record<string, UnderlyingGroup>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'calls' | 'puts'>('all');
  const [sortBy, setSortBy] = useState<string>('days_to_expiration');
  const [expandedUnderlyings, setExpandedUnderlyings] = useState<Set<string>>(new Set());
  const [selectedAccountSSR, setSelectedAccountSSR] = useState<string | undefined>(undefined);
  const [activity, setActivity] = useState<any[]>([]);

  const cardBg = 'gray.800';
  const borderColor = 'gray.600';
  const { status: flexStatus, loading: flexLoading, error: flexError, refresh: refreshFlex, syncTaxLots } = useFlexQuery();

  useEffect(() => {
    const param = selected === 'all' || selected === 'taxable' || selected === 'ira' ? undefined : selected;
    fetchOptionsData(param);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  const fetchOptionsData = async (selectedAccount?: string) => {
    setLoading(true);
    setError(null);
    try {
      // Fetch portfolio data for account selector
      const portfolioResult = await portfolioApi.getLive();
      setPortfolioData(portfolioResult.data);

      // Fetch options data using unified API with account filtering (axios baseURL aware)
      const [optionsPortfolioResult, optionsSummaryResult] = await Promise.all([
        (await fetch(selectedAccount ? `/api/v1/portfolio/options/unified/portfolio?account_id=${selectedAccount}` : '/api/v1/portfolio/options/unified/portfolio')).json(),
        (await fetch(selectedAccount ? `/api/v1/portfolio/options/unified/summary?account_id=${selectedAccount}` : '/api/v1/portfolio/options/unified/summary')).json(),
      ]);

      if (optionsPortfolioResult.status === 'success') {
        setPositions(optionsPortfolioResult.data.positions || []);
        setUnderlyings(optionsPortfolioResult.data.underlyings || {});

        // Log if filtering was applied
        if (optionsPortfolioResult.data.filtering?.applied) {
          console.log(`✅ Options filtered by account: ${selectedAccount}`, optionsPortfolioResult.data.filtering);
        }
      } else {
        const errorMessage = typeof optionsPortfolioResult.error === 'string'
          ? optionsPortfolioResult.error
          : JSON.stringify(optionsPortfolioResult.error) || 'Failed to load options data';
        setError(errorMessage);
      }

      if (optionsSummaryResult.status === 'success') {
        setSummary(optionsSummaryResult.data.summary || {});

        // Log if summary filtering was applied
        if (optionsSummaryResult.data.filtering?.applied) {
          console.log(`✅ Options summary filtered by account: ${selectedAccount}`, optionsSummaryResult.data.filtering);
        }
      } else {
        console.warn('Failed to load options summary:', optionsSummaryResult.error);
        setSummary(null); // Use null as fallback to match type
      }

      // Fetch recent transactions for activity panel (filter to options)
      try {
        const tx = await portfolioApi.getStatements(selectedAccount, 365);
        const rows = tx?.data?.transactions || [];
        const optionRows = rows.filter((r: any) => {
          const ct = (r.contract_type || r.asset_category || '').toString().toUpperCase();
          return ct.includes('OPT') || ct.includes('OPTION');
        });
        setActivity(optionRows);
      } catch (e) {
        console.warn('Activity fetch failed');
        setActivity([]);
      }
    } catch (error: any) {
      console.error('Error fetching options data:', error);
      const errorMessage = typeof error === 'string' ? error : error?.message || 'Failed to load options data';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Toggle underlying expansion
  const toggleUnderlying = (symbol: string) => {
    const newExpanded = new Set(expandedUnderlyings);
    if (newExpanded.has(symbol)) {
      newExpanded.delete(symbol);
    } else {
      newExpanded.add(symbol);
    }
    setExpandedUnderlyings(newExpanded);
  };

  // Wrapper function for click handlers that don't need account filtering
  const handleRefresh = () => {
    fetchOptionsData(selectedAccountSSR);
  };

  // Note: Filtering and sorting is now handled inside AccountFilterWrapper

  // Enhanced data for charts
  const typeDistribution = useMemo(() => {
    const calls = positions.filter(p => p.option_type === 'call');
    const puts = positions.filter(p => p.option_type === 'put');

    return [
      {
        name: 'Calls',
        value: calls.reduce((sum, call) => sum + Math.abs(call.market_value), 0),
        count: calls.length,
        color: '#48BB78'
      },
      {
        name: 'Puts',
        value: puts.reduce((sum, put) => sum + Math.abs(put.market_value), 0),
        count: puts.length,
        color: '#F56565'
      }
    ];
  }, [positions]);

  const underlyingDistribution = useMemo(() => {
    return Object.entries(underlyings)
      .map(([symbol, data], index) => ({
        name: symbol,
        value: Math.abs(data.total_value),
        pnl: data.total_pnl,
        positions: data.calls.length + data.puts.length,
        color: `hsl(${(index * 50) % 360}, 60%, 60%)`
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 10); // Top 10 underlyings
  }, [underlyings]);

  // Transform portfolio data for account selector
  const accounts = portfolioData ? transformPortfolioToAccounts(portfolioData) : [];

  // Options table columns
  const optionsColumns: Column<OptionPosition>[] = [
    {
      key: 'underlying_symbol',
      header: 'Underlying',
      accessor: (item) => item.underlying_symbol,
      sortable: true,
      sortType: 'string',
      render: (value, item) => (
        <VStack align="start" spacing={1}>
          <Text fontWeight="bold">{value}</Text>
          <Badge
            size="sm"
            colorScheme={item.option_type === 'call' ? 'green' : 'red'}
          >
            {item.option_type.toUpperCase()}
          </Badge>
        </VStack>
      ),
    },
    {
      key: 'strike_price',
      header: 'Strike',
      accessor: (item) => item.strike_price,
      sortable: true,
      sortType: 'number',
      isNumeric: true,
      render: (value) => `$${value}`,
    },
    {
      key: 'days_to_expiration',
      header: 'DTE',
      accessor: (item) => item.days_to_expiration,
      sortable: true,
      sortType: 'number',
      isNumeric: true,
      render: (value) => (
        <Badge
          colorScheme={value <= 7 ? 'red' : value <= 30 ? 'orange' : 'green'}
          variant="subtle"
        >
          {value}d
        </Badge>
      ),
    },
    {
      key: 'quantity',
      header: 'Qty',
      accessor: (item) => item.quantity,
      sortable: true,
      sortType: 'number',
      isNumeric: true,
    },
    {
      key: 'current_price',
      header: 'Price',
      accessor: (item) => item.current_price,
      sortable: true,
      sortType: 'number',
      isNumeric: true,
      render: (value) => `$${value.toFixed(2)}`,
    },
    {
      key: 'market_value',
      header: 'Market Value',
      accessor: (item) => item.market_value,
      sortable: true,
      sortType: 'number',
      isNumeric: true,
      render: (value) => `$${value.toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
    },
    {
      key: 'unrealized_pnl',
      header: 'Unrealized P&L',
      accessor: (item) => item.unrealized_pnl,
      sortable: true,
      sortType: 'number',
      isNumeric: true,
      render: (value, item) => (
        <VStack align="end" spacing={0}>
          <Text color={value >= 0 ? 'green.500' : 'red.500'} fontWeight="medium">
            {value >= 0 ? '+' : ''}${value.toFixed(2)}
          </Text>
          <Text fontSize="xs" color={item.unrealized_pnl_pct >= 0 ? 'green.500' : 'red.500'}>
            ({item.unrealized_pnl_pct >= 0 ? '+' : ''}{item.unrealized_pnl_pct.toFixed(1)}%)
          </Text>
        </VStack>
      ),
    },
  ];

  if (loading) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={8} align="stretch">
          <HStack justify="space-between">
            <Heading size="lg">Options Portfolio</Heading>
            <Spinner size="lg" />
          </HStack>
        </VStack>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxW="container.xl" py={8}>
        <AlertRoot status="error">
          <AlertIndicator />
          <Box flex="1">
            <Text fontWeight="bold">Failed to load options portfolio</Text>
            <Text fontSize="sm">{typeof error === 'string' ? error : 'An error occurred'}</Text>
          </Box>
          <Button ml={4} onClick={handleRefresh} size="sm">
            Retry
          </Button>
        </AlertRoot>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Empty state for no positions */}
        {positions.length === 0 && (
          <EmptyState
            icon={FiTarget}
            title="No options positions found"
            description="We couldn’t find any open options in your FlexQuery report. Ensure your Activity Flex Query includes the Open Positions section with derivatives and quantity fields enabled. Once updated, run the sync again."
            action={{ label: 'Refresh', onClick: handleRefresh }}
            secondaryAction={{ label: 'Open API Docs', onClick: () => window.open('/docs', '_blank') }}
          />
        )}
        {/* Header */}
        <Box>
          <HStack justify="space-between" mb={4}>
            <VStack align="start" spacing={1}>
              <Heading size="lg">Options Portfolio</Heading>
              <Text color="gray.600">
                {positions.length} total positions • {Object.keys(underlyings).length} underlyings
              </Text>
              {/* FlexQuery status badge */}
              {flexStatus && (
                <HStack>
                  <Badge colorScheme={flexStatus.configured ? 'green' : 'yellow'}>
                    FlexQuery: {flexStatus.configured ? 'Configured' : 'Setup Required'}
                  </Badge>
                  {!flexStatus.configured && (
                    <Tooltip label="Open backend /docs to configure FlexQuery token & query id">
                      <FiInfo color="gray.500" />
                    </Tooltip>
                  )}
                </HStack>
              )}
            </VStack>
            <HStack spacing={3}>
              <Button leftIcon={<FiRefreshCw />} size="sm" variant="outline" onClick={handleRefresh}>
                Refresh
              </Button>
              <Button
                size="sm"
                variant="solid"
                colorScheme="blue"
                isLoading={flexLoading}
                onClick={async () => {
                  try {
                    const account = selectedAccountSSR || accounts?.[0]?.account_id;
                    if (!account) {
                      toast.error('No account selected');
                      return;
                    }
                    const res: any = await syncTaxLots(account);
                    if (res?.success) toast.success(res?.message || 'Tax lots synced');
                    else toast(res?.message || 'Tax lots synced');
                    refreshFlex();
                  } catch (e: any) {
                    toast.error(e?.message || 'Sync failed');
                  }
                }}
              >
                Sync Official Tax Lots
              </Button>
              <Button leftIcon={<FiDownload />} size="sm" variant="outline">
                Export
              </Button>
            </HStack>
          </HStack>
        </Box>



        {/* Portfolio Filter Wrapper */}
        <AccountFilterWrapper
          data={positions}
          accounts={accounts}
          loading={loading}
          error={error}
          config={{
            showAllOption: true,
            showSummary: true,
            variant: 'detailed',
            size: 'md',
            // default to first account
            defaultSelection: selected || (accounts.length > 0 ? accounts[0].account_id : 'all')
          }}
          onAccountChange={(accountId) => {
            setSelected(accountId as any);
            const param = accountId === 'all' || accountId === 'taxable' || accountId === 'ira' ? undefined : accountId;
            setSelectedAccountSSR(param);
            fetchOptionsData(param);
          }}
        >
          {(accountFilteredPositions, filterState) => {
            // Use filtered positions directly instead of triggering new API calls
            // The filtering is already handled by AccountFilterWrapper

            // Filter positions without pre-sorting (let SortableTable handle sorting)
            const filteredPositions = useMemo(() => {
              return accountFilteredPositions.filter(position => {
                const matchesSearch = position.underlying_symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
                  position.symbol.toLowerCase().includes(searchTerm.toLowerCase());
                const matchesType = filterType === 'all' ||
                  (filterType === 'calls' && position.option_type === 'call') ||
                  (filterType === 'puts' && position.option_type === 'put');
                return matchesSearch && matchesType;
              });
            }, [accountFilteredPositions, searchTerm, filterType]);

            // Recalculate underlyings based on filtered positions
            const filteredUnderlyings = useMemo(() => {
              const underlyingsMap: Record<string, UnderlyingGroup> = {};
              filteredPositions.forEach(position => {
                if (!underlyingsMap[position.underlying_symbol]) {
                  underlyingsMap[position.underlying_symbol] = { calls: [], puts: [], total_value: 0, total_pnl: 0 };
                }

                if (position.option_type === 'call') {
                  underlyingsMap[position.underlying_symbol].calls.push(position);
                } else {
                  underlyingsMap[position.underlying_symbol].puts.push(position);
                }

                underlyingsMap[position.underlying_symbol].total_value += position.market_value;
                underlyingsMap[position.underlying_symbol].total_pnl += position.unrealized_pnl;
              });
              return underlyingsMap;
            }, [filteredPositions]);

            // Calculate dynamic summary from filtered positions
            const filteredSummary = useMemo(() => {
              if (filteredPositions.length === 0) {
                return {
                  total_positions: 0,
                  total_market_value: 0,
                  total_unrealized_pnl: 0,
                  total_unrealized_pnl_pct: 0,
                  total_day_pnl: 0,
                  calls_count: 0,
                  puts_count: 0
                };
              }

              const totalValue = filteredPositions.reduce((sum, pos) => sum + pos.market_value, 0);
              const totalPnL = filteredPositions.reduce((sum, pos) => sum + pos.unrealized_pnl, 0);
              const totalDayPnL = filteredPositions.reduce((sum, pos) => sum + pos.day_pnl, 0);
              const callsCount = filteredPositions.filter(pos => pos.option_type === 'call').length;
              const putsCount = filteredPositions.filter(pos => pos.option_type === 'put').length;

              return {
                total_positions: filteredPositions.length,
                total_market_value: totalValue,
                total_unrealized_pnl: totalPnL,
                total_unrealized_pnl_pct: totalValue > 0 ? (totalPnL / totalValue) * 100 : 0,
                total_day_pnl: totalDayPnL,
                calls_count: callsCount,
                puts_count: putsCount
              };
            }, [filteredPositions]);

            return (
              <VStack spacing={4} align="stretch">
                {/* Dynamic Summary Cards - Updates with filtering */}
                <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
                  <StatRoot>
                    <StatLabel>Filtered Value</StatLabel>
                    <StatValueText>${filteredSummary.total_market_value.toLocaleString()}</StatValueText>
                    <StatHelpText>Market value</StatHelpText>
                  </StatRoot>
                  <StatRoot>
                    <StatLabel>Unrealized P&L</StatLabel>
                    <StatValueText color={filteredSummary.total_unrealized_pnl >= 0 ? 'green.500' : 'red.500'}>
                      {filteredSummary.total_unrealized_pnl >= 0 ? '+' : ''}${filteredSummary.total_unrealized_pnl.toFixed(2)}
                    </StatValueText>
                    <StatHelpText>
                      {filteredSummary.total_unrealized_pnl >= 0 ? <StatUpIndicator /> : <StatDownIndicator />}
                      {filteredSummary.total_unrealized_pnl_pct.toFixed(2)}%
                    </StatHelpText>
                  </StatRoot>
                  <StatRoot>
                    <StatLabel>Day P&L</StatLabel>
                    <StatValueText color={filteredSummary.total_day_pnl >= 0 ? 'green.500' : 'red.500'}>
                      {filteredSummary.total_day_pnl >= 0 ? '+' : ''}${filteredSummary.total_day_pnl.toFixed(2)}
                    </StatValueText>
                    <StatHelpText>Today's change</StatHelpText>
                  </StatRoot>
                  <StatRoot>
                    <StatLabel>Positions</StatLabel>
                    <StatValueText>{filteredSummary.total_positions}</StatValueText>
                    <StatHelpText>
                      {filteredSummary.calls_count}C / {filteredSummary.puts_count}P
                    </StatHelpText>
                  </StatRoot>
                </SimpleGrid>
                {/* Filters */}
                <Card bg={cardBg} borderColor={borderColor}>
                  <CardBody>
                    <Flex wrap="wrap" gap={4} align="center">
                      <InputGroup
                        maxW="300px"
                        startElement={
                          <InputElement pointerEvents="none">
                            <FiSearch color="gray.300" />
                          </InputElement>
                        }
                      >
                        <Input
                          placeholder="Search by symbol..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                        />
                      </InputGroup>

                      <Select
                        value={filterType}
                        onChange={(e) => setFilterType(e.target.value as 'all' | 'calls' | 'puts')}
                        maxW="150px"
                      >
                        <option value="all">All Types</option>
                        <option value="calls">Calls Only</option>
                        <option value="puts">Puts Only</option>
                      </Select>

                      <Select
                        value={sortBy}
                        onChange={(e) => {
                          const newSort = e.target.value;
                          setSortBy(newSort);
                          console.log('Sort changed to:', newSort);
                        }}
                        maxW="200px"
                      >
                        <option value="days_to_expiration">Sort by DTE</option>
                        <option value="unrealized_pnl">Sort by P&L</option>
                        <option value="market_value">Sort by Value</option>
                        <option value="underlying_symbol">Sort by Symbol</option>
                      </Select>

                      <Badge variant="outline" p={2} fontSize="sm">
                        {filteredPositions.length} positions
                      </Badge>
                    </Flex>
                  </CardBody>
                </Card>

                {/* Tabs */}
                <TabsRoot defaultValue="bySymbol" variant="enclosed" colorScheme="blue">
                  <TabsList>
                    <TabsTrigger value="bySymbol">By Symbol ({Object.keys(filteredUnderlyings).length})</TabsTrigger>
                    <TabsTrigger value="allPositions">All Positions ({filteredPositions.length})</TabsTrigger>
                    <TabsTrigger value="analytics">Analytics</TabsTrigger>
                    <TabsTrigger value="activity">Activity</TabsTrigger>
                  </TabsList>

                  {/* By Symbol (default first) */}
                  <TabsContent value="bySymbol" px={0}>
                    <VStack spacing={4} align="stretch">
                      <HStack justify="space-between">
                        <Text fontSize="md" color="gray.600">
                          Click any card to expand details
                        </Text>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            if (expandedUnderlyings.size === Object.keys(filteredUnderlyings).length) {
                              setExpandedUnderlyings(new Set());
                            } else {
                              setExpandedUnderlyings(new Set(Object.keys(filteredUnderlyings)));
                            }
                          }}
                        >
                          {expandedUnderlyings.size === Object.keys(filteredUnderlyings).length ? 'Collapse All' : 'Expand All'}
                        </Button>
                      </HStack>

                      <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
                        {(Object.entries(filteredUnderlyings) as [string, UnderlyingGroup][])
                          .sort(([symbolA, dataA], [symbolB, dataB]) => {
                            // Apply sorting based on sortBy state
                            switch (sortBy) {
                              case 'days_to_expiration':
                                // Average days to expiration for the underlying
                                const avgDaysA = [...dataA.calls, ...dataA.puts].reduce((sum, pos) => sum + pos.days_to_expiration, 0) / (dataA.calls.length + dataA.puts.length) || 0;
                                const avgDaysB = [...dataB.calls, ...dataB.puts].reduce((sum, pos) => sum + pos.days_to_expiration, 0) / (dataB.calls.length + dataB.puts.length) || 0;
                                return avgDaysA - avgDaysB;

                              case 'unrealized_pnl':
                                return dataB.total_pnl - dataA.total_pnl;

                              case 'market_value':
                                return Math.abs(dataB.total_value) - Math.abs(dataA.total_value);

                              case 'underlying_symbol':
                                return symbolA.localeCompare(symbolB);

                              default:
                                return Math.abs(dataB.total_value) - Math.abs(dataA.total_value);
                            }
                          })
                          .map(([symbol, data]) => (
                            <UnderlyingCard
                              key={symbol}
                              symbol={symbol}
                              data={data}
                              isExpanded={expandedUnderlyings.has(symbol)}
                              onToggle={() => toggleUnderlying(symbol)}
                            />
                          ))}
                      </SimpleGrid>
                    </VStack>
                  </TabsContent>

                  {/* All Positions */}
                  <TabsContent value="allPositions" px={0}>
                    <VStack spacing={4} align="stretch">
                      <Card bg={cardBg} borderColor={borderColor}>
                        <CardHeader>
                          <HStack justify="space-between">
                            <Heading size="md">All Options Positions</Heading>
                            <Badge variant="outline" p={2} fontSize="sm">
                              {filteredPositions.length} positions
                            </Badge>
                          </HStack>
                        </CardHeader>
                        <CardBody>
                          <SortableTable
                            key={`options-${sortBy}-${filteredPositions.length}`}
                            data={filteredPositions}
                            columns={optionsColumns}
                            defaultSortBy={sortBy}
                            defaultSortOrder="asc"
                            emptyMessage="No options positions found"
                          />
                        </CardBody>
                      </Card>
                    </VStack>
                  </TabsContent>
                  {/* Analytics */}
                  <TabsContent value="analytics" px={0}>
                    <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
                      <Card bg={cardBg} borderColor={borderColor}>
                        <CardHeader>
                          <Heading size="md">Calls vs Puts Distribution</Heading>
                        </CardHeader>
                        <CardBody>
                          <ResponsiveContainer width="100%" height={300}>
                            <PieChart>
                              <Pie
                                dataKey="value"
                                data={typeDistribution}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={120}
                                paddingAngle={5}
                              >
                                {typeDistribution.map((entry, index) => (
                                  <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                              </Pie>
                              <RechartsTooltip
                                formatter={(value: number, name: string, props: any) => [
                                  `$${value.toLocaleString()} (${props.payload.count} positions)`,
                                  name
                                ]}
                              />
                              <Legend />
                            </PieChart>
                          </ResponsiveContainer>
                        </CardBody>
                      </Card>

                      <Card bg={cardBg} borderColor={borderColor}>
                        <CardHeader>
                          <Heading size="md">Top Underlyings by Value</Heading>
                        </CardHeader>
                        <CardBody>
                          <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={underlyingDistribution}>
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis dataKey="name" />
                              <YAxis tickFormatter={(value) => `$${value.toLocaleString()}`} />
                              <RechartsTooltip
                                formatter={(value: number, name: string, props: any) => [
                                  `$${value.toLocaleString()}`,
                                  `Value (${props.payload.positions} positions)`
                                ]}
                                labelFormatter={(label) => `${label}`}
                              />
                              <Bar dataKey="value" fill="#3182CE" />
                            </BarChart>
                          </ResponsiveContainer>
                        </CardBody>
                      </Card>
                    </SimpleGrid>
                  </TabsContent>

                  {/* Activity */}
                  <TabsContent value="activity" px={0}>
                    <Card bg={cardBg} borderColor={borderColor}>
                      <CardHeader>
                        <HStack justify="space-between">
                          <Heading size="md">Options Activity</Heading>
                          <Badge variant="outline" p={2} fontSize="sm">{activity.length} trades</Badge>
                        </HStack>
                      </CardHeader>
                      <CardBody>
                        <TableScrollArea>
                          <Table size="sm" variant="simple">
                            <Thead>
                              <Tr>
                                <Th>Date</Th>
                                <Th>Type</Th>
                                <Th>Symbol</Th>
                                <Th isNumeric>Qty</Th>
                                <Th isNumeric>Price</Th>
                                <Th>Account</Th>
                              </Tr>
                            </Thead>
                            <Tbody>
                              {activity.map((t) => (
                                <Tr key={`${t.id}-${t.execution_id || t.order_id || t.date}`}>
                                  <Td>
                                    <VStack align="start" spacing={0}>
                                      <Text fontSize="sm">{t.date}</Text>
                                      <Text fontSize="xs" color="gray.500">{t.time}</Text>
                                    </VStack>
                                  </Td>
                                  <Td>
                                    <Badge colorScheme={t.type === 'BUY' ? 'green' : 'red'}>{t.type}</Badge>
                                  </Td>
                                  <Td>{t.symbol}</Td>
                                  <Td isNumeric>{t.quantity}</Td>
                                  <Td isNumeric>${Number(t.price || 0).toFixed(2)}</Td>
                                  <Td>{t.account}</Td>
                                </Tr>
                              ))}
                            </Tbody>
                          </Table>
                        </TableScrollArea>
                      </CardBody>
                    </Card>
                  </TabsContent>
                </TabsRoot>
              </VStack>
            );
          }}
        </AccountFilterWrapper>
      </VStack>
    </Container>
  );
};

export default OptionsPortfolio;