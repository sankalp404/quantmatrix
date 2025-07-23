import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Heading,
  Input,
  InputGroup,
  InputLeftElement,
  Select,
  Grid,
  GridItem,
  Card,
  CardBody,
  Badge,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  useColorModeValue,
  useBreakpointValue,
  Alert,
  AlertIcon,
  Button,
  Collapse,
  useDisclosure,
  IconButton,
  Flex,
  useToast
} from '@chakra-ui/react';
import { FiSearch, FiFilter, FiTrendingUp, FiTrendingDown, FiX, FiExternalLink } from 'react-icons/fi';
import { portfolioApi, handleApiError } from '../services/api';
import AccountFilterWrapper from '../components/AccountFilterWrapper';
import TradingViewChart from '../components/TradingViewChart';
import ErrorBoundary from '../components/ErrorBoundary';
import { HoldingsTableSkeleton, LoadingSpinner } from '../components/LoadingStates';

// Types and Interfaces
interface TaxLot {
  id: string;
  shares: number;
  shares_purchased?: number;
  shares_remaining?: number;
  purchase_date: string;
  cost_per_share: number;
  current_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
  days_held?: number;
  is_long_term: boolean;
}

interface StockHolding {
  id: number;
  symbol: string;
  account_number: string;
  broker: string;
  shares: number;
  current_price: number;
  market_value: number;
  cost_basis: number;
  average_cost: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  day_pnl: number;
  day_pnl_pct: number;
  sector: string;
  industry: string;
  last_updated: string;
}

// AccountData interface to match what AccountFilterWrapper expects
interface AccountData {
  account_id: string;
  account_name: string;
  account_type: string;
  broker: string;
  total_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  allocation_pct: number;
  cash_balance: number;
  positions_count: number;
}

// Utility functions
const transformPortfolioToAccounts = (portfolioData: any): AccountData[] => {
  if (!portfolioData?.accounts) return [];

  // Calculate total portfolio value for allocation percentages
  const totalPortfolioValue = Object.values(portfolioData.accounts).reduce((sum: number, data: any) => {
    return sum + (data.account_summary?.net_liquidation || 0);
  }, 0);

  return Object.entries(portfolioData.accounts).map(([id, data]: [string, any]) => {
    const accountValue = data.account_summary?.net_liquidation || 0;

    return {
      account_id: id,
      account_name: data.account_summary?.account_name || id,
      account_type: id.includes('U19490886') ? 'Taxable' : 'Tax-Deferred',
      broker: 'IBKR',
      total_value: accountValue,
      unrealized_pnl: data.account_summary?.unrealized_pnl || 0,
      unrealized_pnl_pct: 0,
      allocation_pct: totalPortfolioValue > 0 ? (accountValue / totalPortfolioValue) * 100 : 0,
      cash_balance: data.account_summary?.total_cash || 0,
      positions_count: data.all_positions?.length || 0
    };
  });
};

