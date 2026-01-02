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
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Input,
  FormControl,
  FormLabel,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  useDisclosure,
  Progress,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Icon,
  Flex,
  Switch,
  Alert,
  AlertIcon,
  AlertDescription,
  useToast,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
} from '@chakra-ui/react';
import {
  FaRocket,
  FaChartLine,
  FaPlay,
  FaPause,
  FaPlus,
  FaCog,
  FaDollarSign,
  FaBrain,
  FaExchangeAlt,
  FaTrendingUp,
  FaShieldAlt
} from 'react-icons/fa';

interface Strategy {
  id?: number;
  name: string;
  type: string;
  description: string;
  category: 'stocks' | 'options';
  complexity: 'beginner' | 'intermediate' | 'advanced';
  minCapital: number;
  expectedReturn: string;
  maxDrawdown: string;
  timeHorizon: string;
  isActive?: boolean;
  isAvailable: boolean;
}

interface ActiveStrategy {
  id: number;
  name: string;
  type: string;
  brokerage: string;
  allocatedCapital: number;
  currentCapital: number;
  totalPnL: number;
  totalPnLPct: number;
  isAutomated: boolean;
  isActive: boolean;
  profitTargetPct: number;
  stopLossPct: number;
  createdAt: string;
}

interface StrategyFormData {
  strategyType: string;
  brokerage: 'ibkr' | 'tastytrade';
  category: 'stocks' | 'options';
  allocatedAmount: number;
  stopLossPct: number;
  profitTargetPct: number;
  reinvestProfitPct: number;
  isAutomated: boolean;
}

const AVAILABLE_STRATEGIES: Strategy[] = [
  {
    name: "ATR Matrix Options",
    type: "atr_matrix_options",
    description: "Automated options trading using ATR Matrix signals with time horizon-based execution. Targets 20% monthly returns.",
    category: "options",
    complexity: "advanced",
    minCapital: 10000,
    expectedReturn: "15-25% monthly",
    maxDrawdown: "8-12%",
    timeHorizon: "1-45 days",
    isAvailable: true
  },
  {
    name: "ATR Matrix Stocks",
    type: "atr_matrix_stocks",
    description: "Stock trading based on ATR Matrix signals with momentum and mean reversion strategies.",
    category: "stocks",
    complexity: "intermediate",
    minCapital: 5000,
    expectedReturn: "12-18% annually",
    maxDrawdown: "5-8%",
    timeHorizon: "3-30 days",
    isAvailable: true
  },
  {
    name: "Momentum Breakout",
    type: "momentum_breakout",
    description: "High-frequency momentum trading with breakout patterns and volume confirmation.",
    category: "stocks",
    complexity: "advanced",
    minCapital: 25000,
    expectedReturn: "20-30% annually",
    maxDrawdown: "10-15%",
    timeHorizon: "1-7 days",
    isAvailable: false
  },
  {
    name: "Iron Condor Weekly",
    type: "iron_condor",
    description: "Weekly iron condor options strategy targeting high-probability, low-risk income generation.",
    category: "options",
    complexity: "intermediate",
    minCapital: 15000,
    expectedReturn: "8-12% monthly",
    maxDrawdown: "6-10%",
    timeHorizon: "3-7 days",
    isAvailable: false
  },
  {
    name: "Covered Call Enhanced",
    type: "covered_call",
    description: "Enhanced covered call strategy with dynamic strike selection and portfolio optimization.",
    category: "options",
    complexity: "beginner",
    minCapital: 50000,
    expectedReturn: "1-3% monthly",
    maxDrawdown: "2-5%",
    timeHorizon: "30-45 days",
    isAvailable: false
  },
  {
    name: "Pair Trading Arbitrage",
    type: "pair_trading",
    description: "Market-neutral pair trading strategy identifying relative value opportunities.",
    category: "stocks",
    complexity: "advanced",
    minCapital: 100000,
    expectedReturn: "10-15% annually",
    maxDrawdown: "3-6%",
    timeHorizon: "5-21 days",
    isAvailable: false
  }
];

