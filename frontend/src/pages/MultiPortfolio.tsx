import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Badge,
  SimpleGrid,
  Select,
  Input,
  InputGroup,
  InputLeftElement,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Progress,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  IconButton,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  Flex,
  Divider,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Alert,
  AlertIcon,
  AlertDescription,
  useToast,
  Tooltip,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Switch,
  FormControl,
  FormLabel,
} from '@chakra-ui/react';
import {
  FaSearch,
  FaSync,
  FaFilter,
  FaEye,
  FaSort,
  FaSortUp,
  FaSortDown,
  FaExchangeAlt,
  FaChartLine,
  FaDollarSign,
  FaCalendarAlt,
  FaTrendingUp,
  FaTrendingDown,
  FaCog,
  FaDownload,
  FaPlus,
  FaMinus
} from 'react-icons/fa';

interface Holding {
  id: string;
  symbol: string;
  name: string;
  brokerage: 'ibkr' | 'tastytrade';
  type: 'stock' | 'option' | 'etf' | 'crypto';
  quantity: number;
  currentPrice: number;
  costBasis: number;
  marketValue: number;
  unrealizedPnL: number;
  unrealizedPnLPct: number;
  dayChange: number;
  dayChangePct: number;
  sector: string;
  category?: string;

  // Options specific
  strikePrice?: number;
  expirationDate?: string;
  optionType?: 'call' | 'put';
  delta?: number;
  gamma?: number;
  theta?: number;
  vega?: number;
  impliedVolatility?: number;

  // Additional data
  dividendYield?: number;
  peRatio?: number;
  marketCap?: number;
  lastUpdated: string;
}

interface PortfolioSummary {
  totalValue: number;
  totalCost: number;
  totalPnL: number;
  totalPnLPct: number;
  totalDayChange: number;
  totalDayChangePct: number;
  cashBalance: number;
  marginUsed: number;
  buyingPower: number;
  totalPositions: number;
}

