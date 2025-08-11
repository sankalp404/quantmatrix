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
  Select,
  Input,
  InputGroup,
  InputLeftElement,
  Button,
  Badge,
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
  SimpleGrid,
  Flex,
  Divider,
  Tooltip,
  Icon,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Progress,
} from '@chakra-ui/react';
import { SearchIcon, DownloadIcon, CalendarIcon, RepeatIcon, TimeIcon } from '@chakra-ui/icons';
import {
  FiDollarSign,
  FiTrendingUp,
  FiTrendingDown,
  FiFilter,
  FiArrowUpRight,
  FiArrowDownLeft,
  FiClock,
  FiCalendar,
} from 'react-icons/fi';
import { portfolioApi, handleApiError } from '../services/api';
import AccountFilterWrapper from '../components/AccountFilterWrapper';
import { transformPortfolioToAccounts } from '../hooks/useAccountFilter';
import SortableTable, { Column } from '../components/SortableTable';

interface Transaction {
  id: string;
  date: string;
  time: string;
  symbol: string;
  description: string;
  type: 'BUY' | 'SELL';
  action: string;
  quantity: number;
  price: number;
  amount: number;
  commission: number;
  fees: number;
  net_amount: number;
  currency: string;
  exchange: string;
  order_id?: string;
  execution_id?: string;
  contract_type: string;
  account: string;
  settlement_date?: string;
  source: string;
}

interface TransactionSummary {
  total_transactions: number;
  total_value: number;
  total_commission: number;
  total_fees: number;
  buy_count: number;
  sell_count: number;
  date_range: number;
  net_buy_value: number;
  net_sell_value: number;
  avg_transaction_size: number;
}

