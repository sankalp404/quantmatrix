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
  Tooltip,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  IconButton,
  Switch,
  FormControl,
  FormLabel,
  Stack,
  Avatar,
  List,
  ListItem,
  ListIcon,
} from '@chakra-ui/react';
import {
  FiAlertTriangle,
  FiArrowDown,
  FiArrowUp,
  FiBell,
  FiCalendar,
  FiCheck,
  FiChevronDown,
  FiInfo,
  FiSearch,
  FiSettings,
  FiStar,
  FiTrash2,
} from 'react-icons/fi';
import {
  FiDollarSign,
  FiBarChart as BarChart3Icon
} from 'react-icons/fi';
import { usePortfolio } from '../hooks/usePortfolio';

// Mock notification data processor
const processNotifications = (portfolioData: any) => {
  const now = new Date();
  const notifications: any[] = [];
  let notificationId = 1;

  // Generate signals notifications
  const signalSymbols = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'TSLA', 'GOOGL', 'META'];
  signalSymbols.forEach((symbol, idx) => {
    const signalDate = new Date(now.getTime() - (idx * 3600000)); // Spread over last few hours

    // FIXED: Generate deterministic notification data (no more random!)
    const symbolHash = symbol.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);

    notifications.push({
      id: notificationId++,
      type: 'SIGNAL',
      category: 'Entry Signal',
      title: `${symbol} Entry Signal`,
      message: `ATR Matrix detected optimal entry point for ${symbol} at $${(150 + (symbolHash % 100)).toFixed(2)}`, // FIXED: deterministic price
      timestamp: signalDate.toISOString(),
      symbol: symbol,
      priority: 'HIGH',
      isRead: (symbolHash % 10) > 3, // FIXED: deterministic read status (70% read)
      data: {
        price: (150 + (symbolHash % 100)).toFixed(2), // FIXED: deterministic price
        confidence: ((symbolHash % 30) / 100 + 0.7).toFixed(2), // FIXED: deterministic confidence 70-100%
        action: 'BUY',
        targets: ['$' + (180 + ((symbolHash + 1) % 50)).toFixed(2), '$' + (200 + ((symbolHash + 2) % 50)).toFixed(2)], // FIXED: deterministic targets
        stopLoss: '$' + (140 + ((symbolHash + 3) % 20)).toFixed(2) // FIXED: deterministic stop loss
      }
    });
  });

  // Generate portfolio alerts
  if (portfolioData?.accounts) {
    Object.values(portfolioData.accounts).forEach((account: any) => {
      if (account.all_positions) {
        account.all_positions.slice(0, 8).forEach((position: any, idx: number) => {
          const alertDate = new Date(now.getTime() - ((idx + 5) * 1800000)); // Spread over time

          // Scale out alerts for winners
          if ((position.unrealized_pnl_pct || 0) > 25) {
            notifications.push({
              id: notificationId++,
              type: 'ALERT',
              category: 'Scale Out',
              title: `${position.symbol} Scale Out Opportunity`,
              message: `Position up ${(position.unrealized_pnl_pct || 0).toFixed(1)}% - consider taking profits`,
              timestamp: alertDate.toISOString(),
              symbol: position.symbol,
              priority: 'MEDIUM',
              isRead: (position.symbol.charCodeAt(0) % 10) > 5, // FIXED: deterministic read status based on symbol
              data: {
                currentGain: (position.unrealized_pnl_pct || 0).toFixed(1) + '%',
                suggestion: 'Scale out 25-50% of position',
                marketValue: position.position * position.market_price
              }
            });
          }

          // DCA alerts for losers
          if ((position.unrealized_pnl_pct || 0) < -10) {
            notifications.push({
              id: notificationId++,
              type: 'ALERT',
              category: 'DCA Opportunity',
              title: `${position.symbol} DCA Opportunity`,
              message: `Position down ${Math.abs(position.unrealized_pnl_pct || 0).toFixed(1)}% - potential averaging opportunity`,
              timestamp: new Date(alertDate.getTime() - 600000).toISOString(),
              symbol: position.symbol,
              priority: 'LOW',
              isRead: (position.symbol.charCodeAt(0) % 10) > 6, // FIXED: deterministic read status based on symbol
              data: {
                currentLoss: Math.abs(position.unrealized_pnl_pct || 0).toFixed(1) + '%',
                suggestion: 'Consider dollar-cost averaging',
                support: '$' + (position.market_price * 0.95).toFixed(2)
              }
            });
          }
        });
      }
    });
  }

  // Generate system notifications
  const systemAlerts = [
    {
      type: 'SYSTEM',
      category: 'Market Update',
      title: 'Market Analysis Complete',
      message: 'Daily morning scan identified 12 new opportunities across technology and healthcare sectors',
      priority: 'LOW',
      data: { scanResults: '12 opportunities', sectors: 'Tech, Healthcare' }
    },
    {
      type: 'SYSTEM',
      category: 'Portfolio Health',
      title: 'Portfolio Rebalancing Recommended',
      message: 'Your allocation has drifted 3.2% from targets. Consider rebalancing.',
      priority: 'MEDIUM',
      data: { drift: '3.2%', action: 'Rebalance recommended' }
    },
    {
      type: 'SYSTEM',
      category: 'Discord Integration',
      title: 'Notifications Sent Successfully',
      message: 'Morning brew, signals, and portfolio digest delivered to Discord channels',
      priority: 'LOW',
      data: { channels: 'All channels', status: 'Success' }
    }
  ];

  systemAlerts.forEach((alert, idx) => {
    const alertDate = new Date(now.getTime() - ((idx + 1) * 7200000)); // Spread over last day
    notifications.push({
      id: notificationId++,
      ...alert,
      timestamp: alertDate.toISOString(),
      symbol: null,
      isRead: (idx % 10) > 4 // FIXED: deterministic read status for system alerts
    });
  });

  // Generate strategy notifications
  const strategyResults = [
    {
      type: 'STRATEGY',
      category: 'ATR Matrix',
      title: 'Daily ATR Scan Complete',
      message: 'Scanned 508 stocks, found 5 high-confidence entry signals with avg 2.8:1 risk/reward',
      priority: 'HIGH',
      data: {
        stocksScanned: 508,
        signalsFound: 5,
        avgRiskReward: '2.8:1',
        winRate: '72%'
      }
    },
    {
      type: 'STRATEGY',
      category: 'Portfolio Analysis',
      title: 'Weekly Performance Review',
      message: 'Portfolio outperformed S&P 500 by 1.4% this week. Total return: +2.7%',
      priority: 'MEDIUM',
      data: {
        weeklyReturn: '+2.7%',
        outperformance: '+1.4%',
        benchmark: 'S&P 500'
      }
    }
  ];

  strategyResults.forEach((result, idx) => {
    const resultDate = new Date(now.getTime() - ((idx + 1) * 86400000)); // Daily results
    notifications.push({
      id: notificationId++,
      ...result,
      timestamp: resultDate.toISOString(),
      symbol: null,
      isRead: (idx % 10) > 7 // FIXED: deterministic read status for strategy results
    });
  });

  // Sort by timestamp (newest first)
  notifications.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  return notifications;
};

