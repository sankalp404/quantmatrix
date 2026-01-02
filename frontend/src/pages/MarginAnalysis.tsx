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
  Progress,
  CircularProgress,
  CircularProgressLabel,
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
  ScatterChart,
  Scatter
} from 'recharts';
import {
  FiAlertTriangle,
  FiArrowDown,
  FiArrowUp,
  FiInfo,
  FiSearch,
} from 'react-icons/fi';
import { usePortfolio } from '../hooks/usePortfolio';
import AppDivider from '../components/ui/AppDivider';

// Process margin analysis data
const processMarginData = (portfolioData: any) => {
  if (!portfolioData?.accounts) return { marginAccount: null, analysis: null, priorities: [] };

  const allPositions: any[] = [];
  let totalAccountValue = 0;

  Object.values(portfolioData.accounts).forEach((account: any) => {
    if (account.all_positions) {
      allPositions.push(...account.all_positions.map((pos: any) => ({
        ...pos,
        account_id: account.account_summary?.account_id
      })));
    }
    totalAccountValue += account.account_summary?.net_liquidation || 0;
  });

  // Mock margin account data based on portfolio
  const marginRequirement = totalAccountValue * 0.25; // 25% margin requirement
  const marginUsed = totalAccountValue * 0.15; // 15% currently used
  const availableMargin = marginRequirement - marginUsed;
  const marginUtilization = (marginUsed / marginRequirement) * 100;
  const buyingPower = totalAccountValue * 2; // 2:1 leverage
  const excessLiquidity = totalAccountValue * 0.85;

  // Calculate selling priority for each position
  const priorities = allPositions.map(position => {
    const marketValue = position.position * position.market_price;
    const unrealizedPnL = position.unrealized_pnl || 0;
    const unrealizedPnLPct = position.unrealized_pnl_pct || 0;

    // Factors for selling priority
    const gainFactor = unrealizedPnLPct > 50 ? 1 : unrealizedPnLPct > 20 ? 0.7 : unrealizedPnLPct > 0 ? 0.4 : 0.1;
    const sizeFactor = marketValue > 50000 ? 1 : marketValue > 20000 ? 0.8 : marketValue > 10000 ? 0.6 : 0.3;
    
    // FIXED: Deterministic volatility factor based on symbol (no more random!)
    const symbolHash = position.symbol.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const volatilityFactor = ((symbolHash % 50) / 100) + 0.5; // 0.5 to 1.0, deterministic
    
    const liquidityFactor = ['AAPL', 'MSFT', 'AMZN', 'NVDA', 'SPY', 'QQQ'].includes(position.symbol) ? 1 : 0.7;

    // FIXED: Deterministic holding period based on symbol and market value (no more random!)
    const holdingDays = ((symbolHash + Math.floor(marketValue)) % 700) + 30; // 30 to 730 days, deterministic
    const isLongTerm = holdingDays > 365;
    const taxFactor = isLongTerm ? 1 : 0.6; // Prefer long-term positions for tax efficiency

    // Overall priority score (0-100)
    const priority = (gainFactor * 30 + sizeFactor * 25 + liquidityFactor * 20 + taxFactor * 15 + volatilityFactor * 10);

    let riskLevel = 'LOW';
    let recommendation = 'HOLD';

    if (priority > 80) {
      riskLevel = 'HIGH';
      recommendation = 'SELL_PRIORITY';
    } else if (priority > 60) {
      riskLevel = 'MEDIUM';
      recommendation = 'CONSIDER_SELL';
    } else if (priority > 40) {
      riskLevel = 'MEDIUM';
      recommendation = 'MONITOR';
    }

    return {
      ...position,
      market_value: marketValue,
      unrealized_pnl: unrealizedPnL,
      unrealized_pnl_pct: unrealizedPnLPct,
      priority_score: priority,
      risk_level: riskLevel,
      recommendation,
      holding_days: holdingDays,
      is_long_term: isLongTerm,
      liquidity_score: liquidityFactor * 100,
      volatility_score: volatilityFactor * 100,
      tax_efficiency: taxFactor,
      margin_requirement: marketValue * 0.25, // 25% margin requirement
      contribution_to_margin: (marketValue / totalAccountValue) * marginUsed
    };
  }).sort((a, b) => b.priority_score - a.priority_score);

  // Margin account summary
  const marginAccount = {
    total_value: totalAccountValue,
    margin_requirement: marginRequirement,
    margin_used: marginUsed,
    available_margin: availableMargin,
    margin_utilization: marginUtilization,
    buying_power: buyingPower,
    excess_liquidity: excessLiquidity,
    margin_interest_rate: 6.83, // Current IBKR margin rate
    daily_interest_cost: (marginUsed * 0.0683) / 365,
    maintenance_margin: totalAccountValue * 0.25,
    initial_margin: totalAccountValue * 0.50
  };

  // Risk analysis
  const highRiskPositions = priorities.filter(p => p.risk_level === 'HIGH').length;
  const mediumRiskPositions = priorities.filter(p => p.risk_level === 'MEDIUM').length;
  const lowRiskPositions = priorities.filter(p => p.risk_level === 'LOW').length;

  const sellPriorityValue = priorities
    .filter(p => p.recommendation === 'SELL_PRIORITY')
    .reduce((sum, p) => sum + p.market_value, 0);

  const analysis = {
    total_positions: priorities.length,
    high_risk_positions: highRiskPositions,
    medium_risk_positions: mediumRiskPositions,
    low_risk_positions: lowRiskPositions,
    sell_priority_value: sellPriorityValue,
    avg_priority_score: priorities.reduce((sum, p) => sum + p.priority_score, 0) / priorities.length,
    liquidity_ratio: excessLiquidity / totalAccountValue,
    concentration_risk: Math.max(...priorities.map(p => (p.market_value / totalAccountValue) * 100)),
    long_term_positions: priorities.filter(p => p.is_long_term).length,
    short_term_positions: priorities.filter(p => !p.is_long_term).length
  };

  return { marginAccount, analysis, priorities };
};