// Enhanced Transaction Row Component
const TransactionRow: React.FC<{ transaction: Transaction }> = ({ transaction }) => {
  const isBuy = transaction.type === 'BUY';
  const typeColor = isBuy ? 'green.500' : 'red.500';
  const typeBg = useColorModeValue(
    isBuy ? 'green.50' : 'red.50',
    isBuy ? 'green.900' : 'red.900'
  );

  return (
    <Tr bg={typeBg} _hover={{ bg: useColorModeValue('gray.50', 'gray.700') }}>
      <Td>
        <VStack align="start" spacing={1}>
          <Text fontSize="sm" fontWeight="medium">{transaction.date}</Text>
          <Text fontSize="xs" color="gray.500">
            <Icon as={FiClock} mr={1} />
            {transaction.time}
          </Text>
        </VStack>
      </Td>
      <Td>
        <HStack spacing={2}>
          <Icon
            as={isBuy ? FiArrowDownLeft : FiArrowUpRight}
            color={typeColor}
          />
          <Badge
            colorScheme={isBuy ? 'green' : 'red'}
            variant="subtle"
            size="sm"
          >
            {transaction.type}
          </Badge>
        </HStack>
      </Td>
      <Td>
        <VStack align="start" spacing={0}>
          <Text fontWeight="bold">{transaction.symbol}</Text>
          <Text fontSize="xs" color="gray.500">{transaction.exchange}</Text>
        </VStack>
      </Td>
      <Td isNumeric>
        <Text fontWeight="medium">{transaction.quantity.toLocaleString()}</Text>
      </Td>
      <Td isNumeric>
        <Text>${transaction.price.toFixed(2)}</Text>
      </Td>
      <Td isNumeric>
        <VStack align="end" spacing={0}>
          <Text fontWeight="bold" color={typeColor}>
            ${transaction.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </Text>
          <Text fontSize="xs" color="gray.500">
            Commission: ${transaction.commission.toFixed(2)}
          </Text>
        </VStack>
      </Td>
      <Td isNumeric>
        <Text fontWeight="medium">
          ${Math.abs(transaction.net_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
        </Text>
      </Td>
      <Td>
        <Tooltip label={`Order: ${transaction.order_id}`}>
          <Badge size="sm" variant="outline">
            {transaction.account}
          </Badge>
        </Tooltip>
      </Td>
    </Tr>
  );
};

const Transactions: React.FC = () => {
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState<TransactionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedExchange, setSelectedExchange] = useState<string>('all');
  const [dateRange, setDateRange] = useState<number>(30);
  const [sortBy, setSortBy] = useState<string>('date');

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const toast = useToast();

  const [selectedAccountSSR, setSelectedAccountSSR] = useState<string | undefined>(undefined);

  useEffect(() => {
    fetchData(selectedAccountSSR);
  }, [dateRange]);

  const fetchData = async (accountId?: string) => {
    setLoading(true);
    setError(null);
    try {
      // Fetch portfolio data for account selector
      const portfolioResult = await portfolioApi.getLive(accountId);
      setPortfolioData(portfolioResult.data);

      // Fetch transaction data with server-side filtering
      const result = await portfolioApi.getStatements(accountId, dateRange);
      if (result.status === 'success' && result.data) {
        setTransactions(result.data.transactions || []);
        setSummary(result.data.summary || null);
      } else {
        throw new Error(result.error || 'Failed to fetch transaction data');
      }
    } catch (err) {
      console.error('Error fetching transaction data:', err);
      setError(handleApiError(err));
      toast({
        title: 'Error',
        description: 'Failed to load transaction data',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  // Transform portfolio data for account selector
  const accounts = portfolioData ? transformPortfolioToAccounts(portfolioData) : [];

  // Get unique exchanges for filter (from all transactions for dropdown)
  const uniqueExchanges = [...new Set(transactions.map(t => t.exchange))];

  if (loading) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={8} align="stretch">
          <HStack justify="space-between">
            <Heading size="lg">Transaction History</Heading>
            <Spinner size="lg" />
          </HStack>
        </VStack>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxW="container.xl" py={8}>
        <Alert status="error">
          <AlertIcon />
          {error}
          <Button ml={4} onClick={fetchData} size="sm">
            Retry
          </Button>
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Enhanced Header */}
        <Box>
          <HStack justify="space-between" mb={4}>
            <VStack align="start" spacing={1}>
              <Heading size="lg">Transaction History</Heading>
              <Text color="gray.600">
                {transactions.length} transactions • Last {dateRange} days • Real IBKR data
              </Text>
            </VStack>
            <HStack spacing={3}>
              <Button leftIcon={<RepeatIcon />} size="sm" variant="outline" onClick={fetchData}>
                Refresh
              </Button>
              <Button leftIcon={<DownloadIcon />} size="sm" variant="outline">
                Export CSV
              </Button>
            </HStack>
          </HStack>
        </Box>

        {/* Enhanced Summary Cards */}
        {summary && (
          <SimpleGrid columns={{ base: 2, md: 5 }} spacing={4}>
            <Stat>
              <StatLabel>Total Transactions</StatLabel>
              <StatNumber>{summary.total_transactions}</StatNumber>
              <StatHelpText>
                {summary.buy_count} buys • {summary.sell_count} sells
              </StatHelpText>
            </Stat>
            <Stat>
              <StatLabel>Total Volume</StatLabel>
              <StatNumber>${summary.total_value.toLocaleString()}</StatNumber>
              <StatHelpText>Trade volume</StatHelpText>
            </Stat>
            <Stat>
              <StatLabel>Net Buys</StatLabel>
              <StatNumber color="green.500">
                ${summary.net_buy_value.toLocaleString()}
              </StatNumber>
              <StatHelpText>
                <StatArrow type="increase" />
                Purchases
              </StatHelpText>
            </Stat>
            <Stat>
              <StatLabel>Net Sells</StatLabel>
              <StatNumber color="red.500">
                ${summary.net_sell_value.toLocaleString()}
              </StatNumber>
              <StatHelpText>
                <StatArrow type="decrease" />
                Sales
              </StatHelpText>
            </Stat>
            <Stat>
              <StatLabel>Total Fees</StatLabel>
              <StatNumber>${(summary.total_commission + summary.total_fees).toFixed(2)}</StatNumber>
              <StatHelpText>Commission + fees</StatHelpText>
            </Stat>
          </SimpleGrid>
        )}

        {/* Unified Account Filter */}
        <AccountFilterWrapper
          data={transactions}
          accounts={accounts}
          loading={loading}
          error={error}
          config={{
            showAllOption: true,
            showSummary: true,
            variant: 'detailed',
            size: 'md'
          }}
          onAccountChange={(account) => {
            const accParam = account === 'all' ? undefined : account;
            setSelectedAccountSSR(accParam);
            fetchData(accParam);
          }}
        >
          {(accountFilteredTransactions, filterState) => {
            // Enhanced filtering based on account-filtered transactions
            const filteredTransactions = useMemo(() => {
              return accountFilteredTransactions.filter(transaction => {
                const matchesSearch = transaction.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
                  transaction.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                  transaction.order_id?.toLowerCase().includes(searchTerm.toLowerCase());
                const matchesType = selectedType === 'all' || transaction.type === selectedType;
                const matchesExchange = selectedExchange === 'all' || transaction.exchange === selectedExchange;

                return matchesSearch && matchesType && matchesExchange;
              });
            }, [accountFilteredTransactions, searchTerm, selectedType, selectedExchange]);

            // Enhanced sorting
            const sortedTransactions = useMemo(() => {
              return [...filteredTransactions].sort((a, b) => {
                switch (sortBy) {
                  case 'date': return new Date(b.date + ' ' + b.time).getTime() - new Date(a.date + ' ' + a.time).getTime();
                  case 'symbol': return a.symbol.localeCompare(b.symbol);
                  case 'amount': return b.amount - a.amount;
                  case 'quantity': return b.quantity - a.quantity;
                  default: return 0;
                }
              });
            }, [filteredTransactions, sortBy]);

            // Calculate filtered summary
            const filteredSummary = useMemo(() => {
              if (filteredTransactions.length === 0) return null;

              const buys = filteredTransactions.filter(t => t.type === 'BUY');
              const sells = filteredTransactions.filter(t => t.type === 'SELL');

              return {
                total_transactions: filteredTransactions.length,
                total_value: filteredTransactions.reduce((sum, t) => sum + t.amount, 0),
                total_commission: filteredTransactions.reduce((sum, t) => sum + t.commission, 0),
                buy_count: buys.length,
                sell_count: sells.length,
                net_buy_value: buys.reduce((sum, t) => sum + t.amount, 0),
                net_sell_value: sells.reduce((sum, t) => sum + t.amount, 0),
              };
            }, [filteredTransactions]);

            return (
              <VStack spacing={6} align="stretch">
                {/* Enhanced Filters */}
                <Card bg={bgColor} borderColor={borderColor}>
                  <CardBody>
                    <VStack spacing={4}>
                      <Flex wrap="wrap" gap={4} align="center" width="full">
                        <InputGroup maxW="300px">
                          <InputLeftElement pointerEvents="none">
                            <SearchIcon color="gray.300" />
                          </InputLeftElement>
                          <Input
                            placeholder="Search transactions..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                          />
                        </InputGroup>

                        <Select
                          value={selectedType}
                          onChange={(e) => setSelectedType(e.target.value)}
                          maxW="150px"
                        >
                          <option value="all">All Types</option>
                          <option value="BUY">Buys Only</option>
                          <option value="SELL">Sells Only</option>
                        </Select>

                        <Select
                          value={selectedExchange}
                          onChange={(e) => setSelectedExchange(e.target.value)}
                          maxW="150px"
                        >
                          <option value="all">All Exchanges</option>
                          {uniqueExchanges.map(exchange => (
                            <option key={exchange} value={exchange}>{exchange}</option>
                          ))}
                        </Select>

                        <Select
                          value={dateRange}
                          onChange={(e) => setDateRange(Number(e.target.value))}
                          maxW="150px"
                        >
                          <option value={7}>Last 7 days</option>
                          <option value={30}>Last 30 days</option>
                          <option value={90}>Last 90 days</option>
                          <option value={365}>Last year</option>
                        </Select>

                        <Select
                          value={sortBy}
                          onChange={(e) => setSortBy(e.target.value)}
                          maxW="200px"
                        >
                          <option value="date">Sort by Date</option>
                          <option value="symbol">Sort by Symbol</option>
                          <option value="amount">Sort by Amount</option>
                          <option value="quantity">Sort by Quantity</option>
                        </Select>
                      </Flex>

                      {/* Filter Summary */}
                      <HStack spacing={4} wrap="wrap">
                        <Badge variant="outline" p={2} fontSize="sm">
                          {sortedTransactions.length} of {transactions.length} transactions
                        </Badge>
                        {filteredSummary && (
                          <>
                            <Badge colorScheme="green" variant="outline" p={2} fontSize="sm">
                              ${filteredSummary.net_buy_value.toLocaleString()} buys
                            </Badge>
                            <Badge colorScheme="red" variant="outline" p={2} fontSize="sm">
                              ${filteredSummary.net_sell_value.toLocaleString()} sells
                            </Badge>
                          </>
                        )}
                      </HStack>
                    </VStack>
                  </CardBody>
                </Card>

                {/* Enhanced Transactions Table */}
                <Card bg={bgColor} borderColor={borderColor}>
                  <CardHeader>
                    <HStack justify="space-between">
                      <Heading size="md">Transactions</Heading>
                      <HStack>
                        <Icon as={FiCalendar} />
                        <Text fontSize="sm" color="gray.600">
                          Showing last {dateRange} days
                        </Text>
                      </HStack>
                    </HStack>
                  </CardHeader>
                  <CardBody>
                    <TableContainer>
                      <Table size="sm" variant="simple">
                        <Thead>
                          <Tr>
                            <Th>Date & Time</Th>
                            <Th>Type</Th>
                            <Th>Symbol</Th>
                            <Th isNumeric>Quantity</Th>
                            <Th isNumeric>Price</Th>
                            <Th isNumeric>Gross Amount</Th>
                            <Th isNumeric>Net Amount</Th>
                            <Th>Account</Th>
                          </Tr>
                        </Thead>
                        <Tbody>
                          {sortedTransactions.map((transaction) => (
                            <TransactionRow key={transaction.id} transaction={transaction} />
                          ))}
                        </Tbody>
                      </Table>
                    </TableContainer>

                    {sortedTransactions.length === 0 && (
                      <Box textAlign="center" py={8}>
                        <Alert status="info" justifyContent="center">
                          <AlertIcon />
                          <VStack spacing={2}>
                            <Text color="gray.600" fontWeight="medium">
                              {transactions.length === 0
                                ? "No transaction data available"
                                : "No transactions match your current filters"
                              }
                            </Text>
                            {transactions.length === 0 && (
                              <Text fontSize="sm" color="gray.500">
                                Real IBKR transaction data requires live connection. No sample data provided.
                              </Text>
                            )}
                          </VStack>
                        </Alert>
                      </Box>
                    )}
                  </CardBody>
                </Card>
              </VStack>
            );
          }}
        </AccountFilterWrapper>
      </VStack>
    </Container>
  );
};

export default Transactions; 