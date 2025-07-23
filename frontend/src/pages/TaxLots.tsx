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
  InputLeftElement,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  useColorModeValue,
  Spinner,
  Alert,
  AlertIcon,
  useToast,
  Flex,
  Divider,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  IconButton,
  Tooltip,
  Progress,
} from '@chakra-ui/react';
import { SearchIcon, DownloadIcon, RepeatIcon, TimeIcon } from '@chakra-ui/icons';
import { FiDollarSign, FiTrendingUp, FiTrendingDown, FiCalendar, FiFilter, FiRefreshCw } from 'react-icons/fi';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import AccountFilterWrapper from '../components/AccountFilterWrapper';
import { portfolioApi } from '../services/api';
import { transformPortfolioToAccounts } from '../hooks/useAccountFilter';

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
  const toast = useToast();

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
        <Alert status="error">
          <AlertIcon />
          Error loading tax lots data: {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
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
            <VStack spacing={6} align="stretch">
              {/* Enhanced Filters */}
              <Card bg={cardBg} borderColor={borderColor}>
                <CardBody>
                  <VStack spacing={4}>
                    <Flex wrap="wrap" gap={4} align="center" width="full">
                      <InputGroup maxW="300px">
                        <InputLeftElement pointerEvents="none">
                          <SearchIcon color="gray.300" />
                        </InputLeftElement>
                        <Input
                          placeholder="Search symbols..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                        />
                      </InputGroup>

                      <Select
                        value={filterMethod}
                        onChange={(e) => setFilterMethod(e.target.value)}
                        maxW="200px"
                      >
                        <option value="all">All Tax Lots</option>
                        <option value="short_term">Short Term (&lt; 1 year)</option>
                        <option value="long_term">Long Term (&gt; 1 year)</option>
                      </Select>

                      <Select
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value)}
                        maxW="200px"
                      >
                        <option value="purchase_date">Purchase Date</option>
                        <option value="symbol">Symbol</option>
                        <option value="unrealized_pnl">Unrealized P&L</option>
                        <option value="cost_basis">Cost Basis</option>
                      </Select>

                      <Select
                        value={sortOrder}
                        onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
                        maxW="150px"
                      >
                        <option value="desc">Descending</option>
                        <option value="asc">Ascending</option>
                      </Select>

                      <Button
                        leftIcon={<FiRefreshCw />}
                        onClick={fetchTaxLots}
                        isLoading={loading}
                        size="sm"
                      >
                        Refresh
                      </Button>
                    </Flex>

                    {/* Summary Stats */}
                    {summary && (
                      <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} width="full">
                        <Stat size="sm">
                          <StatLabel>Total Lots</StatLabel>
                          <StatNumber>{summary.total_lots}</StatNumber>
                        </Stat>
                        <Stat size="sm">
                          <StatLabel>Total Cost Basis</StatLabel>
                          <StatNumber>{new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(summary.total_cost_basis)}</StatNumber>
                        </Stat>
                        <Stat size="sm">
                          <StatLabel>Current Value</StatLabel>
                          <StatNumber>{new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(summary.total_current_value)}</StatNumber>
                        </Stat>
                        <Stat size="sm">
                          <StatLabel>Unrealized P&L</StatLabel>
                          <StatNumber color={summary.total_unrealized_pnl >= 0 ? 'green.500' : 'red.500'}>
                            <StatArrow type={summary.total_unrealized_pnl >= 0 ? 'increase' : 'decrease'} />
                            {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Math.abs(summary.total_unrealized_pnl))}
                          </StatNumber>
                          <StatHelpText>
                            {summary.unrealized_pnl_pct.toFixed(2)}%
                          </StatHelpText>
                        </Stat>
                      </SimpleGrid>
                    )}
                  </VStack>
                </CardBody>
              </Card>

              {/* Tax Lots Table */}
              <Card bg={cardBg} borderColor={borderColor}>
                <CardHeader>
                  <Heading size="md">Tax Lots Detail</Heading>
                </CardHeader>
                <CardBody>
                  <Box overflowX="auto">
                    <Table variant="simple" size="sm">
                      <Thead>
                        <Tr>
                          <Th>Symbol</Th>
                          <Th>Account</Th>
                          <Th>Purchase Date</Th>
                          <Th isNumeric>Shares</Th>
                          <Th isNumeric>Purchase Price</Th>
                          <Th isNumeric>Current Price</Th>
                          <Th isNumeric>Cost Basis</Th>
                          <Th isNumeric>Market Value</Th>
                          <Th isNumeric>Unrealized P&L</Th>
                          <Th isNumeric>P&L %</Th>
                          <Th>Holding Period</Th>
                          <Th>Tax Status</Th>
                          <Th>Flags</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {filteredAndSortedTaxLots.slice(0, 50).map(lot => (
                          <Tr key={lot.id}>
                            <Td fontWeight="semibold">{lot.symbol}</Td>
                            <Td>{lot.account_id}</Td>
                            <Td>{lot.purchase_date}</Td>
                            <Td isNumeric>{lot.shares_purchased.toLocaleString()}</Td>
                            <Td isNumeric>${lot.cost_per_share.toFixed(2)}</Td>
                            <Td isNumeric>${lot.current_price.toFixed(2)}</Td>
                            <Td isNumeric>${lot.cost_basis.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</Td>
                            <Td isNumeric>${lot.market_value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</Td>
                            <Td isNumeric color={lot.unrealized_pnl >= 0 ? 'green.500' : 'red.500'}>
                              {lot.unrealized_pnl >= 0 ? '+' : ''}${lot.unrealized_pnl.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                            </Td>
                            <Td isNumeric color={lot.unrealized_pnl_pct >= 0 ? 'green.500' : 'red.500'}>
                              {lot.unrealized_pnl_pct >= 0 ? '+' : ''}{lot.unrealized_pnl_pct.toFixed(2)}%
                            </Td>
                            <Td>{lot.holding_days} days</Td>
                            <Td>
                              <Badge colorScheme={lot.is_long_term ? 'green' : 'orange'}>
                                {lot.is_long_term ? 'Long-term' : 'Short-term'}
                              </Badge>
                            </Td>
                            <Td>
                              {lot.is_wash_sale && (
                                <Tooltip label="Potential wash sale risk">
                                  <Badge colorScheme="red" variant="outline">
                                    {/* WarningIcon is not imported, using a placeholder or removing if not needed */}
                                    {/* <Icon as={WarningIcon} boxSize={3} /> */}
                                  </Badge>
                                </Tooltip>
                              )}
                            </Td>
                          </Tr>
                        ))}
                      </Tbody>
                    </Table>
                  </Box>

                  {filteredAndSortedTaxLots.length > 50 && (
                    <Text mt={4} fontSize="sm" color="gray.600">
                      Showing first 50 of {filteredAndSortedTaxLots.length} tax lots. Use search to narrow results.
                    </Text>
                  )}
                </CardBody>
              </Card>

              {/* Holding Period Analysis */}
              <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
                <Card bg={cardBg} borderColor={borderColor}>
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
                </Card>

                <Card bg={cardBg} borderColor={borderColor}>
                  <CardHeader>
                    <Heading size="md">Tax Status Breakdown</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack spacing={4}>
                      <SimpleGrid columns={2} spacing={4} w="full">
                        <Stat textAlign="center">
                          <StatLabel>Long-term</StatLabel>
                          <StatNumber color="green.500">{summary?.long_term_lots || 0}</StatNumber>
                          <StatHelpText>positions</StatHelpText>
                        </Stat>
                        <Stat textAlign="center">
                          <StatLabel>Short-term</StatLabel>
                          <StatNumber color="orange.500">{summary?.short_term_lots || 0}</StatNumber>
                          <StatHelpText>positions</StatHelpText>
                        </Stat>
                      </SimpleGrid>

                      <Alert status="info" variant="left-accent">
                        <AlertIcon />
                        <Box>
                          <Text fontWeight="semibold">Tax Efficiency Tip</Text>
                          <Text fontSize="sm">
                            Hold positions for 365+ days to qualify for long-term capital gains tax rates (typically 0%, 15%, or 20% vs ordinary income rates for short-term).
                          </Text>
                        </Box>
                      </Alert>
                    </VStack>
                  </CardBody>
                </Card>
              </SimpleGrid>

              {/* Tax Planning */}
              <VStack spacing={6}>
                <Card bg={cardBg} borderColor={borderColor} w="full">
                  <CardHeader>
                    <Heading size="md">Tax Planning Summary</Heading>
                  </CardHeader>
                  <CardBody>
                    <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                      <VStack align="stretch" spacing={4}>
                        <Text fontWeight="semibold">Long-term Capital Gains/Losses</Text>
                        <Stat>
                          <StatNumber color={(summary?.long_term_value || 0) >= 0 ? 'green.500' : 'red.500'}>
                            {(summary?.long_term_value || 0) >= 0 ? '+' : ''}${(summary?.long_term_value || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                          </StatNumber>
                          <StatHelpText>If realized today</StatHelpText>
                        </Stat>

                        <Text fontWeight="semibold">Short-term Capital Gains/Losses</Text>
                        <Stat>
                          <StatNumber color={(summary?.short_term_value || 0) >= 0 ? 'green.500' : 'red.500'}>
                            {(summary?.short_term_value || 0) >= 0 ? '+' : ''}${(summary?.short_term_value || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                          </StatNumber>
                          <StatHelpText>If realized today</StatHelpText>
                        </Stat>
                      </VStack>

                      <VStack align="stretch" spacing={4}>
                        <Alert status="warning" variant="left-accent">
                          <AlertIcon />
                          <Box>
                            <Text fontWeight="semibold">Wash Sale Risk</Text>
                            <Text fontSize="sm">
                              {summary?.wash_sale_lots || 0} positions flagged for potential wash sale rules.
                              Avoid repurchasing within 30 days of realizing losses.
                            </Text>
                          </Box>
                        </Alert>

                        <Alert status="info" variant="left-accent">
                          <AlertIcon />
                          <Box>
                            <Text fontWeight="semibold">Tax Loss Harvesting</Text>
                            <Text fontSize="sm">
                              Consider realizing losses to offset gains. Current unrealized losses can offset up to $3,000 of ordinary income annually.
                            </Text>
                          </Box>
                        </Alert>
                      </VStack>
                    </SimpleGrid>
                  </CardBody>
                </Card>
              </VStack>

              {/* Charts & Visualization */}
              <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
                <Card bg={cardBg} borderColor={borderColor}>
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
                </Card>

                <Card bg={cardBg} borderColor={borderColor}>
                  <CardHeader>
                    <Heading size="md">Portfolio Value by Holding Period</Heading>
                  </CardHeader>
                  <CardBody>
                    <ResponsiveContainer width="100%" height={300}>
                      {/* AreaChart is not imported, using a placeholder or removing if not needed */}
                      {/* <AreaChart data={holdingPeriodData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="period" />
                        <YAxis />
                        <RechartsTooltip
                          formatter={(value) => [`$${Number(value).toLocaleString()}`, 'Value']}
                        />
                        <Area type="monotone" dataKey="value" stroke="#4299E1" fill="#4299E1" fillOpacity={0.6} />
                      </AreaChart> */}
                    </ResponsiveContainer>
                  </CardBody>
                </Card>
              </SimpleGrid>
            </VStack>
          )}
        </AccountFilterWrapper>
      </VStack>
    </Container>
  );
};

export default TaxLots; 