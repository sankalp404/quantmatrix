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
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Button,
  Select,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Spinner,
  Alert,
  AlertIcon,
  useColorModeValue,
  Flex,
  Icon,
  Tooltip,
  Progress,
  Divider
} from '@chakra-ui/react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  BarChart,
  Bar,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { CalendarIcon, InfoIcon, WarningIcon } from '@chakra-ui/icons';
import { usePortfolio } from '../hooks/usePortfolio';
import { portfolioApi } from '../services/api';
import SortableTable, { Column } from '../components/SortableTable';

// Calendar component for dividend dates
const DividendCalendar: React.FC<{ dividends: any[], selectedMonth: Date }> = ({ dividends, selectedMonth }) => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const todayColor = useColorModeValue('blue.100', 'blue.900');

  const daysInMonth = new Date(selectedMonth.getFullYear(), selectedMonth.getMonth() + 1, 0).getDate();
  const firstDayOfWeek = new Date(selectedMonth.getFullYear(), selectedMonth.getMonth(), 1).getDay();
  const today = new Date();

  const monthDividends = dividends.filter(div => {
    const divDate = new Date(div.ex_date);
    return divDate.getMonth() === selectedMonth.getMonth() &&
      divDate.getFullYear() === selectedMonth.getFullYear();
  });

  const getDividendsForDate = (date: number) => {
    return monthDividends.filter(div => {
      const divDate = new Date(div.ex_date);
      return divDate.getDate() === date;
    });
  };

  const days = [];
  const monthNames = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];

  // Add empty cells for days before the first day of the month
  for (let i = 0; i < firstDayOfWeek; i++) {
    days.push(<Box key={`empty-${i}`} h="100px" />);
  }

  // Add cells for each day of the month
  for (let date = 1; date <= daysInMonth; date++) {
    const dateDividends = getDividendsForDate(date);
    const isToday = today.getDate() === date &&
      today.getMonth() === selectedMonth.getMonth() &&
      today.getFullYear() === selectedMonth.getFullYear();

    days.push(
      <Box
        key={date}
        h="100px"
        border="1px solid"
        borderColor={borderColor}
        bg={isToday ? todayColor : bgColor}
        p={2}
        position="relative"
      >
        <Text fontWeight={isToday ? "bold" : "normal"} fontSize="sm">
          {date}
        </Text>
        {dateDividends.length > 0 && (
          <VStack spacing={1} mt={2}>
            {dateDividends.slice(0, 2).map((div, idx) => {
              const isProjection = div.type === 'projection';
              const amount = isProjection ? div.estimated_total || div.estimated_dividend_per_share : (div.total_dividend || div.dividend_per_share);
              const tooltipText = isProjection
                ? `${div.symbol}: $${amount?.toFixed(2)} (Projected - ${div.confidence} confidence)`
                : `${div.symbol}: $${amount?.toFixed(2)} (Historical)`;

              return (
                <Tooltip key={idx} label={tooltipText}>
                  <Badge
                    size="sm"
                    colorScheme={isProjection ? 'purple' : 'green'}
                    variant={isProjection ? 'outline' : 'solid'}
                    fontSize="xs"
                    w="full"
                  >
                    {div.symbol} ${amount?.toFixed(2)}
                    {isProjection && ' *'}
                  </Badge>
                </Tooltip>
              );
            })}
            {dateDividends.length > 2 && (
              <Text fontSize="xs" color="gray.500">
                +{dateDividends.length - 2} more
              </Text>
            )}
          </VStack>
        )}
      </Box>
    );
  }

  return (
    <Card bg={bgColor} borderColor={borderColor}>
      <CardHeader>
        <Heading size="md">
          {monthNames[selectedMonth.getMonth()]} {selectedMonth.getFullYear()}
        </Heading>
      </CardHeader>
      <CardBody>
        <SimpleGrid columns={7} spacing={0}>
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
            <Box key={day} p={2} textAlign="center" fontWeight="bold" borderBottom="1px" borderColor={borderColor}>
              {day}
            </Box>
          ))}
          {days}
        </SimpleGrid>
      </CardBody>
    </Card>
  );
};

