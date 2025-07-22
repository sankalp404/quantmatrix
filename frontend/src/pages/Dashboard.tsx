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
import AccountSelector from '../components/AccountSelector';

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

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getChangeColor = (value: number) => {
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

        {/* Unified Account Selector */}
        <AccountSelector
          accounts={dashboardData.accounts_summary}
          selectedAccount={selectedBrokerage === 'all' ? 'all' : selectedBrokerage}
          onAccountChange={(accountId) => setSelectedBrokerage(accountId)}
          showAllOption={true}
          showSummary={true}
          variant="detailed"
        />

        {/* Main Dashboard Content */}
        <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
          {/* Portfolio Overview */}
          <Card bg={cardBg}>
            <CardHeader>
              <HStack justify="space-between">
                <Text fontSize="lg" fontWeight="bold">Portfolio Overview</Text>
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
              </HStack>
            </CardHeader>
            <CardBody>
              <SimpleGrid columns={2} spacing={4}>
                <Stat>
                  <StatLabel>Total Value</StatLabel>
                  <StatNumber>{formatCurrency(dashboardData.total_value)}</StatNumber>
                  <StatHelpText>
                    <StatArrow type={dashboardData.total_unrealized_pnl >= 0 ? 'increase' : 'decrease'} />
                    {dashboardData.total_unrealized_pnl_pct.toFixed(2)}%
                  </StatHelpText>
                </Stat>
                <Stat>
                  <StatLabel>Day Change</StatLabel>
                  <StatNumber color={getChangeColor(dashboardData.day_change)}>
                    {formatCurrency(dashboardData.day_change)}
                  </StatNumber>
                  <StatHelpText>
                    <StatArrow type={dashboardData.day_change >= 0 ? 'increase' : 'decrease'} />
                    {dashboardData.day_change_pct.toFixed(2)}%
                  </StatHelpText>
                </Stat>
              </SimpleGrid>
            </CardBody>
          </Card>

          {/* Key Metrics Row */}
          <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6} mb={8}>
            <Card bg={cardBg} border="1px" borderColor={borderColor}>
              <CardBody>
                <Stat>
                  <StatLabel>Total Positions</StatLabel>
                  <StatNumber fontSize="2xl">{dashboardData.holdings_count}</StatNumber>
                  <StatHelpText>
                    Across {dashboardData.accounts_count} accounts
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={cardBg} border="1px" borderColor={borderColor}>
              <CardBody>
                <Stat>
                  <StatLabel>Cost Basis</StatLabel>
                  <StatNumber fontSize="2xl">{formatCurrency(dashboardData.total_cost_basis)}</StatNumber>
                  <StatHelpText>
                    Total invested capital
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={cardBg} border="1px" borderColor={borderColor}>
              <CardBody>
                <Stat>
                  <StatLabel>Day Change</StatLabel>
                  <StatNumber fontSize="2xl" color={getChangeColor(dashboardData.day_change)}>
                    {formatCurrency(dashboardData.day_change)}
                  </StatNumber>
                  <StatHelpText>
                    <StatArrow type={dashboardData.day_change >= 0 ? "increase" : "decrease"} />
                    {formatPercent(dashboardData.day_change_pct)}
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>

          {/* Accounts Summary */}
          <Card bg={cardBg} border="1px" borderColor={borderColor} mb={8}>
            <CardHeader>
              <Text fontSize="lg" fontWeight="semibold">Accounts Summary</Text>
            </CardHeader>
            <CardBody>
              <TableContainer>
                <Table size="sm">
                  <Thead>
                    <Tr>
                      <Th>Account</Th>
                      <Th>Brokerage</Th>
                      <Th isNumeric>Value</Th>
                      <Th isNumeric>P&L</Th>
                      <Th isNumeric>Positions</Th>
                      <Th isNumeric>Allocation</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {dashboardData.accounts_summary.map((account) => (
                      <Tr key={account.account_id}>
                        <Td>
                          <VStack align="start" spacing={1}>
                            <Text fontWeight="bold">{account.account_name}</Text>
                            <Text fontSize="xs" color="gray.500">{account.account_id}</Text>
                          </VStack>
                        </Td>
                        <Td>
                          <Badge colorScheme={account.broker === 'IBKR' ? 'blue' : 'orange'}>
                            {account.broker}
                          </Badge>
                        </Td>
                        <Td isNumeric>{formatCurrency(account.total_value)}</Td>
                        <Td isNumeric color={getChangeColor(account.unrealized_pnl)}>
                          {formatCurrency(account.unrealized_pnl)}
                        </Td>
                        <Td isNumeric>{account.positions_count}</Td>
                        <Td isNumeric>{account.allocation_pct.toFixed(1)}%</Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </TableContainer>
            </CardBody>
          </Card>

          {/* Charts and Performance Row */}
          <Grid templateColumns={{ base: '1fr', lg: '1fr 1fr' }} gap={8} mb={8}>
            {/* Sector Allocation */}
            <Card bg={cardBg} border="1px" borderColor={borderColor}>
              <CardHeader>
                <Text fontSize="lg" fontWeight="semibold">Sector Allocation</Text>
              </CardHeader>
              <CardBody>
                {dashboardData.sector_allocation.length > 0 ? (
                  <Box height="300px">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={dashboardData.sector_allocation}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ name, percentage }) => `${name} ${percentage.toFixed(1)}%`}
                          outerRadius={80}
                          fill="#8884d8"
                          dataKey="value"
                        >
                          {dashboardData.sector_allocation.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value) => formatCurrency(value as number)} />
                      </PieChart>
                    </ResponsiveContainer>
                  </Box>
                ) : (
                  <Text color="gray.500" textAlign="center" py={8}>
                    No sector data available
                  </Text>
                )}
              </CardBody>
            </Card>

            {/* Top Performers */}
            <Card bg={cardBg} border="1px" borderColor={borderColor}>
              <CardHeader>
                <Text fontSize="lg" fontWeight="semibold">Top Performers</Text>
              </CardHeader>
              <CardBody>
                <VStack spacing={4} align="stretch">
                  {dashboardData.top_performers.length > 0 ?
                    dashboardData.top_performers.map((holding, index) => (
                      <Flex key={`${holding.symbol}-${holding.account_id}`} justify="space-between" align="center">
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="bold">{holding.symbol}</Text>
                          <HStack spacing={2}>
                            <Badge size="sm" colorScheme={holding.brokerage === 'IBKR' ? 'blue' : 'orange'}>
                              {holding.brokerage}
                            </Badge>
                            <Text fontSize="xs" color="gray.500">{holding.sector}</Text>
                          </HStack>
                        </VStack>
                        <VStack align="end" spacing={0}>
                          <Text fontWeight="bold">{formatCurrency(holding.market_value)}</Text>
                          <Text fontSize="sm" color="green.500">
                            {formatPercent(holding.unrealized_pnl_pct)}
                          </Text>
                        </VStack>
                      </Flex>
                    )) :
                    <Text color="gray.500" textAlign="center">No positions available</Text>
                  }
                </VStack>
              </CardBody>
            </Card>
          </Grid>

          {/* Bottom Row - Top Losers */}
          {dashboardData.top_losers.length > 0 && (
            <Card bg={cardBg} border="1px" borderColor={borderColor}>
              <CardHeader>
                <Text fontSize="lg" fontWeight="semibold">Top Losers</Text>
              </CardHeader>
              <CardBody>
                <SimpleGrid columns={{ base: 1, md: 2, lg: 5 }} spacing={4}>
                  {dashboardData.top_losers.map((holding, index) => (
                    <Box key={`${holding.symbol}-${holding.account_id}`} p={3} borderRadius="md" bg="red.50" border="1px" borderColor="red.200">
                      <VStack spacing={2}>
                        <Text fontWeight="bold">{holding.symbol}</Text>
                        <Text fontSize="sm" color="red.600">
                          {formatPercent(holding.unrealized_pnl_pct)}
                        </Text>
                        <Text fontSize="xs">{formatCurrency(holding.market_value)}</Text>
                        <Badge size="sm" colorScheme={holding.brokerage === 'IBKR' ? 'blue' : 'orange'}>
                          {holding.brokerage}
                        </Badge>
                      </VStack>
                    </Box>
                  ))}
                </SimpleGrid>
              </CardBody>
            </Card>
          )}
        </SimpleGrid>
      </VStack>
    </Box>
  );
};

export default Dashboard; 