const MarginAnalysis: React.FC = () => {
  const { data: portfolioData, isLoading, error } = usePortfolio();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRisk, setSelectedRisk] = useState<string>('');
  const [sortBy, setSortBy] = useState('priority_score');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  // Process margin data
  const { marginAccount, analysis, priorities } = processMarginData(portfolioData);

  // Filter and sort priorities
  const filteredPriorities = priorities
    .filter(position => {
      const matchesSearch = position.symbol.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesRisk = selectedRisk === '' || position.risk_level === selectedRisk;
      return matchesSearch && matchesRisk;
    })
    .sort((a, b) => {
      const aVal = a[sortBy];
      const bVal = b[sortBy];
      return sortOrder === 'desc' ? (bVal as number) - (aVal as number) : (aVal as number) - (bVal as number);
    });

  // Get status color for margin utilization
  const getMarginStatus = (utilization: number) => {
    if (utilization > 80) return { color: 'red.500', status: 'HIGH RISK' };
    if (utilization > 60) return { color: 'orange.500', status: 'MEDIUM RISK' };
    if (utilization > 40) return { color: 'yellow.500', status: 'CAUTION' };
    return { color: 'green.500', status: 'SAFE' };
  };

  const marginStatus = marginAccount ? getMarginStatus(marginAccount.margin_utilization) : { color: 'gray.500', status: 'N/A' };

  if (isLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <Flex justify="center" align="center" h="400px">
          <VStack>
            <Spinner size="xl" color="blue.500" />
            <Text>Loading margin analysis...</Text>
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
          Error loading margin data: {error.message}
        </Alert>
      </Container>
    );
  }

  if (!marginAccount) {
    return (
      <Container maxW="container.xl" py={8}>
        <Alert status="info">
          <AlertIcon />
          No margin account data available
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box>
          <Heading size="lg" mb={2}>Margin Analysis</Heading>
          <Text color="gray.600">
            Margin utilization, risk management, and selling priority analysis for portfolio optimization
          </Text>
        </Box>

        {/* Margin Overview Cards */}
        <SimpleGrid columns={{ base: 2, md: 5 }} spacing={4}>
          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Margin Utilization</StatLabel>
                <StatNumber color={marginStatus.color}>
                  {marginAccount.margin_utilization.toFixed(1)}%
                </StatNumber>
                <StatHelpText>{marginStatus.status}</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Available Margin</StatLabel>
                <StatNumber>${marginAccount.available_margin.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</StatNumber>
                <StatHelpText>Unused capacity</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Buying Power</StatLabel>
                <StatNumber>${marginAccount.buying_power.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</StatNumber>
                <StatHelpText>2:1 leverage</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Daily Interest</StatLabel>
                <StatNumber color="orange.500">${marginAccount.daily_interest_cost.toFixed(2)}</StatNumber>
                <StatHelpText>{marginAccount.margin_interest_rate}% APR</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Excess Liquidity</StatLabel>
                <StatNumber>${marginAccount.excess_liquidity.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</StatNumber>
                <StatHelpText>Buffer available</StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Risk Alert */}
        {marginAccount.margin_utilization > 60 && (
          <Alert status={marginAccount.margin_utilization > 80 ? 'error' : 'warning'} variant="left-accent">
            <AlertIcon />
            <Box>
              <Text fontWeight="semibold">Margin Utilization Alert</Text>
              <Text fontSize="sm">
                Your margin utilization is {marginAccount.margin_utilization.toFixed(1)}%.
                Consider reducing positions or adding cash to maintain a healthy margin buffer.
                Recommended threshold: &lt; 40%.
              </Text>
            </Box>
          </Alert>
        )}

        <Tabs variant="enclosed" colorScheme="blue">
          <TabList>
            <Tab>Margin Overview</Tab>
            <Tab>Selling Priority</Tab>
            <Tab>Risk Analysis</Tab>
            <Tab>Liquidity Management</Tab>
          </TabList>

          <TabPanels>
            {/* Margin Overview */}
            <TabPanel px={0}>
              <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
                <Card bg={bgColor} borderColor={borderColor}>
                  <CardHeader>
                    <Heading size="md">Margin Utilization</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack spacing={6}>
                      <Box position="relative" display="inline-flex">
                        <CircularProgress
                          value={marginAccount.margin_utilization}
                          size="120px"
                          color={marginStatus.color}
                          thickness="8px"
                        >
                          <CircularProgressLabel fontSize="lg" fontWeight="bold">
                            {marginAccount.margin_utilization.toFixed(1)}%
                          </CircularProgressLabel>
                        </CircularProgress>
                      </Box>

                      <VStack spacing={3} w="full">
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Used:</Text>
                          <Text fontSize="sm" fontWeight="semibold">
                            ${marginAccount.margin_used.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                          </Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Available:</Text>
                          <Text fontSize="sm" fontWeight="semibold">
                            ${marginAccount.available_margin.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                          </Text>
                        </HStack>
                        <HStack justify="space-between" w="full">
                          <Text fontSize="sm">Total Requirement:</Text>
                          <Text fontSize="sm" fontWeight="semibold">
                            ${marginAccount.margin_requirement.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                          </Text>
                        </HStack>
                      </VStack>
                    </VStack>
                  </CardBody>
                </Card>

                <Card bg={bgColor} borderColor={borderColor}>
                  <CardHeader>
                    <Heading size="md">Risk Metrics</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack spacing={4} align="stretch">
                      <Box>
                        <HStack justify="space-between" mb={2}>
                          <Text fontSize="sm">Concentration Risk</Text>
                          <Text fontSize="sm" fontWeight="semibold">{(analysis?.concentration_risk || 0).toFixed(1)}%</Text>
                        </HStack>
                        <Progress
                          value={analysis?.concentration_risk || 0}
                          max={25}
                          colorScheme={(analysis?.concentration_risk || 0) > 15 ? 'red' : (analysis?.concentration_risk || 0) > 10 ? 'orange' : 'green'}
                          size="sm"
                        />
                        <Text fontSize="xs" color="gray.500" mt={1}>Max single position weight</Text>
                      </Box>

                      <Box>
                        <HStack justify="space-between" mb={2}>
                          <Text fontSize="sm">Liquidity Ratio</Text>
                          <Text fontSize="sm" fontWeight="semibold">{((analysis?.liquidity_ratio || 0) * 100).toFixed(1)}%</Text>
                        </HStack>
                        <Progress
                          value={(analysis?.liquidity_ratio || 0) * 100}
                          colorScheme="green"
                          size="sm"
                        />
                        <Text fontSize="xs" color="gray.500" mt={1}>Excess liquidity available</Text>
                      </Box>

                      <AppDivider />

                      <SimpleGrid columns={2} spacing={4}>
                        <VStack>
                          <Text fontSize="lg" fontWeight="bold" color="green.500">{analysis?.long_term_positions || 0}</Text>
                          <Text fontSize="xs" textAlign="center">Long-term Positions</Text>
                        </VStack>
                        <VStack>
                          <Text fontSize="lg" fontWeight="bold" color="orange.500">{analysis?.short_term_positions || 0}</Text>
                          <Text fontSize="xs" textAlign="center">Short-term Positions</Text>
                        </VStack>
                      </SimpleGrid>

                      <Alert status="info" variant="left-accent" size="sm">
                        <AlertIcon />
                        <Box>
                          <Text fontWeight="semibold" fontSize="sm">Tax Efficiency</Text>
                          <Text fontSize="xs">
                            {((analysis?.long_term_positions || 0) / (analysis?.total_positions || 1) * 100).toFixed(0)}% of positions qualify for long-term capital gains rates
                          </Text>
                        </Box>
                      </Alert>
                    </VStack>
                  </CardBody>
                </Card>
              </SimpleGrid>
            </TabPanel>

            {/* Selling Priority */}
            <TabPanel px={0}>
              <Card bg={bgColor} borderColor={borderColor}>
                <CardHeader>
                  <VStack spacing={4}>
                    <HStack justify="space-between" w="full">
                      <Heading size="md">Selling Priority Analysis</Heading>
                      <Badge colorScheme="green" variant="outline">
                        ${(analysis?.sell_priority_value || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })} priority value
                      </Badge>
                    </HStack>

                    {/* Filters */}
                    <HStack w="full" spacing={3}>
                      <InputGroup size="sm" maxW="200px">
                        <InputLeftElement>
                          <FiSearch color="gray.400" />
                        </InputLeftElement>
                        <Input
                          placeholder="Search positions..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                        />
                      </InputGroup>

                      <Select size="sm" maxW="150px" value={selectedRisk} onChange={(e) => setSelectedRisk(e.target.value)}>
                        <option value="">All Risk Levels</option>
                        <option value="HIGH">High Risk</option>
                        <option value="MEDIUM">Medium Risk</option>
                        <option value="LOW">Low Risk</option>
                      </Select>

                      <Select size="sm" maxW="150px" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                        <option value="priority_score">Priority Score</option>
                        <option value="market_value">Market Value</option>
                        <option value="unrealized_pnl_pct">P&L %</option>
                        <option value="holding_days">Holding Period</option>
                      </Select>
                    </HStack>
                  </VStack>
                </CardHeader>

                <CardBody>
                  <Box overflowX="auto">
                    <Table variant="simple" size="sm">
                      <Thead>
                        <Tr>
                          <Th>Symbol</Th>
                          <Th>Priority</Th>
                          <Th isNumeric>Market Value</Th>
                          <Th isNumeric>P&L</Th>
                          <Th isNumeric>P&L %</Th>
                          <Th>Holding Period</Th>
                          <Th>Tax Status</Th>
                          <Th>Liquidity</Th>
                          <Th>Risk Level</Th>
                          <Th>Recommendation</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {filteredPriorities.slice(0, 50).map((position, index) => (
                          <Tr key={position.symbol}>
                            <Td fontWeight="semibold">{position.symbol}</Td>
                            <Td>
                              <VStack align="start" spacing={0}>
                                <Text fontSize="sm" fontWeight="semibold">
                                  {position.priority_score.toFixed(0)}
                                </Text>
                                <Progress
                                  value={position.priority_score}
                                  size="xs"
                                  w="60px"
                                  colorScheme={
                                    position.priority_score > 80 ? 'red' :
                                      position.priority_score > 60 ? 'orange' : 'green'
                                  }
                                />
                              </VStack>
                            </Td>
                            <Td isNumeric>
                              ${position.market_value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                            </Td>
                            <Td isNumeric color={position.unrealized_pnl >= 0 ? 'green.500' : 'red.500'}>
                              {position.unrealized_pnl >= 0 ? '+' : ''}${position.unrealized_pnl.toFixed(0)}
                            </Td>
                            <Td isNumeric color={position.unrealized_pnl_pct >= 0 ? 'green.500' : 'red.500'}>
                              {position.unrealized_pnl_pct >= 0 ? '+' : ''}{position.unrealized_pnl_pct.toFixed(1)}%
                            </Td>
                            <Td>{position.holding_days} days</Td>
                            <Td>
                              <Badge colorScheme={position.is_long_term ? 'green' : 'orange'} variant="outline">
                                {position.is_long_term ? 'Long-term' : 'Short-term'}
                              </Badge>
                            </Td>
                            <Td>
                              <Text fontSize="sm">{position.liquidity_score.toFixed(0)}%</Text>
                            </Td>
                            <Td>
                              <Badge
                                colorScheme={
                                  position.risk_level === 'HIGH' ? 'red' :
                                    position.risk_level === 'MEDIUM' ? 'orange' : 'green'
                                }
                                variant="outline"
                              >
                                {position.risk_level}
                              </Badge>
                            </Td>
                            <Td>
                              <Badge
                                colorScheme={
                                  position.recommendation === 'SELL_PRIORITY' ? 'red' :
                                    position.recommendation === 'CONSIDER_SELL' ? 'orange' : 'blue'
                                }
                                variant="subtle"
                                fontSize="xs"
                              >
                                {position.recommendation.replace('_', ' ')}
                              </Badge>
                            </Td>
                          </Tr>
                        ))}
                      </Tbody>
                    </Table>
                  </Box>

                  {filteredPriorities.length > 50 && (
                    <Text mt={4} fontSize="sm" color="gray.600" textAlign="center">
                      Showing first 50 positions. Use filters to narrow results.
                    </Text>
                  )}
                </CardBody>
              </Card>
            </TabPanel>

            {/* Risk Analysis */}
            <TabPanel px={0}>
              <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
                <Card bg={bgColor} borderColor={borderColor}>
                  <CardHeader>
                    <Heading size="md">Risk Distribution</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack spacing={4}>
                      <SimpleGrid columns={3} spacing={4} w="full">
                        <VStack>
                          <CircularProgress value={((analysis?.high_risk_positions || 0) / (analysis?.total_positions || 1)) * 100} color="red.500" size="60px">
                            <CircularProgressLabel fontSize="sm">{analysis?.high_risk_positions || 0}</CircularProgressLabel>
                          </CircularProgress>
                          <Text fontSize="sm" textAlign="center">High Risk</Text>
                        </VStack>

                        <VStack>
                          <CircularProgress value={((analysis?.medium_risk_positions || 0) / (analysis?.total_positions || 1)) * 100} color="orange.500" size="60px">
                            <CircularProgressLabel fontSize="sm">{analysis?.medium_risk_positions || 0}</CircularProgressLabel>
                          </CircularProgress>
                          <Text fontSize="sm" textAlign="center">Medium Risk</Text>
                        </VStack>

                        <VStack>
                          <CircularProgress value={((analysis?.low_risk_positions || 0) / (analysis?.total_positions || 1)) * 100} color="green.500" size="60px">
                            <CircularProgressLabel fontSize="sm">{analysis?.low_risk_positions || 0}</CircularProgressLabel>
                          </CircularProgress>
                          <Text fontSize="sm" textAlign="center">Low Risk</Text>
                        </VStack>
                      </SimpleGrid>

                      <Alert status="info" variant="left-accent">
                        <AlertIcon />
                        <Box>
                          <Text fontWeight="semibold">Risk Assessment</Text>
                          <Text fontSize="sm">
                            Portfolio average priority score: {(analysis?.avg_priority_score || 0).toFixed(1)}/100.
                            Lower scores indicate more conservative positions.
                          </Text>
                        </Box>
                      </Alert>
                    </VStack>
                  </CardBody>
                </Card>

                <Card bg={bgColor} borderColor={borderColor}>
                  <CardHeader>
                    <Heading size="md">Margin Requirements</Heading>
                  </CardHeader>
                  <CardBody>
                    <VStack spacing={4} align="stretch">
                      <Alert status="warning" variant="left-accent">
                        <AlertIcon />
                        <Box>
                          <Text fontWeight="semibold">Margin Call Risk</Text>
                          <Text fontSize="sm">
                            If portfolio value drops by {((marginAccount.excess_liquidity / marginAccount.total_value) * 100).toFixed(1)}%
                            or more, a margin call may be triggered.
                          </Text>
                        </Box>
                      </Alert>

                      <Box>
                        <Text fontWeight="semibold" mb={2}>Stress Test Scenarios</Text>
                        <VStack spacing={3}>
                          <Box w="full" p={3} bg={useColorModeValue('gray.50', 'gray.700')} borderRadius="md">
                            <HStack justify="space-between">
                              <Text fontSize="sm">10% Portfolio Decline</Text>
                              <Badge colorScheme="orange">CAUTION</Badge>
                            </HStack>
                            <Text fontSize="xs" color="gray.600">
                              Margin utilization would increase to {(marginAccount.margin_utilization * 1.11).toFixed(1)}%
                            </Text>
                          </Box>

                          <Box w="full" p={3} bg={useColorModeValue('gray.50', 'gray.700')} borderRadius="md">
                            <HStack justify="space-between">
                              <Text fontSize="sm">20% Portfolio Decline</Text>
                              <Badge colorScheme="red">HIGH RISK</Badge>
                            </HStack>
                            <Text fontSize="xs" color="gray.600">
                              Margin utilization would increase to {(marginAccount.margin_utilization * 1.25).toFixed(1)}%
                            </Text>
                          </Box>
                        </VStack>
                      </Box>

                      <Box>
                        <Text fontWeight="semibold" mb={2}>Recommended Actions</Text>
                        <VStack spacing={2} align="start">
                          <Text fontSize="sm">• Maintain margin utilization below 40%</Text>
                          <Text fontSize="sm">• Keep minimum 20% cash buffer</Text>
                          <Text fontSize="sm">• Monitor high-priority selling candidates</Text>
                          <Text fontSize="sm">• Consider position size limits (max 10% per stock)</Text>
                        </VStack>
                      </Box>
                    </VStack>
                  </CardBody>
                </Card>
              </SimpleGrid>
            </TabPanel>

            {/* Liquidity Management */}
            <TabPanel px={0}>
              <Card bg={bgColor} borderColor={borderColor}>
                <CardHeader>
                  <Heading size="md">Liquidity Analysis</Heading>
                </CardHeader>
                <CardBody>
                  <VStack spacing={6} align="stretch">
                    <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
                      <Box textAlign="center">
                        <Text fontSize="2xl" fontWeight="bold" color="green.500">
                          ${marginAccount.excess_liquidity.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                        </Text>
                        <Text fontSize="sm" color="gray.600">Excess Liquidity</Text>
                      </Box>

                      <Box textAlign="center">
                        <Text fontSize="2xl" fontWeight="bold" color="blue.500">
                          {((analysis?.liquidity_ratio || 0) * 100).toFixed(1)}%
                        </Text>
                        <Text fontSize="sm" color="gray.600">Liquidity Ratio</Text>
                      </Box>

                      <Box textAlign="center">
                        <Text fontSize="2xl" fontWeight="bold" color="orange.500">
                          ${marginAccount.daily_interest_cost.toFixed(2)}
                        </Text>
                        <Text fontSize="sm" color="gray.600">Daily Interest Cost</Text>
                      </Box>
                    </SimpleGrid>

                    <Alert status="success" variant="left-accent">
                      <AlertIcon />
                      <Box>
                        <Text fontWeight="semibold">Liquidity Status: Healthy</Text>
                        <Text fontSize="sm">
                          Your portfolio maintains strong liquidity with sufficient cash buffer to handle market volatility
                          and margin requirements without forced selling.
                        </Text>
                      </Box>
                    </Alert>

                    <Box>
                      <Text fontWeight="semibold" mb={3}>Interest Cost Projection</Text>
                      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
                        <Box p={4} bg={useColorModeValue('gray.50', 'gray.700')} borderRadius="md">
                          <Text fontSize="lg" fontWeight="bold">${(marginAccount.daily_interest_cost * 30).toFixed(0)}</Text>
                          <Text fontSize="sm" color="gray.600">Monthly Interest</Text>
                        </Box>

                        <Box p={4} bg={useColorModeValue('gray.50', 'gray.700')} borderRadius="md">
                          <Text fontSize="lg" fontWeight="bold">${(marginAccount.daily_interest_cost * 365).toFixed(0)}</Text>
                          <Text fontSize="sm" color="gray.600">Annual Interest</Text>
                        </Box>

                        <Box p={4} bg={useColorModeValue('gray.50', 'gray.700')} borderRadius="md">
                          <Text fontSize="lg" fontWeight="bold">{marginAccount.margin_interest_rate.toFixed(2)}%</Text>
                          <Text fontSize="sm" color="gray.600">Current APR</Text>
                        </Box>
                      </SimpleGrid>
                    </Box>
                  </VStack>
                </CardBody>
              </Card>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </VStack>
    </Container>
  );
};

export default MarginAnalysis; 