// Real dividend data fetcher - gets actual IBKR dividend history with enhanced projections
const fetchDividendData = async (days: number = 365, accountId?: string) => {
  try {
    const result = await portfolioApi.getDividends(accountId, days);

    if (result.status === 'success') {
      return {
        dividends: result.data.dividends || [],
        summary: result.data.summary || {},
        projections: result.data.projections || [],
        upcomingDividends: result.data.upcoming_dividends || [],
        analysis: result.data.analysis || {},
        source: 'real_ibkr_data_with_projections'
      };
    } else {
      throw new Error(result.error || 'Failed to fetch dividend data');
    }
  } catch (error: any) {
    console.error('Error fetching real dividend data:', error);
    return {
      dividends: [],
      summary: null,
      projections: [],
      upcomingDividends: [],
      analysis: {},
      error: (error && (error as any).message) || 'Unknown error'
    };
  }
};

const DividendsCalendar: React.FC = () => {
  const [dividendData, setDividendData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedView, setSelectedView] = useState<'upcoming' | 'calendar' | 'analysis'>('upcoming');
  const [timeframe, setTimeframe] = useState<string>('365');
  const [selectedAccount, setSelectedAccount] = useState<string | undefined>(undefined);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  useEffect(() => {
    loadDividendData();
  }, [timeframe, selectedAccount]);

  const loadDividendData = async () => {
    setLoading(true);
    setError(null);

    try {
      const days = parseInt(timeframe) || 365;
      const data = await fetchDividendData(days, selectedAccount);

      if (data.error) {
        setError(data.error);
      } else {
        setDividendData(data);
      }
    } catch (err: any) {
      console.error('Error loading dividend data:', err);
      setError('Failed to load dividend data');
    } finally {
      setLoading(false);
    }
  };

  // Process dividend data with enhanced projections
  const {
    dividends = [],
    summary = null,
    projections = [],
    upcomingDividends: upcomingFromAPI = [],
    analysis = {}
  } = dividendData || {};

  // Combine historical dividends with projections for calendar view
  const allDividendEvents = [
    ...dividends.map((d: any) => ({ ...d, type: 'historical' })),
    ...projections.map((p: any) => ({ ...p, type: 'projection' }))
  ].sort((a, b) => new Date(a.ex_date).getTime() - new Date(b.ex_date).getTime());

  // Filter dividends for current view - use projections for upcoming
  const upcomingDividends = projections.filter((proj: any) => {
    const projDate = new Date(proj.ex_date);
    const today = new Date();
    return projDate > today;
  }).slice(0, 10);

  const thisMonthDividends = allDividendEvents.filter((div: any) => {
    const divDate = new Date(div.ex_date);
    const today = new Date();
    return divDate.getMonth() === today.getMonth() && divDate.getFullYear() === today.getFullYear();
  });

  if (loading) {
    return (
      <Container maxW="container.xl" py={8}>
        <Flex justify="center" align="center" h="400px">
          <VStack>
            <Spinner size="xl" color="blue.500" />
            <Text>Loading real dividend data from IBKR...</Text>
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
          Error loading dividend data: {error}
          <Button ml={4} onClick={loadDividendData} size="sm">
            Retry
          </Button>
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box>
          <Heading size="lg" mb={2}>Dividends Calendar</Heading>
          <Text color="gray.600">
            Track dividend income, upcoming payments, and annual projections
          </Text>
        </Box>

        {/* Account Selector (reusing AccountFilterWrapper is heavier here; simple dropdown for SSR filter) */}
        {/* In a future pass we can unify with AccountFilterWrapper for consistency */}
        {/* Summary Cards */}
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Annual Income</StatLabel>
                <StatNumber>${(summary?.total_annual_income || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</StatNumber>
                <StatHelpText>
                  <StatArrow type="increase" />
                  {(summary?.growth_rate || 0).toFixed(1)}% growth
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Monthly Average</StatLabel>
                <StatNumber>${(summary?.avg_monthly_income || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</StatNumber>
                <StatHelpText>Projected income</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Portfolio Yield</StatLabel>
                <StatNumber>{(summary?.dividend_yield || 0).toFixed(2)}%</StatNumber>
                <StatHelpText>Dividend yield</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Dividend Stocks</StatLabel>
                <StatNumber>{summary?.dividend_stocks_count || 0}</StatNumber>
                <StatHelpText>Income generators</StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Next Month Preview */}
        <Card bg={bgColor} borderColor={borderColor}>
          <CardHeader>
            <HStack justify="space-between">
              <Heading size="md">This Month's Dividends</Heading>
              <Badge colorScheme="green" variant="subtle">
                ${(summary?.next_month_income || 0).toFixed(0)} expected
              </Badge>
            </HStack>
          </CardHeader>
          <CardBody>
            {thisMonthDividends.length > 0 ? (
              <HStack spacing={4} wrap="wrap">
                {thisMonthDividends.map((div, idx) => (
                  <Badge key={idx} colorScheme="blue" variant="outline" p={2}>
                    {div.symbol}: ${div.amount} on {new Date(div.ex_date).toLocaleDateString()}
                  </Badge>
                ))}
              </HStack>
            ) : (
              <Text color="gray.600">No dividends expected this month</Text>
            )}
          </CardBody>
        </Card>

        <Tabs variant="enclosed" colorScheme="blue">
          <TabList>
            <Tab>Upcoming Dividends</Tab>
            <Tab>Calendar View</Tab>
            <Tab>All Dividends</Tab>
            <Tab>Income Analysis</Tab>
          </TabList>

          <TabPanels>
            {/* Upcoming Dividends */}
            <TabPanel px={0}>
              <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
                <Card bg={bgColor} borderColor={borderColor}>
                  <CardHeader>
                    <Heading size="md">Next 10 Dividend Payments</Heading>
                  </CardHeader>
                  <CardBody>
                    <SortableTable
                      data={upcomingDividends}
                      columns={[
                        {
                          key: 'symbol',
                          header: 'Symbol',
                          accessor: (item: any) => item.symbol,
                          sortable: true,
                          sortType: 'string',
                        },
                        {
                          key: 'ex_date',
                          header: 'Ex-Date',
                          accessor: (item: any) => item.ex_date,
                          sortable: true,
                          sortType: 'date',
                          render: (value: string) => new Date(value).toLocaleDateString(),
                        },
                        {
                          key: 'dividend_per_share',
                          header: 'Per Share',
                          accessor: (item: any) => item.dividend_per_share || item.amount,
                          sortable: true,
                          sortType: 'number',
                          isNumeric: true,
                          render: (value: number) => `$${value?.toFixed(4) || '0.0000'}`,
                        },
                        {
                          key: 'total_dividend',
                          header: 'Total',
                          accessor: (item: any) => item.total_dividend || item.total_amount,
                          sortable: true,
                          sortType: 'number',
                          isNumeric: true,
                          render: (value: number) => `$${value?.toFixed(2) || '0.00'}`,
                        },
                      ]}
                      defaultSortBy="ex_date"
                      defaultSortOrder="asc"
                      size="sm"
                      emptyMessage="No upcoming dividends found"
                    />
                  </CardBody>
                </Card>

                <Card bg={bgColor} borderColor={borderColor}>
                  <CardHeader>
                    <Heading size="md">This Month's Dividends</Heading>
                  </CardHeader>
                  <CardBody>
                    <SortableTable
                      data={thisMonthDividends}
                      columns={[
                        {
                          key: 'symbol',
                          header: 'Symbol',
                          accessor: (item: any) => item.symbol,
                          sortable: true,
                          sortType: 'string',
                        },
                        {
                          key: 'pay_date',
                          header: 'Pay Date',
                          accessor: (item: any) => item.pay_date,
                          sortable: true,
                          sortType: 'date',
                          render: (value: string) => new Date(value).toLocaleDateString(),
                        },
                        {
                          key: 'total_amount',
                          header: 'Amount',
                          accessor: (item: any) => item.total_amount || item.total_dividend,
                          sortable: true,
                          sortType: 'number',
                          isNumeric: true,
                          render: (value: number) => `$${value?.toFixed(2) || '0.00'}`,
                        },
                        {
                          key: 'status',
                          header: 'Status',
                          accessor: (item: any) => item.status || 'upcoming',
                          sortable: true,
                          sortType: 'string',
                          render: (value: string) => (
                            <Badge colorScheme={value === 'paid' ? 'green' : 'blue'}>
                              {value.toUpperCase()}
                            </Badge>
                          ),
                        },
                      ]}
                      defaultSortBy="pay_date"
                      defaultSortOrder="asc"
                      size="sm"
                      emptyMessage="No dividends this month"
                    />
                  </CardBody>
                </Card>
              </SimpleGrid>
            </TabPanel>

            {/* All Dividends Table */}
            <TabPanel px={0}>
              <Card bg={bgColor} borderColor={borderColor}>
                <CardHeader>
                  <HStack justify="space-between">
                    <Heading size="md">All Dividend History</Heading>
                    <Badge variant="outline">
                      {dividends.length} total payments
                    </Badge>
                  </HStack>
                </CardHeader>
                <CardBody>
                  <SortableTable
                    data={dividends}
                    columns={[
                      {
                        key: 'symbol',
                        header: 'Symbol',
                        accessor: (item: any) => item.symbol,
                        sortable: true,
                        sortType: 'string',
                        width: '100px',
                      },
                      {
                        key: 'ex_date',
                        header: 'Ex-Date',
                        accessor: (item: any) => item.ex_date,
                        sortable: true,
                        sortType: 'date',
                        render: (value: string) => new Date(value).toLocaleDateString(),
                      },
                      {
                        key: 'pay_date',
                        header: 'Pay Date',
                        accessor: (item: any) => item.pay_date,
                        sortable: true,
                        sortType: 'date',
                        render: (value: string) => new Date(value).toLocaleDateString(),
                      },
                      {
                        key: 'dividend_per_share',
                        header: 'Per Share',
                        accessor: (item: any) => item.dividend_per_share || item.amount,
                        sortable: true,
                        sortType: 'number',
                        isNumeric: true,
                        render: (value: number) => `$${value?.toFixed(4) || '0.0000'}`,
                      },
                      {
                        key: 'shares',
                        header: 'Shares',
                        accessor: (item: any) => item.shares || item.quantity,
                        sortable: true,
                        sortType: 'number',
                        isNumeric: true,
                        render: (value: number) => value?.toLocaleString() || '0',
                      },
                      {
                        key: 'total_dividend',
                        header: 'Total Dividend',
                        accessor: (item: any) => item.total_dividend || item.total_amount,
                        sortable: true,
                        sortType: 'number',
                        isNumeric: true,
                        render: (value: number) => `$${value?.toFixed(2) || '0.00'}`,
                      },
                      {
                        key: 'tax_withheld',
                        header: 'Tax Withheld',
                        accessor: (item: any) => item.tax_withheld || 0,
                        sortable: true,
                        sortType: 'number',
                        isNumeric: true,
                        render: (value: number) => `$${value?.toFixed(2) || '0.00'}`,
                      },
                      {
                        key: 'net_dividend',
                        header: 'Net Amount',
                        accessor: (item: any) => item.net_dividend || item.total_dividend || item.total_amount,
                        sortable: true,
                        sortType: 'number',
                        isNumeric: true,
                        render: (value: number) => `$${value?.toFixed(2) || '0.00'}`,
                      },
                      {
                        key: 'frequency',
                        header: 'Frequency',
                        accessor: (item: any) => item.frequency || 'quarterly',
                        sortable: true,
                        sortType: 'string',
                        render: (value: string) => (
                          <Badge size="sm" variant="outline">
                            {value.toUpperCase()}
                          </Badge>
                        ),
                      },
                    ]}
                    defaultSortBy="ex_date"
                    defaultSortOrder="desc"
                    size="sm"
                    maxHeight="500px"
                    emptyMessage="No dividend history available"
                  />
                </CardBody>
              </Card>
            </TabPanel>

            {/* Income Projections */}
            <TabPanel px={0}>
              <VStack spacing={6}>
                <Card bg={bgColor} borderColor={borderColor} w="full">
                  <CardHeader>
                    <Heading size="md">12-Month Income Projection</Heading>
                  </CardHeader>
                  <CardBody>
                    <ResponsiveContainer width="100%" height={400}>
                      <BarChart data={analysis.quarterly_trend || []}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="quarter" />
                        <YAxis />
                        <RechartsTooltip
                          formatter={(value) => [`$${Number(value).toLocaleString()}`, 'Dividend Income']}
                        />
                        <Bar dataKey="total" fill="#4299E1" />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardBody>
                </Card>

                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6} w="full">
                  <Card bg={bgColor} borderColor={borderColor}>
                    <CardHeader>
                      <Heading size="md">Income Growth</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={4}>
                        <Stat textAlign="center">
                          <StatLabel>Target Annual Growth</StatLabel>
                          <StatNumber color="green.500">{(summary?.growth_rate || 0).toFixed(1)}%</StatNumber>
                          <StatHelpText>Compound annual growth</StatHelpText>
                        </Stat>

                        <Progress
                          value={65}
                          colorScheme="green"
                          size="lg"
                          w="full"
                          hasStripe
                          isAnimated
                        />

                        <Text fontSize="sm" color="gray.600" textAlign="center">
                          65% progress toward annual target
                        </Text>
                      </VStack>
                    </CardBody>
                  </Card>

                  <Card bg={bgColor} borderColor={borderColor}>
                    <CardHeader>
                      <Heading size="md">Income Diversification</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={3}>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Technology</Text>
                          <Text fontSize="sm" fontWeight="semibold">45%</Text>
                        </HStack>
                        <Progress value={45} colorScheme="blue" size="sm" w="full" />

                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Financial</Text>
                          <Text fontSize="sm" fontWeight="semibold">25%</Text>
                        </HStack>
                        <Progress value={25} colorScheme="green" size="sm" w="full" />

                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Healthcare</Text>
                          <Text fontSize="sm" fontWeight="semibold">20%</Text>
                        </HStack>
                        <Progress value={20} colorScheme="purple" size="sm" w="full" />

                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Other</Text>
                          <Text fontSize="sm" fontWeight="semibold">10%</Text>
                        </HStack>
                        <Progress value={10} colorScheme="orange" size="sm" w="full" />
                      </VStack>
                    </CardBody>
                  </Card>
                </SimpleGrid>
              </VStack>
            </TabPanel>

            {/* Analytics */}
            <TabPanel px={0}>
              <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
                <Card bg={bgColor} borderColor={borderColor}>
                  <CardHeader>
                    <Heading size="md">Dividend Frequency</Heading>
                  </CardHeader>
                  <CardBody>
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie
                          dataKey="value"
                          data={[
                            { name: 'Quarterly', value: 85, color: '#4299E1' },
                            { name: 'Monthly', value: 10, color: '#48BB78' },
                            { name: 'Annual', value: 5, color: '#ED8936' }
                          ]}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={120}
                          fill="#8884d8"
                        >
                          {[
                            { name: 'Quarterly', value: 85, color: '#4299E1' },
                            { name: 'Monthly', value: 10, color: '#48BB78' },
                            { name: 'Annual', value: 5, color: '#ED8936' }
                          ].map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <RechartsTooltip />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </CardBody>
                </Card>

                <Card bg={bgColor} borderColor={borderColor}>
                  <CardHeader>
                    <Heading size="md">Dividend Insights</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack spacing={4} align="stretch">
                      <Alert status="info" variant="left-accent">
                        <AlertIcon />
                        <Box>
                          <Text fontWeight="semibold">Income Stability</Text>
                          <Text fontSize="sm">
                            Your portfolio generates consistent quarterly income with {summary?.dividend_stocks_count || 0} dividend-paying stocks.
                          </Text>
                        </Box>
                      </Alert>

                      <Alert status="success" variant="left-accent">
                        <AlertIcon />
                        <Box>
                          <Text fontWeight="semibold">Growth Trajectory</Text>
                          <Text fontSize="sm">
                            Dividend income is projected to grow {(summary?.growth_rate || 0).toFixed(1)}% annually through reinvestment and stock appreciation.
                          </Text>
                        </Box>
                      </Alert>

                      <Alert status="warning" variant="left-accent">
                        <AlertIcon />
                        <Box>
                          <Text fontWeight="semibold">Tax Efficiency</Text>
                          <Text fontSize="sm">
                            Consider holding dividend stocks in tax-advantaged accounts to maximize after-tax income.
                          </Text>
                        </Box>
                      </Alert>

                      <Divider />

                      <Box>
                        <Text fontWeight="semibold" mb={2}>Key Metrics</Text>
                        <VStack spacing={2} align="stretch">
                          <HStack justify="space-between">
                            <Text fontSize="sm">Average Dividend Yield:</Text>
                            <Text fontSize="sm" fontWeight="semibold">{(summary?.dividend_yield || 0).toFixed(2)}%</Text>
                          </HStack>
                          <HStack justify="space-between">
                            <Text fontSize="sm">Payout Frequency:</Text>
                            <Text fontSize="sm" fontWeight="semibold">Quarterly</Text>
                          </HStack>
                          <HStack justify="space-between">
                            <Text fontSize="sm">Next Payment:</Text>
                            <Text fontSize="sm" fontWeight="semibold">
                              {upcomingDividends.length > 0 ?
                                new Date(upcomingDividends[0].ex_date).toLocaleDateString() :
                                'No upcoming payments'
                              }
                            </Text>
                          </HStack>
                        </VStack>
                      </Box>
                    </VStack>
                  </CardBody>
                </Card>
              </SimpleGrid>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </VStack>
    </Container>
  );
};

export default DividendsCalendar; 