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
  Input,
  InputGroup,
  InputLeftElement,
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
  useToast
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
import { SearchIcon, WarningIcon, InfoIcon } from '@chakra-ui/icons';
import { FiRefreshCw } from 'react-icons/fi';

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
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAccount, setSelectedAccount] = useState('');
  const [filterMethod, setFilterMethod] = useState('all');
  const [sortBy, setSortBy] = useState('purchase_date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const toast = useToast();

  useEffect(() => {
    fetchTaxLots();
  }, [selectedAccount]);

  const fetchTaxLots = async () => {
    setLoading(true);
    setError(null);
    try {
      // FIXED: Remove account_id filtering for now - backend doesn't support account filtering yet
      // const params = new URLSearchParams();
      // if (selectedAccount && selectedAccount !== 'all') {
      //   params.append('account_id', selectedAccount);
      // }

      const response = await fetch(`/api/v1/portfolio/tax-lots`); // Simplified API call without parameters
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

  // Filter and sort tax lots
  const filteredTaxLots = taxLots
    .filter(lot =>
      lot.symbol.toLowerCase().includes(searchTerm.toLowerCase()) &&
      (selectedAccount === '' || lot.account_id === selectedAccount)
    )
    .sort((a, b) => {
      const aVal = a[sortBy as keyof TaxLot];
      const bVal = b[sortBy as keyof TaxLot];
      return sortOrder === 'desc' ? bVal - aVal : aVal - bVal;
    });

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
          <Text color="gray.600">
            Detailed tax lot tracking with cost basis, holding periods, and tax implications
          </Text>
        </Box>

        {/* Summary Cards */}
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
          <Card bg={cardBg} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Total Positions</StatLabel>
                <StatNumber>{summary?.total_lots || 0}</StatNumber>
                <StatHelpText>Tax lots tracked</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={cardBg} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Total Cost Basis</StatLabel>
                <StatNumber>${(summary?.total_cost_basis || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</StatNumber>
                <StatHelpText>Original investment</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={cardBg} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Total Market Value</StatLabel>
                <StatNumber>${(summary?.total_market_value || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</StatNumber>
                <StatHelpText>Current value</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={cardBg} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Unrealized P&L</StatLabel>
                <StatNumber color={(summary?.total_unrealized_pnl || 0) >= 0 ? 'green.500' : 'red.500'}>
                  <StatArrow type={(summary?.total_unrealized_pnl || 0) >= 0 ? 'increase' : 'decrease'} />
                  ${Math.abs(summary?.total_unrealized_pnl || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                </StatNumber>
                <StatHelpText>
                  {((summary?.total_unrealized_pnl_pct || 0) >= 0 ? '+' : '')}{(summary?.total_unrealized_pnl_pct || 0).toFixed(2)}%
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        <Tabs variant="enclosed" colorScheme="blue">
          <TabList>
            <Tab>Tax Lots Table</Tab>
            <Tab>Holding Period Analysis</Tab>
            <Tab>Tax Planning</Tab>
            <Tab>Charts & Visualization</Tab>
          </TabList>

          <TabPanels>
            {/* Tax Lots Table */}
            <TabPanel px={0}>
              <Card bg={cardBg} borderColor={borderColor}>
                <CardHeader>
                  <HStack justify="space-between" wrap="wrap" spacing={4}>
                    <Heading size="md">Tax Lots Detail</Heading>
                    <HStack spacing={3}>
                      <InputGroup size="sm" maxW="200px">
                        <InputLeftElement>
                          <SearchIcon color="gray.400" />
                        </InputLeftElement>
                        <Input
                          placeholder="Search symbols..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                        />
                      </InputGroup>

                      <Select size="sm" maxW="150px" value={selectedAccount} onChange={(e) => setSelectedAccount(e.target.value)}>
                        <option value="">All Accounts</option>
                        {/* Assuming you have a list of accounts from your portfolio data */}
                        {/* For now, we'll just show a placeholder */}
                        <option value="IBKR_123456">IBKR_123456</option>
                        <option value="IBKR_789012">IBKR_789012</option>
                      </Select>

                      <Select size="sm" maxW="150px" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                        <option value="purchase_date">Purchase Date</option>
                        <option value="market_value">Market Value</option>
                        <option value="unrealized_pnl_pct">P&L %</option>
                        <option value="holding_days">Holding Days</option>
                      </Select>
                    </HStack>
                  </HStack>
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
                        {filteredTaxLots.slice(0, 50).map(lot => (
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
                                    <Icon as={WarningIcon} boxSize={3} />
                                  </Badge>
                                </Tooltip>
                              )}
                            </Td>
                          </Tr>
                        ))}
                      </Tbody>
                    </Table>
                  </Box>

                  {filteredTaxLots.length > 50 && (
                    <Text mt={4} fontSize="sm" color="gray.600">
                      Showing first 50 of {filteredTaxLots.length} tax lots. Use search to narrow results.
                    </Text>
                  )}
                </CardBody>
              </Card>
            </TabPanel>

            {/* Holding Period Analysis */}
            <TabPanel px={0}>
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
            </TabPanel>

            {/* Tax Planning */}
            <TabPanel px={0}>
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
            </TabPanel>

            {/* Charts & Visualization */}
            <TabPanel px={0}>
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
                      <AreaChart data={holdingPeriodData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="period" />
                        <YAxis />
                        <RechartsTooltip
                          formatter={(value) => [`$${Number(value).toLocaleString()}`, 'Value']}
                        />
                        <Area type="monotone" dataKey="value" stroke="#4299E1" fill="#4299E1" fillOpacity={0.6} />
                      </AreaChart>
                    </ResponsiveContainer>
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

export default TaxLots; 