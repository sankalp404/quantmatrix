import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Container,
  Heading,
  VStack,
  HStack,
  Text,
  CardRoot,
  CardBody,
  CardHeader,
  SimpleGrid,
  Badge,
  Button,
  Input,
  InputGroup,
  InputElement,
  StatRoot,
  StatLabel,
  StatHelpText,
  StatValueText,
  StatUpIndicator,
  StatDownIndicator,
  Spinner,
  AlertRoot,
  AlertIndicator,
  AlertDescription,
  Flex,
  TableScrollArea,
  IconButton,
  Progress,
  TableRoot,
  TableHeader,
  TableBody,
  TableRow,
  TableColumnHeader,
  TableCell,
} from '@chakra-ui/react';
import hotToast from 'react-hot-toast';
import { FiDollarSign, FiTrendingUp, FiTrendingDown, FiCalendar, FiFilter, FiRefreshCw, FiDownload, FiSearch, FiClock } from 'react-icons/fi';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import AccountFilterWrapper from '../components/ui/AccountFilterWrapper';
import { portfolioApi } from '../services/api';
import { transformPortfolioToAccounts } from '../hooks/useAccountFilter';

// Chakra v3 migration shim: prefer dark values until we reintroduce color-mode properly.
const useColorModeValue = <T,>(_light: T, dark: T) => dark;

// Interface for tax lot data from API
interface TaxLot {
  id: number;
  symbol: string;
  account_id: string;
  purchase_date: string;
  shares_purchased: number;
  shares_remaining: number;
  shares_sold: number;
  cost_per_share: number;
  current_price: number;
  cost_basis: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  holding_days: number;
  is_long_term: boolean;
  is_wash_sale: boolean;
  wash_sale_amount: number;
  commission: number;
  notes?: string;
}

interface TaxLotSummary {
  total_lots: number;
  total_cost_basis: number;
  total_market_value: number;
  total_unrealized_pnl: number;
  total_unrealized_pnl_pct: number;
  long_term_lots: number;
  short_term_lots: number;
  long_term_value: number;
  short_term_value: number;
  wash_sale_lots: number;
  unique_symbols: number;
}

const CHART_COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

