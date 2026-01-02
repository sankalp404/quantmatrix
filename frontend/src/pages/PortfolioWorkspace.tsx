import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Flex,
  VStack,
  HStack,
  Input,
  InputGroup,
  InputLeftElement,
  Text,
  Badge,
  Card,
  CardBody,
  CardHeader,
  SimpleGrid,
  Table,
  Thead,
  Tr,
  Th,
  Tbody,
  Td,
  useColorModeValue,
  Spinner,
  Button,
} from '@chakra-ui/react';
import { FiRefreshCw, FiSearch } from 'react-icons/fi';
import PageHeader from '../components/ui/PageHeader';
import SymbolChartWithMarkers from '../components/SymbolChartWithMarkers';
import TradingViewChart from '../components/TradingViewChart';
import { marketDataApi } from '../services/api';
import { portfolioApi } from '../services/api';
import { useAccountContext } from '../context/AccountContext';

interface StockRow {
  id: number;
  symbol: string;
  shares: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}

interface TxRow {
  id?: string;
  date?: string;
  time?: string;
  type?: string;
  action?: string;
  symbol?: string;
  quantity?: number;
  price?: number;
  amount?: number;
  description?: string;
}

interface LotRow {
  id?: string;
  purchase_date?: string;
  cost_per_share?: number;
  shares?: number;
  shares_remaining?: number;
}

