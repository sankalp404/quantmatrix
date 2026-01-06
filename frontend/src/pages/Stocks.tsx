import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Heading,
  Input,
  InputGroup,
  InputElement,
  Select,
  Grid,
  GridItem,
  Card,
  CardBody,
  Badge,
  StatRoot,
  StatLabel,
  StatHelpText,
  StatValueText,
  StatUpIndicator,
  StatDownIndicator,
  useBreakpointValue,
  AlertRoot,
  AlertIndicator,
  Button,
  Collapse,
  useDisclosure,
  IconButton,
  Flex,
} from '@chakra-ui/react';
import { FiSearch, FiFilter, FiTrendingUp, FiTrendingDown, FiX, FiExternalLink } from 'react-icons/fi';
import { portfolioApi, handleApiError } from '../services/api';
import AccountFilterWrapper from '../components/ui/AccountFilterWrapper';
import TradingViewChart from '../components/charts/TradingViewChart';
import ErrorBoundary from '../components/ErrorBoundary';
import { HoldingsTableSkeleton, LoadingSpinner } from '../components/LoadingStates';
import PageHeader from '../components/ui/PageHeader';
import toast from 'react-hot-toast';

// Chakra v3 migration shim: prefer dark values until we reintroduce color-mode properly.
const useColorModeValue = <T,>(_light: T, dark: T) => dark;
import EmptyState from '../components/ui/EmptyState';
import { useAccountContext } from '../context/AccountContext';

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