const TaxLots: React.FC = () => {
  const [taxLots, setTaxLots] = useState<TaxLot[]>([]);
  const [summary, setSummary] = useState<TaxLotSummary | null>(null);
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterMethod, setFilterMethod] = useState('all');
  const [sortBy, setSortBy] = useState('purchase_date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  // Temporary shim: preserve legacy `toast({title, status, description})` call sites.
  const toast = (args: { title: string; description?: string; status?: 'success' | 'error' | 'info' | 'warning'; duration?: number; isClosable?: boolean }) => {
    const msg = args.description ? `${args.title}: ${args.description}` : args.title;
    if (args.status === 'success') return hotToast.success(args.title);
    if (args.status === 'error') return hotToast.error(msg);
    return hotToast(msg);
  };

  useEffect(() => {
    fetchTaxLots();
  }, []);

  const fetchTaxLots = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch portfolio data for account selector
      const portfolioResult = await portfolioApi.getLive();
      setPortfolioData(portfolioResult.data);

      const response = await fetch(`/api/v1/portfolio/tax-lots`);
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || 'Failed to fetch tax lots');
      }

      if (result.status === 'success') {
        setTaxLots(result.data.tax_lots || []);
        setSummary(result.data.summary || null);
      } else {
        throw new Error(result.error || 'Unknown error');
      }
    } catch (err: any) {
      console.error('Error fetching tax lots:', err);
      setError(err.message || 'Failed to fetch tax lots');
    } finally {
      setLoading(false);
    }
  };

  const syncTaxLots = async () => {
    setSyncing(true);
    try {
      // First sync portfolio data
      const syncResponse = await fetch('/api/v1/portfolio/sync', {
        method: 'POST'
      });
      const syncResult = await syncResponse.json();

      if (!syncResponse.ok) {
        throw new Error(syncResult.detail || 'Failed to sync portfolio data');
      }

      toast({
        title: 'Data Synced',
        description: 'Portfolio and tax lot data has been synced',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      // Refresh tax lots after sync
      await fetchTaxLots();

    } catch (err: any) {
      console.error('Error syncing tax lots:', err);
      toast({
        title: 'Sync Failed',
        description: err.message || 'Failed to sync data',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setSyncing(false);
    }
  };

  // Transform portfolio data for account selector
  const accounts = portfolioData ? transformPortfolioToAccounts(portfolioData) : [];

  // Filter and sort tax lots
  const filteredAndSortedTaxLots = useMemo(() => {
    return taxLots.filter(lot => {
      const matchesSearch = lot.symbol.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesMethod = filterMethod === 'all' ||
        (filterMethod === 'short_term' && !lot.is_long_term) ||
        (filterMethod === 'long_term' && lot.is_long_term);
      return matchesSearch && matchesMethod;
    }).sort((a, b) => {
      const aValue = a[sortBy as keyof TaxLot];
      const bValue = b[sortBy as keyof TaxLot];

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortOrder === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      const aNum = Number(aValue);
      const bNum = Number(bValue);
      return sortOrder === 'asc' ? aNum - bNum : bNum - aNum;
    });
  }, [taxLots, searchTerm, filterMethod, sortBy, sortOrder]);

  // Get unique symbols for filter
  const uniqueSymbols = [...new Set(taxLots.map(lot => lot.symbol))].sort();

  // Prepare chart data
  const holdingPeriodData = taxLots.reduce((acc: any[], lot) => {
    const period = lot.holding_days <= 30 ? '0-30 days' :
      lot.holding_days <= 90 ? '31-90 days' :
        lot.holding_days <= 365 ? '91-365 days' :
          '365+ days';

    const existing = acc.find(item => item.period === period);
    if (existing) {
      existing.count += 1;
      existing.value += lot.market_value;
    } else {
      acc.push({
        period,
        count: 1,
        value: lot.market_value
      });
    }
    return acc;
  }, []);

  const gainLossData = [
    { type: 'Long-term Gains/Losses', value: summary?.long_term_value || 0, color: '#4FD1C7' },
    { type: 'Short-term Gains/Losses', value: summary?.short_term_value || 0, color: '#F687B3' }
  ];

  if (loading) {
    return (
      <Container maxW="container.xl" py={8}>
        <Flex justify="center" align="center" h="400px">
          <VStack>
            <Spinner size="xl" color="blue.500" />
            <Text>Loading tax lots data...</Text>
          </VStack>
        </Flex>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxW="container.xl" py={8}>
        <AlertRoot status="error">
          <AlertIndicator />
          <AlertDescription>Error loading tax lots data: {error}</AlertDescription>
        </AlertRoot>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack gap={6} align="stretch">
        {/* Header */}
        <Box>
          <Heading size="lg" mb={2}>Tax Lots Analysis</Heading>
          <Text color="gray.500" fontSize="sm">
            Detailed tax lot information for optimal tax planning
          </Text>
        </Box>

        {/* Account Filter */}
        <AccountFilterWrapper
          data={taxLots}
          accounts={accounts}
          loading={loading}
          error={error}
          config={{
            showAllOption: true,
            showSummary: true,
            variant: 'detailed',
            size: 'md'
          }}
        >
          {(accountFilteredTaxLots, filterState) => (
            <VStack gap={6} align="stretch">
              {/* Enhanced Filters */}
              <CardRoot bg={cardBg} borderColor={borderColor} borderWidth="1px" borderRadius="xl">
                <CardBody>
                  <VStack gap={4}>
                    <Flex wrap="wrap" gap={4} align="center" width="full">
                      <InputGroup
                        maxW="300px"
                        startElement={
                          <InputElement pointerEvents="none">
                            <FiSearch color="gray.300" />
                          </InputElement>
                        }
                      >
                        <Input
                          placeholder="Search symbols..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                        />
                      </InputGroup>

                      <select
                        value={filterMethod}
                        onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFilterMethod(e.target.value)}
                        style={{ maxWidth: 200, padding: '8px 10px', borderRadius: 10, border: `1px solid ${String(borderColor)}`, background: String(cardBg) }}
                      >
                        <option value="all">All Tax Lots</option>
                        <option value="short_term">Short Term (&lt; 1 year)</option>
                        <option value="long_term">Long Term (&gt; 1 year)</option>
                      </select>

                      <select
                        value={sortBy}
                        onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSortBy(e.target.value)}
                        style={{ maxWidth: 200, padding: '8px 10px', borderRadius: 10, border: `1px solid ${String(borderColor)}`, background: String(cardBg) }}
                      >
                        <option value="purchase_date">Purchase Date</option>
                        <option value="symbol">Symbol</option>
                        <option value="unrealized_pnl">Unrealized P&L</option>
                        <option value="cost_basis">Cost Basis</option>
                      </select>

                      <select
                        value={sortOrder}
                        onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSortOrder(e.target.value as 'asc' | 'desc')}
                        style={{ maxWidth: 150, padding: '8px 10px', borderRadius: 10, border: `1px solid ${String(borderColor)}`, background: String(cardBg) }}
                      >
                        <option value="desc">Descending</option>
                        <option value="asc">Ascending</option>
                      </select>

                      <Button
                        onClick={fetchTaxLots}
                        loading={loading}
                        size="sm"
                      >
                        <HStack gap={2}>
                          <FiRefreshCw />
                          <Text>Refresh</Text>
                        </HStack>
                      </Button>
                    </Flex>

                    {/* Summary Stats */}
                    {summary && (
                      <SimpleGrid columns={{ base: 2, md: 4 }} gap={4} width="full">
                        <StatRoot size="sm">
                          <StatLabel>Total Lots</StatLabel>
                          <StatValueText>{summary.total_lots}</StatValueText>
                        </StatRoot>
                        <StatRoot size="sm">
                          <StatLabel>Total Cost Basis</StatLabel>
                          <StatValueText>{new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(summary.total_cost_basis)}</StatValueText>
                        </StatRoot>
                        <StatRoot size="sm">
                          <StatLabel>Current Value</StatLabel>
                          <StatValueText>{new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(summary.total_market_value)}</StatValueText>
                        </StatRoot>
                        <StatRoot size="sm">
                          <StatLabel>Unrealized P&L</StatLabel>
                          <StatValueText color={summary.total_unrealized_pnl >= 0 ? 'green.500' : 'red.500'}>
                            {summary.total_unrealized_pnl >= 0 ? <StatUpIndicator /> : <StatDownIndicator />}
                            {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Math.abs(summary.total_unrealized_pnl))}
                          </StatValueText>
                          <StatHelpText>
                            {summary.total_unrealized_pnl_pct.toFixed(2)}%
                          </StatHelpText>
                        </StatRoot>
                      </SimpleGrid>
                    )}
                  </VStack>
                </CardBody>
              </CardRoot>

              {/* Tax Lots Table */}
              <CardRoot bg={cardBg} borderColor={borderColor} borderWidth="1px" borderRadius="xl">
                <CardHeader>
                  <Heading size="md">Tax Lots Detail</Heading>
                </CardHeader>
                <CardBody>
                  <TableScrollArea>
                    <TableRoot variant="line" size="sm">
                      <TableHeader>
                        <TableRow>
                          <TableColumnHeader>Symbol</TableColumnHeader>
                          <TableColumnHeader>Account</TableColumnHeader>
                          <TableColumnHeader>Purchase Date</TableColumnHeader>
                          <TableColumnHeader textAlign="end">Shares</TableColumnHeader>
                          <TableColumnHeader textAlign="end">Purchase Price</TableColumnHeader>
                          <TableColumnHeader textAlign="end">Current Price</TableColumnHeader>
                          <TableColumnHeader textAlign="end">Cost Basis</TableColumnHeader>
                          <TableColumnHeader textAlign="end">Market Value</TableColumnHeader>
                          <TableColumnHeader textAlign="end">Unrealized P&amp;L</TableColumnHeader>
                          <TableColumnHeader textAlign="end">P&amp;L %</TableColumnHeader>
                          <TableColumnHeader>Holding Period</TableColumnHeader>
                          <TableColumnHeader>Tax Status</TableColumnHeader>
                          <TableColumnHeader>Flags</TableColumnHeader>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredAndSortedTaxLots.slice(0, 50).map(lot => (
                          <TableRow key={lot.id}>
                            <TableCell fontWeight="semibold">{lot.symbol}</TableCell>
                            <TableCell>{lot.account_id}</TableCell>
                            <TableCell>{lot.purchase_date}</TableCell>
                            <TableCell textAlign="end">{lot.shares_purchased.toLocaleString()}</TableCell>
                            <TableCell textAlign="end">${lot.cost_per_share.toFixed(2)}</TableCell>
                            <TableCell textAlign="end">${lot.current_price.toFixed(2)}</TableCell>
                            <TableCell textAlign="end">${lot.cost_basis.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</TableCell>
                            <TableCell textAlign="end">${lot.market_value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</TableCell>
                            <TableCell textAlign="end" color={lot.unrealized_pnl >= 0 ? 'green.500' : 'red.500'}>
                              {lot.unrealized_pnl >= 0 ? '+' : ''}${lot.unrealized_pnl.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                            </TableCell>
                            <TableCell textAlign="end" color={lot.unrealized_pnl_pct >= 0 ? 'green.500' : 'red.500'}>
                              {lot.unrealized_pnl_pct >= 0 ? '+' : ''}{lot.unrealized_pnl_pct.toFixed(2)}%
                            </TableCell>
                            <TableCell>{lot.holding_days} days</TableCell>
                            <TableCell>
                              <Badge colorScheme={lot.is_long_term ? 'green' : 'orange'}>
                                {lot.is_long_term ? 'Long-term' : 'Short-term'}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              {lot.is_wash_sale && (
                                <Badge title="Potential wash sale risk" colorScheme="red" variant="outline">
                                  WS
                                </Badge>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </TableRoot>
                  </TableScrollArea>

                  {filteredAndSortedTaxLots.length > 50 && (
                    <Text mt={4} fontSize="sm" color="gray.600">
                      Showing first 50 of {filteredAndSortedTaxLots.length} tax lots. Use search to narrow results.
                    </Text>
                  )}
                </CardBody>
              </CardRoot>

              {/* Holding Period Analysis */}
              <SimpleGrid columns={{ base: 1, lg: 2 }} gap={6}>
                <CardRoot bg={cardBg} borderColor={borderColor} borderWidth="1px" borderRadius="xl">
                  <CardHeader>
                    <Heading size="md">Holdings by Period</Heading>
                  </CardHeader>
                  <CardBody>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={holdingPeriodData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="period" />
                        <YAxis />
                        <RechartsTooltip
                          formatter={(value, name) => [
                            name === 'count' ? `${value} positions` : `$${Number(value).toLocaleString()}`,
                            name === 'count' ? 'Positions' : 'Value'
                          ]}
                        />
                        <Bar dataKey="count" fill="#4299E1" name="count" />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardBody>
                </CardRoot>

                <CardRoot bg={cardBg} borderColor={borderColor} borderWidth="1px" borderRadius="xl">
                  <CardHeader>
                    <Heading size="md">Tax Status Breakdown</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack gap={4}>
                      <SimpleGrid columns={2} gap={4} w="full">
                        <StatRoot textAlign="center">
                          <StatLabel>Long-term</StatLabel>
                          <StatValueText color="green.500">{summary?.long_term_lots || 0}</StatValueText>
                          <StatHelpText>positions</StatHelpText>
                        </StatRoot>
                        <StatRoot textAlign="center">
                          <StatLabel>Short-term</StatLabel>
                          <StatValueText color="orange.500">{summary?.short_term_lots || 0}</StatValueText>
                          <StatHelpText>positions</StatHelpText>
                        </StatRoot>
                      </SimpleGrid>

                      <AlertRoot status="info" borderRadius="md">
                        <AlertIndicator />
                        <Box>
                          <Text fontWeight="semibold">Tax Efficiency Tip</Text>
                          <Text fontSize="sm">
                            Hold positions for 365+ days to qualify for long-term capital gains tax rates (typically 0%, 15%, or 20% vs ordinary income rates for short-term).
                          </Text>
                        </Box>
                      </AlertRoot>
                    </VStack>
                  </CardBody>
                </CardRoot>
              </SimpleGrid>

              {/* Tax Planning */}
              <VStack gap={6}>
                <CardRoot bg={cardBg} borderColor={borderColor} borderWidth="1px" borderRadius="xl" w="full">
                  <CardHeader>
                    <Heading size="md">Tax Planning Summary</Heading>
                  </CardHeader>
                  <CardBody>
                    <SimpleGrid columns={{ base: 1, md: 2 }} gap={6}>
                      <VStack align="stretch" gap={4}>
                        <Text fontWeight="semibold">Long-term Capital Gains/Losses</Text>
                        <StatRoot>
                          <StatValueText color={(summary?.long_term_value || 0) >= 0 ? 'green.500' : 'red.500'}>
                            {(summary?.long_term_value || 0) >= 0 ? '+' : ''}${(summary?.long_term_value || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                          </StatValueText>
                          <StatHelpText>If realized today</StatHelpText>
                        </StatRoot>

                        <Text fontWeight="semibold">Short-term Capital Gains/Losses</Text>
                        <StatRoot>
                          <StatValueText color={(summary?.short_term_value || 0) >= 0 ? 'green.500' : 'red.500'}>
                            {(summary?.short_term_value || 0) >= 0 ? '+' : ''}${(summary?.short_term_value || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                          </StatValueText>
                          <StatHelpText>If realized today</StatHelpText>
                        </StatRoot>
                      </VStack>

                      <VStack align="stretch" gap={4}>
                        <AlertRoot status="warning" borderRadius="md">
                          <AlertIndicator />
                          <Box>
                            <Text fontWeight="semibold">Wash Sale Risk</Text>
                            <Text fontSize="sm">
                              {summary?.wash_sale_lots || 0} positions flagged for potential wash sale rules.
                              Avoid repurchasing within 30 days of realizing losses.
                            </Text>
                          </Box>
                        </AlertRoot>

                        <AlertRoot status="info" borderRadius="md">
                          <AlertIndicator />
                          <Box>
                            <Text fontWeight="semibold">Tax Loss Harvesting</Text>
                            <Text fontSize="sm">
                              Consider realizing losses to offset gains. Current unrealized losses can offset up to $3,000 of ordinary income annually.
                            </Text>
                          </Box>
                        </AlertRoot>
                      </VStack>
                    </SimpleGrid>
                  </CardBody>
                </CardRoot>
              </VStack>

              {/* Charts & Visualization */}
              <SimpleGrid columns={{ base: 1, lg: 2 }} gap={6}>
                <CardRoot bg={cardBg} borderColor={borderColor} borderWidth="1px" borderRadius="xl">
                  <CardHeader>
                    <Heading size="md">Gain/Loss Distribution</Heading>
                  </CardHeader>
                  <CardBody>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={gainLossData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="type" />
                        <YAxis />
                        <RechartsTooltip
                          formatter={(value) => [`$${Number(value).toLocaleString()}`, 'Amount']}
                        />
                        <Bar dataKey="value" fill="#4299E1" />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardBody>
                </CardRoot>

                <CardRoot bg={cardBg} borderColor={borderColor} borderWidth="1px" borderRadius="xl">
                  <CardHeader>
                    <Heading size="md">Portfolio Value by Holding Period</Heading>
                  </CardHeader>
                  <CardBody>
                    <Box p={6}>
                      <Text color="gray.500" fontSize="sm">
                        Portfolio value-by-holding-period visualization coming soon.
                      </Text>
                    </Box>
                  </CardBody>
                </CardRoot>
              </SimpleGrid>
            </VStack>
          )}
        </AccountFilterWrapper>
      </VStack>
    </Container>
  );
};

export default TaxLots; 