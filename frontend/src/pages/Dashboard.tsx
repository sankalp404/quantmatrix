import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  StatRoot,
  StatLabel,
  StatHelpText,
  StatValueText,
  StatUpIndicator,
  StatDownIndicator,
  CardRoot,
  CardHeader,
  CardBody,
  Text,
  VStack,
  HStack,
  Badge,
  SimpleGrid,
  Progress,
  IconButton,
  Select,
  Spinner,
  AlertRoot,
  AlertIndicator,
  AlertDescription,
  Button,
  Flex,
  TableScrollArea,
  TableRoot,
  TableHeader,
  TableBody,
  TableRow,
  TableColumnHeader,
  TableCell,
  Heading,
} from '@chakra-ui/react';
import { FiTrendingUp, FiTrendingDown, FiDollarSign, FiPieChart, FiActivity, FiRefreshCw, FiFilter } from 'react-icons/fi';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { portfolioApi, handleApiError } from '../services/api';
import AccountFilterWrapper from '../components/ui/AccountFilterWrapper';
import { transformPortfolioToAccounts } from '../hooks/useAccountFilter';
import AppDivider from '../components/ui/AppDivider';
import toast from 'react-hot-toast';

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
  unrealized_pnl_pct?: number;
  positions_count: number;
  allocation_pct: number;
}

interface SectorData {
  [key: string]: unknown;
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

  const cardBg = 'bg.card';
  const borderColor = 'border.subtle';

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

      toast.success('Portfolio data has been synced successfully');

