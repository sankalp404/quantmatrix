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
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  IconButton,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Alert,
  AlertIcon,
  AlertDescription,
  useToast,
  Flex,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Tooltip,
  Switch,
  useColorModeValue,
} from '@chakra-ui/react';
import {
  FaPlus,
  FaEdit,
  FaTrash,
  FaEllipsisV,
  FaChartPie,
  FaExchangeAlt,
  FaBalanceScale,
  FaTarget,
  FaTrendingUp,
  FaTrendingDown,
  FaInfoCircle,
} from 'react-icons/fa';

interface Category {
  id: string;
  name: string;
  description: string;
  targetAllocation: number; // Percentage
  currentValue: number;
  currentAllocation: number; // Percentage
  color: string;
  holdings: Holding[];
  isCore?: boolean; // Core categories cannot be deleted
}

interface Holding {
  id: string;
  symbol: string;
  name: string;
  value: number;
  categoryId: string | null;
  brokerage: 'ibkr' | 'tastytrade';
  type: 'stock' | 'option' | 'etf' | 'crypto';
  sector: string;
}

interface AllocationRecommendation {
  categoryId: string;
  categoryName: string;
  action: 'buy' | 'sell' | 'rebalance';
  amount: number;
  reason: string;
}

const DEFAULT_CATEGORIES: Omit<Category, 'id' | 'currentValue' | 'currentAllocation' | 'holdings'>[] = [
  {
    name: 'Growth Stocks',
    description: 'High-growth technology and growth-oriented companies',
    targetAllocation: 40,
    color: '#4299E1',
    isCore: true,
  },
  {
    name: 'Value Stocks',
    description: 'Undervalued dividend-paying and stable companies',
    targetAllocation: 25,
    color: '#48BB78',
    isCore: true,
  },
  {
    name: 'Options Strategies',
    description: 'Options positions and derivative strategies',
    targetAllocation: 15,
    color: '#ED8936',
    isCore: true,
  },
  {
    name: 'International',
    description: 'International and emerging market exposure',
    targetAllocation: 10,
    color: '#9F7AEA',
    isCore: true,
  },
  {
    name: 'Cash & Bonds',
    description: 'Cash, bonds, and fixed-income investments',
    targetAllocation: 10,
    color: '#38B2AC',
    isCore: true,
  },
];

const CATEGORY_COLORS = [
  '#4299E1', '#48BB78', '#ED8936', '#9F7AEA', '#38B2AC',
  '#F56565', '#EC407A', '#66BB6A', '#42A5F5', '#AB47BC'
];