const Notifications: React.FC = () => {
  const { data: portfolioData, isLoading, error } = usePortfolio();
  const [notifications, setNotifications] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [selectedPriority, setSelectedPriority] = useState<string>('');
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  // Process notifications
  useEffect(() => {
    if (portfolioData) {
      const processedNotifications = processNotifications(portfolioData);
      setNotifications(processedNotifications);
    }
  }, [portfolioData]);

  // Filter notifications
  const filteredNotifications = notifications.filter(notification => {
    const matchesSearch = notification.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      notification.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (notification.symbol && notification.symbol.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesType = selectedType === '' || notification.type === selectedType;
    const matchesPriority = selectedPriority === '' || notification.priority === selectedPriority;
    const matchesReadStatus = !showUnreadOnly || !notification.isRead;

    return matchesSearch && matchesType && matchesPriority && matchesReadStatus;
  });

  // Statistics
  const stats = {
    total: notifications.length,
    unread: notifications.filter(n => !n.isRead).length,
    high: notifications.filter(n => n.priority === 'HIGH').length,
    signals: notifications.filter(n => n.type === 'SIGNAL').length,
    alerts: notifications.filter(n => n.type === 'ALERT').length
  };

  // Mark as read
  const markAsRead = (notificationId: number) => {
    setNotifications(prev => prev.map(n =>
      n.id === notificationId ? { ...n, isRead: true } : n
    ));
  };

  // Mark all as read
  const markAllAsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, isRead: true })));
  };

  // Delete notification
  const deleteNotification = (notificationId: number) => {
    setNotifications(prev => prev.filter(n => n.id !== notificationId));
  };

  // Get notification icon
  const getNotificationIcon = (type: string, category: string) => {
    switch (type) {
      case 'SIGNAL':
        return FiArrowUp;
      case 'ALERT':
        return FiAlertTriangle;
      case 'STRATEGY':
        return BarChart3Icon;
      case 'SYSTEM':
        return FiInfo;
      default:
        return FiBell;
    }
  };

  // Get notification color
  const getNotificationColor = (priority: string) => {
    switch (priority) {
      case 'HIGH':
        return 'red';
      case 'MEDIUM':
        return 'orange';
      case 'LOW':
        return 'blue';
      default:
        return 'gray';
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) {
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      return `${diffMinutes}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  if (isLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <Flex justify="center" align="center" h="400px">
          <VStack>
            <Spinner size="xl" color="blue.500" />
            <Text>Loading notifications...</Text>
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
              <Heading size="lg">Notifications</Heading>
              {stats.unread > 0 && (
                <Badge colorScheme="red" variant="solid" borderRadius="full">
                  {stats.unread}
                </Badge>
              )}
            </HStack>
            <HStack>
              <Button size="sm" variant="outline" onClick={markAllAsRead}>
                Mark All Read
              </Button>
              <Menu>
                <MenuButton as={IconButton} icon={<FiSettings />} size="sm" variant="outline" />
                <MenuList>
                  <MenuItem>Notification Settings</MenuItem>
                  <MenuItem>Discord Integration</MenuItem>
                  <MenuItem>Email Preferences</MenuItem>
                </MenuList>
              </Menu>
            </HStack>
          </HStack>
          <Text color="gray.600">
            Real-time signals, portfolio alerts, and strategy notifications
          </Text>
        </Box>

        {/* Statistics Cards */}
        <SimpleGrid columns={{ base: 3, md: 5 }} spacing={4}>
          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Total</StatLabel>
                <StatNumber>{stats.total}</StatNumber>
                <StatHelpText>All notifications</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Unread</StatLabel>
                <StatNumber color="red.500">{stats.unread}</StatNumber>
                <StatHelpText>Need attention</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>High Priority</StatLabel>
                <StatNumber color="orange.500">{stats.high}</StatNumber>
                <StatHelpText>Urgent items</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Signals</StatLabel>
                <StatNumber color="green.500">{stats.signals}</StatNumber>
                <StatHelpText>Entry/exit alerts</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody>
              <Stat>
                <StatLabel>Portfolio Alerts</StatLabel>
                <StatNumber color="blue.500">{stats.alerts}</StatNumber>
                <StatHelpText>Position updates</StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        <Tabs variant="enclosed" colorScheme="blue">
          <TabList>
            <Tab>All Notifications</Tab>
            <Tab>Signals <Badge ml={2} colorScheme="green">{stats.signals}</Badge></Tab>
            <Tab>Alerts <Badge ml={2} colorScheme="orange">{stats.alerts}</Badge></Tab>
            <Tab>Strategies</Tab>
            <Tab>System</Tab>
          </TabList>

          <TabPanels>
            {/* All Notifications */}
            <TabPanel px={0}>
              <Card bg={bgColor} borderColor={borderColor}>
                <CardHeader>
                  <VStack spacing={4}>
                    <HStack justify="space-between" w="full">
                      <Heading size="md">Recent Notifications</Heading>
                      <Text fontSize="sm" color="gray.600">
                        {filteredNotifications.length} of {notifications.length} notifications
                      </Text>
                    </HStack>

                    {/* Filters */}
                    <HStack w="full" wrap="wrap" spacing={3}>
                      <InputGroup size="sm" maxW="200px">
                        <InputLeftElement>
                          <FiSearch color="gray.400" />
                        </InputLeftElement>
                        <Input
                          placeholder="Search notifications..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                        />
                      </InputGroup>

                      <Select size="sm" maxW="120px" value={selectedType} onChange={(e) => setSelectedType(e.target.value)}>
                        <option value="">All Types</option>
                        <option value="SIGNAL">Signals</option>
                        <option value="ALERT">Alerts</option>
                        <option value="STRATEGY">Strategy</option>
                        <option value="SYSTEM">System</option>
                      </Select>

                      <Select size="sm" maxW="120px" value={selectedPriority} onChange={(e) => setSelectedPriority(e.target.value)}>
                        <option value="">All Priority</option>
                        <option value="HIGH">High</option>
                        <option value="MEDIUM">Medium</option>
                        <option value="LOW">Low</option>
                      </Select>

                      <FormControl display="flex" alignItems="center" maxW="150px">
                        <FormLabel htmlFor="unread-only" mb="0" fontSize="sm">
                          Unread only
                        </FormLabel>
                        <Switch
                          id="unread-only"
                          size="sm"
                          isChecked={showUnreadOnly}
                          onChange={(e) => setShowUnreadOnly(e.target.checked)}
                        />
                      </FormControl>
                    </HStack>
                  </VStack>
                </CardHeader>

                <CardBody>
                  <VStack spacing={3} align="stretch">
                    {filteredNotifications.length > 0 ? (
                      filteredNotifications.map((notification) => {
                        const IconComponent = getNotificationIcon(notification.type, notification.category);
                        const priorityColor = getNotificationColor(notification.priority);

                        return (
                          <Box
                            key={notification.id}
                            p={4}
                            border="1px solid"
                            borderColor={borderColor}
                            borderRadius="md"
                            bg={notification.isRead ? bgColor : useColorModeValue('blue.50', 'blue.900')}
                            borderLeftWidth="4px"
                            borderLeftColor={`${priorityColor}.500`}
                          >
                            <HStack justify="space-between" align="start">
                              <HStack align="start" flex={1}>
                                <Icon as={IconComponent} color={`${priorityColor}.500`} mt={1} />
                                <VStack align="start" spacing={1} flex={1}>
                                  <HStack>
                                    <Text fontWeight="semibold" fontSize="sm">
                                      {notification.title}
                                    </Text>
                                    {notification.symbol && (
                                      <Badge variant="outline" fontSize="xs">
                                        {notification.symbol}
                                      </Badge>
                                    )}
                                    <Badge colorScheme={priorityColor} variant="subtle" fontSize="xs">
                                      {notification.priority}
                                    </Badge>
                                    <Badge variant="outline" fontSize="xs">
                                      {notification.category}
                                    </Badge>
                                  </HStack>

                                  <Text fontSize="sm" color="gray.600">
                                    {notification.message}
                                  </Text>

                                  {notification.data && (
                                    <HStack wrap="wrap" spacing={2} mt={1}>
                                      {Object.entries(notification.data).map(([key, value]) => (
                                        <Text key={key} fontSize="xs" color="gray.500">
                                          {key}: {String(value)}
                                        </Text>
                                      ))}
                                    </HStack>
                                  )}

                                  <Text fontSize="xs" color="gray.500">
                                    {formatTimestamp(notification.timestamp)}
                                  </Text>
                                </VStack>
                              </HStack>

                              <HStack>
                                {!notification.isRead && (
                                  <IconButton
                                    aria-label="Mark as read"
                                    icon={<FiCheck />}
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => markAsRead(notification.id)}
                                  />
                                )}
                                <IconButton
                                  aria-label="Delete notification"
                                  icon={<FiTrash2 />}
                                  size="sm"
                                  variant="ghost"
                                  colorScheme="red"
                                  onClick={() => deleteNotification(notification.id)}
                                />
                              </HStack>
                            </HStack>
                          </Box>
                        );
                      })
                    ) : (
                      <Alert status="info">
                        <AlertIcon />
                        No notifications match your current filters
                      </Alert>
                    )}
                  </VStack>
                </CardBody>
              </Card>
            </TabPanel>

            {/* Signals Tab */}
            <TabPanel px={0}>
              <VStack spacing={4}>
                {notifications.filter(n => n.type === 'SIGNAL').map(notification => (
                  <Card key={notification.id} bg={bgColor} borderColor={borderColor} w="full">
                    <CardBody>
                      <HStack justify="space-between">
                        <VStack align="start" spacing={2}>
                          <HStack>
                            <Icon as={FiArrowUp} color="green.500" />
                            <Text fontWeight="semibold">{notification.title}</Text>
                            <Badge colorScheme="green">{notification.category}</Badge>
                          </HStack>
                          <Text fontSize="sm" color="gray.600">{notification.message}</Text>
                          {notification.data && (
                            <HStack spacing={4} fontSize="sm">
                              <Text>Price: {notification.data.price}</Text>
                              <Text>Confidence: {(parseFloat(notification.data.confidence) * 100).toFixed(0)}%</Text>
                              <Text>Stop: {notification.data.stopLoss}</Text>
                            </HStack>
                          )}
                          <Text fontSize="xs" color="gray.500">{formatTimestamp(notification.timestamp)}</Text>
                        </VStack>
                        <Button size="sm" colorScheme="green" variant="outline">
                          View Signal
                        </Button>
                      </HStack>
                    </CardBody>
                  </Card>
                ))}
              </VStack>
            </TabPanel>

            {/* Alerts Tab */}
            <TabPanel px={0}>
              <VStack spacing={4}>
                {notifications.filter(n => n.type === 'ALERT').map(notification => (
                  <Card key={notification.id} bg={bgColor} borderColor={borderColor} w="full">
                    <CardBody>
                      <HStack justify="space-between">
                        <VStack align="start" spacing={2}>
                          <HStack>
                            <Icon as={FiAlertTriangle} color="orange.500" />
                            <Text fontWeight="semibold">{notification.title}</Text>
                            <Badge colorScheme="orange">{notification.category}</Badge>
                          </HStack>
                          <Text fontSize="sm" color="gray.600">{notification.message}</Text>
                          {notification.data && (
                            <Text fontSize="sm" color="blue.600">
                              {notification.data.suggestion}
                            </Text>
                          )}
                          <Text fontSize="xs" color="gray.500">{formatTimestamp(notification.timestamp)}</Text>
                        </VStack>
                        <Button size="sm" colorScheme="orange" variant="outline">
                          Take Action
                        </Button>
                      </HStack>
                    </CardBody>
                  </Card>
                ))}
              </VStack>
            </TabPanel>

            {/* Strategies Tab */}
            <TabPanel px={0}>
              <VStack spacing={4}>
                {notifications.filter(n => n.type === 'STRATEGY').map(notification => (
                  <Card key={notification.id} bg={bgColor} borderColor={borderColor} w="full">
                    <CardBody>
                      <HStack justify="space-between">
                        <VStack align="start" spacing={2}>
                          <HStack>
                            <Icon as={BarChart3Icon} color="blue.500" />
                            <Text fontWeight="semibold">{notification.title}</Text>
                            <Badge colorScheme="blue">{notification.category}</Badge>
                          </HStack>
                          <Text fontSize="sm" color="gray.600">{notification.message}</Text>
                          {notification.data && (
                            <HStack spacing={4} fontSize="sm">
                              {Object.entries(notification.data).map(([key, value]) => (
                                <Text key={key}>{key}: {String(value)}</Text>
                              ))}
                            </HStack>
                          )}
                          <Text fontSize="xs" color="gray.500">{formatTimestamp(notification.timestamp)}</Text>
                        </VStack>
                        <Button size="sm" colorScheme="blue" variant="outline">
                          View Details
                        </Button>
                      </HStack>
                    </CardBody>
                  </Card>
                ))}
              </VStack>
            </TabPanel>

            {/* System Tab */}
            <TabPanel px={0}>
              <VStack spacing={4}>
                {notifications.filter(n => n.type === 'SYSTEM').map(notification => (
                  <Card key={notification.id} bg={bgColor} borderColor={borderColor} w="full">
                    <CardBody>
                      <HStack justify="space-between">
                        <VStack align="start" spacing={2}>
                          <HStack>
                            <Icon as={FiInfo} color="gray.500" />
                            <Text fontWeight="semibold">{notification.title}</Text>
                            <Badge variant="outline">{notification.category}</Badge>
                          </HStack>
                          <Text fontSize="sm" color="gray.600">{notification.message}</Text>
                          <Text fontSize="xs" color="gray.500">{formatTimestamp(notification.timestamp)}</Text>
                        </VStack>
                      </HStack>
                    </CardBody>
                  </Card>
                ))}
              </VStack>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </VStack>
    </Container>
  );
};

export default Notifications; 