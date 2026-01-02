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
  Switch,
  FormControl,
  FormLabel,
  Stack,
  Progress,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  IconButton,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Textarea,
} from '@chakra-ui/react';
import {
  FiArrowDown,
  FiArrowUp,
  FiChevronDown,
  FiEdit2,
  FiPlus,
  FiSearch,
  FiSettings,
} from 'react-icons/fi';
import {
  FiPlay as PlayIcon,
  FiPause as PauseIcon,
  FiSquare as StopIcon,
  FiBarChart as BarChartIcon,
  FiCalendar as CalendarIcon,
  FiClock as TimeIcon
} from 'react-icons/fi';
import { usePortfolio } from '../hooks/usePortfolio';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell } from 'recharts';

// Mock strategy data
const strategies = [
  {
    id: 'atr_matrix',
    name: 'ATR Matrix Strategy',
    status: 'active',
    description: 'Multi-timeframe ATR analysis for optimal entry/exit points',
    type: 'momentum',
    riskLevel: 'medium',
    config: {
      atrPeriod: 20,
      smoothingFactor: 0.2,
      entryThreshold: 1.5,
      exitThreshold: 0.8,
      maxPositions: 10,
      positionSize: 0.02,
      stopLoss: 0.15,
      takeProfit: 0.30
    },
    performance: {
      totalReturn: 47.3,
      winRate: 72.4,
      maxDrawdown: -8.2,
      sharpeRatio: 2.1,
      calmarRatio: 5.8,
      trades: 127,
      avgHoldTime: '3.2 days'
    },
    recentSignals: [
      { symbol: 'AAPL', action: 'BUY', price: 211.02, confidence: 0.85, timestamp: '2025-07-18 14:30:00' },
      { symbol: 'NVDA', action: 'SELL', price: 172.41, confidence: 0.78, timestamp: '2025-07-18 13:45:00' },
      { symbol: 'MSFT', action: 'BUY', price: 511.74, confidence: 0.92, timestamp: '2025-07-18 12:15:00' },
      { symbol: 'TSLA', action: 'HOLD', price: 428.56, confidence: 0.67, timestamp: '2025-07-18 11:30:00' },
      { symbol: 'AMZN', action: 'BUY', price: 225.98, confidence: 0.81, timestamp: '2025-07-18 10:45:00' }
    ]
  },
  {
    id: 'mean_reversion',
    name: 'Mean Reversion Strategy',
    status: 'paused',
    description: 'Statistical arbitrage based on price mean reversion patterns',
    type: 'mean_reversion',
    riskLevel: 'low',
    config: {
      lookbackPeriod: 50,
      zScoreThreshold: 2.0,
      minVolume: 1000000,
      maxPositions: 5,
      positionSize: 0.015,
      stopLoss: 0.10,
      takeProfit: 0.20
    },
    performance: {
      totalReturn: 23.7,
      winRate: 68.2,
      maxDrawdown: -5.1,
      sharpeRatio: 1.8,
      calmarRatio: 4.6,
      trades: 89,
      avgHoldTime: '5.8 days'
    },
    recentSignals: []
  },
  {
    id: 'momentum_breakout',
    name: 'Momentum Breakout',
    status: 'inactive',
    description: 'Breakout strategy using volume and price momentum indicators',
    type: 'breakout',
    riskLevel: 'high',
    config: {
      volumeThreshold: 2.0,
      priceThreshold: 0.05,
      confirmationPeriods: 3,
      maxPositions: 8,
      positionSize: 0.025,
      stopLoss: 0.20,
      takeProfit: 0.40
    },
    performance: {
      totalReturn: 62.1,
      winRate: 64.3,
      maxDrawdown: -12.4,
      sharpeRatio: 1.9,
      calmarRatio: 5.0,
      trades: 156,
      avgHoldTime: '2.1 days'
    },
    recentSignals: []
  }
];