// Modern Holding Card Component with enhanced loading states
const HoldingCard: React.FC<{
  holding: StockHolding;
  isLoading?: boolean;
  isSelected?: boolean;
  onClick?: () => void;
  showChart?: boolean;
}> = ({ holding, isLoading = false, isSelected = false, onClick, showChart = false }) => {
  // All color mode values at top level to maintain hooks order
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const selectedBorderColor = useColorModeValue('blue.400', 'blue.300');
  const taxLotBg = useColorModeValue('gray.50', 'gray.700');
  const taxLotBorderColor = useColorModeValue('gray.200', 'gray.600');

  // Calculate colors based on P&L but don't use hooks conditionally
  const profitColor = holding?.unrealized_pnl >= 0 ? 'green.500' : 'red.500';
  const dayProfitColor = holding?.day_pnl >= 0 ? 'green.500' : 'red.500';

  // Get real tax lots from backend API call with enhanced error handling
  const [taxLots, setTaxLots] = useState<TaxLot[]>([]);
  const [loadingTaxLots, setLoadingTaxLots] = useState(false);
  const [taxLotsError, setTaxLotsError] = useState<string | null>(null);
  const [taxLotDiscrepancy, setTaxLotDiscrepancy] = useState<{
    hasDiscrepancy: boolean;
    holdingShares: number;
    taxLotShares: number;
    difference: number;
  } | null>(null);

  useEffect(() => {
    if (!isLoading && holding?.id) {
      fetchTaxLots();
    }
  }, [holding?.id, isLoading]);

  const fetchTaxLots = async () => {
    if (!holding?.id) return;

    setLoadingTaxLots(true);
    setTaxLotsError(null);

    try {
      // Use improved backend API
      const result = await portfolioApi.getHoldingTaxLots(holding.id);

      if (result.status === 'success' && result.data?.tax_lots) {
        const lots = result.data.tax_lots.length > 0 ? result.data.tax_lots : [];
        setTaxLots(lots);

        // Calculate tax lot discrepancy
        if (lots.length > 0) {
          const taxLotTotalShares = lots.reduce((sum, lot) => sum + (lot.shares_remaining || lot.shares || 0), 0);
          const holdingShares = holding.shares;
          const difference = Math.abs(holdingShares - taxLotTotalShares);
          
          if (difference > 0.01) { // Allow for small rounding differences
            setTaxLotDiscrepancy({
              hasDiscrepancy: true,
              holdingShares: holdingShares,
              taxLotShares: taxLotTotalShares,
              difference: difference
            });
          } else {
            setTaxLotDiscrepancy(null);
          }
        } else {
          setTaxLotDiscrepancy(null);
        }

        // Log performance if available
        if (result.data.processing_time_ms) {
          console.log(`Tax lots loaded in ${result.data.processing_time_ms}ms from ${result.data.source}`);
        }
      } else {
        setTaxLots([]);
        setTaxLotDiscrepancy(null);
        setTaxLotsError('Tax lots data unavailable');
      }
    } catch (error) {
      console.error('Error fetching tax lots:', error);
      setTaxLots([]);
      setTaxLotsError(handleApiError(error));
    } finally {
      setLoadingTaxLots(false);
    }
  };

  const { isOpen: isTaxLotsOpen, onToggle: onTaxLotsToggle } = useDisclosure();

  if (isLoading) {
    return (
      <Card bg={cardBg} shadow="sm" _hover={{ shadow: 'md' }}>
        <CardBody>
          <VStack align="stretch" spacing={3}>
            <HStack justify="space-between">
              <HStack spacing={3}>
                <Box w="40px" h="40px" bg="gray.200" borderRadius="full" />
                <VStack align="start" spacing={1}>
                  <Box h="16px" w="60px" bg="gray.200" borderRadius="md" />
                  <Box h="12px" w="80px" bg="gray.100" borderRadius="md" />
                </VStack>
              </HStack>
              <VStack align="end" spacing={1}>
                <Box h="16px" w="80px" bg="gray.200" borderRadius="md" />
                <Box h="12px" w="60px" bg="gray.100" borderRadius="md" />
              </VStack>
            </HStack>
          </VStack>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card
      bg={cardBg}
      shadow="sm"
      _hover={{ shadow: 'md' }}
      border="2px"
      borderColor={isSelected ? selectedBorderColor : borderColor}
      cursor={onClick ? 'pointer' : 'default'}
      onClick={onClick}
    >
      <CardBody>
        <VStack align="stretch" spacing={3}>
          {/* Main holding info */}
          <HStack justify="space-between">
            <HStack spacing={3}>
              <Box
                w="40px"
                h="40px"
                bg="blue.500"
                borderRadius="full"
                display="flex"
                alignItems="center"
                justifyContent="center"
                color="white"
                fontWeight="bold"
                fontSize="sm"
              >
                {holding.symbol.slice(0, 2)}
              </Box>
              <VStack align="start" spacing={1}>
                <Text fontWeight="bold" fontSize="lg">{holding.symbol}</Text>
                <Text fontSize="sm" color="gray.500">
                  {holding.shares} shares • {holding.industry || 'Stock'}
                </Text>
              </VStack>
            </HStack>

            <VStack align="end" spacing={1}>
              <Text fontWeight="bold" fontSize="lg">
                ${holding.market_value.toLocaleString()}
              </Text>
              <HStack spacing={2}>
                <Text color={profitColor} fontSize="sm" fontWeight="medium">
                  ${holding.unrealized_pnl > 0 ? '+' : ''}{holding.unrealized_pnl.toFixed(2)}
                </Text>
                <Badge colorScheme={holding.unrealized_pnl >= 0 ? 'green' : 'red'}>
                  {holding.unrealized_pnl_pct > 0 ? '+' : ''}{holding.unrealized_pnl_pct.toFixed(2)}%
                </Badge>
              </HStack>
            </VStack>
          </HStack>

          {/* Performance metrics */}
          <Grid templateColumns="repeat(3, 1fr)" gap={4}>
            <Stat size="sm">
              <StatLabel fontSize="xs">Current Price</StatLabel>
              <StatNumber fontSize="md">${holding.current_price.toFixed(2)}</StatNumber>
            </Stat>
            <Stat size="sm">
              <StatLabel fontSize="xs">Avg Cost</StatLabel>
              <StatNumber fontSize="md">${holding.average_cost.toFixed(2)}</StatNumber>
            </Stat>
            <Stat size="sm">
              <StatLabel fontSize="xs">Day P&L</StatLabel>
              <StatNumber fontSize="md" color={dayProfitColor}>
                ${holding.day_pnl.toFixed(2)}
              </StatNumber>
            </Stat>
          </Grid>

          {/* Tax lots section */}
          <Box>
            <Button
              size="sm"
              variant="ghost"
              leftIcon={<FiTrendingUp />}
              onClick={(e) => {
                e.stopPropagation();
                onTaxLotsToggle();
              }}
              isLoading={loadingTaxLots}
            >
              Tax Lots ({taxLots.length})
            </Button>

                      <Collapse in={isTaxLotsOpen} animateOpacity>
            <VStack spacing={2} mt={3} align="stretch">
              {/* Tax Lot Discrepancy Alert */}
              {taxLotDiscrepancy?.hasDiscrepancy && (
                <Alert status="warning" size="sm" borderRadius="md">
                  <AlertIcon />
                  <Box flex="1">
                    <Text fontSize="sm" fontWeight="bold">Tax Lot Discrepancy</Text>
                    <Text fontSize="xs">
                      Holding: {taxLotDiscrepancy.holdingShares} shares | 
                      Tax Lots: {taxLotDiscrepancy.taxLotShares} shares | 
                      Difference: {taxLotDiscrepancy.difference.toFixed(2)}
                    </Text>
                  </Box>
                </Alert>
              )}
              
              {taxLotsError ? (
                <Text fontSize="sm" color="red.500">{taxLotsError}</Text>
              ) : taxLots.length > 0 ? (
                  taxLots.map((lot, index) => (
                    <Box
                      key={lot.id}
                      p={3}
                      bg={taxLotBg}
                      borderRadius="md"
                      border="1px"
                      borderColor={taxLotBorderColor}
                    >
                      <Grid templateColumns="repeat(4, 1fr)" gap={2} fontSize="sm">
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="medium">{lot.shares_remaining || lot.shares || 0} shares</Text>
                          <Text color="gray.500">{lot.purchase_date?.slice(0, 10)}</Text>
                        </VStack>
                        <VStack align="start" spacing={0}>
                          <Text>${lot.cost_per_share?.toFixed(2)}</Text>
                          <Text color="gray.500">Cost/share</Text>
                        </VStack>
                        <VStack align="start" spacing={0}>
                          {lot.unrealized_pnl !== undefined ? (
                            <>
                              <Text color={lot.unrealized_pnl >= 0 ? 'green.500' : 'red.500'}>
                                ${lot.unrealized_pnl > 0 ? '+' : ''}{lot.unrealized_pnl.toFixed(2)}
                              </Text>
                              <Text color="gray.500">
                                {lot.unrealized_pnl_pct && lot.unrealized_pnl_pct > 0 ? '+' : ''}{lot.unrealized_pnl_pct?.toFixed(1) || '0.0'}%
                              </Text>
                            </>
                          ) : (
                            <>
                              <Text color="gray.500">-</Text>
                              <Text color="gray.500" fontSize="xs">No P&L calc</Text>
                            </>
                          )}
                        </VStack>
                        <VStack align="start" spacing={0}>
                          <Badge colorScheme={lot.is_long_term ? 'green' : 'orange'} size="sm">
                            {lot.is_long_term ? 'Long' : 'Short'}
                          </Badge>
                          <Text color="gray.500" fontSize="xs">
                            {lot.days_held ? `${lot.days_held}d` : 'Recent'}
                          </Text>
                        </VStack>
                      </Grid>
                    </Box>
                  ))
                ) : (
                  <Text fontSize="sm" color="gray.500">No tax lots available</Text>
                )}
              </VStack>
            </Collapse>
          </Box>
        </VStack>
      </CardBody>
    </Card>
  );
};

// Enhanced Holdings page with comprehensive loading states
const Holdings: React.FC = () => {
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [holdings, setHoldings] = useState<StockHolding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSector, setSelectedSector] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('market_value');
  const [selectedHolding, setSelectedHolding] = useState<string | null>(null);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const toast = useToast();

  // Responsive layout
  const isMobile = useBreakpointValue({ base: true, lg: false });
  const chartPosition = useBreakpointValue({ base: 'top', lg: 'side' });

  useEffect(() => {
    fetchHoldingsData();
  }, []);

  const fetchHoldingsData = async (isRetry = false) => {
    if (!isRetry) {
      setLoading(true);
    }
    setError(null);

    try {
      // Show loading message based on retry status
      if (isRetry && retryCount > 0) {
        toast({
          title: 'Retrying...',
          description: `Attempt ${retryCount + 1}`,
          status: 'info',
          duration: 2000,
        });
      }

      // Get portfolio data for account selector with timeout
      const portfolioResult = await portfolioApi.getLive();
      setPortfolioData(portfolioResult.data);

      // Get real holdings data from backend with enhanced error handling
      const holdingsResult = await portfolioApi.getStocksOnly();

      if (holdingsResult.status === 'success') {
        setHoldings(holdingsResult.data.holdings || []);
        setRetryCount(0); // Reset retry count on success
      } else {
        throw new Error(holdingsResult.error || 'Failed to load holdings');
      }
    } catch (err) {
      console.error('Error fetching holdings data:', err);
      const errorMessage = handleApiError(err);
      setError(errorMessage);

      // Show error toast
      toast({
        title: 'Error Loading Holdings',
        description: errorMessage,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  // Enhanced retry with exponential backoff
  const handleRetry = async () => {
    const newRetryCount = retryCount + 1;
    setRetryCount(newRetryCount);

    // Exponential backoff: wait 1s, 2s, 4s, etc.
    const delay = Math.min(1000 * Math.pow(2, newRetryCount - 1), 10000);

    if (newRetryCount <= 3) {
      setTimeout(() => {
        fetchHoldingsData(true);
      }, delay);
    } else {
      toast({
        title: 'Max Retries Reached',
        description: 'Please check your connection and try again later.',
        status: 'warning',
        duration: 5000,
      });
    }
  };

  // Get unique sectors (from all holdings for dropdown)
  const sectors = useMemo(() => {
    const sectorSet = new Set(holdings.map(h => h.sector).filter(Boolean));
    return Array.from(sectorSet).sort();
  }, [holdings]);

  // Transform portfolio data for account selector
  const accounts = portfolioData ? transformPortfolioToAccounts(portfolioData) : [];

  // Enhanced loading state with skeleton
  if (loading) {
    return (
      <Box p={6}>
        <VStack spacing={6} align="stretch">
          <Box>
            <Heading size="lg" mb={2}>Stock Holdings</Heading>
            <Text color="gray.500" fontSize="sm">
              Loading your stock positions...
            </Text>
          </Box>
          <HoldingsTableSkeleton rows={8} />
        </VStack>
      </Box>
    );
  }

  // Enhanced error state with retry options
  if (error) {
    return (
      <Box p={6}>
        <VStack spacing={6} align="stretch">
          <Box>
            <Heading size="lg" mb={2}>Stock Holdings</Heading>
            <Text color="gray.500" fontSize="sm">
              Error loading holdings data
            </Text>
          </Box>

          <Alert status="error" borderRadius="md">
            <AlertIcon />
            <Box flex="1">
              <Text fontWeight="bold">Failed to load holdings</Text>
              <Text fontSize="sm">{error}</Text>
            </Box>
            <VStack spacing={2}>
              <Button size="sm" colorScheme="red" onClick={() => fetchHoldingsData()}>
                Retry Now
              </Button>
              {retryCount < 3 && (
                <Button size="sm" variant="outline" onClick={handleRetry}>
                  Auto Retry ({3 - retryCount} left)
                </Button>
              )}
            </VStack>
          </Alert>
        </VStack>
      </Box>
    );
  }

  // Main holdings display
  return (
    <ErrorBoundary>
      <Box p={6}>
        <VStack spacing={6} align="stretch">
          {/* Header */}
          <Box>
            <Heading size="lg" mb={2}>Stock Holdings</Heading>
            <Text color="gray.500" fontSize="sm">
              Real-time data from IBKR • Last updated: {new Date().toLocaleTimeString()}
            </Text>
          </Box>

          {/* Account Filter */}
          <AccountFilterWrapper
            data={holdings}
            accounts={accounts}
            config={{
              showAllOption: true,
              showSummary: true,
              size: 'lg',
              variant: 'detailed'
            }}
            loading={loading}
            error={error}
          >
            {(accountFilteredHoldings, filterState) => {
              // Filter and sort holdings based on account-filtered data
              const filteredAndSortedHoldings = useMemo(() => {
                let filtered = accountFilteredHoldings.filter(holding => {
                  const matchesSearch = holding.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
                    holding.industry.toLowerCase().includes(searchTerm.toLowerCase());
                  const matchesSector = selectedSector === 'all' || holding.sector === selectedSector;

                  return matchesSearch && matchesSector;
                });

                // Sort holdings
                filtered.sort((a, b) => {
                  switch (sortBy) {
                    case 'market_value':
                      return b.market_value - a.market_value;
                    case 'unrealized_pnl':
                      return b.unrealized_pnl - a.unrealized_pnl;
                    case 'unrealized_pnl_pct':
                      return b.unrealized_pnl_pct - a.unrealized_pnl_pct;
                    case 'symbol':
                      return a.symbol.localeCompare(b.symbol);
                    default:
                      return 0;
                  }
                });

                return filtered;
              }, [accountFilteredHoldings, searchTerm, selectedSector, sortBy]);

              return (
                <VStack spacing={6} align="stretch">
                  {/* Search and Filters */}
                  <HStack spacing={4} wrap="wrap">
                    <Box flex="1" minW="200px">
                      <InputGroup>
                        <InputLeftElement pointerEvents="none">
                          <FiSearch color="gray.300" />
                        </InputLeftElement>
                        <Input
                          placeholder="Search holdings..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                        />
                      </InputGroup>
                    </Box>

                    <Select value={selectedSector} onChange={(e) => setSelectedSector(e.target.value)} maxW="200px">
                      <option value="all">All Sectors</option>
                      {sectors.map(sector => (
                        <option key={sector} value={sector}>{sector}</option>
                      ))}
                    </Select>

                    <Select value={sortBy} onChange={(e) => setSortBy(e.target.value)} maxW="200px">
                      <option value="market_value">Market Value</option>
                      <option value="unrealized_pnl">Total P&L</option>
                      <option value="unrealized_pnl_pct">P&L %</option>
                      <option value="symbol">Symbol</option>
                    </Select>
                  </HStack>

                  {/* Holdings Grid */}
                  <Grid templateColumns={isMobile ? "1fr" : "repeat(auto-fill, minmax(400px, 1fr))"} gap={6}>
                    {filteredAndSortedHoldings.map((holding) => (
                      <GridItem key={holding.id}>
                        <HoldingCard
                          holding={holding}
                          isSelected={selectedHolding === holding.symbol}
                          onClick={() => setSelectedHolding(
                            selectedHolding === holding.symbol ? null : holding.symbol
                          )}
                          showChart={selectedHolding === holding.symbol}
                        />

                        {/* TradingView Chart */}
                        {selectedHolding === holding.symbol && (
                          <Box mt={4}>
                            <TradingViewChart
                              symbol={holding.symbol}
                              height={chartPosition === 'top' ? 300 : 400}
                              showHeader={true}
                              interval="D"
                              theme={useColorModeValue('light', 'dark')}
                            />
                          </Box>
                        )}
                      </GridItem>
                    ))}
                  </Grid>

                  {/* Empty state */}
                  {filteredAndSortedHoldings.length === 0 && (
                    <Box textAlign="center" py={12}>
                      <Text fontSize="lg" color="gray.500">
                        No holdings match your filters
                      </Text>
                    </Box>
                  )}
                </VStack>
              );
            }}
          </AccountFilterWrapper>
        </VStack>
      </Box>
    </ErrorBoundary>
  );
};

export default Holdings; 