const transformPortfolioToAccounts = (portfolioData: any): AccountData[] => {
  if (!portfolioData?.accounts) return [];
  const totalPortfolioValue = Object.values(portfolioData.accounts).reduce((sum: number, data: any) => {
    return sum + (data.account_summary?.net_liquidation || 0);
  }, 0);
  return Object.entries(portfolioData.accounts).map(([id, data]: [string, any]) => {
    const accountValue = data.account_summary?.net_liquidation || 0;
    return {
      account_id: id,
      account_name: data.account_summary?.account_name || id,
      account_type: id.toLowerCase().includes('ira') ? 'Tax-Deferred' : 'Taxable',
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

const HoldingCard: React.FC<{
  holding: StockHolding;
  isLoading?: boolean;
  isSelected?: boolean;
  onClick?: () => void;
  showChart?: boolean;
}> = ({ holding, isLoading = false, isSelected = false, onClick, showChart = false }) => {
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const selectedBorderColor = useColorModeValue('blue.400', 'blue.300');
  const taxLotBg = useColorModeValue('gray.50', 'gray.700');
  const taxLotBorderColor = useColorModeValue('gray.200', 'gray.600');
  const profitColor = holding?.unrealized_pnl >= 0 ? 'green.500' : 'red.500';
  const dayProfitColor = holding?.day_pnl >= 0 ? 'green.500' : 'red.500';

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
      const result = await portfolioApi.getHoldingTaxLots(holding.id);
      if (result.status === 'success' && result.data?.tax_lots) {
        const lots = result.data.tax_lots.length > 0 ? result.data.tax_lots : [];
        setTaxLots(lots);
        if (lots.length > 0) {
          const taxLotTotalShares = lots.reduce((sum, lot) => sum + (lot.shares_remaining || lot.shares || 0), 0);
          const holdingShares = holding.shares;
          const difference = Math.abs(holdingShares - taxLotTotalShares);
          if (difference > 0.01) {
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
                {holding.market_value.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
              </Text>
              <HStack spacing={2}>
                <Text color={profitColor} fontSize="sm" fontWeight="medium">
                  {holding.unrealized_pnl >= 0 ? '+' : '-'}{Math.abs(holding.unrealized_pnl).toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
                </Text>
                <Badge colorScheme={holding.unrealized_pnl >= 0 ? 'green' : 'red'}>
                  {holding.unrealized_pnl_pct > 0 ? '+' : ''}{holding.unrealized_pnl_pct.toFixed(2)}%
                </Badge>
              </HStack>
            </VStack>
          </HStack>
          <Grid templateColumns="repeat(3, 1fr)" gap={4}>
            <StatRoot size="sm">
              <StatLabel fontSize="xs">Current Price</StatLabel>
              <StatValueText fontSize="md">{holding.current_price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}</StatValueText>
            </StatRoot>
            <StatRoot size="sm">
              <StatLabel fontSize="xs">Avg Cost</StatLabel>
              <StatValueText fontSize="md">{holding.average_cost.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}</StatValueText>
            </StatRoot>
            <StatRoot size="sm">
              <StatLabel fontSize="xs">Day P&L</StatLabel>
              <StatValueText fontSize="md" color={dayProfitColor}>
                {holding.day_pnl.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
              </StatValueText>
            </StatRoot>
          </Grid>
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
              <VStack spacing={3} mt={3} align="stretch">
                {taxLotDiscrepancy?.hasDiscrepancy && (
                  <AlertRoot status="warning" size="sm" borderRadius="md">
                    <AlertIndicator />
                    <Box flex="1">
                      <Text fontSize="sm" fontWeight="bold">Tax Lot Discrepancy</Text>
                      <Text fontSize="xs">
                        Holding: {taxLotDiscrepancy.holdingShares} shares |
                        Tax Lots: {taxLotDiscrepancy.taxLotShares} shares |
                        Difference: {taxLotDiscrepancy.difference.toFixed(2)}
                      </Text>
                    </Box>
                  </AlertRoot>
                )}
                {taxLotsError ? (
                  <Text fontSize="sm" color="red.500">{taxLotsError}</Text>
                ) : taxLots.length > 0 ? (
                  (() => {
                    const mergedMap = new Map<string, TaxLot>();
                    for (const lot of taxLots) {
                      const key = `${lot.purchase_date?.slice(0, 10)}|${(lot.cost_per_share || 0).toFixed(4)}|${lot.is_long_term ? 'L' : 'S'}`;
                      if (!mergedMap.has(key)) {
                        mergedMap.set(key, { ...lot });
                      } else {
                        const acc = mergedMap.get(key)!;
                        acc.shares = (acc.shares || 0) + (lot.shares || 0);
                        acc.shares_remaining = (acc.shares_remaining || 0) + (lot.shares_remaining || lot.shares || 0);
                        if (typeof acc.unrealized_pnl === 'number' && typeof lot.unrealized_pnl === 'number') {
                          acc.unrealized_pnl = (acc.unrealized_pnl || 0) + (lot.unrealized_pnl || 0);
                        }
                      }
                    }
                    const merged = Array.from(mergedMap.values());
                    const sorted = merged.sort((a, b) => new Date(b.purchase_date).getTime() - new Date(a.purchase_date).getTime());
                    const longLots = sorted.filter(l => l.is_long_term);
                    const shortLots = sorted.filter(l => !l.is_long_term);
                    const renderGroup = (lots: TaxLot[], title: string) => (
                      <VStack align="stretch" spacing={2}>
                        <Text fontSize="sm" fontWeight="semibold" color="gray.600">{title} ({lots.length})</Text>
                        {lots.map((lot) => (
                          <HStack
                            key={lot.id}
                            p={3}
                            bg={taxLotBg}
                            borderRadius="md"
                            border="1px"
                            borderColor={taxLotBorderColor}
                            justify="space-between"
                          >
                            <HStack spacing={4}>
                              <Box w="8px" h="8px" borderRadius="full" bg={lot.is_long_term ? 'green.400' : 'orange.400'} />
                              <VStack align="start" spacing={0}>
                                <Text fontWeight="medium">{(lot.shares_remaining || lot.shares || 0).toLocaleString()} sh @ {(lot.cost_per_share || 0).toLocaleString('en-US', { style: 'currency', currency: 'USD' })}</Text>
                                <Text color="gray.500" fontSize="xs">{lot.purchase_date?.slice(0, 10)}</Text>
                              </VStack>
                            </HStack>
                            <HStack spacing={6}>
                              <VStack align="end" spacing={0}>
                                <Text color={typeof lot.unrealized_pnl === 'number' && lot.unrealized_pnl >= 0 ? 'green.500' : 'red.500'} fontWeight="medium">
                                  {typeof lot.unrealized_pnl === 'number' ? (lot.unrealized_pnl >= 0 ? '+' : '-') + Math.abs(lot.unrealized_pnl).toLocaleString('en-US', { style: 'currency', currency: 'USD' }) : '-'}
                                </Text>
                                <Text color="gray.500" fontSize="xs">
                                  {typeof lot.unrealized_pnl_pct === 'number' ? `${lot.unrealized_pnl_pct > 0 ? '+' : ''}${lot.unrealized_pnl_pct.toFixed(1)}%` : ''}
                                </Text>
                              </VStack>
                              <Text color="gray.500" fontSize="xs">{lot.days_held ? `${lot.days_held}d` : ''}</Text>
                            </HStack>
                          </HStack>
                        ))}
                      </VStack>
                    );
                    return (
                      <VStack align="stretch" spacing={4}>
                        {shortLots.length > 0 && renderGroup(shortLots, 'Short Term')}
                        {longLots.length > 0 && renderGroup(longLots, 'Long Term')}
                      </VStack>
                    );
                  })()
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

const Stocks: React.FC = () => {
  const { selected, setSelected } = useAccountContext();
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
  const isMobile = useBreakpointValue({ base: true, lg: false });
  const chartPosition = useBreakpointValue({ base: 'top', lg: 'side' });

  useEffect(() => {
    const param = selected === 'taxable' || selected === 'ira' || selected === 'all' ? undefined : selected;
    fetchHoldingsData(false, param);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  const fetchHoldingsData = async (isRetry = false, accountId?: string) => {
    if (!isRetry) {
      setLoading(true);
    }
    setError(null);
    try {
      if (isRetry && retryCount > 0) {
        toast(`Retrying… Attempt ${retryCount + 1}`);
      }
      const portfolioResult = await portfolioApi.getLive();
      setPortfolioData(portfolioResult.data);
      const allAccounts = Object.keys(portfolioResult.data?.accounts || {});
      const effectiveAccountId = accountId || (allAccounts.length > 0 ? allAccounts[0] : undefined);
      const holdingsResult = await portfolioApi.getStocksOnly(effectiveAccountId);
      if (holdingsResult.status === 'success') {
        const rows = holdingsResult.data.holdings || holdingsResult.data.stocks || [];
        setHoldings(rows);
        setRetryCount(0);
      } else {
        throw new Error(holdingsResult.error || 'Failed to load holdings');
      }
    } catch (err) {
      console.error('Error fetching holdings data:', err);
      const errorMessage = handleApiError(err);
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async () => {
    const newRetryCount = retryCount + 1;
    setRetryCount(newRetryCount);
    const delay = Math.min(1000 * Math.pow(2, newRetryCount - 1), 10000);
    if (newRetryCount <= 3) {
      setTimeout(() => {
        fetchHoldingsData(true);
      }, delay);
    } else {
      toast.error('Max retries reached. Please check your connection and try again later.');
    }
  };

  const sectors = useMemo(() => {
    const sectorSet = new Set(holdings.map(h => h.sector).filter(Boolean));
    return Array.from(sectorSet).sort();
  }, [holdings]);

  const accounts = portfolioData ? transformPortfolioToAccounts(portfolioData) : [];

  if (loading) {
    return (
      <Box p={6}>
        <VStack spacing={6} align="stretch">
          <Box>
            <Heading size="lg" mb={2}>Stocks</Heading>
            <Text color="gray.500" fontSize="sm">
              Loading your stock positions...
            </Text>
          </Box>
          <HoldingsTableSkeleton rows={8} />
        </VStack>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={6}>
        <VStack spacing={6} align="stretch">
          <Box>
            <Heading size="lg" mb={2}>Stocks</Heading>
            <Text color="gray.500" fontSize="sm">
              Error loading stocks
            </Text>
          </Box>
          <AlertRoot status="error" borderRadius="md">
            <AlertIndicator />
            <Box flex="1">
              <Text fontWeight="bold">Failed to load stocks</Text>
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
          </AlertRoot>
        </VStack>
      </Box>
    );
  }

  return (
    <ErrorBoundary>
      <Box p={6}>
        <VStack spacing={6} align="stretch">
          <PageHeader
            title="Stocks"
            subtitle={`Real data from backend • Last updated: ${new Date().toLocaleTimeString()}`}
          />
          {holdings.length === 0 && (
            <EmptyState
              icon={FiTrendingUp}
              title="No stock holdings found"
              description="We couldn’t find any stock positions. Once your IBKR FlexQuery sync completes and stocks are available, they will appear here."
              action={{ label: 'Retry', onClick: () => fetchHoldingsData() }}
            />
          )}
          <AccountFilterWrapper
            data={holdings}
            accounts={accounts}
            config={{
              showAllOption: true,
              showSummary: true,
              size: 'lg',
              variant: 'detailed',
              defaultSelection: selected || (accounts.length > 0 ? accounts[0].account_id : 'all')
            }}
            loading={loading}
            error={error}
            onAccountChange={(account) => {
              setSelected(account as any);
              const accParam = account === 'all' || account === 'taxable' || account === 'ira' ? undefined : account;
              fetchHoldingsData(false, accParam);
            }}
          >
            {(accountFilteredHoldings, filterState) => {
              const selectedAccountId = filterState?.selectedAccount && filterState.selectedAccount !== 'all' ? filterState.selectedAccount : undefined;
              const accountSummary = useMemo(() => {
                if (!portfolioData?.accounts) return null;
                if (selectedAccountId) {
                  return portfolioData.accounts[selectedAccountId]?.account_summary || null;
                }
                const summaries = Object.values<any>(portfolioData.accounts).map((a: any) => a.account_summary || {});
                return summaries.reduce((acc: any, s: any) => ({
                  net_liquidation: (acc.net_liquidation || 0) + (s.net_liquidation || 0),
                  unrealized_pnl: (acc.unrealized_pnl || 0) + (s.unrealized_pnl || 0),
                  day_change: (acc.day_change || 0) + (s.day_change || 0)
                }), {});
              }, [portfolioData, selectedAccountId]);
              const summaryBar = accountSummary ? (
                <HStack spacing={6} p={3} border="1px" borderColor={borderColor} borderRadius="md">
                  <VStack align="start" spacing={0}>
                    <Text fontSize="xs" color="gray.500">Portfolio Value</Text>
                    <Text fontWeight="bold">{(accountSummary.net_liquidation || 0).toLocaleString('en-US', { style: 'currency', currency: 'USD' })}</Text>
                  </VStack>
                  <VStack align="start" spacing={0}>
                    <Text fontSize="xs" color="gray.500">Unrealized P&L</Text>
                    <Text color={(accountSummary.unrealized_pnl || 0) >= 0 ? 'green.500' : 'red.500'} fontWeight="bold">
                      {(accountSummary.unrealized_pnl || 0) >= 0 ? '+' : '-'}{Math.abs(accountSummary.unrealized_pnl || 0).toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
                    </Text>
                  </VStack>
                  <VStack align="start" spacing={0}>
                    <Text fontSize="xs" color="gray.500">Day P&L</Text>
                    <Text color={(accountSummary.day_change || 0) >= 0 ? 'green.500' : 'red.500'} fontWeight="bold">
                      {(accountSummary.day_change || 0) >= 0 ? '+' : '-'}{Math.abs(accountSummary.day_change || 0).toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
                    </Text>
                  </VStack>
                </HStack>
              ) : null;
              const filteredAndSortedHoldings = useMemo(() => {
                let filtered = accountFilteredHoldings.filter(holding => {
                  const matchesSearch = holding.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
                    holding.industry.toLowerCase().includes(searchTerm.toLowerCase());
                  const matchesSector = selectedSector === 'all' || holding.sector === selectedSector;
                  return matchesSearch && matchesSector;
                });
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
                  {summaryBar}
                  <HStack spacing={4} wrap="wrap">
                    <Box flex="1" minW="200px">
                      <InputGroup
                        startElement={
                          <InputElement pointerEvents="none">
                            <FiSearch color="gray.300" />
                          </InputElement>
                        }
                      >
                        <Input
                          placeholder="Search stocks..."
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
                  {filteredAndSortedHoldings.length === 0 && (
                    <Box textAlign="center" py={12}>
                      <Text fontSize="lg" color="gray.500">
                        No stocks match your filters
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

export default Stocks;