import React, { useState, useEffect } from 'react';
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
  Progress,
  Divider,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  List,
  ListItem,
  ListIcon,
} from '@chakra-ui/react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from 'recharts';
import { FiRefreshCw, FiDownload, FiTrendingUp, FiTrendingDown, FiCheckCircle, FiAlertTriangle } from 'react-icons/fi';
import { portfolioApi, handleApiError } from '../services/api';
import AccountFilterWrapper from '../components/AccountFilterWrapper';
import { transformPortfolioToAccounts } from '../hooks/useAccountFilter';
import SortableTable, { Column } from '../components/SortableTable';
import FinvizHeatMap from '../components/FinvizHeatMap';

interface Holding {
  symbol: string;
  account: string;
  value: number;
  gainLoss: number;
  gainLossPct: number;
  quantity: number;
  currentPrice: number;
  dayChange: number;
  dayChangePct: number;
  sector: string;
}

const Portfolio: React.FC = () => {
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [performanceData, setPerformanceData] = useState<any>(null);
  const [taxData, setTaxData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [performanceLoading, setPerformanceLoading] = useState(false);
  const [taxLoading, setTaxLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState('value');

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const toast = useToast();

  useEffect(() => {
    fetchPortfolioData();
  }, []);

  const fetchPortfolioData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await portfolioApi.getLive();
      setPortfolioData(data.data);

      // Transform portfolio data into holdings array
      const allHoldings: Holding[] = [];
      if (data.data?.accounts) {
        Object.entries(data.data.accounts).forEach(([accountId, accountData]: [string, any]) => {
          if (accountData.all_positions) {
            accountData.all_positions.forEach((position: any) => {
              // Only include stocks (exclude options)
              if (position.contract_type === 'STK') {
                allHoldings.push({
                  symbol: position.symbol,
                  account: accountId,
                  value: position.position_value || 0,
                  gainLoss: position.unrealized_pnl || 0,
                  gainLossPct: position.unrealized_pnl_pct || 0,
                  quantity: position.position || 0,
                  currentPrice: position.market_price || 0,
                  dayChange: position.day_change || 0,
                  dayChangePct: position.day_change_pct || 0,
                  sector: position.sector || 'Unknown',
                });
              }
            });
          }
        });
      }
      setHoldings(allHoldings);
    } catch (error) {
      console.error('Error fetching portfolio data:', error);
      setError(handleApiError(error));
    } finally {
      setLoading(false);
    }
  };

  const fetchPerformanceData = async () => {
    setPerformanceLoading(true);
    try {
      const response = await fetch('/api/v1/portfolio/performance-analytics');
      const data = await response.json();
      if (data.status === 'success') {
        setPerformanceData(data.data);
      }
    } catch (error) {
      console.error('Error fetching performance data:', error);
      toast({
        title: 'Error',
        description: 'Failed to load performance analytics',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setPerformanceLoading(false);
    }
  };

  const fetchTaxData = async () => {
    setTaxLoading(true);
    try {
      const response = await fetch('/api/v1/portfolio/tax-optimization');
      const data = await response.json();
      if (data.status === 'success') {
        setTaxData(data.data);
      }
    } catch (error) {
      console.error('Error fetching tax data:', error);
      toast({
        title: 'Error',
        description: 'Failed to load tax optimization analysis',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setTaxLoading(false);
    }
  };

  const syncPortfolioData = async () => {
    setSyncing(true);
    try {
      await portfolioApi.sync();

      toast({
        title: 'Portfolio Synced',
        description: 'Portfolio data has been synced successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      await fetchPortfolioData();

    } catch (err: any) {
      console.error('Error syncing portfolio data:', err);
      toast({
        title: 'Sync Failed',
        description: err.message || 'Failed to sync portfolio data',
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

  // Sort holdings based on selection
  const sortHoldings = (holdingsToSort: Holding[]) => {
    return [...holdingsToSort].sort((a, b) => {
      switch (sortBy) {
        case 'value': return b.value - a.value;
        case 'gainLoss': return b.gainLoss - a.gainLoss;
        case 'gainLossPct': return b.gainLossPct - a.gainLossPct;
        case 'symbol': return a.symbol.localeCompare(b.symbol);
        default: return 0;
      }
    });
  };

  // Holdings table columns
  const holdingsColumns: Column<Holding>[] = [
    {
      key: 'symbol',
      header: 'Symbol',
      accessor: (item) => item.symbol,
      sortable: true,
      sortType: 'string',
      render: (value) => <Text fontWeight="bold">{value}</Text>,
    },
    {
      key: 'account',
      header: 'Account',
      accessor: (item) => item.account,
      sortable: true,
      sortType: 'string',
      render: (value) => (
        <Badge size="sm" colorScheme="blue">{value}</Badge>
      ),
    },
    {
      key: 'quantity',
      header: 'Shares',
      accessor: (item) => item.quantity,
      sortable: true,
      sortType: 'number',
      isNumeric: true,
      render: (value) => value.toFixed(2),
    },
    {
      key: 'currentPrice',
      header: 'Price',
      accessor: (item) => item.currentPrice,
      sortable: true,
      sortType: 'number',
      isNumeric: true,
      render: (value) => `$${value.toFixed(2)}`,
    },
    {
      key: 'value',
      header: 'Value',
      accessor: (item) => item.value,
      sortable: true,
      sortType: 'number',
      isNumeric: true,
      render: (value) => `$${value.toLocaleString()}`,
    },
    {
      key: 'dayChange',
      header: 'Day Change',
      accessor: (item) => item.dayChange,
      sortable: true,
      sortType: 'number',
      isNumeric: true,
      render: (value, item) => (
        <VStack align="end" spacing={0}>
          <Text color={value >= 0 ? 'green.500' : 'red.500'}>
            {value >= 0 ? '+' : ''}${value.toFixed(2)}
          </Text>
          <Text fontSize="xs" color={item.dayChangePct >= 0 ? 'green.500' : 'red.500'}>
            ({item.dayChangePct >= 0 ? '+' : ''}{item.dayChangePct.toFixed(2)}%)
          </Text>
        </VStack>
      ),
    },
    {
      key: 'gainLoss',
      header: 'Total Return',
      accessor: (item) => item.gainLoss,
      sortable: true,
      sortType: 'number',
      isNumeric: true,
      render: (value, item) => (
        <VStack align="end" spacing={0}>
          <Text color={value >= 0 ? 'green.500' : 'red.500'} fontWeight="medium">
            {value >= 0 ? '+' : ''}${value.toFixed(2)}
          </Text>
          <Text fontSize="xs" color={item.gainLossPct >= 0 ? 'green.500' : 'red.500'}>
            ({item.gainLossPct >= 0 ? '+' : ''}{item.gainLossPct.toFixed(2)}%)
          </Text>
        </VStack>
      ),
    },
    {
      key: 'sector',
      header: 'Sector',
      accessor: (item) => item.sector,
      sortable: true,
      sortType: 'string',
      render: (value) => (
        <Badge size="sm" variant="outline">{value}</Badge>
      ),
    },
  ];

  if (loading) {
    return (
      <Container maxW="container.xl" py={8}>
        <Flex justify="center" align="center" h="400px">
          <VStack>
            <Spinner size="xl" color="blue.500" />
            <Text>Loading portfolio...</Text>
          </VStack>
        </Flex>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box>
          <HStack justify="space-between" mb={2}>
            <Heading size="lg">Portfolio Overview</Heading>
            <HStack>
              <Button
                leftIcon={<FiRefreshCw />}
                onClick={syncPortfolioData}
                isLoading={syncing}
                loadingText="Syncing..."
                colorScheme="blue"
                size="sm"
              >
                Sync Portfolio
              </Button>
              <Button leftIcon={<FiDownload />} size="sm" variant="outline">
                Export
              </Button>
            </HStack>
          </HStack>
          <Text color="gray.500">
            Real-time portfolio data with advanced filtering and analytics
          </Text>
        </Box>

        {/* Unified Account Filter */}
        <AccountFilterWrapper
          data={holdings}
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
          {(filteredHoldings, filterState) => (
            <Tabs variant="enclosed" colorScheme="blue">
              <TabList>
                <Tab>Holdings Overview</Tab>
                <Tab>Performance</Tab>
                <Tab>Tax Analysis</Tab>
              </TabList>

              <TabPanels>
                <TabPanel px={0}>
                  {/* Controls */}
                  <HStack spacing={4} mb={6}>
                    <Select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value)}
                      w="200px"
                      size="sm"
                    >
                      <option value="value">Sort by Value</option>
                      <option value="gainLoss">Sort by Gain/Loss $</option>
                      <option value="gainLossPct">Sort by Gain/Loss %</option>
                      <option value="symbol">Sort by Symbol</option>
                    </Select>

                    <Badge variant="outline" p={2}>
                      {filteredHoldings.length} positions • ${filteredHoldings.reduce((sum, h) => sum + h.value, 0).toLocaleString()}
                    </Badge>
                  </HStack>

                  {/* Holdings Table */}
                  <Card bg={cardBg} borderColor={borderColor}>
                    <CardHeader>
                      <Heading size="md">Current Holdings</Heading>
                    </CardHeader>
                    <CardBody>
                      <SortableTable
                        data={sortHoldings(filteredHoldings)}
                        columns={holdingsColumns}
                        defaultSortBy="value"
                        defaultSortOrder="desc"
                        emptyMessage="No holdings found for the selected account."
                      />
                    </CardBody>
                  </Card>
                </TabPanel>

                <TabPanel px={0}>
                  {/* Performance Tab with Real Analytics */}
                  <VStack spacing={6} align="stretch">
                    {!performanceData && (
                      <Button onClick={fetchPerformanceData} isLoading={performanceLoading} loadingText="Loading Analytics...">
                        Load Performance Analytics
                      </Button>
                    )}

                    {performanceData && (
                      <>
                        {/* Performance Metrics Cards */}
                        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
                          <Card bg={cardBg} borderColor={borderColor}>
                            <CardBody>
                              <Stat>
                                <StatLabel>Total Return</StatLabel>
                                <StatNumber color={performanceData.performance_metrics.total_return >= 0 ? 'green.500' : 'red.500'}>
                                  {performanceData.performance_metrics.total_return >= 0 ? '+' : ''}
                                  ${performanceData.performance_metrics.total_return?.toLocaleString()}
                                </StatNumber>
                                <StatHelpText>
                                  <StatArrow type={performanceData.performance_metrics.total_return_pct >= 0 ? 'increase' : 'decrease'} />
                                  {performanceData.performance_metrics.total_return_pct?.toFixed(2)}%
                                </StatHelpText>
                              </Stat>
                            </CardBody>
                          </Card>

                          <Card bg={cardBg} borderColor={borderColor}>
                            <CardBody>
                              <Stat>
                                <StatLabel>Win Rate</StatLabel>
                                <StatNumber>{performanceData.performance_metrics.win_rate}%</StatNumber>
                                <StatHelpText>
                                  {performanceData.performance_metrics.winners_count} winners / {performanceData.performance_metrics.losers_count} losers
                                </StatHelpText>
                              </Stat>
                            </CardBody>
                          </Card>

                          <Card bg={cardBg} borderColor={borderColor}>
                            <CardBody>
                              <Stat>
                                <StatLabel>Sharpe Ratio</StatLabel>
                                <StatNumber color={performanceData.risk_metrics.sharpe_ratio >= 1 ? 'green.500' : 'orange.500'}>
                                  {performanceData.risk_metrics.sharpe_ratio?.toFixed(2)}
                                </StatNumber>
                                <StatHelpText>Risk-adjusted return</StatHelpText>
                              </Stat>
                            </CardBody>
                          </Card>

                          <Card bg={cardBg} borderColor={borderColor}>
                            <CardBody>
                              <Stat>
                                <StatLabel>Max Drawdown</StatLabel>
                                <StatNumber color="red.500">
                                  -{performanceData.risk_metrics.max_drawdown?.toFixed(2)}%
                                </StatNumber>
                                <StatHelpText>Largest decline</StatHelpText>
                              </Stat>
                            </CardBody>
                          </Card>
                        </SimpleGrid>

                        {/* Risk Metrics */}
                        <Card bg={cardBg} borderColor={borderColor}>
                          <CardHeader>
                            <Heading size="md">Risk Analysis</Heading>
                          </CardHeader>
                          <CardBody>
                            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                              <VStack align="start" spacing={4}>
                                <Box w="full">
                                  <Text fontSize="sm" fontWeight="semibold" mb={2}>Portfolio Concentration</Text>
                                  <HStack justify="space-between">
                                    <Text fontSize="sm">Top 5 Holdings:</Text>
                                    <Text fontSize="sm" fontWeight="bold">{performanceData.risk_metrics.top_5_concentration}%</Text>
                                  </HStack>
                                  <Progress value={performanceData.risk_metrics.top_5_concentration} colorScheme={performanceData.risk_metrics.top_5_concentration > 50 ? 'red' : 'green'} size="sm" />

                                  <HStack justify="space-between" mt={2}>
                                    <Text fontSize="sm">Top 10 Holdings:</Text>
                                    <Text fontSize="sm" fontWeight="bold">{performanceData.risk_metrics.top_10_concentration}%</Text>
                                  </HStack>
                                  <Progress value={performanceData.risk_metrics.top_10_concentration} colorScheme={performanceData.risk_metrics.top_10_concentration > 75 ? 'red' : 'green'} size="sm" />
                                </Box>

                                <Box w="full">
                                  <Text fontSize="sm" fontWeight="semibold" mb={2}>Risk Metrics</Text>
                                  <VStack spacing={2} align="stretch">
                                    <HStack justify="space-between">
                                      <Text fontSize="sm">Portfolio Volatility:</Text>
                                      <Text fontSize="sm" fontWeight="bold">{performanceData.risk_metrics.portfolio_volatility}%</Text>
                                    </HStack>
                                    <HStack justify="space-between">
                                      <Text fontSize="sm">Beta vs Market:</Text>
                                      <Text fontSize="sm" fontWeight="bold">{performanceData.risk_metrics.beta}</Text>
                                    </HStack>
                                    <HStack justify="space-between">
                                      <Text fontSize="sm">Value at Risk (95%):</Text>
                                      <Text fontSize="sm" fontWeight="bold" color="red.500">${performanceData.risk_metrics.value_at_risk_95?.toLocaleString()}</Text>
                                    </HStack>
                                  </VStack>
                                </Box>
                              </VStack>

                              <Box>
                                <Text fontSize="sm" fontWeight="semibold" mb={2}>Sector Performance</Text>
                                <ResponsiveContainer width="100%" height={200}>
                                  <BarChart data={performanceData.attribution_analysis.sector_performance}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="sector" tick={{ fontSize: 12 }} />
                                    <YAxis tick={{ fontSize: 12 }} />
                                    <RechartsTooltip
                                      formatter={(value, name) => [
                                        name === 'return' ? `${value}%` : `${value}%`,
                                        name === 'return' ? 'Sector Return' : 'Portfolio Weight'
                                      ]}
                                    />
                                    <Bar dataKey="return" fill="#4299E1" />
                                  </BarChart>
                                </ResponsiveContainer>
                              </Box>
                            </SimpleGrid>
                          </CardBody>
                        </Card>

                        {/* Top Contributors/Detractors */}
                        <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
                          <Card bg={cardBg} borderColor={borderColor}>
                            <CardHeader>
                              <Heading size="md" color="green.500">Top Contributors</Heading>
                            </CardHeader>
                            <CardBody>
                              <TableContainer>
                                <Table size="sm">
                                  <Thead>
                                    <Tr>
                                      <Th>Symbol</Th>
                                      <Th isNumeric>Contribution</Th>
                                      <Th isNumeric>Return</Th>
                                    </Tr>
                                  </Thead>
                                  <Tbody>
                                    {performanceData.attribution_analysis.top_contributors.slice(0, 5).map((stock: any, idx: number) => (
                                      <Tr key={idx}>
                                        <Td fontWeight="bold">{stock.symbol}</Td>
                                        <Td isNumeric color="green.500">+{stock.contribution}%</Td>
                                        <Td isNumeric>{stock.return}%</Td>
                                      </Tr>
                                    ))}
                                  </Tbody>
                                </Table>
                              </TableContainer>
                            </CardBody>
                          </Card>

                          <Card bg={cardBg} borderColor={borderColor}>
                            <CardHeader>
                              <Heading size="md" color="red.500">Top Detractors</Heading>
                            </CardHeader>
                            <CardBody>
                              <TableContainer>
                                <Table size="sm">
                                  <Thead>
                                    <Tr>
                                      <Th>Symbol</Th>
                                      <Th isNumeric>Contribution</Th>
                                      <Th isNumeric>Return</Th>
                                    </Tr>
                                  </Thead>
                                  <Tbody>
                                    {performanceData.attribution_analysis.top_detractors.map((stock: any, idx: number) => (
                                      <Tr key={idx}>
                                        <Td fontWeight="bold">{stock.symbol}</Td>
                                        <Td isNumeric color="red.500">{stock.contribution}%</Td>
                                        <Td isNumeric>{stock.return}%</Td>
                                      </Tr>
                                    ))}
                                  </Tbody>
                                </Table>
                              </TableContainer>
                            </CardBody>
                          </Card>
                        </SimpleGrid>

                        {/* Benchmark Comparison */}
                        <Card bg={cardBg} borderColor={borderColor}>
                          <CardHeader>
                            <Heading size="md">Benchmark Comparison</Heading>
                          </CardHeader>
                          <CardBody>
                            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                              <Box>
                                <Text fontWeight="semibold" mb={2}>vs S&P 500</Text>
                                <VStack spacing={2} align="stretch">
                                  <HStack justify="space-between">
                                    <Text fontSize="sm">Portfolio Return:</Text>
                                    <Text fontSize="sm" fontWeight="bold" color="blue.500">
                                      {performanceData.benchmarks.vs_sp500.portfolio_return}%
                                    </Text>
                                  </HStack>
                                  <HStack justify="space-between">
                                    <Text fontSize="sm">S&P 500 Return:</Text>
                                    <Text fontSize="sm" fontWeight="bold">
                                      {performanceData.benchmarks.vs_sp500.benchmark_return}%
                                    </Text>
                                  </HStack>
                                  <HStack justify="space-between">
                                    <Text fontSize="sm">Alpha:</Text>
                                    <Text fontSize="sm" fontWeight="bold" color={performanceData.benchmarks.vs_sp500.alpha >= 0 ? 'green.500' : 'red.500'}>
                                      {performanceData.benchmarks.vs_sp500.alpha >= 0 ? '+' : ''}{performanceData.benchmarks.vs_sp500.alpha}%
                                    </Text>
                                  </HStack>
                                </VStack>
                              </Box>

                              <Box>
                                <Text fontWeight="semibold" mb={2}>vs NASDAQ</Text>
                                <VStack spacing={2} align="stretch">
                                  <HStack justify="space-between">
                                    <Text fontSize="sm">Portfolio Return:</Text>
                                    <Text fontSize="sm" fontWeight="bold" color="blue.500">
                                      {performanceData.benchmarks.vs_nasdaq.portfolio_return}%
                                    </Text>
                                  </HStack>
                                  <HStack justify="space-between">
                                    <Text fontSize="sm">NASDAQ Return:</Text>
                                    <Text fontSize="sm" fontWeight="bold">
                                      {performanceData.benchmarks.vs_nasdaq.benchmark_return}%
                                    </Text>
                                  </HStack>
                                  <HStack justify="space-between">
                                    <Text fontSize="sm">Alpha:</Text>
                                    <Text fontSize="sm" fontWeight="bold" color={performanceData.benchmarks.vs_nasdaq.alpha >= 0 ? 'green.500' : 'red.500'}>
                                      {performanceData.benchmarks.vs_nasdaq.alpha >= 0 ? '+' : ''}{performanceData.benchmarks.vs_nasdaq.alpha}%
                                    </Text>
                                  </HStack>
                                </VStack>
                              </Box>
                            </SimpleGrid>
                          </CardBody>
                        </Card>
                      </>
                    )}
                  </VStack>
                </TabPanel>

                <TabPanel px={0}>
                  <Alert status="info">
                    <AlertIcon />
                    Tax analysis coming soon...
                  </Alert>
                </TabPanel>
              </TabPanels>
            </Tabs>
          )}
        </AccountFilterWrapper>
      </VStack>
    </Container>
  );
};

export default Portfolio; 