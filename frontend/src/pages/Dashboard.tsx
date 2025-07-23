import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Card,
  CardHeader,
  CardBody,
  Text,
  VStack,
  HStack,
  Badge,
  Divider,
  SimpleGrid,
  Progress,
  IconButton,
  useColorModeValue,
  Select,
  Spinner,
  Alert,
  AlertIcon,
  AlertDescription,
  useToast,
  Button,
  Flex,
  TableContainer,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Heading,
} from '@chakra-ui/react';
import { FiTrendingUp, FiTrendingDown, FiDollarSign, FiPieChart, FiActivity, FiRefreshCw, FiFilter } from 'react-icons/fi';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { portfolioApi, handleApiError } from '../services/api';
import AccountFilterWrapper from '../components/AccountFilterWrapper';
import { transformPortfolioToAccounts } from '../hooks/useAccountFilter';

interface DashboardData {
  total_value: number;
  total_unrealized_pnl: number;
  total_unrealized_pnl_pct: number;
  total_cost_basis: number;
  day_change: number;
  day_change_pct: number;
  accounts_summary: AccountSummary[];
  accounts_count: number;
  sector_allocation: SectorData[];
  top_performers: Holding[];
  top_losers: Holding[];
  holdings_count: number;
  last_updated: string;
  brokerage_filter?: string;
  brokerages: string[];
}

interface AccountSummary {
  account_id: string;
  account_name: string;
  account_type: string;
  broker: string;
  total_value: number;
  unrealized_pnl: number;
  positions_count: number;
  allocation_pct: number;
}

interface SectorData {
  name: string;
  value: number;
  percentage: number;
}

interface Holding {
  symbol: string;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  quantity: number;
  current_price: number;
  sector: string;
  account_id: string;
  brokerage: string;
}

const CHART_COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D', '#FFC658', '#FF7C7C'];

const Dashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedBrokerage, setSelectedBrokerage] = useState<string>('all');

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const toast = useToast();

  useEffect(() => {
    fetchDashboardData();
  }, [selectedBrokerage]);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const brokerage = selectedBrokerage !== 'all' ? selectedBrokerage : undefined;
      const result = await portfolioApi.getDashboard(brokerage);

      if (result.status === 'success') {
        setDashboardData(result.data);
      } else {
        throw new Error(result.error || 'Unknown error');
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setError(handleApiError(error));
    } finally {
      setLoading(false);
    }
  };

  const syncPortfolioData = async () => {
    setSyncing(true);
    try {
      const response = await fetch('/api/v1/portfolio/sync', {
        method: 'POST'
      });
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || 'Failed to sync portfolio data');
      }

      toast({
        title: 'Portfolio Synced',
        description: 'Portfolio data has been synced successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      // Refresh the dashboard data after sync
      await fetchDashboardData();

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

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercent = (value: number | undefined | null) => {
    if (value === undefined || value === null || isNaN(value)) {
      return '0.00%';
    }
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getChangeColor = (value: number | undefined | null) => {
    if (value === undefined || value === null || isNaN(value)) {
      return 'gray.500';
    }
    return value >= 0 ? 'green.500' : 'red.500';
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="400px">
        <VStack spacing={4}>
          <Spinner size="xl" color="brand.500" />
          <Text>Loading dashboard data...</Text>
        </VStack>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={6}>
        <Alert status="error" borderRadius="md" mb={4}>
          <AlertIcon />
          <AlertDescription>
            {error}
          </AlertDescription>
        </Alert>
        <HStack spacing={3}>
          <Button onClick={fetchDashboardData} leftIcon={<FiRefreshCw />}>
            Retry
          </Button>
          <Button onClick={syncPortfolioData} leftIcon={<FiActivity />} colorScheme="blue">
            Sync Portfolio
          </Button>
        </HStack>
      </Box>
    );
  }

  if (!dashboardData) {
    return (
      <Box p={6}>
        <Text>No dashboard data available</Text>
      </Box>
    );
  }

  return (
    <Box p={6}>
      {/* Header with unified account selector */}
      <VStack spacing={6} align="stretch">
        <Box>
          <Heading size="lg" mb={2}>Portfolio Dashboard</Heading>
          <Text color="gray.500" fontSize="sm">
            Real-time data from IBKR • Last updated: {new Date(dashboardData.last_updated).toLocaleTimeString()}
          </Text>
        </Box>

        {/* Unified Account Filter */}
        <AccountFilterWrapper
          data={dashboardData.top_performers || []}
          accounts={dashboardData.accounts_summary}
          loading={loading}
          error={error}
          config={{
            showAllOption: true,
            showSummary: true,
            variant: 'detailed',
            size: 'md'
          }}
          onAccountChange={(accountId) => setSelectedBrokerage(accountId)}
        >
          {(filteredData, filterState) => (
            <>
              {/* Main Dashboard Content */}
              <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)", lg: "repeat(4, 1fr)" }} gap={6}>
                {/* Total Portfolio Value */}
                <Card bg={cardBg} borderColor={borderColor}>
                  <CardBody>
                    <Stat>
                      <StatLabel>
                        <HStack>
                          <FiDollarSign />
                          <Text>Total Value</Text>
                        </HStack>
                      </StatLabel>
                      <StatNumber>{formatCurrency(dashboardData.total_value)}</StatNumber>
                      <StatHelpText>
                        <StatArrow type={dashboardData.day_change >= 0 ? 'increase' : 'decrease'} />
                        {formatPercent(dashboardData.day_change_pct)} today
                      </StatHelpText>
                    </Stat>
                  </CardBody>
                </Card>

                {/* Unrealized P&L */}
                <Card bg={cardBg} borderColor={borderColor}>
                  <CardBody>
                    <Stat>
                      <StatLabel>
                        <HStack>
                          <FiTrendingUp />
                          <Text>Unrealized P&L</Text>
                        </HStack>
                      </StatLabel>
                      <StatNumber color={getChangeColor(dashboardData.total_unrealized_pnl)}>
                        {formatCurrency(dashboardData.total_unrealized_pnl)}
                      </StatNumber>
                      <StatHelpText>
                        {formatPercent(dashboardData.total_unrealized_pnl_pct)} total return
                      </StatHelpText>
                    </Stat>
                  </CardBody>
                </Card>

                {/* Day Change */}
                <Card bg={cardBg} borderColor={borderColor}>
                  <CardBody>
                    <Stat>
                      <StatLabel>
                        <HStack>
                          <FiActivity />
                          <Text>Day Change</Text>
                        </HStack>
                      </StatLabel>
                      <StatNumber color={getChangeColor(dashboardData.day_change)}>
                        {formatCurrency(dashboardData.day_change)}
                      </StatNumber>
                      <StatHelpText>
                        <StatArrow type={dashboardData.day_change >= 0 ? 'increase' : 'decrease'} />
                        {formatPercent(dashboardData.day_change_pct)}
                      </StatHelpText>
                    </Stat>
                  </CardBody>
                </Card>

                {/* Holdings Count */}
                <Card bg={cardBg} borderColor={borderColor}>
                  <CardBody>
                    <Stat>
                      <StatLabel>
                        <HStack>
                          <FiPieChart />
                          <Text>Holdings</Text>
                        </HStack>
                      </StatLabel>
                      <StatNumber>{dashboardData.holdings_count}</StatNumber>
                      <StatHelpText>
                        {dashboardData.accounts_count} accounts
                      </StatHelpText>
                    </Stat>
                  </CardBody>
                </Card>
              </Grid>

              {/* Secondary metrics and charts */}
              <Grid templateColumns={{ base: "1fr", lg: "2fr 1fr" }} gap={6}>
                {/* Sector Allocation */}
                <Card bg={cardBg} borderColor={borderColor}>
                  <CardHeader>
                    <Heading size="md">Sector Allocation</Heading>
                  </CardHeader>
                  <CardBody>
                    {dashboardData.sector_allocation && dashboardData.sector_allocation.length > 0 ? (
                      <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                          <Pie
                            data={dashboardData.sector_allocation}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            outerRadius={80}
                            fill="#8884d8"
                            dataKey="value"
                            label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                          >
                            {dashboardData.sector_allocation.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    ) : (
                      <Box textAlign="center" py={8}>
                        <Text color="gray.500">No sector data available</Text>
                      </Box>
                    )}
                  </CardBody>
                </Card>

                {/* Account Summary */}
                <Card bg={cardBg} borderColor={borderColor}>
                  <CardHeader>
                    <Heading size="md">Account Summary</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack spacing={4} align="stretch">
                      {dashboardData.accounts_summary.map((account, index) => (
                        <Box key={account.account_id}>
                          <HStack justify="space-between" mb={2}>
                            <VStack align="start" spacing={0}>
                              <Text fontWeight="medium" fontSize="sm">
                                {account.account_name}
                              </Text>
                              <Badge colorScheme={account.broker === 'IBKR' ? 'blue' : 'orange'} size="sm">
                                {account.broker}
                              </Badge>
                            </VStack>
                            <VStack align="end" spacing={0}>
                              <Text fontWeight="bold" fontSize="sm">
                                {formatCurrency(account.total_value)}
                              </Text>
                              <Text
                                fontSize="xs"
                                color={getChangeColor(account.unrealized_pnl_pct)}
                              >
                                {formatPercent(account.unrealized_pnl_pct)}
                              </Text>
                            </VStack>
                          </HStack>
                          <Progress
                            value={account.allocation_pct || 0}
                            size="sm"
                            colorScheme={(account.unrealized_pnl_pct || 0) >= 0 ? 'green' : 'red'}
                            borderRadius="md"
                          />
                          {index < dashboardData.accounts_summary.length - 1 && <Divider mt={4} />}
                        </Box>
                      ))}
                    </VStack>
                  </CardBody>
                </Card>
              </Grid>

              {/* Top Performers and Losers */}
              <Grid templateColumns={{ base: "1fr", lg: "1fr 1fr" }} gap={6}>
                {/* Top Performers */}
                <Card bg={cardBg} borderColor={borderColor}>
                  <CardHeader>
                    <HStack justify="space-between">
                      <Heading size="md">Top Performers</Heading>
                      <Badge colorScheme="green">
                        {dashboardData.top_performers.length} holdings
                      </Badge>
                    </HStack>
                  </CardHeader>
                  <CardBody>
                    {dashboardData.top_performers.length > 0 ? (
                      <TableContainer>
                        <Table size="sm">
                          <Thead>
                            <Tr>
                              <Th>Symbol</Th>
                              <Th isNumeric>Value</Th>
                              <Th isNumeric>P&L %</Th>
                            </Tr>
                          </Thead>
                          <Tbody>
                            {dashboardData.top_performers.map((holding, index) => (
                              <Tr key={index}>
                                <Td fontWeight="medium">{holding.symbol}</Td>
                                <Td isNumeric>{formatCurrency(holding.market_value)}</Td>
                                <Td isNumeric>
                                  <Text color="green.500" fontWeight="medium">
                                    +{formatPercent(holding.unrealized_pnl_pct)}
                                  </Text>
                                </Td>
                              </Tr>
                            ))}
                          </Tbody>
                        </Table>
                      </TableContainer>
                    ) : (
                      <Box textAlign="center" py={4}>
                        <Text color="gray.500" fontSize="sm">No performance data available</Text>
                      </Box>
                    )}
                  </CardBody>
                </Card>

                {/* Top Losers */}
                <Card bg={cardBg} borderColor={borderColor}>
                  <CardHeader>
                    <HStack justify="space-between">
                      <Heading size="md">Biggest Losers</Heading>
                      <Badge colorScheme="red">
                        {dashboardData.top_losers.length} holdings
                      </Badge>
                    </HStack>
                  </CardHeader>
                  <CardBody>
                    {dashboardData.top_losers.length > 0 ? (
                      <TableContainer>
                        <Table size="sm">
                          <Thead>
                            <Tr>
                              <Th>Symbol</Th>
                              <Th isNumeric>Value</Th>
                              <Th isNumeric>P&L %</Th>
                            </Tr>
                          </Thead>
                          <Tbody>
                            {dashboardData.top_losers.map((holding, index) => (
                              <Tr key={index}>
                                <Td fontWeight="medium">{holding.symbol}</Td>
                                <Td isNumeric>{formatCurrency(holding.market_value)}</Td>
                                <Td isNumeric>
                                  <Text color="red.500" fontWeight="medium">
                                    {formatPercent(holding.unrealized_pnl_pct)}
                                  </Text>
                                </Td>
                              </Tr>
                            ))}
                          </Tbody>
                        </Table>
                      </TableContainer>
                    ) : (
                      <Box textAlign="center" py={4}>
                        <Text color="gray.500" fontSize="sm">No performance data available</Text>
                      </Box>
                    )}
                  </CardBody>
                </Card>
              </Grid>
            </>
          )}
        </AccountFilterWrapper>
      </VStack>
    </Box>
  );
};

export default Dashboard; 