      // Refresh the dashboard data after sync
      await fetchDashboardData();

    } catch (err: any) {
      console.error('Error syncing portfolio data:', err);
      toast.error(err.message || 'Failed to sync portfolio data');
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
        <VStack gap={4}>
          <Spinner size="xl" color="brand.500" />
          <Text>Loading dashboard data...</Text>
        </VStack>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={6}>
        <AlertRoot status="error" borderRadius="md" mb={4}>
          <AlertIndicator />
          <AlertDescription>{error}</AlertDescription>
        </AlertRoot>
        <HStack gap={3}>
          <Button onClick={fetchDashboardData}>
            <FiRefreshCw style={{ marginRight: 8 }} />
            Retry
          </Button>
          <Button onClick={syncPortfolioData} colorScheme="blue">
            <FiActivity style={{ marginRight: 8 }} />
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
      <VStack gap={6} align="stretch">
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
                <CardRoot bg={cardBg} borderColor={borderColor} borderWidth="1px" borderRadius="xl">
                  <CardBody>
                    <StatRoot>
                      <StatLabel>
                        <HStack>
                          <FiDollarSign />
                          <Text>Total Value</Text>
                        </HStack>
                      </StatLabel>
                      <StatValueText>{formatCurrency(dashboardData.total_value)}</StatValueText>
                      <StatHelpText>
                        {dashboardData.day_change >= 0 ? <StatUpIndicator /> : <StatDownIndicator />}
                        {formatPercent(dashboardData.day_change_pct)} today
                      </StatHelpText>
                    </StatRoot>
                  </CardBody>
                </CardRoot>

                {/* Unrealized P&L */}
                <CardRoot bg={cardBg} borderColor={borderColor} borderWidth="1px" borderRadius="xl">
                  <CardBody>
                    <StatRoot>
                      <StatLabel>
                        <HStack>
                          <FiTrendingUp />
                          <Text>Unrealized P&L</Text>
                        </HStack>
                      </StatLabel>
                      <StatValueText color={getChangeColor(dashboardData.total_unrealized_pnl)}>
                        {formatCurrency(dashboardData.total_unrealized_pnl)}
                      </StatValueText>
                      <StatHelpText>
                        {formatPercent(dashboardData.total_unrealized_pnl_pct)} total return
                      </StatHelpText>
                    </StatRoot>
                  </CardBody>
                </CardRoot>

                {/* Day Change */}
                <CardRoot bg={cardBg} borderColor={borderColor} borderWidth="1px" borderRadius="xl">
                  <CardBody>
                    <StatRoot>
                      <StatLabel>
                        <HStack>
                          <FiActivity />
                          <Text>Day Change</Text>
                        </HStack>
                      </StatLabel>
                      <StatValueText color={getChangeColor(dashboardData.day_change)}>
                        {formatCurrency(dashboardData.day_change)}
                      </StatValueText>
                      <StatHelpText>
                        {dashboardData.day_change >= 0 ? <StatUpIndicator /> : <StatDownIndicator />}
                        {formatPercent(dashboardData.day_change_pct)}
                      </StatHelpText>
                    </StatRoot>
                  </CardBody>
                </CardRoot>

                {/* Holdings Count */}
                <CardRoot bg={cardBg} borderColor={borderColor} borderWidth="1px" borderRadius="xl">
                  <CardBody>
                    <StatRoot>
                      <StatLabel>
                        <HStack>
                          <FiPieChart />
                          <Text>Holdings</Text>
                        </HStack>
                      </StatLabel>
                      <StatValueText>{dashboardData.holdings_count}</StatValueText>
                      <StatHelpText>
                        {dashboardData.accounts_count} accounts
                      </StatHelpText>
                    </StatRoot>
                  </CardBody>
                </CardRoot>
              </Grid>

              {/* Secondary metrics and charts */}
              <Grid templateColumns={{ base: "1fr", lg: "2fr 1fr" }} gap={6}>
                {/* Sector Allocation */}
                <CardRoot bg={cardBg} borderColor={borderColor} borderWidth="1px" borderRadius="xl">
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
                            label={({ name, percent }) => `${name}: ${(((percent ?? 0) as number) * 100).toFixed(0)}%`}
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
                </CardRoot>

                {/* Account Summary */}
                <CardRoot bg={cardBg} borderColor={borderColor} borderWidth="1px" borderRadius="xl">
                  <CardHeader>
                    <Heading size="md">Account Summary</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack gap={4} align="stretch">
                      {dashboardData.accounts_summary.map((account, index) => (
                        <Box key={account.account_id}>
                          <HStack justify="space-between" mb={2}>
                            <VStack align="start" gap={0}>
                              <Text fontWeight="medium" fontSize="sm">
                                {account.account_name}
                              </Text>
                              <Badge colorScheme={account.broker === 'IBKR' ? 'blue' : 'orange'} size="sm">
                                {account.broker}
                              </Badge>
                            </VStack>
                            <VStack align="end" gap={0}>
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
                          <Progress.Root value={account.allocation_pct || 0} max={100}>
                            <Progress.Track borderRadius="md">
                              <Progress.Range />
                            </Progress.Track>
                          </Progress.Root>
                          {index < dashboardData.accounts_summary.length - 1 && <AppDivider mt={4} />}
                        </Box>
                      ))}
                    </VStack>
                  </CardBody>
                </CardRoot>
              </Grid>

              {/* Top Performers and Losers */}
              <Grid templateColumns={{ base: "1fr", lg: "1fr 1fr" }} gap={6}>
                {/* Top Performers */}
                <CardRoot bg={cardBg} borderColor={borderColor} borderWidth="1px" borderRadius="xl">
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
                      <TableScrollArea>
                        <TableRoot size="sm" variant="line">
                          <TableHeader>
                            <TableRow>
                              <TableColumnHeader>Symbol</TableColumnHeader>
                              <TableColumnHeader textAlign="end">Value</TableColumnHeader>
                              <TableColumnHeader textAlign="end">P&amp;L %</TableColumnHeader>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {dashboardData.top_performers.map((holding, index) => (
                              <TableRow key={index}>
                                <TableCell fontWeight="medium">{holding.symbol}</TableCell>
                                <TableCell textAlign="end">{formatCurrency(holding.market_value)}</TableCell>
                                <TableCell textAlign="end">
                                  <Text color="green.500" fontWeight="medium">
                                    +{formatPercent(holding.unrealized_pnl_pct)}
                                  </Text>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </TableRoot>
                      </TableScrollArea>
                    ) : (
                      <Box textAlign="center" py={4}>
                        <Text color="gray.500" fontSize="sm">No performance data available</Text>
                      </Box>
                    )}
                  </CardBody>
                </CardRoot>

                {/* Top Losers */}
                <CardRoot bg={cardBg} borderColor={borderColor} borderWidth="1px" borderRadius="xl">
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
                      <TableScrollArea>
                        <TableRoot size="sm" variant="line">
                          <TableHeader>
                            <TableRow>
                              <TableColumnHeader>Symbol</TableColumnHeader>
                              <TableColumnHeader textAlign="end">Value</TableColumnHeader>
                              <TableColumnHeader textAlign="end">P&amp;L %</TableColumnHeader>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {dashboardData.top_losers.map((holding, index) => (
                              <TableRow key={index}>
                                <TableCell fontWeight="medium">{holding.symbol}</TableCell>
                                <TableCell textAlign="end">{formatCurrency(holding.market_value)}</TableCell>
                                <TableCell textAlign="end">
                                  <Text color="red.500" fontWeight="medium">
                                    {formatPercent(holding.unrealized_pnl_pct)}
                                  </Text>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </TableRoot>
                      </TableScrollArea>
                    ) : (
                      <Box textAlign="center" py={4}>
                        <Text color="gray.500" fontSize="sm">No performance data available</Text>
                      </Box>
                    )}
                  </CardBody>
                </CardRoot>
              </Grid>
            </>
          )}
        </AccountFilterWrapper>
      </VStack>
    </Box>
  );
};

export default Dashboard; 