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
  InputElement,
  Button,
  Badge,
  StatRoot,
  StatLabel,
  StatHelpText,
  StatValueText,
  StatUpIndicator,
  StatDownIndicator,
  Spinner,
  AlertRoot,
  AlertIndicator,
  SimpleGrid,
  Flex,
  Tooltip,
  Icon,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableScrollArea,
  Progress,
} from '@chakra-ui/react';
import {
  FiDollarSign,
  FiTrendingUp,
  FiTrendingDown,
  FiFilter,
  FiArrowUpRight,
  FiArrowDownLeft,
  FiClock,
  FiCalendar,
  FiDownload,
  FiRefreshCw,
  FiSearch,
} from 'react-icons/fi';
import { portfolioApi, handleApiError, activityApi } from '../services/api';
import AccountFilterWrapper from '../components/ui/AccountFilterWrapper';
import { transformPortfolioToAccounts, AccountData } from '../hooks/useAccountFilter';
import SortableTable, { Column } from '../components/SortableTable';
import { useAccountContext } from '../context/AccountContext';
import toast from 'react-hot-toast';

// Chakra v3 migration shim: prefer dark values until we reintroduce color-mode properly.
const useColorModeValue = <T,>(_light: T, dark: T) => dark;

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

// Unified Activity row -> Transaction projection for UI reuse
const activityToTransaction = (row: any): Transaction => {
  const ts = row.ts ? new Date(row.ts) : new Date();
  const date = ts.toISOString().slice(0, 10);
  const time = ts.toTimeString().slice(0, 8);
  const type = (row.category === 'TRADE' ? (row.side === 'BUY' ? 'BUY' : row.side === 'SELL' ? 'SELL' : undefined) : undefined) as any;
  return {
    id: row.external_id || `${row.src}-${row.symbol}-${row.ts}`,
    date,
    time,
    symbol: row.symbol || '',
    description: row.category,
    type,
    action: row.side || '',
    quantity: Number(row.quantity || 0),
    price: Number(row.price || 0),
    amount: Number(row.amount || row.net_amount || 0),
    commission: Number(row.commission || 0),
    fees: 0,
    net_amount: Number(row.net_amount ?? row.amount ?? 0),
    currency: 'USD',
    exchange: '',
    order_id: undefined,
    execution_id: row.external_id,
    contract_type: '',
    account: String(row.account_id || ''),
    settlement_date: undefined,
    source: row.src || 'activity'
  };
};

// Helper to derive standardized trade type from mixed IBKR fields
const getDerivedType = (t: Partial<Transaction>): 'BUY' | 'SELL' | undefined => {
  const k = `${t.type || ''} ${t.action || ''} ${t.description || ''}`.toUpperCase();
  if (k.includes('BUY') || k.includes('BOT')) return 'BUY';
  if (k.includes('SELL') || k.includes('SLD')) return 'SELL';
  return undefined;
};