// Performance chart data
const performanceData = [
  { date: '2024-07', atr: 100, mean: 100, momentum: 100 },
  { date: '2024-08', atr: 103.2, mean: 101.8, momentum: 98.5 },
  { date: '2024-09', atr: 107.1, mean: 103.5, momentum: 105.2 },
  { date: '2024-10', atr: 112.4, mean: 105.1, momentum: 108.7 },
  { date: '2024-11', atr: 118.7, mean: 107.3, momentum: 115.4 },
  { date: '2024-12', atr: 125.9, mean: 109.8, momentum: 122.1 },
  { date: '2025-01', atr: 133.4, mean: 112.5, momentum: 128.9 },
  { date: '2025-02', atr: 139.8, mean: 115.2, momentum: 135.6 },
  { date: '2025-03', atr: 142.1, mean: 117.8, momentum: 140.2 },
  { date: '2025-04', atr: 146.5, mean: 120.1, momentum: 147.3 },
  { date: '2025-05', atr: 144.2, mean: 122.4, momentum: 151.8 },
  { date: '2025-06', atr: 147.3, mean: 123.7, momentum: 162.1 }
];

const Strategies: React.FC = () => {
  const { data: portfolioData, isLoading } = usePortfolio();
  const [selectedStrategy, setSelectedStrategy] = useState<string>('atr_matrix');
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [editingStrategy, setEditingStrategy] = useState<any>(null);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const filteredStrategies = strategies.filter(strategy => {
    const matchesSearch = strategy.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      strategy.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === '' || strategy.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const currentStrategy = strategies.find(s => s.id === selectedStrategy) || strategies[0];

  // Get status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'green';
      case 'paused': return 'yellow';
      case 'inactive': return 'gray';
      default: return 'gray';
    }
  };

  // Get risk color
  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'green';
      case 'medium': return 'yellow';
      case 'high': return 'red';
      default: return 'gray';
    }
  };

  // Handle strategy action
  const handleStrategyAction = (strategyId: string, action: string) => {
    // In real implementation, this would call the backend API
    console.log(`${action} strategy ${strategyId}`);
  };

  // Open edit modal
  const openEditModal = (strategy: any) => {
    setEditingStrategy(strategy);
    onOpen();
  };

  if (isLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <Flex justify="center" align="center" h="400px">
          <VStack>
            <Spinner size="xl" color="blue.500" />
            <Text>Loading strategies...</Text>
          </VStack>
        </Flex>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box>
          <HStack justify="space-between" mb={2}>
            <HStack>
              <Heading size="lg">Strategy Management</Heading>
              <Badge colorScheme="blue" variant="solid" borderRadius="full">
                {strategies.filter(s => s.status === 'active').length} Active
              </Badge>
            </HStack>
            <HStack>
              <Button size="sm" colorScheme="blue" leftIcon={<FiPlus />}>
                New Strategy
              </Button>
              <Menu>
                <MenuButton as={IconButton} icon={<FiSettings />} size="sm" variant="outline" />
                <MenuList>
                  <MenuItem>Global Settings</MenuItem>
                  <MenuItem>Risk Management</MenuItem>
                  <MenuItem>Backtesting Config</MenuItem>
                  <MenuItem>Export Results</MenuItem>
                </MenuList>
              </Menu>
            </HStack>
          </HStack>
          <Text color="gray.600">
            Automated trading strategies with real-time monitoring and backtesting
          </Text>
        </Box>

        {/* Strategy Overview Cards */}
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Total Strategies</StatLabel>
                <StatNumber>{strategies.length}</StatNumber>
                <StatHelpText>
                  <HStack>
                    <Text color="green.500">{strategies.filter(s => s.status === 'active').length} active</Text>
                    <Text>•</Text>
                    <Text color="yellow.500">{strategies.filter(s => s.status === 'paused').length} paused</Text>
                  </HStack>
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Combined Performance</StatLabel>
                <StatNumber color="green.500">+34.7%</StatNumber>
                <StatHelpText>
                  <HStack>
                    <FiArrowUp color="green.500" />
                    <Text>YTD return</Text>
                  </HStack>
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Total Signals</StatLabel>
                <StatNumber>1,247</StatNumber>
                <StatHelpText>
                  <HStack>
                    <Text color="green.500">72% win rate</Text>
                    <Text>•</Text>
                    <Text>156 this month</Text>
                  </HStack>
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        <Tabs variant="enclosed" colorScheme="blue">
          <TabList>
            <Tab>Active Strategies</Tab>
            <Tab>Performance Analysis</Tab>
            <Tab>Signal History</Tab>
            <Tab>Backtesting</Tab>
          </TabList>

          <TabPanels>
            {/* Active Strategies */}
            <TabPanel px={0}>
              <Card bg={bgColor} borderColor={borderColor}>
                <CardHeader>
                  <HStack justify="space-between">
                    <Heading size="md">Strategy Management</Heading>
                    <HStack>
                      <InputGroup size="sm" maxW="200px">
                        <InputLeftElement>
                          <FiSearch color="gray.400" />
                        </InputLeftElement>
                        <Input
                          placeholder="Search strategies..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                        />
                      </InputGroup>
                      <Select size="sm" maxW="120px" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                        <option value="">All Status</option>
                        <option value="active">Active</option>
                        <option value="paused">Paused</option>
                        <option value="inactive">Inactive</option>
                      </Select>
                    </HStack>
                  </HStack>
                </CardHeader>

                <CardBody>
                  <VStack spacing={4} align="stretch">
                    {filteredStrategies.map((strategy) => (
                      <Box
                        key={strategy.id}
                        p={4}
                        border="1px solid"
                        borderColor={borderColor}
                        borderRadius="md"
                        bg={strategy.id === selectedStrategy ? useColorModeValue('blue.50', 'blue.900') : bgColor}
                        cursor="pointer"
                        onClick={() => setSelectedStrategy(strategy.id)}
                      >
                        <HStack justify="space-between" align="start">
                          <VStack align="start" spacing={2} flex={1}>
                            <HStack>
                              <Text fontWeight="semibold" fontSize="lg">
                                {strategy.name}
                              </Text>
                              <Badge colorScheme={getStatusColor(strategy.status)} variant="solid">
                                {strategy.status.toUpperCase()}
                              </Badge>
                              <Badge colorScheme={getRiskColor(strategy.riskLevel)} variant="outline">
                                {strategy.riskLevel.toUpperCase()} RISK
                              </Badge>
                              <Badge variant="outline">{strategy.type}</Badge>
                            </HStack>

                            <Text fontSize="sm" color="gray.600">
                              {strategy.description}
                            </Text>

                            <SimpleGrid columns={5} spacing={4} w="full">
                              <Box>
                                <Text fontSize="xs" color="gray.500">Total Return</Text>
                                <Text fontSize="sm" fontWeight="semibold" color="green.500">
                                  +{strategy.performance.totalReturn}%
                                </Text>
                              </Box>
                              <Box>
                                <Text fontSize="xs" color="gray.500">Win Rate</Text>
                                <Text fontSize="sm" fontWeight="semibold">
                                  {strategy.performance.winRate}%
                                </Text>
                              </Box>
                              <Box>
                                <Text fontSize="xs" color="gray.500">Sharpe Ratio</Text>
                                <Text fontSize="sm" fontWeight="semibold">
                                  {strategy.performance.sharpeRatio}
                                </Text>
                              </Box>
                              <Box>
                                <Text fontSize="xs" color="gray.500">Trades</Text>
                                <Text fontSize="sm" fontWeight="semibold">
                                  {strategy.performance.trades}
                                </Text>
                              </Box>
                              <Box>
                                <Text fontSize="xs" color="gray.500">Avg Hold</Text>
                                <Text fontSize="sm" fontWeight="semibold">
                                  {strategy.performance.avgHoldTime}
                                </Text>
                              </Box>
                            </SimpleGrid>
                          </VStack>

                          <VStack>
                            <HStack>
                              {strategy.status === 'active' ? (
                                <Button
                                  size="sm"
                                  colorScheme="red"
                                  variant="outline"
                                  leftIcon={<Icon as={PauseIcon} />}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleStrategyAction(strategy.id, 'pause');
                                  }}
                                >
                                  Pause
                                </Button>
                              ) : (
                                <Button
                                  size="sm"
                                  colorScheme="green"
                                  variant="outline"
                                  leftIcon={<Icon as={PlayIcon} />}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleStrategyAction(strategy.id, 'start');
                                  }}
                                >
                                  Start
                                </Button>
                              )}
                              <IconButton
                                aria-label="Edit strategy"
                                icon={<FiEdit2 />}
                                size="sm"
                                variant="outline"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openEditModal(strategy);
                                }}
                              />
                            </HStack>
                          </VStack>
                        </HStack>
                      </Box>
                    ))}
                  </VStack>
                </CardBody>
              </Card>
            </TabPanel>

            {/* Performance Analysis */}
            <TabPanel px={0}>
              <VStack spacing={6}>
                <Card bg={bgColor} borderColor={borderColor} w="full">
                  <CardHeader>
                    <Heading size="md">Strategy Performance Comparison</Heading>
                  </CardHeader>
                  <CardBody>
                    <Box h="400px">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={performanceData}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="date" />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Line
                            type="monotone"
                            dataKey="atr"
                            stroke="#3182ce"
                            strokeWidth={3}
                            name="ATR Matrix"
                          />
                          <Line
                            type="monotone"
                            dataKey="mean"
                            stroke="#38a169"
                            strokeWidth={2}
                            name="Mean Reversion"
                          />
                          <Line
                            type="monotone"
                            dataKey="momentum"
                            stroke="#e53e3e"
                            strokeWidth={2}
                            name="Momentum Breakout"
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </Box>
                  </CardBody>
                </Card>

                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6} w="full">
                  <Card bg={bgColor} borderColor={borderColor}>
                    <CardHeader>
                      <Heading size="md">Risk Metrics</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={4}>
                        {strategies.map((strategy) => (
                          <Box key={strategy.id} w="full">
                            <HStack justify="space-between" mb={1}>
                              <Text fontSize="sm" fontWeight="medium">{strategy.name}</Text>
                              <Text fontSize="sm" color="red.500">
                                {strategy.performance.maxDrawdown}%
                              </Text>
                            </HStack>
                            <Progress
                              value={Math.abs(strategy.performance.maxDrawdown)}
                              max={15}
                              colorScheme="red"
                              size="sm"
                            />
                          </Box>
                        ))}
                      </VStack>
                    </CardBody>
                  </Card>

                  <Card bg={bgColor} borderColor={borderColor}>
                    <CardHeader>
                      <Heading size="md">Strategy Allocation</Heading>
                    </CardHeader>
                    <CardBody>
                      <VStack spacing={4}>
                        {strategies.map((strategy, index) => {
                          const colors = ['#3182ce', '#38a169', '#e53e3e'];
                          const allocation = [45, 30, 25][index];
                          return (
                            <Box key={strategy.id} w="full">
                              <HStack justify="space-between" mb={1}>
                                <HStack>
                                  <Box w="12px" h="12px" bg={colors[index]} borderRadius="full" />
                                  <Text fontSize="sm" fontWeight="medium">{strategy.name}</Text>
                                </HStack>
                                <Text fontSize="sm" fontWeight="semibold">
                                  {allocation}%
                                </Text>
                              </HStack>
                              <Progress
                                value={allocation}
                                colorScheme={['blue', 'green', 'red'][index]}
                                size="sm"
                              />
                            </Box>
                          );
                        })}
                      </VStack>
                    </CardBody>
                  </Card>
                </SimpleGrid>
              </VStack>
            </TabPanel>

            {/* Signal History */}
            <TabPanel px={0}>
              <Card bg={bgColor} borderColor={borderColor}>
                <CardHeader>
                  <HStack justify="space-between">
                    <Heading size="md">Recent Signals - {currentStrategy.name}</Heading>
                    <HStack>
                      <Text fontSize="sm" color="gray.600">
                        Last updated: {new Date().toLocaleTimeString()}
                      </Text>
                      <Button size="sm" variant="outline">
                        Refresh
                      </Button>
                    </HStack>
                  </HStack>
                </CardHeader>
                <CardBody>
                  {currentStrategy.recentSignals.length > 0 ? (
                    <TableContainer>
                      <Table variant="simple" size="sm">
                        <Thead>
                          <Tr>
                            <Th>Symbol</Th>
                            <Th>Action</Th>
                            <Th>Price</Th>
                            <Th>Confidence</Th>
                            <Th>Timestamp</Th>
                            <Th>Status</Th>
                          </Tr>
                        </Thead>
                        <Tbody>
                          {currentStrategy.recentSignals.map((signal, index) => (
                            <Tr key={index}>
                              <Td fontWeight="semibold">{signal.symbol}</Td>
                              <Td>
                                <Badge
                                  colorScheme={
                                    signal.action === 'BUY' ? 'green' :
                                      signal.action === 'SELL' ? 'red' : 'gray'
                                  }
                                >
                                  {signal.action}
                                </Badge>
                              </Td>
                              <Td>${signal.price.toFixed(2)}</Td>
                              <Td>
                                <HStack>
                                  <Progress
                                    value={signal.confidence * 100}
                                    size="sm"
                                    colorScheme={signal.confidence > 0.8 ? 'green' : signal.confidence > 0.6 ? 'yellow' : 'red'}
                                    w="50px"
                                  />
                                  <Text fontSize="xs">{(signal.confidence * 100).toFixed(0)}%</Text>
                                </HStack>
                              </Td>
                              <Td fontSize="xs" color="gray.500">{signal.timestamp}</Td>
                              <Td>
                                <Badge variant="outline" colorScheme="blue">
                                  Active
                                </Badge>
                              </Td>
                            </Tr>
                          ))}
                        </Tbody>
                      </Table>
                    </TableContainer>
                  ) : (
                    <Alert status="info">
                      <AlertIcon />
                      No recent signals for this strategy
                    </Alert>
                  )}
                </CardBody>
              </Card>
            </TabPanel>

            {/* Backtesting */}
            <TabPanel px={0}>
              <VStack spacing={6}>
                <Card bg={bgColor} borderColor={borderColor} w="full">
                  <CardHeader>
                    <Heading size="md">Backtesting Configuration</Heading>
                  </CardHeader>
                  <CardBody>
                    <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
                      <FormControl>
                        <FormLabel>Start Date</FormLabel>
                        <Input type="date" defaultValue="2024-01-01" />
                      </FormControl>
                      <FormControl>
                        <FormLabel>End Date</FormLabel>
                        <Input type="date" defaultValue="2024-12-31" />
                      </FormControl>
                      <FormControl>
                        <FormLabel>Initial Capital</FormLabel>
                        <NumberInput defaultValue={100000}>
                          <NumberInputField />
                          <NumberInputStepper>
                            <NumberIncrementStepper />
                            <NumberDecrementStepper />
                          </NumberInputStepper>
                        </NumberInput>
                      </FormControl>
                    </SimpleGrid>
                    <HStack mt={4}>
                      <Button colorScheme="blue" leftIcon={<Icon as={PlayIcon} />}>
                        Run Backtest
                      </Button>
                      <Button variant="outline">
                        Load Preset
                      </Button>
                    </HStack>
                  </CardBody>
                </Card>

                <Card bg={bgColor} borderColor={borderColor} w="full">
                  <CardHeader>
                    <Heading size="md">Backtest Results Summary</Heading>
                  </CardHeader>
                  <CardBody>
                    <SimpleGrid columns={{ base: 2, md: 4 }} spacing={6}>
                      <Stat>
                        <StatLabel>Total Return</StatLabel>
                        <StatNumber color="green.500">+{currentStrategy.performance.totalReturn}%</StatNumber>
                        <StatHelpText>vs {((currentStrategy.performance.totalReturn * 0.6)).toFixed(1)}% benchmark</StatHelpText>
                      </Stat>
                      <Stat>
                        <StatLabel>Sharpe Ratio</StatLabel>
                        <StatNumber>{currentStrategy.performance.sharpeRatio}</StatNumber>
                        <StatHelpText>Risk-adjusted return</StatHelpText>
                      </Stat>
                      <Stat>
                        <StatLabel>Max Drawdown</StatLabel>
                        <StatNumber color="red.500">{currentStrategy.performance.maxDrawdown}%</StatNumber>
                        <StatHelpText>Worst peak-to-trough</StatHelpText>
                      </Stat>
                      <Stat>
                        <StatLabel>Win Rate</StatLabel>
                        <StatNumber>{currentStrategy.performance.winRate}%</StatNumber>
                        <StatHelpText>{currentStrategy.performance.trades} total trades</StatHelpText>
                      </Stat>
                    </SimpleGrid>
                  </CardBody>
                </Card>
              </VStack>
            </TabPanel>
          </TabPanels>
        </Tabs>

        {/* Strategy Configuration Modal */}
        <Modal isOpen={isOpen} onClose={onClose} size="xl">
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>
              {editingStrategy ? `Configure ${editingStrategy.name}` : 'Create New Strategy'}
            </ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              {editingStrategy && (
                <VStack spacing={4} align="stretch">
                  <FormControl>
                    <FormLabel>Strategy Name</FormLabel>
                    <Input defaultValue={editingStrategy.name} />
                  </FormControl>

                  <FormControl>
                    <FormLabel>Description</FormLabel>
                    <Textarea defaultValue={editingStrategy.description} />
                  </FormControl>

                  <SimpleGrid columns={2} spacing={4}>
                    <FormControl>
                      <FormLabel>Position Size (%)</FormLabel>
                      <NumberInput defaultValue={editingStrategy.config.positionSize * 100} min={0.1} max={10}>
                        <NumberInputField />
                        <NumberInputStepper>
                          <NumberIncrementStepper />
                          <NumberDecrementStepper />
                        </NumberInputStepper>
                      </NumberInput>
                    </FormControl>

                    <FormControl>
                      <FormLabel>Max Positions</FormLabel>
                      <NumberInput defaultValue={editingStrategy.config.maxPositions} min={1} max={50}>
                        <NumberInputField />
                        <NumberInputStepper>
                          <NumberIncrementStepper />
                          <NumberDecrementStepper />
                        </NumberInputStepper>
                      </NumberInput>
                    </FormControl>
                  </SimpleGrid>

                  <SimpleGrid columns={2} spacing={4}>
                    <FormControl>
                      <FormLabel>Stop Loss (%)</FormLabel>
                      <NumberInput defaultValue={editingStrategy.config.stopLoss * 100} min={1} max={50}>
                        <NumberInputField />
                        <NumberInputStepper>
                          <NumberIncrementStepper />
                          <NumberDecrementStepper />
                        </NumberInputStepper>
                      </NumberInput>
                    </FormControl>

                    <FormControl>
                      <FormLabel>Take Profit (%)</FormLabel>
                      <NumberInput defaultValue={editingStrategy.config.takeProfit * 100} min={5} max={100}>
                        <NumberInputField />
                        <NumberInputStepper>
                          <NumberIncrementStepper />
                          <NumberDecrementStepper />
                        </NumberInputStepper>
                      </NumberInput>
                    </FormControl>
                  </SimpleGrid>

                  {editingStrategy.id === 'atr_matrix' && (
                    <SimpleGrid columns={2} spacing={4}>
                      <FormControl>
                        <FormLabel>ATR Period</FormLabel>
                        <NumberInput defaultValue={editingStrategy.config.atrPeriod} min={5} max={50}>
                          <NumberInputField />
                          <NumberInputStepper>
                            <NumberIncrementStepper />
                            <NumberDecrementStepper />
                          </NumberInputStepper>
                        </NumberInput>
                      </FormControl>

                      <FormControl>
                        <FormLabel>Entry Threshold</FormLabel>
                        <NumberInput defaultValue={editingStrategy.config.entryThreshold} min={0.5} max={3.0} step={0.1}>
                          <NumberInputField />
                          <NumberInputStepper>
                            <NumberIncrementStepper />
                            <NumberDecrementStepper />
                          </NumberInputStepper>
                        </NumberInput>
                      </FormControl>
                    </SimpleGrid>
                  )}
                </VStack>
              )}
            </ModalBody>

            <ModalFooter>
              <Button variant="ghost" mr={3} onClick={onClose}>
                Cancel
              </Button>
              <Button colorScheme="blue">
                Save Configuration
              </Button>
            </ModalFooter>
          </ModalContent>
        </Modal>
      </VStack>
    </Container>
  );
};

export default Strategies; 