const PortfolioCategories: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [unassignedHoldings, setUnassignedHoldings] = useState<Holding[]>([]);
  const [totalPortfolioValue, setTotalPortfolioValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);
  const [categoryFormData, setCategoryFormData] = useState({
    name: '',
    description: '',
    targetAllocation: 0,
    color: CATEGORY_COLORS[0],
  });
  const [allocationRecommendations, setAllocationRecommendations] = useState<AllocationRecommendation[]>([]);

  const { isOpen: isCategoryModalOpen, onOpen: onCategoryModalOpen, onClose: onCategoryModalClose } = useDisclosure();
  const { isOpen: isAssignModalOpen, onOpen: onAssignModalOpen, onClose: onAssignModalClose } = useDisclosure();
  const { isOpen: isRebalanceModalOpen, onOpen: onRebalanceModalOpen, onClose: onRebalanceModalClose } = useDisclosure();

  const toast = useToast();
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  useEffect(() => {
    initializeData();
  }, []);

  useEffect(() => {
    calculateAllocationRecommendations();
  }, [categories, totalPortfolioValue]);

  const initializeData = async () => {
    setLoading(true);
    try {
      // Initialize with default categories if none exist
      const initialCategories = DEFAULT_CATEGORIES.map((cat, index) => ({
        ...cat,
        id: `category-${index + 1}`,
        currentValue: 0,
        currentAllocation: 0,
        holdings: [],
      }));

      setCategories(initialCategories);

      // Fetch real portfolio data
      await fetchPortfolioData();
    } catch (error) {
      console.error('Error initializing categories:', error);
      toast({
        title: 'Error',
        description: 'Failed to initialize portfolio categories',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchPortfolioData = async () => {
    try {
      // Fetch IBKR data
      const ibkrResponse = await fetch('/api/v1/portfolio/live');
      const mockHoldings: Holding[] = [];
      let totalValue = 0;

      if (ibkrResponse.ok) {
        const ibkrData = await ibkrResponse.json();

        if (ibkrData.status === 'success' && ibkrData.data.accounts) {
          Object.entries(ibkrData.data.accounts).forEach(([accountId, accountData]: [string, any]) => {
            if ('error' in accountData) return;

            const positions = accountData.all_positions || [];
            positions.forEach((pos: any, positionIndex: number) => {
              if (pos.position && pos.position !== 0) {
                const holding: Holding = {
                  id: `ibkr-${pos.symbol}-${accountId}-${pos.contract_type || 'STK'}-${positionIndex}-${Math.round(pos.avg_cost || 0)}`, // FIXED: Add position index and avg_cost for complete uniqueness
                  symbol: pos.symbol,
                  name: pos.symbol,
                  value: pos.position_value || 0,
                  categoryId: null, // Initially unassigned
                  brokerage: 'ibkr',
                  type: 'stock',
                  sector: pos.sector || 'Unknown',
                };
                mockHoldings.push(holding);
                totalValue += holding.value;
              }
            });
          });
        }
      }

      // Fetch Tastytrade data - handle gracefully if API doesn't exist
      try {
        const tastytradeResponse = await fetch('/api/v1/options/accounts');
        if (tastytradeResponse.ok) {
          const tastytradeData = await tastytradeResponse.json();

          if (tastytradeData.status === 'success' && tastytradeData.data?.positions) {
            tastytradeData.data.positions.forEach((position: any) => {
              const holding: Holding = {
                id: `tastytrade-${position.symbol}`,
                symbol: position.symbol,
                name: position.instrument?.underlying_symbol ?
                  `${position.instrument.underlying_symbol} ${position.instrument.expiration_date} $${position.instrument.strike_price} ${position.instrument.option_type}` :
                  position.symbol,
                value: position.mark || 0,
                categoryId: null,
                brokerage: 'tastytrade',
                type: position.instrument?.instrument_type === 'Equity Option' ? 'option' : 'stock',
                sector: 'Options',
              };
              mockHoldings.push(holding);
              totalValue += holding.value;
            });
          }
        } else if (tastytradeResponse.status === 404) {
          // Silently handle missing options API - don't log error
          console.debug('Options API not available - continuing without Tastytrade data');
        }
      } catch (error) {
        // Silently handle network errors for options API
        console.debug('Tastytrade API unavailable:', error);
      }

      setHoldings(mockHoldings);
      setUnassignedHoldings(mockHoldings.filter(h => !h.categoryId));
      setTotalPortfolioValue(totalValue);

      // Update category current values
      updateCategoryValues(mockHoldings);

    } catch (error) {
      console.error('Error fetching portfolio data:', error);
    }
  };

  const updateCategoryValues = (holdingsData: Holding[]) => {
    setCategories(prevCategories =>
      prevCategories.map(category => {
        const categoryHoldings = holdingsData.filter(h => h.categoryId === category.id);
        const currentValue = categoryHoldings.reduce((sum, h) => sum + h.value, 0);
        const currentAllocation = totalPortfolioValue > 0 ? (currentValue / totalPortfolioValue) * 100 : 0;

        return {
          ...category,
          holdings: categoryHoldings,
          currentValue,
          currentAllocation,
        };
      })
    );
  };

  const calculateAllocationRecommendations = () => {
    const recommendations: AllocationRecommendation[] = [];

    categories.forEach(category => {
      const allocationDiff = category.currentAllocation - category.targetAllocation;
      const valueDiff = (allocationDiff / 100) * totalPortfolioValue;

      if (Math.abs(allocationDiff) > 2) { // 2% threshold
        recommendations.push({
          categoryId: category.id,
          categoryName: category.name,
          action: allocationDiff > 0 ? 'sell' : 'buy',
          amount: Math.abs(valueDiff),
          reason: allocationDiff > 0
            ? `${allocationDiff.toFixed(1)}% overweight`
            : `${Math.abs(allocationDiff).toFixed(1)}% underweight`,
        });
      }
    });

    setAllocationRecommendations(recommendations);
  };

  const createCategory = () => {
    const newCategory: Category = {
      id: `category-${Date.now()}`,
      ...categoryFormData,
      currentValue: 0,
      currentAllocation: 0,
      holdings: [],
    };

    setCategories(prev => [...prev, newCategory]);
    setCategoryFormData({
      name: '',
      description: '',
      targetAllocation: 0,
      color: CATEGORY_COLORS[0],
    });
    onCategoryModalClose();

    toast({
      title: 'Category Created',
      description: `${newCategory.name} has been added to your portfolio`,
      status: 'success',
      duration: 3000,
      isClosable: true,
    });
  };

  const deleteCategory = (categoryId: string) => {
    const category = categories.find(c => c.id === categoryId);
    if (category?.isCore) {
      toast({
        title: 'Cannot Delete',
        description: 'Core categories cannot be deleted',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    // Move holdings back to unassigned
    setHoldings(prev =>
      prev.map(h => h.categoryId === categoryId ? { ...h, categoryId: null } : h)
    );
    setCategories(prev => prev.filter(c => c.id !== categoryId));

    toast({
      title: 'Category Deleted',
      description: 'Holdings have been moved to unassigned',
      status: 'info',
      duration: 3000,
      isClosable: true,
    });
  };

  const assignHoldingToCategory = (holdingId: string, categoryId: string) => {
    setHoldings(prev =>
      prev.map(h => h.id === holdingId ? { ...h, categoryId } : h)
    );

    const updatedHoldings = holdings.map(h => h.id === holdingId ? { ...h, categoryId } : h);
    updateCategoryValues(updatedHoldings);
    setUnassignedHoldings(prev => prev.filter(h => h.id !== holdingId));

    const holding = holdings.find(h => h.id === holdingId);
    const category = categories.find(c => c.id === categoryId);

    toast({
      title: 'Holding Assigned',
      description: `${holding?.symbol} moved to ${category?.name}`,
      status: 'success',
      duration: 2000,
      isClosable: true,
    });
  };

  const getAllocationStatus = (category: Category) => {
    const diff = category.currentAllocation - category.targetAllocation;
    if (Math.abs(diff) <= 1) return 'on-target';
    return diff > 0 ? 'overweight' : 'underweight';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'on-target': return 'green';
      case 'overweight': return 'orange';
      case 'underweight': return 'red';
      default: return 'gray';
    }
  };

  return (
    <Box p={6}>
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Flex justify="space-between" align="center">
          <Box>
            <Heading size="lg" mb={2} display="flex" alignItems="center">
              <FaChartPie color="#4299E1" style={{ marginRight: '12px' }} />
              Portfolio Categories
            </Heading>
            <Text color="gray.600">
              Organize your holdings into categories and manage target allocations
            </Text>
          </Box>
          <HStack spacing={3}>
            <Button
              leftIcon={<FaBalanceScale />}
              onClick={onRebalanceModalOpen}
              colorScheme="blue"
              size="sm"
              variant="outline"
            >
              Rebalance
            </Button>
            <Button
              leftIcon={<FaPlus />}
              onClick={onCategoryModalOpen}
              colorScheme="blue"
              size="sm"
            >
              Add Category
            </Button>
          </HStack>
        </Flex>

        {/* Portfolio Overview */}
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={6}>
          <Stat>
            <StatLabel>Total Portfolio</StatLabel>
            <StatNumber>${totalPortfolioValue.toLocaleString()}</StatNumber>
            <StatHelpText>{categories.length} categories</StatHelpText>
          </Stat>
          <Stat>
            <StatLabel>Assigned Holdings</StatLabel>
            <StatNumber>{holdings.filter(h => h.categoryId).length}</StatNumber>
            <StatHelpText>of {holdings.length} total</StatHelpText>
          </Stat>
          <Stat>
            <StatLabel>Allocation Drift</StatLabel>
            <StatNumber>{allocationRecommendations.length}</StatNumber>
            <StatHelpText>recommendations</StatHelpText>
          </Stat>
          <Stat>
            <StatLabel>Target Allocation</StatLabel>
            <StatNumber>{categories.reduce((sum, c) => sum + c.targetAllocation, 0)}%</StatNumber>
            <StatHelpText>configured</StatHelpText>
          </Stat>
        </SimpleGrid>

        {/* Categories Grid */}
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
          {categories.map((category) => {
            const status = getAllocationStatus(category);
            return (
              <Card key={category.id} bg={cardBg} border="2px" borderColor={category.color}>
                <CardHeader pb={2}>
                  <Flex justify="space-between" align="center">
                    <VStack align="start" spacing={1}>
                      <Heading size="sm">{category.name}</Heading>
                      <Badge colorScheme={getStatusColor(status)}>
                        {status.replace('-', ' ')}
                      </Badge>
                    </VStack>
                    <Menu>
                      <MenuButton
                        as={IconButton}
                        icon={<FaEllipsisV />}
                        variant="ghost"
                        size="sm"
                      />
                      <MenuList>
                        <MenuItem icon={<FaEdit />}>Edit</MenuItem>
                        {!category.isCore && (
                          <MenuItem
                            icon={<FaTrash />}
                            onClick={() => deleteCategory(category.id)}
                            color="red.500"
                          >
                            Delete
                          </MenuItem>
                        )}
                      </MenuList>
                    </Menu>
                  </Flex>
                </CardHeader>
                <CardBody pt={0}>
                  <VStack spacing={3} align="stretch">
                    <Box>
                      <Text fontSize="xs" color="gray.500" mb={1}>Current Value</Text>
                      <Text fontWeight="bold" fontSize="lg">${category.currentValue.toLocaleString()}</Text>
                    </Box>

                    <Box>
                      <Flex justify="space-between" mb={2}>
                        <Text fontSize="xs" color="gray.500">Allocation</Text>
                        <Text fontSize="xs" color="gray.500">
                          {category.currentAllocation.toFixed(1)}% / {category.targetAllocation}%
                        </Text>
                      </Flex>
                      <Progress
                        value={category.currentAllocation}
                        max={Math.max(category.targetAllocation, category.currentAllocation)}
                        colorScheme={getStatusColor(status)}
                        size="sm"
                        bg="gray.100"
                      />
                    </Box>

                    <Box>
                      <Text fontSize="xs" color="gray.500" mb={1}>Holdings</Text>
                      <Text fontWeight="semibold">{category.holdings.length} positions</Text>
                    </Box>

                    <Button
                      size="sm"
                      variant="outline"
                      leftIcon={<FaExchangeAlt />}
                      onClick={onAssignModalOpen}
                    >
                      Assign Holdings
                    </Button>
                  </VStack>
                </CardBody>
              </Card>
            );
          })}
        </SimpleGrid>

        {/* Unassigned Holdings */}
        {unassignedHoldings.length > 0 && (
          <Card bg={cardBg} border="1px" borderColor={borderColor}>
            <CardHeader>
              <Heading size="md">Unassigned Holdings ({unassignedHoldings.length})</Heading>
            </CardHeader>
            <CardBody>
              <TableContainer>
                <Table size="sm">
                  <Thead>
                    <Tr>
                      <Th>Symbol</Th>
                      <Th>Value</Th>
                      <Th>Brokerage</Th>
                      <Th>Type</Th>
                      <Th>Action</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {unassignedHoldings.map((holding) => (
                      <Tr key={holding.id}>
                        <Td>{holding.symbol}</Td>
                        <Td>${holding.value.toLocaleString()}</Td>
                        <Td>
                          <Badge colorScheme={holding.brokerage === 'ibkr' ? 'blue' : 'orange'}>
                            {holding.brokerage.toUpperCase()}
                          </Badge>
                        </Td>
                        <Td>
                          <Badge variant="outline">{holding.type}</Badge>
                        </Td>
                        <Td>
                          <Select
                            placeholder="Assign to category"
                            size="sm"
                            onChange={(e) => {
                              if (e.target.value) {
                                assignHoldingToCategory(holding.id, e.target.value);
                              }
                            }}
                          >
                            {categories.map((category) => (
                              <option key={category.id} value={category.id}>
                                {category.name}
                              </option>
                            ))}
                          </Select>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </TableContainer>
            </CardBody>
          </Card>
        )}

        {/* Rebalancing Recommendations */}
        {allocationRecommendations.length > 0 && (
          <Card bg={cardBg} border="1px" borderColor={borderColor}>
            <CardHeader>
              <Heading size="md">Rebalancing Recommendations</Heading>
            </CardHeader>
            <CardBody>
              <VStack spacing={3} align="stretch">
                {allocationRecommendations.map((rec, index) => (
                  <Alert key={index} status="info" borderRadius="md">
                    <AlertIcon />
                    <Box flex="1">
                      <Text fontWeight="bold">{rec.categoryName}</Text>
                      <Text fontSize="sm">
                        {rec.action === 'buy' ? 'Buy' : 'Sell'} ${rec.amount.toLocaleString()} - {rec.reason}
                      </Text>
                    </Box>
                  </Alert>
                ))}
              </VStack>
            </CardBody>
          </Card>
        )}
      </VStack>

      {/* Create Category Modal */}
      <Modal isOpen={isCategoryModalOpen} onClose={onCategoryModalClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Create New Category</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl>
                <FormLabel>Category Name</FormLabel>
                <Input
                  value={categoryFormData.name}
                  onChange={(e) => setCategoryFormData({ ...categoryFormData, name: e.target.value })}
                  placeholder="e.g., Tech Growth"
                />
              </FormControl>

              <FormControl>
                <FormLabel>Description</FormLabel>
                <Input
                  value={categoryFormData.description}
                  onChange={(e) => setCategoryFormData({ ...categoryFormData, description: e.target.value })}
                  placeholder="Brief description of this category"
                />
              </FormControl>

              <FormControl>
                <FormLabel>Target Allocation (%)</FormLabel>
                <NumberInput
                  value={categoryFormData.targetAllocation}
                  onChange={(valueString, valueNumber) =>
                    setCategoryFormData({ ...categoryFormData, targetAllocation: valueNumber })
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

              <FormControl>
                <FormLabel>Color</FormLabel>
                <HStack spacing={2} flexWrap="wrap">
                  {CATEGORY_COLORS.map((color) => (
                    <Box
                      key={color}
                      w={8}
                      h={8}
                      bg={color}
                      borderRadius="md"
                      cursor="pointer"
                      border={categoryFormData.color === color ? '3px solid' : '1px solid'}
                      borderColor={categoryFormData.color === color ? 'blue.500' : 'gray.300'}
                      onClick={() => setCategoryFormData({ ...categoryFormData, color })}
                    />
                  ))}
                </HStack>
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onCategoryModalClose}>
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              onClick={createCategory}
              disabled={!categoryFormData.name || categoryFormData.targetAllocation <= 0}
            >
              Create Category
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default PortfolioCategories; 