const StrategiesManager: React.FC = () => {
  const [activeStrategies, setActiveStrategies] = useState<ActiveStrategy[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<'all' | 'stocks' | 'options'>('all');
  const [selectedComplexity, setSelectedComplexity] = useState<'all' | 'beginner' | 'intermediate' | 'advanced'>('all');
  const [loading, setLoading] = useState(false);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [formData, setFormData] = useState<StrategyFormData>({
    strategyType: '',
    brokerage: 'tastytrade',
    category: 'options',
    allocatedAmount: 10000,
    stopLossPct: 10,
    profitTargetPct: 20,
    reinvestProfitPct: 50,
    isAutomated: true
  });
  const toast = useToast();

  useEffect(() => {
    fetchActiveStrategies();
  }, []);

  const fetchActiveStrategies = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/options/strategies');
      if (response.ok) {
        const data = await response.json();
        setActiveStrategies(data.strategies || []);
      }
    } catch (error) {
      console.error('Error fetching strategies:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleInitializeStrategy = (strategy: Strategy) => {
    setSelectedStrategy(strategy);
    setFormData({
      ...formData,
      strategyType: strategy.type,
      category: strategy.category,
      brokerage: strategy.category === 'options' ? 'tastytrade' : 'ibkr'
    });
    onOpen();
  };

  const handleSubmitStrategy = async () => {
    if (!selectedStrategy) return;

    try {
      setLoading(true);

      let endpoint = '';
      let payload: any = {};

      if (selectedStrategy.type === 'atr_matrix_options') {
        endpoint = '/api/v1/options/strategies/atr-matrix/initialize';
        payload = {
          account_number: 'demo_account', // Replace with actual account selection
          initial_capital: formData.allocatedAmount
        };
      } else {
        // For other strategies, we'll create a generic initialization
        endpoint = '/api/v1/strategies/initialize';
        payload = {
          strategy_type: formData.strategyType,
          brokerage: formData.brokerage,
          allocated_capital: formData.allocatedAmount,
          stop_loss_pct: formData.stopLossPct,
          profit_target_pct: formData.profitTargetPct,
          reinvest_profit_pct: formData.reinvestProfitPct,
          is_automated: formData.isAutomated
        };
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const result = await response.json();
        toast({
          title: "Strategy Initialized!",
          description: `${selectedStrategy.name} has been successfully initialized with $${formData.allocatedAmount.toLocaleString()}.`,
          status: "success",
          duration: 5000,
          isClosable: true,
        });

        onClose();
        fetchActiveStrategies();
      } else {
        throw new Error('Failed to initialize strategy');
      }
    } catch (error) {
      toast({
        title: "Initialization Failed",
        description: "There was an error initializing the strategy. Please try again.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const toggleStrategy = async (strategyId: number, isActive: boolean) => {
    try {
      const response = await fetch(`/api/v1/options/strategies/${strategyId}/toggle`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ active: !isActive }),
      });

      if (response.ok) {
        toast({
          title: `Strategy ${!isActive ? 'Activated' : 'Deactivated'}`,
          status: "success",
          duration: 3000,
          isClosable: true,
        });
        fetchActiveStrategies();
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to toggle strategy",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const getComplexityColor = (complexity: string) => {
    switch (complexity) {
      case 'beginner': return 'green';
      case 'intermediate': return 'orange';
      case 'advanced': return 'red';
      default: return 'gray';
    }
  };

  const getCategoryIcon = (category: string) => {
    return category === 'options' ? FaExchangeAlt : FaChartLine;
  };

  const filteredStrategies = AVAILABLE_STRATEGIES.filter(strategy => {
    const categoryMatch = selectedCategory === 'all' || strategy.category === selectedCategory;
    const complexityMatch = selectedComplexity === 'all' || strategy.complexity === selectedComplexity;
    return categoryMatch && complexityMatch;
  });

  const totalAllocatedCapital = activeStrategies.reduce((sum, strategy) => sum + strategy.allocatedCapital, 0);
  const totalCurrentCapital = activeStrategies.reduce((sum, strategy) => sum + strategy.currentCapital, 0);
  const totalPnL = totalCurrentCapital - totalAllocatedCapital;
  const totalPnLPct = totalAllocatedCapital > 0 ? (totalPnL / totalAllocatedCapital) * 100 : 0;

  return (
    <Box p={6}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box>
          <Heading size="lg" mb={2} display="flex" alignItems="center">
            <Icon as={FaBrain} mr={3} color="purple.500" />
            Strategy Management Center
          </Heading>
          <Text color="gray.600">
            Deploy and manage automated trading strategies across multiple brokerages
          </Text>
        </Box>

        {/* Portfolio Overview */}
        <Card>
          <CardHeader>
            <Heading size="md">Portfolio Overview</Heading>
          </CardHeader>
          <CardBody>
            <SimpleGrid columns={{ base: 2, md: 4 }} spacing={6}>
              <Stat>
                <StatLabel>Total Allocated</StatLabel>
                <StatNumber>${totalAllocatedCapital.toLocaleString()}</StatNumber>
                <StatHelpText>Across {activeStrategies.length} strategies</StatHelpText>
              </Stat>
              <Stat>
                <StatLabel>Current Value</StatLabel>
                <StatNumber>${totalCurrentCapital.toLocaleString()}</StatNumber>
                <StatHelpText>
                  <StatArrow type={totalPnL >= 0 ? 'increase' : 'decrease'} />
                  {totalPnLPct.toFixed(2)}%
                </StatHelpText>
              </Stat>
              <Stat>
                <StatLabel>Total P&L</StatLabel>
                <StatNumber color={totalPnL >= 0 ? 'green.500' : 'red.500'}>
                  ${totalPnL.toLocaleString()}
                </StatNumber>
                <StatHelpText>Unrealized</StatHelpText>
              </Stat>
              <Stat>
                <StatLabel>Active Strategies</StatLabel>
                <StatNumber>{activeStrategies.filter(s => s.isActive).length}</StatNumber>
                <StatHelpText>of {activeStrategies.length} total</StatHelpText>
              </Stat>
            </SimpleGrid>
          </CardBody>
        </Card>

        <Tabs>
          <TabList>
            <Tab>Available Strategies</Tab>
            <Tab>Active Strategies ({activeStrategies.length})</Tab>
          </TabList>

          <TabPanels>
            {/* Available Strategies Tab */}
            <TabPanel>
              <VStack spacing={4} align="stretch">
                {/* Filters */}
                <HStack spacing={4}>
                  <FormControl maxW="200px">
                    <FormLabel>Category</FormLabel>
                    <Select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value as any)}>
                      <option value="all">All Categories</option>
                      <option value="stocks">Stocks</option>
                      <option value="options">Options</option>
                    </Select>
                  </FormControl>
                  <FormControl maxW="200px">
                    <FormLabel>Complexity</FormLabel>
                    <Select value={selectedComplexity} onChange={(e) => setSelectedComplexity(e.target.value as any)}>
                      <option value="all">All Levels</option>
                      <option value="beginner">Beginner</option>
                      <option value="intermediate">Intermediate</option>
                      <option value="advanced">Advanced</option>
                    </Select>
                  </FormControl>
                </HStack>

                {/* Strategy Cards */}
                <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
                  {filteredStrategies.map((strategy, index) => (
                    <Card key={index} opacity={strategy.isAvailable ? 1 : 0.6}>
                      <CardBody>
                        <VStack align="stretch" spacing={4}>
                          <HStack justify="space-between">
                            <HStack>
                              <Icon as={getCategoryIcon(strategy.category)} color="blue.500" />
                              <Heading size="sm">{strategy.name}</Heading>
                            </HStack>
                            <Badge colorScheme={getComplexityColor(strategy.complexity)}>
                              {strategy.complexity}
                            </Badge>
                          </HStack>

                          <Text fontSize="sm" color="gray.600" noOfLines={3}>
                            {strategy.description}
                          </Text>

                          <VStack spacing={2} align="stretch">
                            <HStack justify="space-between">
                              <Text fontSize="xs" color="gray.500">Expected Return:</Text>
                              <Text fontSize="xs" fontWeight="bold" color="green.500">
                                {strategy.expectedReturn}
                              </Text>
                            </HStack>
                            <HStack justify="space-between">
                              <Text fontSize="xs" color="gray.500">Max Drawdown:</Text>
                              <Text fontSize="xs" fontWeight="bold" color="red.500">
                                {strategy.maxDrawdown}
                              </Text>
                            </HStack>
                            <HStack justify="space-between">
                              <Text fontSize="xs" color="gray.500">Time Horizon:</Text>
                              <Text fontSize="xs">{strategy.timeHorizon}</Text>
                            </HStack>
                            <HStack justify="space-between">
                              <Text fontSize="xs" color="gray.500">Min Capital:</Text>
                              <Text fontSize="xs" fontWeight="bold">
                                ${strategy.minCapital.toLocaleString()}
                              </Text>
                            </HStack>
                          </VStack>

                          <Button
                            leftIcon={<FaRocket />}
                            colorScheme="blue"
                            size="sm"
                            isDisabled={!strategy.isAvailable}
                            onClick={() => handleInitializeStrategy(strategy)}
                          >
                            {strategy.isAvailable ? 'Initialize Strategy' : 'Coming Soon'}
                          </Button>
                        </VStack>
                      </CardBody>
                    </Card>
                  ))}
                </SimpleGrid>
              </VStack>
            </TabPanel>

            {/* Active Strategies Tab */}
            <TabPanel>
              <VStack spacing={4} align="stretch">
                {activeStrategies.length === 0 ? (
                  <Alert status="info">
                    <AlertIcon />
                    <AlertDescription>
                      No active strategies yet. Initialize your first strategy from the Available Strategies tab!
                    </AlertDescription>
                  </Alert>
                ) : (
                  <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
                    {activeStrategies.map((strategy) => (
                      <Card key={strategy.id}>
                        <CardBody>
                          <VStack align="stretch" spacing={4}>
                            <HStack justify="space-between">
                              <VStack align="start" spacing={1}>
                                <Heading size="sm">{strategy.name}</Heading>
                                <Badge colorScheme="blue">{strategy.brokerage.toUpperCase()}</Badge>
                              </VStack>
                              <Switch
                                isChecked={strategy.isActive}
                                onChange={() => toggleStrategy(strategy.id, strategy.isActive)}
                                colorScheme="green"
                              />
                            </HStack>

                            <SimpleGrid columns={2} spacing={4}>
                              <Box>
                                <Text fontSize="xs" color="gray.500">Allocated</Text>
                                <Text fontWeight="bold">${strategy.allocatedCapital.toLocaleString()}</Text>
                              </Box>
                              <Box>
                                <Text fontSize="xs" color="gray.500">Current</Text>
                                <Text fontWeight="bold">${strategy.currentCapital.toLocaleString()}</Text>
                              </Box>
                              <Box>
                                <Text fontSize="xs" color="gray.500">P&L</Text>
                                <Text fontWeight="bold" color={strategy.totalPnL >= 0 ? 'green.500' : 'red.500'}>
                                  ${strategy.totalPnL.toLocaleString()}
                                </Text>
                              </Box>
                              <Box>
                                <Text fontSize="xs" color="gray.500">Return</Text>
                                <Text fontWeight="bold" color={strategy.totalPnLPct >= 0 ? 'green.500' : 'red.500'}>
                                  {strategy.totalPnLPct.toFixed(2)}%
                                </Text>
                              </Box>
                            </SimpleGrid>

                            <Progress
                              value={Math.abs(strategy.totalPnLPct)}
                              colorScheme={strategy.totalPnLPct >= 0 ? 'green' : 'red'}
                              size="sm"
                              max={strategy.profitTargetPct}
                            />

                            <HStack justify="space-between">
                              <Badge colorScheme={strategy.isAutomated ? 'green' : 'gray'}>
                                {strategy.isAutomated ? 'Automated' : 'Manual'}
                              </Badge>
                              <Button size="xs" leftIcon={<FaCog />}>
                                Configure
                              </Button>
                            </HStack>
                          </VStack>
                        </CardBody>
                      </Card>
                    ))}
                  </SimpleGrid>
                )}
              </VStack>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </VStack>

      {/* Strategy Initialization Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="lg">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Initialize {selectedStrategy?.name}</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <Text color="gray.600" fontSize="sm">
                {selectedStrategy?.description}
              </Text>

              <SimpleGrid columns={2} spacing={4}>
                <FormControl>
                  <FormLabel>Brokerage</FormLabel>
                  <Select
                    value={formData.brokerage}
                    onChange={(e) => setFormData({ ...formData, brokerage: e.target.value as any })}
                  >
                    <option value="ibkr">Interactive Brokers</option>
                    <option value="tastytrade">Tastytrade</option>
                  </Select>
                </FormControl>

                <FormControl>
                  <FormLabel>Allocated Amount</FormLabel>
                  <NumberInput
                    value={formData.allocatedAmount}
                    onChange={(valueString, valueNumber) =>
                      setFormData({ ...formData, allocatedAmount: valueNumber })
                    }
                    min={selectedStrategy?.minCapital || 1000}
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                </FormControl>

                <FormControl>
                  <FormLabel>Stop Loss %</FormLabel>
                  <NumberInput
                    value={formData.stopLossPct}
                    onChange={(valueString, valueNumber) =>
                      setFormData({ ...formData, stopLossPct: valueNumber })
                    }
                    min={1}
                    max={50}
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                </FormControl>

                <FormControl>
                  <FormLabel>Profit Target %</FormLabel>
                  <NumberInput
                    value={formData.profitTargetPct}
                    onChange={(valueString, valueNumber) =>
                      setFormData({ ...formData, profitTargetPct: valueNumber })
                    }
                    min={5}
                    max={100}
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                </FormControl>

                <FormControl>
                  <FormLabel>Reinvest Profit %</FormLabel>
                  <NumberInput
                    value={formData.reinvestProfitPct}
                    onChange={(valueString, valueNumber) =>
                      setFormData({ ...formData, reinvestProfitPct: valueNumber })
                    }
                    min={0}
                    max={100}
                  >
                    <NumberInputField />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                </FormControl>

                <FormControl display="flex" alignItems="center">
                  <FormLabel mb="0">Automated Execution</FormLabel>
                  <Switch
                    isChecked={formData.isAutomated}
                    onChange={(e) => setFormData({ ...formData, isAutomated: e.target.checked })}
                    colorScheme="green"
                  />
                </FormControl>
              </SimpleGrid>

              <Box p={4} bg="blue.50" borderRadius="md">
                <Text fontSize="sm" fontWeight="bold" mb={2}>Strategy Summary</Text>
                <Text fontSize="xs" color="gray.600">
                  Allocating ${formData.allocatedAmount.toLocaleString()} to {selectedStrategy?.name} on {formData.brokerage.toUpperCase()}
                  with {formData.profitTargetPct}% profit target and {formData.stopLossPct}% stop loss.
                  {formData.reinvestProfitPct > 0 && ` ${formData.reinvestProfitPct}% of profits will be reinvested.`}
                </Text>
              </Box>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleSubmitStrategy}
              isLoading={loading}
              leftIcon={<FaRocket />}
            >
              Initialize Strategy
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default StrategiesManager; 