// Enhanced Transaction Row Component
const TransactionRow: React.FC<{ transaction: Transaction }> = ({ transaction }) => {
  const derived = getDerivedType(transaction);
  const isBuy = derived === 'BUY';
  const isSell = derived === 'SELL';
  const typeColor = isBuy ? 'green.500' : isSell ? 'red.500' : useColorModeValue('gray.700', 'gray.300');
  const typeBg = useColorModeValue(
    isBuy ? 'green.50' : isSell ? 'red.50' : 'gray.50',
    isBuy ? 'green.900' : isSell ? 'red.900' : 'gray.900'
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
            colorScheme={isBuy ? 'green' : isSell ? 'red' : 'gray'}
            variant="subtle"
            size="sm"
          >
            {derived || transaction.type || '—'}
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
  const { selected, setSelected } = useAccountContext();
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
  const [viewMode, setViewMode] = useState<'table' | 'timeline' | 'calendar'>('table');
  const [calendarMonth, setCalendarMonth] = useState<Date>(new Date());
  const [tableLimit, setTableLimit] = useState<number>(100);
  const [tableOffset, setTableOffset] = useState<number>(0);
  const [hasMore, setHasMore] = useState<boolean>(false);
  const [dailySummary, setDailySummary] = useState<Array<any>>([]);
  const [cursorEnds, setCursorEnds] = useState<string[]>([]);
  const [currentEndISO, setCurrentEndISO] = useState<string | undefined>(undefined);
  const [isYTD, setIsYTD] = useState<boolean>(false);

  // Load persisted UI state
  useEffect(() => {
    try {
      const v = localStorage.getItem('tx.viewMode');
      if (v === 'table' || v === 'timeline' || v === 'calendar') setViewMode(v);
      const y = localStorage.getItem('tx.isYTD');
      if (y !== null) setIsYTD(JSON.parse(y));
      const dr = localStorage.getItem('tx.dateRange');
      if (dr) setDateRange(Number(dr) || 30);
      const ce = localStorage.getItem('tx.cursorEnds');
      if (ce) {
        const arr = JSON.parse(ce);
        if (Array.isArray(arr)) setCursorEnds(arr);
      }
      const end = localStorage.getItem('tx.currentEndISO');
      if (end) setCurrentEndISO(end || undefined);
      const cm = localStorage.getItem('tx.calendarMonthISO');
      if (cm) {
        const d = new Date(cm);
        if (!isNaN(d.getTime())) setCalendarMonth(d);
      }
    } catch { }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist UI state
  useEffect(() => {
    try {
      localStorage.setItem('tx.viewMode', viewMode);
      localStorage.setItem('tx.isYTD', JSON.stringify(isYTD));
      localStorage.setItem('tx.dateRange', String(dateRange));
      localStorage.setItem('tx.cursorEnds', JSON.stringify(cursorEnds));
      localStorage.setItem('tx.currentEndISO', currentEndISO || '');
      localStorage.setItem('tx.calendarMonthISO', calendarMonth.toISOString());
    } catch { }
  }, [viewMode, isYTD, dateRange, cursorEnds, currentEndISO, calendarMonth]);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const [selectedAccountSSR, setSelectedAccountSSR] = useState<string | undefined>(undefined);

  useEffect(() => {
    fetchData(selectedAccountSSR, 0, currentEndISO);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange, currentEndISO]);

  const fetchData = async (accountId?: string, offset: number = 0, endISO?: string) => {
    setLoading(true);
    setError(null);
    try {
      // Fetch portfolio data for account selector
      const portfolioResult = await portfolioApi.getLive(accountId);
      setPortfolioData(portfolioResult.data);

      // Fetch unified activity for range
      const end = endISO ? new Date(endISO) : new Date();
      const start = new Date();
      if (isYTD) {
        start.setMonth(0, 1);
        start.setHours(0, 0, 0, 0);
      } else {
        start.setDate(end.getDate() - dateRange);
      }
      const res: any = await activityApi.getActivity({
        accountId,
        start: start.toISOString().slice(0, 10),
        end: end.toISOString().slice(0, 10),
        limit: tableLimit,
        offset,
      });
      const rows = res?.data?.data?.activity || res?.data?.activity || [];
      // Map backend account_id -> account_number for client filtering
      const idToNum = new Map<string | number, string>();
      (ctxAccounts || []).forEach((a: any) => {
        if (a?.id != null && a?.account_number) idToNum.set(a.id, a.account_number);
      });
      const txs: Transaction[] = rows.map((row: any) => {
        const t = activityToTransaction(row);
        const num = idToNum.get(row.account_id) || String(row.account_id || '');
        return { ...t, account: num, account_id: num as any };
      });
      setTransactions(txs);
      setHasMore(rows.length === tableLimit);
      // Track last ts for cursor
      const lastTs: string | undefined = rows.length ? rows[rows.length - 1]?.ts : undefined;
      if (lastTs) {
        // store as state for next-page calculation
        // do not update currentEndISO here; next page action will set it
      }
      // Compute lightweight summary on client
      const buys = txs.filter(t => getDerivedType(t) === 'BUY');
      const sells = txs.filter(t => getDerivedType(t) === 'SELL');
      const total_value = txs.reduce((s, t) => s + Math.abs(Number(t.amount || 0)), 0);
      const total_commission = txs.reduce((s, t) => s + Math.abs(Number(t.commission || 0)), 0);
      const total_fees = txs.reduce((s, t) => s + Math.abs(Number(t.fees || 0)), 0);
      setSummary({
        total_transactions: txs.length,
        total_value,
        total_commission,
        total_fees,
        buy_count: buys.length,
        sell_count: sells.length,
        date_range: dateRange,
        net_buy_value: buys.reduce((s, t) => s + Math.abs(Number(t.amount || 0)), 0),
        net_sell_value: sells.reduce((s, t) => s + Math.abs(Number(t.amount || 0)), 0),
        avg_transaction_size: txs.length ? total_value / txs.length : 0,
      });
    } catch (err) {
      console.error('Error fetching transaction data:', err);
      setError(handleApiError(err));
      toast.error('Failed to load transaction data');
    } finally {
      setLoading(false);
    }
  };

  // Prefer global AccountContext accounts (authoritative ids and numbers)
  const { accounts: ctxAccounts } = useAccountContext();
  const accounts: AccountData[] = useMemo(() => {
    if (ctxAccounts && ctxAccounts.length) {
      return ctxAccounts.map((a: any) => ({
        account_id: a.account_number,
        account_name: a.account_name || a.account_number,
        account_type: a.account_type || 'taxable',
        broker: a.broker || 'IBKR',
        total_value: 0,
        unrealized_pnl: 0,
        unrealized_pnl_pct: 0,
        positions_count: 0,
        allocation_pct: 0,
      }));
    }
    return portfolioData ? transformPortfolioToAccounts(portfolioData) : [];
  }, [ctxAccounts, portfolioData]);

  // Get unique exchanges for filter (from all transactions for dropdown)
  const uniqueExchanges = [...new Set(transactions.map(t => t.exchange))];

  // Keep page in sync with global AccountContext when user changes header selector
  useEffect(() => {
    // translate global selection to server param (undefined for all/taxable/ira)
    const accParam = selected === 'all' || selected === 'taxable' || selected === 'ira' ? undefined : selected;
    setSelectedAccountSSR(accParam);
    setTableOffset(0);
    setCursorEnds([]);
    setCurrentEndISO(undefined);
    fetchData(accParam, 0, undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  // Load calendar daily summary for current month
  useEffect(() => {
    const loadDaily = async () => {
      try {
        const accParam = selectedAccountSSR;
        const first = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth(), 1);
        const last = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 0);
        const res: any = await activityApi.getDailySummary({
          accountId: accParam,
          start: first.toISOString().slice(0, 10),
          end: last.toISOString().slice(0, 10),
        });
        const rows = res?.data?.data?.daily || res?.data?.daily || [];
        setDailySummary(rows);
      } catch (e) {
        setDailySummary([]);
      }
    };
    loadDaily();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAccountSSR, calendarMonth]);

  const onNextPage = async () => {
    if (!hasMore) return;
    // Determine last ts from current transactions
    const last = transactions[transactions.length - 1];
    if (!last) return;
    const lastISO = new Date(`${last.date}T${last.time}Z`).toISOString();
    const newStack = [...cursorEnds, currentEndISO || new Date().toISOString()];
    setCursorEnds(newStack);
    // set end to just before last item to avoid duplication
    const newEnd = new Date(new Date(lastISO).getTime() - 1000).toISOString();
    setCurrentEndISO(newEnd);
    setTableOffset(0);
    await fetchData(selectedAccountSSR, 0, newEnd);
  };
  const onPrevPage = async () => {
    if (cursorEnds.length === 0) return;
    const prevStack = [...cursorEnds];
    const prevEnd = prevStack.pop();
    setCursorEnds(prevStack);
    setCurrentEndISO(prevStack.length ? prevStack[prevStack.length - 1] : undefined);
    setTableOffset(0);
    await fetchData(selectedAccountSSR, 0, prevEnd);
  };

  // Money In / Out classification
  const classifyMoneyFlow = (t: Transaction) => {
    const k = (t.type || t.action || t.description || '').toUpperCase();
    if (k.includes('DIV')) return { in: Math.abs(t.amount || 0), out: 0 };
    if (k.includes('SELL') || k.includes('SLD')) return { in: Math.abs(t.amount || 0), out: 0 };
    if (k.includes('BUY')) return { in: 0, out: Math.abs(t.amount || 0) };
    if (k.includes('FEE') || k.includes('COMMISSION') || k.includes('INTEREST CHARGED')) return { in: 0, out: Math.abs(t.amount || 0) };
    if (k.includes('INTEREST') && (t.amount || 0) > 0) return { in: Math.abs(t.amount || 0), out: 0 };
    return { in: 0, out: 0 };
  };
  const moneyTotals = useMemo(() => {
    const totals = transactions.reduce((acc, t) => {
      const { in: mi, out: mo } = classifyMoneyFlow(t);
      acc.in += mi;
      acc.out += mo;
      return acc;
    }, { in: 0, out: 0 });
    return totals;
  }, [transactions]);

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
        <AlertRoot status="error">
          <AlertIndicator />
          {error}
          <Button ml={4} onClick={() => fetchData(selectedAccountSSR, tableOffset)} size="sm">
            Retry
          </Button>
        </AlertRoot>
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
              <Button leftIcon={<FiRefreshCw />} size="sm" variant="outline" onClick={() => fetchData(selectedAccountSSR, tableOffset)}>
                Refresh
              </Button>
              <Button leftIcon={<FiDownload />} size="sm" variant="outline">
                Export CSV
              </Button>
              <HStack spacing={1}>
                <Button size="sm" variant={viewMode === 'table' ? 'solid' : 'outline'} onClick={() => setViewMode('table')}>Table</Button>
                <Button size="sm" variant={viewMode === 'timeline' ? 'solid' : 'outline'} onClick={() => setViewMode('timeline')}>Timeline</Button>
                <Button size="sm" variant={viewMode === 'calendar' ? 'solid' : 'outline'} onClick={() => setViewMode('calendar')}>Calendar</Button>
              </HStack>
            </HStack>
          </HStack>
        </Box>

        {/* Enhanced Summary Cards */}
        {summary && (
          <SimpleGrid columns={{ base: 2, md: 5 }} spacing={4}>
            <StatRoot>
              <StatLabel>Total Transactions</StatLabel>
              <StatValueText>{summary.total_transactions}</StatValueText>
              <StatHelpText>
                {summary.buy_count} buys • {summary.sell_count} sells
              </StatHelpText>
            </StatRoot>
            <StatRoot>
              <StatLabel>Total Volume</StatLabel>
              <StatValueText>${summary.total_value.toLocaleString()}</StatValueText>
              <StatHelpText>Trade volume</StatHelpText>
            </StatRoot>
            <StatRoot>
              <StatLabel>Net Buys</StatLabel>
              <StatValueText color="green.500">
                ${summary.net_buy_value.toLocaleString()}
              </StatValueText>
              <StatHelpText>
                <StatUpIndicator />
                Purchases
              </StatHelpText>
            </StatRoot>
            <StatRoot>
              <StatLabel>Net Sells</StatLabel>
              <StatValueText color="red.500">
                ${summary.net_sell_value.toLocaleString()}
              </StatValueText>
              <StatHelpText>
                <StatDownIndicator />
                Sales
              </StatHelpText>
            </StatRoot>
            <StatRoot>
              <StatLabel>Total Fees</StatLabel>
              <StatValueText>${(summary.total_commission + summary.total_fees).toFixed(2)}</StatValueText>
              <StatHelpText>Commission + fees</StatHelpText>
            </StatRoot>
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
            // Sync to global
            if (account && account !== selected) {
              setSelected(account);
            } else {
              fetchData(accParam);
            }
          }}
        >
          {(accountFilteredTransactions, filterState) => {
            // Enhanced filtering based on account-filtered transactions
            const filteredTransactions = useMemo(() => {
              return accountFilteredTransactions.filter(transaction => {
                const matchesSearch = transaction.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
                  transaction.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                  transaction.order_id?.toLowerCase().includes(searchTerm.toLowerCase());
                const derived = getDerivedType(transaction as any);
                const matchesType = selectedType === 'all' || derived === selectedType;
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

            const moneyFlowFiltered = useMemo(() => {
              return filteredTransactions.reduce((acc, t) => {
                const { in: mi, out: mo } = classifyMoneyFlow(t as any);
                acc.in += mi; acc.out += mo;
                return acc;
              }, { in: 0, out: 0 });
            }, [filteredTransactions]);

            return (
              <VStack spacing={6} align="stretch">
                {/* Enhanced Filters */}
                <Card bg={bgColor} borderColor={borderColor}>
                  <CardBody>
                    <VStack spacing={4}>
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
                            placeholder="Search transactions..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                          />
                        </InputGroup>

                        {/* Quick presets */}
                        <HStack>
                          <Button size="sm" variant={!isYTD && dateRange === 7 ? 'solid' : 'outline'} onClick={() => { setIsYTD(false); setDateRange(7); setCursorEnds([]); setCurrentEndISO(undefined); }}>7d</Button>
                          <Button size="sm" variant={!isYTD && dateRange === 30 ? 'solid' : 'outline'} onClick={() => { setIsYTD(false); setDateRange(30); setCursorEnds([]); setCurrentEndISO(undefined); }}>30d</Button>
                          <Button size="sm" variant={!isYTD && dateRange === 90 ? 'solid' : 'outline'} onClick={() => { setIsYTD(false); setDateRange(90); setCursorEnds([]); setCurrentEndISO(undefined); }}>90d</Button>
                          <Button size="sm" variant={isYTD ? 'solid' : 'outline'} onClick={() => { setIsYTD(true); setCursorEnds([]); setCurrentEndISO(undefined); }}>YTD</Button>
                        </HStack>

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
                          value={isYTD ? 'ytd' : String(dateRange)}
                          onChange={(e) => {
                            const val = e.target.value;
                            if (val === 'ytd') {
                              setIsYTD(true);
                            } else {
                              setIsYTD(false);
                              setDateRange(Number(val));
                            }
                            setCursorEnds([]);
                            setCurrentEndISO(undefined);
                          }}
                          maxW="150px"
                        >
                          <option value={7}>Last 7 days</option>
                          <option value={30}>Last 30 days</option>
                          <option value={90}>Last 90 days</option>
                          <option value={365}>Last year</option>
                          <option value="ytd">YTD</option>
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
                        <Badge colorScheme="purple" variant="subtle" p={2} fontSize="sm">
                          Money In: ${moneyFlowFiltered.in.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </Badge>
                        <Badge colorScheme="orange" variant="subtle" p={2} fontSize="sm">
                          Money Out: ${moneyFlowFiltered.out.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </Badge>
                      </HStack>
                    </VStack>
                  </CardBody>
                </Card>

                {/* View Container */}
                {viewMode === 'table' && (
                  <Card bg={bgColor} borderColor={borderColor}>
                    <CardHeader>
                      <HStack justify="space-between">
                        <Heading size="md">Transactions</Heading>
                        <HStack>
                          <Icon as={FiCalendar} />
                          <Text fontSize="sm" color="gray.600">
                            {isYTD ? 'Showing YTD' : `Showing last ${dateRange} days`}
                          </Text>
                          <HStack spacing={2} ml={4}>
                            <Button size="xs" onClick={onPrevPage} isDisabled={tableOffset === 0}>Prev</Button>
                            <Text fontSize="xs" color="gray.500">Page {Math.floor(tableOffset / tableLimit) + 1}</Text>
                            <Button size="xs" onClick={onNextPage} isDisabled={!hasMore}>Next</Button>
                          </HStack>
                        </HStack>
                      </HStack>
                    </CardHeader>
                    <CardBody>
                      <TableScrollArea>
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
                      </TableScrollArea>

                      {sortedTransactions.length === 0 && (
                        <Box textAlign="center" py={8}>
                          <AlertRoot status="info" justifyContent="center">
                            <AlertIndicator />
                            <VStack spacing={2}>
                              <Text color="gray.600" fontWeight="medium">
                                {transactions.length === 0
                                  ? "No transaction data available"
                                  : "No transactions match your current filters"
                                }
                              </Text>
                            </VStack>
                          </AlertRoot>
                        </Box>
                      )}
                    </CardBody>
                  </Card>
                )}

                {viewMode === 'timeline' && (
                  <Card bg={bgColor} borderColor={borderColor}>
                    <CardHeader>
                      <Heading size="md">Timeline</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack align="stretch" spacing={4}>
                        {Object.entries(
                          sortedTransactions.reduce((acc: Record<string, Transaction[]>, t: any) => {
                            const d = t.date;
                            (acc[d] = acc[d] || []).push(t);
                            return acc;
                          }, {})
                        ).sort((a, b) => new Date(b[0]).getTime() - new Date(a[0]).getTime())
                          .map(([day, items]) => (
                            <Box key={day}>
                              <HStack justify="space-between" mb={2}>
                                <Badge variant="subtle">{new Date(day).toLocaleDateString()}</Badge>
                                <HStack spacing={2}>
                                  <Badge colorScheme="blue" variant="outline">{items.length} trades</Badge>
                                  {(() => {
                                    const agg = items.reduce((acc, t: any) => {
                                      const isBuy = (t.type || t.action || '').toUpperCase().includes('BUY');
                                      const isSell = (t.type || t.action || '').toUpperCase().includes('SELL') || (t.type || '').toUpperCase().includes('SLD');
                                      if (isBuy) { acc.buyCount++; acc.buyQty += Number(t.quantity || 0); }
                                      if (isSell) { acc.sellCount++; acc.sellQty += Number(t.quantity || 0); }
                                      const { in: mi, out: mo } = classifyMoneyFlow(t);
                                      acc.in += mi; acc.out += mo;
                                      return acc;
                                    }, { buyCount: 0, sellCount: 0, buyQty: 0, sellQty: 0, in: 0, out: 0 });
                                    return (
                                      <>
                                        <Badge colorScheme="green" variant="subtle">Buys {agg.buyCount} • {agg.buyQty.toLocaleString()}</Badge>
                                        <Badge colorScheme="red" variant="subtle">Sells {agg.sellCount} • {agg.sellQty.toLocaleString()}</Badge>
                                        <Badge colorScheme="purple" variant="subtle">In ${agg.in.toFixed(0)}</Badge>
                                        <Badge colorScheme="orange" variant="subtle">Out ${agg.out.toFixed(0)}</Badge>
                                      </>
                                    );
                                  })()}
                                </HStack>
                              </HStack>
                              <Table size="sm" variant="simple">
                                <Thead>
                                  <Tr>
                                    <Th>Time</Th>
                                    <Th>Type</Th>
                                    <Th>Symbol</Th>
                                    <Th isNumeric>Qty</Th>
                                    <Th isNumeric>Price</Th>
                                    <Th isNumeric>Amount</Th>
                                  </Tr>
                                </Thead>
                                <Tbody>
                                  {items.map((t) => (
                                    <Tr key={t.id}>
                                      <Td>{t.time}</Td>
                                      <Td>{getDerivedType(t as any) || t.type || '—'}</Td>
                                      <Td>{t.symbol}</Td>
                                      <Td isNumeric>{t.quantity?.toLocaleString()}</Td>
                                      <Td isNumeric>${t.price?.toFixed(2)}</Td>
                                      <Td isNumeric>${Math.abs(t.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</Td>
                                    </Tr>
                                  ))}
                                </Tbody>
                              </Table>
                            </Box>
                          ))}
                      </VStack>
                    </CardBody>
                  </Card>
                )}

                {viewMode === 'calendar' && (
                  <Card bg={bgColor} borderColor={borderColor}>
                    <CardHeader>
                      <HStack justify="space-between">
                        <Heading size="md">Calendar</Heading>
                        <HStack>
                          <Button size="sm" variant="outline" onClick={() => setCalendarMonth(new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() - 1, 1))}>Prev</Button>
                          <Text>
                            {calendarMonth.toLocaleString('default', { month: 'long' })} {calendarMonth.getFullYear()}
                          </Text>
                          <Button size="sm" variant="outline" onClick={() => setCalendarMonth(new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 1))}>Next</Button>
                        </HStack>
                      </HStack>
                    </CardHeader>
                    <CardBody>
                      {(() => {
                        const bg = useColorModeValue('white', 'gray.800');
                        const b = borderColor;
                        const firstDay = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth(), 1);
                        const startOffset = firstDay.getDay();
                        const daysInMonth = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 0).getDate();
                        const cells: JSX.Element[] = [];
                        const dailyMap = new Map<number, any>();
                        for (const r of dailySummary) {
                          const dt = new Date(r.day);
                          if (dt.getMonth() === calendarMonth.getMonth() && dt.getFullYear() === calendarMonth.getFullYear()) {
                            dailyMap.set(dt.getDate(), r);
                          }
                        }
                        for (let i = 0; i < startOffset; i++) {
                          cells.push(<Box key={`empty-${i}`} h="100px" />);
                        }
                        for (let day = 1; day <= daysInMonth; day++) {
                          const r = dailyMap.get(day);
                          const tradeCount = r?.trade_count || 0;
                          const buyCount = r?.buy_count || 0;
                          const sellCount = r?.sell_count || 0;
                          const buyQty = r?.buy_qty || 0;
                          const sellQty = r?.sell_qty || 0;
                          const moneyIn = r?.money_in || 0;
                          const moneyOut = r?.money_out || 0;
                          cells.push(
                            <Box key={day} h="100px" border="1px solid" borderColor={b} bg={bg} p={2}>
                              <HStack justify="space-between">
                                <Text fontWeight="semibold" fontSize="sm">{day}</Text>
                                <Badge variant="outline" colorScheme="blue">{tradeCount}</Badge>
                              </HStack>
                              <VStack align="start" spacing={1} mt={2}>
                                {buyCount > 0 && <Text fontSize="xs" color="green.400">Buys {buyCount} • {Number(buyQty).toLocaleString()}</Text>}
                                {sellCount > 0 && <Text fontSize="xs" color="red.400">Sells {sellCount} • {Number(sellQty).toLocaleString()}</Text>}
                                {moneyIn > 0 && <Text fontSize="xs" color="purple.400">In ${Number(moneyIn).toFixed(0)}</Text>}
                                {moneyOut > 0 && <Text fontSize="xs" color="orange.400">Out ${Number(moneyOut).toFixed(0)}</Text>}
                              </VStack>
                            </Box>
                          );
                        }
                        return (
                          <SimpleGrid columns={7} spacing={0}>
                            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => (
                              <Box key={d} p={2} textAlign="center" fontWeight="bold" borderBottom="1px" borderColor={b}>{d}</Box>
                            ))}
                            {cells}
                          </SimpleGrid>
                        );
                      })()}
                      <HStack mt={3} spacing={3} color="gray.500">
                        <HStack><Box w="10px" h="10px" bg="green.400" borderRadius="sm" /> <Text fontSize="xs">Buys (count • qty)</Text></HStack>
                        <HStack><Box w="10px" h="10px" bg="red.400" borderRadius="sm" /> <Text fontSize="xs">Sells (count • qty)</Text></HStack>
                        <HStack><Box w="10px" h="10px" bg="purple.400" borderRadius="sm" /> <Text fontSize="xs">Money In</Text></HStack>
                        <HStack><Box w="10px" h="10px" bg="orange.400" borderRadius="sm" /> <Text fontSize="xs">Money Out</Text></HStack>
                      </HStack>
                    </CardBody>
                  </Card>
                )}
              </VStack>
            );
          }}
        </AccountFilterWrapper>
      </VStack>
    </Container>
  );
};

export default Transactions; 