const MultiPortfolio: React.FC = () => {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [filteredHoldings, setFilteredHoldings] = useState<Holding[]>([]);
  const [ibkrSummary, setIbkrSummary] = useState<PortfolioSummary | null>(null);
  const [tastytradeSummary, setTastytradeSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedBrokerage, setSelectedBrokerage] = useState<'all' | 'ibkr' | 'tastytrade'>('all');
  const [selectedType, setSelectedType] = useState<'all' | 'stock' | 'option' | 'etf' | 'crypto'>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'symbol' | 'value' | 'pnl' | 'pnlPct'>('value');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [showOnlyProfitable, setShowOnlyProfitable] = useState(false);
  const [showOnlyOptions, setShowOnlyOptions] = useState(false);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedHolding, setSelectedHolding] = useState<Holding | null>(null);
  const toast = useToast();

  useEffect(() => {
    fetchPortfolioData();
  }, []);

  useEffect(() => {
    filterAndSortHoldings();
  }, [holdings, searchTerm, selectedBrokerage, selectedType, selectedCategory, sortBy, sortDirection, showOnlyProfitable, showOnlyOptions]);

  const fetchPortfolioData = async () => {
    setLoading(true);
    try {
      // Fetch IBKR data
      const ibkrResponse = await fetch('/api/v1/portfolio/live');
      if (ibkrResponse.ok) {
        const ibkrData = await ibkrResponse.json();

        if (ibkrData.status === 'success' && ibkrData.data.accounts) {
          const ibkrHoldings: Holding[] = [];
          let totalIbkrValue = 0;
          let totalIbkrPnL = 0;

          Object.entries(ibkrData.data.accounts).forEach(([accountId, accountData]: [string, any]) => {
            if ('error' in accountData) {
              console.warn(`IBKR Account ${accountId} has error:`, accountData.error);
              return;
            }

            const positions = accountData.all_positions || [];
            const accountSummary = accountData.account_summary || {};

            totalIbkrValue += accountSummary.net_liquidation || 0;

            positions.forEach((pos: any) => {
              if (pos.position && pos.position !== 0) {
                const holding: Holding = {
                  id: `ibkr-${pos.symbol}-${accountId}`,
                  symbol: pos.symbol,
                  name: pos.symbol, // Would need company name lookup
                  brokerage: 'ibkr',
                  type: 'stock', // Simplifying for now
                  quantity: Math.abs(pos.position),
                  currentPrice: pos.market_price || 0,
                  costBasis: pos.avg_cost || 0,
                  marketValue: pos.position_value || 0,
                  unrealizedPnL: pos.unrealized_pnl || 0,
                  unrealizedPnLPct: pos.unrealized_pnl_pct || 0,
                  dayChange: 0, // Would need daily change data
                  dayChangePct: 0,
                  sector: pos.sector || 'Unknown',
                  lastUpdated: new Date().toISOString()
                };
                ibkrHoldings.push(holding);
                totalIbkrPnL += pos.unrealized_pnl || 0;
              }
            });
          });

          const ibkrSummary: PortfolioSummary = {
            totalValue: totalIbkrValue,
            totalCost: totalIbkrValue - totalIbkrPnL,
            totalPnL: totalIbkrPnL,
            totalPnLPct: totalIbkrValue > 0 ? (totalIbkrPnL / (totalIbkrValue - totalIbkrPnL)) * 100 : 0,
            totalDayChange: 0, // Would need daily change calculation
            totalDayChangePct: 0,
            cashBalance: 0, // Extract from account summary if needed
            marginUsed: 0,
            buyingPower: 0,
            totalPositions: ibkrHoldings.length
          };

          setIbkrSummary(ibkrSummary);
          setHoldings(prev => [...prev.filter(h => h.brokerage !== 'ibkr'), ...ibkrHoldings]);
        } else {
          console.warn('IBKR data fetch failed:', ibkrData.error || 'Unknown error');
        }
      }

      // Fetch Tastytrade data
      try {
        const tastytradeResponse = await fetch('/api/v1/options/accounts');
        if (tastytradeResponse.ok) {
          const tastytradeData = await tastytradeResponse.json();

          if (tastytradeData.status === 'success' && tastytradeData.data) {
            // Process real Tastytrade account data
            const tastytradeHoldings: Holding[] = [];
            let totalTastyValue = 0;
            let totalTastyPnL = 0;

            // If we have real position data, process it
            if (tastytradeData.data.positions) {
              tastytradeData.data.positions.forEach((position: any) => {
                const holding: Holding = {
                  id: `tastytrade-${position.symbol}`,
                  symbol: position.symbol,
                  name: position.instrument?.underlying_symbol ?
                    `${position.instrument.underlying_symbol} ${position.instrument.expiration_date} $${position.instrument.strike_price} ${position.instrument.option_type}` :
                    position.symbol,
                  brokerage: 'tastytrade',
                  type: position.instrument?.instrument_type === 'Equity Option' ? 'option' : 'stock',
                  quantity: Math.abs(position.quantity || 0),
                  currentPrice: position.mark_price || 0,
                  costBasis: position.average_open_price || 0,
                  marketValue: position.mark || 0,
                  unrealizedPnL: position.day_gain_loss || 0,
                  unrealizedPnLPct: position.mark && position.average_open_price ?
                    ((position.mark - position.average_open_price) / position.average_open_price) * 100 : 0,
                  dayChange: position.day_gain_loss || 0,
                  dayChangePct: position.day_gain_loss_percentage || 0,
                  sector: 'Options', // Default for options
                  // Options specific data
                  strikePrice: position.instrument?.strike_price,
                  expirationDate: position.instrument?.expiration_date,
                  optionType: position.instrument?.option_type?.toLowerCase() as 'call' | 'put',
                  delta: position.delta,
                  gamma: position.gamma,
                  theta: position.theta,
                  vega: position.vega,
                  impliedVolatility: position.implied_volatility,
                  lastUpdated: new Date().toISOString()
                };
                tastytradeHoldings.push(holding);
                totalTastyValue += position.mark || 0;
                totalTastyPnL += position.day_gain_loss || 0;
              });
            }

            const tastytradeSummary: PortfolioSummary = {
              totalValue: totalTastyValue,
              totalCost: totalTastyValue - totalTastyPnL,
              totalPnL: totalTastyPnL,
              totalPnLPct: totalTastyValue > 0 ? (totalTastyPnL / (totalTastyValue - totalTastyPnL)) * 100 : 0,
              totalDayChange: totalTastyPnL,
              totalDayChangePct: 0,
              cashBalance: tastytradeData.data.cash_balance || 0,
              marginUsed: tastytradeData.data.margin_used || 0,
              buyingPower: tastytradeData.data.buying_power || 0,
              totalPositions: tastytradeHoldings.length
            };

            setTastytradeSummary(tastytradeSummary);
            setHoldings(prev => [...prev.filter(h => h.brokerage !== 'tastytrade'), ...tastytradeHoldings]);
          } else {
            console.warn('Tastytrade data not available or connection error');
            // Set empty tastytrade summary if no data available
            setTastytradeSummary({
              totalValue: 0,
              totalCost: 0,
              totalPnL: 0,
              totalPnLPct: 0,
              totalDayChange: 0,
              totalDayChangePct: 0,
              cashBalance: 0,
              marginUsed: 0,
              buyingPower: 0,
              totalPositions: 0
            });
          }
        }
      } catch (tastyError) {
        console.warn('Tastytrade API not available:', tastyError);
        // Set empty tastytrade summary if API fails
        setTastytradeSummary({
          totalValue: 0,
          totalCost: 0,
          totalPnL: 0,
          totalPnLPct: 0,
          totalDayChange: 0,
          totalDayChangePct: 0,
          cashBalance: 0,
          marginUsed: 0,
          buyingPower: 0,
          totalPositions: 0
        });
      }

    } catch (error) {
      console.error('Error fetching portfolio data:', error);
      toast({
        title: "Error",
        description: "Failed to fetch portfolio data",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const syncData = async () => {
    setSyncing(true);
    try {
      // Sync IBKR data first
      const ibkrSyncResponse = await fetch('/api/v1/portfolio/sync', {
        method: 'POST'
      });

      if (ibkrSyncResponse.ok) {
        toast({
          title: "IBKR Sync Complete",
          description: "IBKR portfolio data has been synced",
          status: "success",
          duration: 2000,
          isClosable: true,
        });
      }

      // Fetch updated data
      await fetchPortfolioData();

      toast({
        title: "Portfolio Updated",
        description: "All portfolio data has been refreshed",
        status: "success",
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: "Sync Failed",
        description: "Failed to sync portfolio data",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setSyncing(false);
    }
  };

  const filterAndSortHoldings = () => {
    let filtered = holdings.filter(holding => {
      const matchesSearch = holding.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
        holding.name.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesBrokerage = selectedBrokerage === 'all' || holding.brokerage === selectedBrokerage;
      const matchesType = selectedType === 'all' || holding.type === selectedType;
      const matchesCategory = selectedCategory === 'all' || holding.category === selectedCategory;
      const matchesProfitable = !showOnlyProfitable || holding.unrealizedPnL > 0;
      const matchesOptions = !showOnlyOptions || holding.type === 'option';

      return matchesSearch && matchesBrokerage && matchesType && matchesCategory && matchesProfitable && matchesOptions;
    });

    // Sort
    filtered.sort((a, b) => {
      let aValue: number;
      let bValue: number;

      switch (sortBy) {
        case 'symbol':
          return sortDirection === 'asc' ? a.symbol.localeCompare(b.symbol) : b.symbol.localeCompare(a.symbol);
        case 'value':
          aValue = Math.abs(a.marketValue);
          bValue = Math.abs(b.marketValue);
          break;
        case 'pnl':
          aValue = a.unrealizedPnL;
          bValue = b.unrealizedPnL;
          break;
        case 'pnlPct':
          aValue = a.unrealizedPnLPct;
          bValue = b.unrealizedPnLPct;
          break;
        default:
          return 0;
      }

      return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
    });

    setFilteredHoldings(filtered);
  };

  const handleSort = (field: typeof sortBy) => {
    if (sortBy === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortDirection('desc');
    }
  };

  const getSortIcon = (field: typeof sortBy) => {
    if (sortBy !== field) return <FaSort />;
    return sortDirection === 'asc' ? <FaSortUp /> : <FaSortDown />;
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getChangeColor = (value: number) => {
    return value >= 0 ? 'green.500' : 'red.500';
  };

  const totalPortfolioValue = (ibkrSummary?.totalValue || 0) + (tastytradeSummary?.totalValue || 0);
  const totalPortfolioPnL = (ibkrSummary?.totalPnL || 0) + (tastytradeSummary?.totalPnL || 0);
  const totalPortfolioPnLPct = totalPortfolioValue > 0 ? (totalPortfolioPnL / (totalPortfolioValue - totalPortfolioPnL)) * 100 : 0;

  const viewHoldingDetails = (holding: Holding) => {
    setSelectedHolding(holding);
    onOpen();
  };

  return (
    <Box p={6}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Flex justify="space-between" align="center">
          <Box>
            <Heading size="lg" mb={2}>Multi-Brokerage Portfolio</Heading>
            <Text color="gray.600">
              Unified view of your IBKR and Tastytrade holdings
            </Text>
          </Box>
          <HStack spacing={3}>
            <Button
              leftIcon={<FaSync />}
              onClick={syncData}
              isLoading={syncing}
              loadingText="Syncing"
              colorScheme="blue"
              size="sm"
            >
              Sync Data
            </Button>
            <Button leftIcon={<FaDownload />} size="sm" variant="outline">
              Export
            </Button>
          </HStack>
        </Flex>

        {/* Portfolio Summary */}
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={6}>
          <Stat>
            <StatLabel>Total Portfolio Value</StatLabel>
            <StatNumber fontSize="2xl">{formatCurrency(totalPortfolioValue)}</StatNumber>
            <StatHelpText>
              <StatArrow type={totalPortfolioPnL >= 0 ? 'increase' : 'decrease'} />
              {formatPercent(totalPortfolioPnLPct)}
            </StatHelpText>
          </Stat>
          <Stat>
            <StatLabel>Total P&L</StatLabel>
            <StatNumber fontSize="2xl" color={getChangeColor(totalPortfolioPnL)}>
              {formatCurrency(totalPortfolioPnL)}
            </StatNumber>
            <StatHelpText>Unrealized</StatHelpText>
          </Stat>
          <Stat>
            <StatLabel>Total Positions</StatLabel>
            <StatNumber fontSize="2xl">{filteredHoldings.length}</StatNumber>
            <StatHelpText>Across {selectedBrokerage === 'all' ? 'both brokerages' : selectedBrokerage.toUpperCase()}</StatHelpText>
          </Stat>
          <Stat>
            <StatLabel>Day Change</StatLabel>
            <StatNumber fontSize="2xl" color={getChangeColor((ibkrSummary?.totalDayChange || 0) + (tastytradeSummary?.totalDayChange || 0))}>
              {formatCurrency((ibkrSummary?.totalDayChange || 0) + (tastytradeSummary?.totalDayChange || 0))}
            </StatNumber>
            <StatHelpText>
              {formatPercent(((ibkrSummary?.totalDayChangePct || 0) + (tastytradeSummary?.totalDayChangePct || 0)) / 2)}
            </StatHelpText>
          </Stat>
        </SimpleGrid>

        {/* Brokerage Breakdown */}
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
          {/* IBKR Card */}
          <Card>
            <CardHeader>
              <HStack justify="space-between">
                <Heading size="md">Interactive Brokers</Heading>
                <Badge colorScheme="blue">IBKR</Badge>
              </HStack>
            </CardHeader>
            <CardBody>
              <SimpleGrid columns={2} spacing={4}>
                <Box>
                  <Text fontSize="sm" color="gray.500">Total Value</Text>
                  <Text fontWeight="bold" fontSize="lg">{formatCurrency(ibkrSummary?.totalValue || 0)}</Text>
                </Box>
                <Box>
                  <Text fontSize="sm" color="gray.500">P&L</Text>
                  <Text fontWeight="bold" fontSize="lg" color={getChangeColor(ibkrSummary?.totalPnL || 0)}>
                    {formatCurrency(ibkrSummary?.totalPnL || 0)}
                  </Text>
                </Box>
                <Box>
                  <Text fontSize="sm" color="gray.500">Cash</Text>
                  <Text fontWeight="bold">{formatCurrency(ibkrSummary?.cashBalance || 0)}</Text>
                </Box>
                <Box>
                  <Text fontSize="sm" color="gray.500">Positions</Text>
                  <Text fontWeight="bold">{ibkrSummary?.totalPositions || 0}</Text>
                </Box>
              </SimpleGrid>
            </CardBody>
          </Card>

          {/* Tastytrade Card */}
          <Card>
            <CardHeader>
              <HStack justify="space-between">
                <Heading size="md">Tastytrade</Heading>
                <Badge colorScheme="orange">TT</Badge>
              </HStack>
            </CardHeader>
            <CardBody>
              <SimpleGrid columns={2} spacing={4}>
                <Box>
                  <Text fontSize="sm" color="gray.500">Total Value</Text>
                  <Text fontWeight="bold" fontSize="lg">{formatCurrency(tastytradeSummary?.totalValue || 0)}</Text>
                </Box>
                <Box>
                  <Text fontSize="sm" color="gray.500">P&L</Text>
                  <Text fontWeight="bold" fontSize="lg" color={getChangeColor(tastytradeSummary?.totalPnL || 0)}>
                    {formatCurrency(tastytradeSummary?.totalPnL || 0)}
                  </Text>
                </Box>
                <Box>
                  <Text fontSize="sm" color="gray.500">Cash</Text>
                  <Text fontWeight="bold">{formatCurrency(tastytradeSummary?.cashBalance || 0)}</Text>
                </Box>
                <Box>
                  <Text fontSize="sm" color="gray.500">Positions</Text>
                  <Text fontWeight="bold">{tastytradeSummary?.totalPositions || 0}</Text>
                </Box>
              </SimpleGrid>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Filters and Search */}
        <Card>
          <CardBody>
            <SimpleGrid columns={{ base: 2, md: 6 }} spacing={4} mb={4}>
              <InputGroup>
                <InputLeftElement pointerEvents="none">
                  <FaSearch color="gray" />
                </InputLeftElement>
                <Input
                  placeholder="Search holdings..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </InputGroup>

              <Select
                value={selectedBrokerage}
                onChange={(e) => setSelectedBrokerage(e.target.value as any)}
              >
                <option value="all">All Brokerages</option>
                <option value="ibkr">IBKR Only</option>
                <option value="tastytrade">Tastytrade Only</option>
              </Select>

              <Select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value as any)}
              >
                <option value="all">All Types</option>
                <option value="stock">Stocks</option>
                <option value="option">Options</option>
                <option value="etf">ETFs</option>
                <option value="crypto">Crypto</option>
              </Select>

              <FormControl display="flex" alignItems="center">
                <FormLabel htmlFor="profitable-switch" mb="0" fontSize="sm">
                  Profitable Only
                </FormLabel>
                <Switch
                  id="profitable-switch"
                  isChecked={showOnlyProfitable}
                  onChange={(e) => setShowOnlyProfitable(e.target.checked)}
                  size="sm"
                />
              </FormControl>

              <FormControl display="flex" alignItems="center">
                <FormLabel htmlFor="options-switch" mb="0" fontSize="sm">
                  Options Only
                </FormLabel>
                <Switch
                  id="options-switch"
                  isChecked={showOnlyOptions}
                  onChange={(e) => setShowOnlyOptions(e.target.checked)}
                  size="sm"
                />
              </FormControl>

              <Text fontSize="sm" color="gray.500" alignSelf="center">
                Showing {filteredHoldings.length} of {holdings.length} positions
              </Text>
            </SimpleGrid>
          </CardBody>
        </Card>

        {/* Holdings Table */}
        <Card>
          <CardBody>
            <TableContainer>
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th>
                      <Button variant="ghost" size="xs" onClick={() => handleSort('symbol')}>
                        Symbol {getSortIcon('symbol')}
                      </Button>
                    </Th>
                    <Th>Brokerage</Th>
                    <Th>Type</Th>
                    <Th>Quantity</Th>
                    <Th>Price</Th>
                    <Th>
                      <Button variant="ghost" size="xs" onClick={() => handleSort('value')}>
                        Market Value {getSortIcon('value')}
                      </Button>
                    </Th>
                    <Th>
                      <Button variant="ghost" size="xs" onClick={() => handleSort('pnl')}>
                        P&L {getSortIcon('pnl')}
                      </Button>
                    </Th>
                    <Th>
                      <Button variant="ghost" size="xs" onClick={() => handleSort('pnlPct')}>
                        P&L % {getSortIcon('pnlPct')}
                      </Button>
                    </Th>
                    <Th>Greeks</Th>
                    <Th>Actions</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {filteredHoldings.map((holding) => (
                    <Tr key={holding.id} _hover={{ bg: 'gray.50' }}>
                      <Td>
                        <VStack align="start" spacing={1}>
                          <Text fontWeight="bold" fontSize="sm">
                            {holding.type === 'option' ? holding.symbol.slice(0, 4) : holding.symbol}
                          </Text>
                          {holding.type === 'option' && (
                            <Text fontSize="xs" color="gray.500">
                              {holding.optionType?.toUpperCase()} ${holding.strikePrice} {holding.expirationDate}
                            </Text>
                          )}
                        </VStack>
                      </Td>
                      <Td>
                        <Badge colorScheme={holding.brokerage === 'ibkr' ? 'blue' : 'orange'}>
                          {holding.brokerage.toUpperCase()}
                        </Badge>
                      </Td>
                      <Td>
                        <Badge colorScheme={holding.type === 'option' ? 'purple' : 'gray'}>
                          {holding.type.toUpperCase()}
                        </Badge>
                      </Td>
                      <Td>
                        <Text color={holding.quantity >= 0 ? 'green.500' : 'red.500'}>
                          {holding.quantity >= 0 ? '+' : ''}{holding.quantity}
                        </Text>
                      </Td>
                      <Td>{formatCurrency(holding.currentPrice)}</Td>
                      <Td fontWeight="bold">{formatCurrency(Math.abs(holding.marketValue))}</Td>
                      <Td fontWeight="bold" color={getChangeColor(holding.unrealizedPnL)}>
                        {formatCurrency(holding.unrealizedPnL)}
                      </Td>
                      <Td fontWeight="bold" color={getChangeColor(holding.unrealizedPnLPct)}>
                        {formatPercent(holding.unrealizedPnLPct)}
                      </Td>
                      <Td>
                        {holding.type === 'option' && (
                          <VStack align="start" spacing={0}>
                            <Text fontSize="xs">Δ {holding.delta?.toFixed(3)}</Text>
                            <Text fontSize="xs">Θ {holding.theta?.toFixed(3)}</Text>
                          </VStack>
                        )}
                      </Td>
                      <Td>
                        <HStack spacing={1}>
                          <IconButton
                            icon={<FaEye />}
                            size="xs"
                            aria-label="View details"
                            onClick={() => viewHoldingDetails(holding)}
                          />
                          <IconButton
                            icon={<FaChartLine />}
                            size="xs"
                            aria-label="View chart"
                          />
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </TableContainer>
          </CardBody>
        </Card>
      </VStack>

      {/* Holding Details Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>
            {selectedHolding?.symbol} Details
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            {selectedHolding && (
              <VStack spacing={4} align="stretch">
                <SimpleGrid columns={2} spacing={4}>
                  <Box>
                    <Text fontSize="sm" color="gray.500">Name</Text>
                    <Text fontWeight="bold">{selectedHolding.name}</Text>
                  </Box>
                  <Box>
                    <Text fontSize="sm" color="gray.500">Brokerage</Text>
                    <Badge colorScheme={selectedHolding.brokerage === 'ibkr' ? 'blue' : 'orange'}>
                      {selectedHolding.brokerage.toUpperCase()}
                    </Badge>
                  </Box>
                  <Box>
                    <Text fontSize="sm" color="gray.500">Type</Text>
                    <Badge>{selectedHolding.type.toUpperCase()}</Badge>
                  </Box>
                  <Box>
                    <Text fontSize="sm" color="gray.500">Sector</Text>
                    <Text>{selectedHolding.sector}</Text>
                  </Box>
                </SimpleGrid>

                <Divider />

                <SimpleGrid columns={3} spacing={4}>
                  <Stat size="sm">
                    <StatLabel>Quantity</StatLabel>
                    <StatNumber>{selectedHolding.quantity}</StatNumber>
                  </Stat>
                  <Stat size="sm">
                    <StatLabel>Current Price</StatLabel>
                    <StatNumber>{formatCurrency(selectedHolding.currentPrice)}</StatNumber>
                  </Stat>
                  <Stat size="sm">
                    <StatLabel>Cost Basis</StatLabel>
                    <StatNumber>{formatCurrency(selectedHolding.costBasis)}</StatNumber>
                  </Stat>
                </SimpleGrid>

                <SimpleGrid columns={3} spacing={4}>
                  <Stat size="sm">
                    <StatLabel>Market Value</StatLabel>
                    <StatNumber>{formatCurrency(Math.abs(selectedHolding.marketValue))}</StatNumber>
                  </Stat>
                  <Stat size="sm">
                    <StatLabel>Unrealized P&L</StatLabel>
                    <StatNumber color={getChangeColor(selectedHolding.unrealizedPnL)}>
                      {formatCurrency(selectedHolding.unrealizedPnL)}
                    </StatNumber>
                  </Stat>
                  <Stat size="sm">
                    <StatLabel>P&L %</StatLabel>
                    <StatNumber color={getChangeColor(selectedHolding.unrealizedPnLPct)}>
                      {formatPercent(selectedHolding.unrealizedPnLPct)}
                    </StatNumber>
                  </Stat>
                </SimpleGrid>

                {selectedHolding.type === 'option' && (
                  <>
                    <Divider />
                    <Text fontWeight="bold">Options Details</Text>
                    <SimpleGrid columns={3} spacing={4}>
                      <Box>
                        <Text fontSize="sm" color="gray.500">Strike Price</Text>
                        <Text fontWeight="bold">${selectedHolding.strikePrice}</Text>
                      </Box>
                      <Box>
                        <Text fontSize="sm" color="gray.500">Expiration</Text>
                        <Text fontWeight="bold">{selectedHolding.expirationDate}</Text>
                      </Box>
                      <Box>
                        <Text fontSize="sm" color="gray.500">Type</Text>
                        <Badge colorScheme={selectedHolding.optionType === 'call' ? 'green' : 'red'}>
                          {selectedHolding.optionType?.toUpperCase()}
                        </Badge>
                      </Box>
                    </SimpleGrid>

                    <Text fontWeight="bold">Greeks</Text>
                    <SimpleGrid columns={4} spacing={4}>
                      <Stat size="sm">
                        <StatLabel>Delta (Δ)</StatLabel>
                        <StatNumber fontSize="sm">{selectedHolding.delta?.toFixed(4)}</StatNumber>
                      </Stat>
                      <Stat size="sm">
                        <StatLabel>Gamma (Γ)</StatLabel>
                        <StatNumber fontSize="sm">{selectedHolding.gamma?.toFixed(4)}</StatNumber>
                      </Stat>
                      <Stat size="sm">
                        <StatLabel>Theta (Θ)</StatLabel>
                        <StatNumber fontSize="sm">{selectedHolding.theta?.toFixed(4)}</StatNumber>
                      </Stat>
                      <Stat size="sm">
                        <StatLabel>Vega (ν)</StatLabel>
                        <StatNumber fontSize="sm">{selectedHolding.vega?.toFixed(4)}</StatNumber>
                      </Stat>
                    </SimpleGrid>

                    <Box>
                      <Text fontSize="sm" color="gray.500">Implied Volatility</Text>
                      <Text fontWeight="bold">{((selectedHolding.impliedVolatility || 0) * 100).toFixed(2)}%</Text>
                    </Box>
                  </>
                )}
              </VStack>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default MultiPortfolio; 