const PortfolioWorkspace: React.FC = () => {
  const { selected } = useAccountContext();
  const [loading, setLoading] = useState(true);
  const [holdings, setHoldings] = useState<StockRow[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<TxRow[]>([]);
  const [lots, setLots] = useState<LotRow[]>([]);
  const [search, setSearch] = useState('');
  const border = useColorModeValue('gray.200', 'gray.700');
  const bgPane = useColorModeValue('white', 'gray.800');
  const hoverBg = useColorModeValue('gray.50', 'gray.700');
  const [bars, setBars] = useState<any[]>([]);
  const [showTrades, setShowTrades] = useState(true);
  const [showDividends, setShowDividends] = useState(true);
  const [hoverDaySec, setHoverDaySec] = useState<number | null>(null);
  const [lockedDaySec, setLockedDaySec] = useState<number | null>(null);
  const focusedDaySec = lockedDaySec ?? hoverDaySec;
  const [showLine, setShowLine] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [period, setPeriod] = useState<'1y' | '3y' | '5y' | 'max'>('max'); // fetch all by default
  const [zoomYears, setZoomYears] = useState<number | 'all'>(2); // default zoom to last 2 years
  const currencyFmt = useMemo(() => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }), []);
  const fmtDate = (iso: string | undefined) => {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: '2-digit' });
  };
  // Render-only with Lightweight charts (no TradingView embed toggle)

  const fetchAll = async () => {
    setLoading(true);
    try {
      const param = selected === 'all' || selected === 'taxable' || selected === 'ira' ? undefined : selected;
      const [stocksRes, statementsRes] = await Promise.all([
        portfolioApi.getStocks(param),
        portfolioApi.getStatements(param, 3650),
      ]);

      const stocks: StockRow[] = (stocksRes as any)?.data?.stocks || (stocksRes as any)?.data?.holdings || [];
      setHoldings(stocks);
      if (!selectedSymbol && stocks.length > 0) {
        setSelectedSymbol(stocks[0].symbol);
      }
      const tx: TxRow[] = (statementsRes as any)?.data?.transactions || [];
      setTransactions(tx);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  // Load history for selected symbol
  useEffect(() => {
    const loadHistory = async () => {
      if (!selectedSymbol) return;
      try {
        const res: any = await marketDataApi.getHistory(selectedSymbol, period, '1d');
        setBars(res?.data?.bars || res?.bars || []);
      } catch {
        setBars([]);
      }
    };
    loadHistory();
  }, [selectedSymbol, period]);

  // Load tax lots for selected holding (to backfill buy markers)
  useEffect(() => {
    const loadLots = async () => {
      if (!selectedSymbol) return setLots([]);
      try {
        const h = holdings.find(h => h.symbol === selectedSymbol);
        if (!h?.id) return setLots([]);
        const res: any = await portfolioApi.getHoldingTaxLots(h.id);
        const tl = res?.data?.tax_lots || [];
        setLots(tl);
      } catch {
        setLots([]);
      }
    };
    loadLots();
  }, [selectedSymbol, holdings]);
  const filteredHoldings = useMemo(() => {
    const q = search.trim().toLowerCase();
    const list = holdings.slice().sort((a, b) => b.market_value - a.market_value);
    if (!q) return list;
    return list.filter((h) => h.symbol.toLowerCase().includes(q));
  }, [holdings, search]);

  // Auto-scroll panels to keep focused date in view
  useEffect(() => {
    if (!lockedDaySec && !hoverDaySec) return;
    const daySec = lockedDaySec ?? hoverDaySec;
    if (!daySec) return;
    const day = new Date(daySec * 1000).toISOString().slice(0, 10);
    let el = document.querySelector<HTMLElement>(`[id^="lot-${day}"]`);
    if (!el) el = document.querySelector<HTMLElement>(`[id^="div-${day}"]`);
    if (el) el.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [lockedDaySec, hoverDaySec]);

  const symbolTx = useMemo(() => {
    if (!selectedSymbol) return [];
    return transactions
      .filter((t) => (t.symbol || '').toUpperCase() === selectedSymbol.toUpperCase())
      .sort((a, b) => (a.date || '').localeCompare(b.date || ''))
      .reverse()
      .slice(0, 50);
  }, [transactions, selectedSymbol]);

  if (loading) {
    return (
      <VStack p={6} spacing={6} align="stretch">
        <HStack justify="space-between">
          <PageHeader title="Workspace" subtitle="Holdings list • Trades and dividends by symbol" />
          <Spinner />
        </HStack>
      </VStack>
    );
  }

  return (
    <VStack p={6} spacing={4} align="stretch">
      <Flex gap={4} align="stretch">
        {/* Left: holdings list */}
        <VStack bg={bgPane} border="1px solid" borderColor={border} borderRadius="md" p={3} spacing={3} align="stretch" w="340px" h="calc(100vh - 2rem)">
          <HStack>
            <InputGroup>
              <InputLeftElement pointerEvents="none">
                <FiSearch color="gray.400" />
              </InputLeftElement>
              <Input placeholder="Search holdings..." value={search} onChange={(e) => setSearch(e.target.value)} />
            </InputGroup>
            <Button size="sm" leftIcon={<FiRefreshCw />} variant="outline" onClick={fetchAll}>
              Refresh
            </Button>
          </HStack>
          <VStack spacing={2} align="stretch" overflowY="auto">
            {filteredHoldings.map((h) => {
              const active = selectedSymbol?.toUpperCase() === h.symbol.toUpperCase();
              const color = h.unrealized_pnl >= 0 ? 'green.400' : 'red.400';
              return (
                <HStack
                  key={h.id}
                  onClick={() => setSelectedSymbol(h.symbol)}
                  cursor="pointer"
                  p={2}
                  borderRadius="md"
                  border="1px solid"
                  borderColor={active ? 'blue.400' : border}
                  _hover={{ bg: hoverBg }}
                >
                  <Box w="8px" h="8px" borderRadius="full" bg="blue.400" />
                  <VStack spacing={0} align="start" flex={1}>
                    <HStack justify="space-between" width="full">
                      <Text fontWeight="bold">{h.symbol}</Text>
                      <Badge colorScheme={h.unrealized_pnl >= 0 ? 'green' : 'red'}>
                        {h.unrealized_pnl_pct.toFixed(2)}%
                      </Badge>
                    </HStack>
                    <HStack justify="space-between" width="full">
                      <Text fontSize="xs" color="gray.500">{h.shares.toLocaleString()} sh</Text>
                      <Text fontSize="xs" color={color}>${Math.abs(h.unrealized_pnl).toLocaleString()}</Text>
                    </HStack>
                  </VStack>
                </HStack>
              );
            })}
          </VStack>
        </VStack>

        {/* Right: detail pane */}
        <VStack flex={1} spacing={4} align="stretch">
          {/* Chart */}
          <Card border="1px solid" borderColor={border} bg={bgPane}>
            <CardHeader pb={2}>
              <HStack justify="space-between">
                <Text fontWeight="bold">{selectedSymbol || '—'}</Text>
                <HStack spacing={3}>
                  <Badge>Live</Badge>
                  <HStack spacing={2}>
                    <Text fontSize="xs" color="gray.500">Advanced</Text>
                    <Button size="xs" variant={showAdvanced ? 'solid' : 'outline'} onClick={() => setShowAdvanced(v => !v)}>
                      {showAdvanced ? 'On' : 'Off'}
                    </Button>
                  </HStack>
                  <HStack spacing={2} opacity={showAdvanced ? 0.4 : 1}>
                    <Text fontSize="xs" color="gray.500">Range</Text>
                    <Button size="xs" isDisabled={showAdvanced} variant={period === '1y' ? 'solid' : 'outline'} onClick={() => { setPeriod('1y'); setZoomYears(1); }}>1y</Button>
                    <Button size="xs" isDisabled={showAdvanced} variant={period === '3y' ? 'solid' : 'outline'} onClick={() => { setPeriod('3y'); setZoomYears(3); }}>3y</Button>
                    <Button size="xs" isDisabled={showAdvanced} variant={period === '5y' ? 'solid' : 'outline'} onClick={() => { setPeriod('5y'); setZoomYears(5); }}>5y</Button>
                    <Button size="xs" isDisabled={showAdvanced} variant={period === 'max' ? 'solid' : 'outline'} onClick={() => { setPeriod('max'); setZoomYears('all'); }}>All</Button>
                  </HStack>
                  <HStack spacing={2}>
                    <Text fontSize="xs" color="gray.500">Trades</Text>
                    <Button size="xs" variant={showTrades ? 'solid' : 'outline'} onClick={() => setShowTrades(v => !v)}>
                      {showTrades ? 'On' : 'Off'}
                    </Button>
                  </HStack>
                  <HStack spacing={2}>
                    <Text fontSize="xs" color="gray.500">Dividends</Text>
                    <Button size="xs" variant={showDividends ? 'solid' : 'outline'} onClick={() => setShowDividends(v => !v)}>
                      {showDividends ? 'On' : 'Off'}
                    </Button>
                  </HStack>
                  <HStack spacing={2}>
                    <Text fontSize="xs" color="gray.500">Line</Text>
                    <Button size="xs" variant={showLine ? 'solid' : 'outline'} onClick={() => setShowLine(v => !v)}>
                      {showLine ? 'On' : 'Off'}
                    </Button>
                  </HStack>
                </HStack>
              </HStack>
              {lockedDaySec && (
                <HStack mt={2} spacing={3}>
                  <Badge colorScheme="purple">Pinned</Badge>
                  <Text fontSize="sm">{new Date(lockedDaySec * 1000).toISOString().slice(0, 10)}</Text>
                  <Button size="xs" variant="outline" onClick={() => setLockedDaySec(null)}>
                    Clear
                  </Button>
                </HStack>
              )}
            </CardHeader>
            <CardBody>
              {selectedSymbol ? (
                showAdvanced ? (
                  <TradingViewChart
                    symbol={selectedSymbol}
                    height={520}
                    showHeader={false}
                    theme="dark"
                  />
                ) : (
                  <SymbolChartWithMarkers
                  height={520}
                  bars={bars}
                  showTrades={showTrades}
                  showDividends={showDividends}
                  onHoverDaySec={setHoverDaySec}
                  onClickDaySec={(t) => setLockedDaySec(prev => (prev === t ? null : t || null))}
                  showLine={showLine}
                  zoomYears={zoomYears}
                  avgPrice={(() => {
                    // Weighted average cost based on lots
                    if (!lots?.length) return undefined;
                    const entries = lots.map(l => ({ cost: Number(l.cost_per_share || 0), sh: Number((l.shares_remaining ?? l.shares) || 0) })).filter(e => e.sh > 0 && e.cost > 0);
                    const totSh = entries.reduce((s, e) => s + e.sh, 0);
                    if (!totSh) return undefined;
                    const wavg = entries.reduce((s, e) => s + e.cost * e.sh, 0) / totSh;
                    return Number.isFinite(wavg) ? wavg : undefined;
                  })()}
                  pinnedDaySec={lockedDaySec}
                  buys={symbolTx
                    .filter(t => {
                      const k = (t.type || t.action || '').toUpperCase();
                      const d = (t.description || '').toUpperCase();
                      return k.includes('BUY') || d.includes('BUY') || d.includes('BOT');
                    })
                    .map(t => {
                      const iso = `${t.date || ''}T${t.time || '13:30:00'}Z`;
                      const fallbackClose = (() => {
                        if (!bars?.length) return 0;
                        const target = new Date(iso).getTime();
                        let best = bars[0];
                        let diff = Math.abs(new Date(bars[0].time).getTime() - target);
                        for (const b of bars) {
                          const d = Math.abs(new Date(b.time).getTime() - target);
                          if (d < diff) {
                            best = b; diff = d;
                          }
                        }
                        return Number(best?.close || 0);
                      })();
                      const price = Number(t.price || 0) || fallbackClose;
                      const qty = Number(t.quantity || 0);
                      return { time: iso, price, type: 'BUY' as const, label: `Buy ${qty} @ ${price.toFixed(2)}` };
                    }).concat(
                      // Tax-lot derived opening purchases (fallback)
                      (lots || []).map((l) => {
                        const iso = `${(l.purchase_date || '').slice(0, 10)}T13:30:00Z`;
                        const price = Number(l.cost_per_share || 0) || 0;
                        const qty = Number((l.shares_remaining ?? l.shares) || 0);
                        return { time: iso, price, type: 'BUY' as const, label: `Buy ${qty} @ ${price.toFixed(2)}` };
                      })
                    )}
                  sells={symbolTx
                    .filter(t => {
                      const k = (t.type || t.action || '').toUpperCase();
                      const d = (t.description || '').toUpperCase();
                      return k.includes('SELL') || k.includes('SLD') || d.includes('SELL') || d.includes('SLD');
                    })
                    .map(t => {
                      const iso = `${t.date || ''}T${t.time || '13:30:00'}Z`;
                      const fallbackClose = (() => {
                        if (!bars?.length) return 0;
                        const target = new Date(iso).getTime();
                        let best = bars[0];
                        let diff = Math.abs(new Date(bars[0].time).getTime() - target);
                        for (const b of bars) {
                          const d = Math.abs(new Date(b.time).getTime() - target);
                          if (d < diff) {
                            best = b; diff = d;
                          }
                        }
                        return Number(best?.close || 0);
                      })();
                      const price = Number(t.price || 0) || fallbackClose;
                      const qty = Number(t.quantity || 0);
                      return { time: iso, price, type: 'SELL' as const, label: `Sell ${qty} @ ${price.toFixed(2)}` };
                    })}
                  dividends={symbolTx
                    .filter(t => {
                      const k = (t.type || t.description || '').toUpperCase();
                      return k.includes('DIV');
                    })
                    .map(t => {
                      const amt = Number(t.amount || 0);
                      return { time: `${t.date || ''}T13:30:00Z`, amount: amt, label: `Div $${amt.toFixed(2)}` };
                    })}
                  />
                )
              ) : <Box h="520px" />}
            </CardBody>
          </Card>

          <SimpleGrid columns={{ base: 1, xl: 2 }} spacing={4}>
            {/* Tax Lots panel (focused on hover) */}
            <Card border="1px solid" borderColor={border} maxH="320px" overflowY="auto" bg={bgPane}>
              <CardHeader pb={2}>
                <HStack justify="space-between">
                  <Text fontWeight="bold">Tax Lots</Text>
                  <Badge variant="outline">{(lots || []).length}</Badge>
                </HStack>
              </CardHeader>
              <CardBody p={0}>
                <Table size="sm" variant="simple">
                  <Thead>
                    <Tr>
                      <Th>Date</Th>
                      <Th isNumeric>Shares</Th>
                      <Th isNumeric>Cost/Share</Th>
                      <Th isNumeric>Cost</Th>
                      <Th isNumeric>Value</Th>
                      <Th isNumeric>P/L</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {(lots || [])
                      .slice()
                      .sort((a, b) => new Date(b.purchase_date || '').getTime() - new Date(a.purchase_date || '').getTime())
                      .map((l, idx) => {
                        const lotDay = (l.purchase_date || '').slice(0, 10);
                        const hoverDay = focusedDaySec ? new Date(focusedDaySec * 1000).toISOString().slice(0, 10) : '';
                        const focused = hoverDay && lotDay === hoverDay;
                        const sh = Number((l.shares_remaining ?? l.shares) || 0);
                        const cps = Number(l.cost_per_share || 0);
                        const cost = sh * cps;
                        const lastClose = bars?.length ? Number(bars[bars.length - 1].close || 0) : 0;
                        const val = sh * lastClose;
                        const pnl = val - cost;
                        return (
                          <Tr id={`lot-${lotDay}-${idx}`} key={`lot-${l.id || idx}`} bg={focused ? useColorModeValue('blue.50', 'blue.900') : undefined}>
                            <Td>{fmtDate(l.purchase_date)}</Td>
                            <Td isNumeric>{sh.toLocaleString()}</Td>
                            <Td isNumeric>{cps ? currencyFmt.format(cps) : '-'}</Td>
                            <Td isNumeric>{cost ? currencyFmt.format(cost) : '-'}</Td>
                            <Td isNumeric>{val ? currencyFmt.format(val) : '-'}</Td>
                            <Td isNumeric style={{ color: pnl >= 0 ? 'var(--chakra-colors-green-400)' as any : 'var(--chakra-colors-red-400)' as any }}>
                              {pnl ? currencyFmt.format(pnl) : '-'}
                            </Td>
                          </Tr>
                        );
                      })}
                  </Tbody>
                </Table>
              </CardBody>
            </Card>

            {/* Dividends (focused on hover) */}
            <Card border="1px solid" borderColor={border} maxH="320px" overflowY="auto" bg={bgPane}>
              <CardHeader pb={2}>
                <HStack justify="space-between">
                  <Text fontWeight="bold">Dividends (received)</Text>
                </HStack>
              </CardHeader>
              <CardBody p={0}>
                <Table size="sm" variant="simple">
                  <Thead>
                    <Tr>
                      <Th>Date</Th>
                      <Th isNumeric>Amount</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {symbolTx
                      .filter((t) => {
                        const k = (t.type || '').toUpperCase();
                        const d = (t.description || '').toUpperCase();
                        return k.includes('DIV') || d.includes('DIV');
                      })
                      .map((t, idx) => {
                        const day = (t.date || '').slice(0, 10);
                        const hoverDay = focusedDaySec ? new Date(focusedDaySec * 1000).toISOString().slice(0, 10) : '';
                        const focused = hoverDay && day === hoverDay;
                        return (
                          <Tr id={`div-${day}-${idx}`} key={`div-${t.id || idx}`} bg={focused ? useColorModeValue('blue.50', 'blue.900') : undefined}>
                            <Td>{fmtDate(t.date)}</Td>
                            <Td isNumeric>{t.amount ? currencyFmt.format(Number(t.amount)) : '-'}</Td>
                          </Tr>
                        );
                      })}
                  </Tbody>
                </Table>
              </CardBody>
            </Card>
          </SimpleGrid>
        </VStack>
      </Flex>
    </VStack>
  );
};

export default PortfolioWorkspace;


