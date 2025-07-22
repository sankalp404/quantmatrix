import React from 'react';
import {
  Box,
  Flex,
  HStack,
  VStack,
  IconButton,
  Text,
  useColorModeValue,
  Avatar,
  Badge,
  Divider,
  Select,
} from '@chakra-ui/react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  FiHome,
  FiPieChart,
  FiBarChart,
  FiTrendingUp,
  FiSettings,
  FiBell,
  FiMenu,
  FiTarget,
  FiCalendar,
  FiList,
  FiDollarSign,
  FiActivity, // Added FiActivity for the new navigation item
} from 'react-icons/fi';
import { BsGraphUp } from 'react-icons/bs';
import { FaBrain } from 'react-icons/fa';
import { FaChartPie } from 'react-icons/fa';

// Navigation items inspired by Snowball Analytics
const navigationItems = [
  { label: 'Dashboard', icon: FiHome, path: '/' },
  { label: 'Portfolio', icon: FiPieChart, path: '/portfolio' },
  { label: 'Categories', icon: FaChartPie, path: '/portfolio-categories' },
  { label: 'Holdings', icon: BsGraphUp, path: '/holdings' },
  { label: 'Options', icon: FiTarget, path: '/options-portfolio' }, // Options Portfolio with target icon
  { label: 'Dividends', icon: FiCalendar, path: '/dividends' },
  { label: 'Transactions', icon: FiList, path: '/transactions' },
  { label: 'Margin', icon: FiDollarSign, path: '/margin' },
  { label: 'Analytics', icon: FiBarChart, path: '/analytics' },
  { label: 'Strategies', icon: FiActivity, path: '/strategies' }, // Changed icon to avoid conflict
  { label: 'Strategy Manager', icon: FaBrain, path: '/strategies-manager' },
  { label: 'Notifications', icon: FiBell, path: '/notifications' },
  { label: 'Settings', icon: FiSettings, path: '/settings' },
];

interface NavItemProps {
  icon: React.ElementType;
  label: string;
  path: string;
  isActive: boolean;
  onClick: () => void;
  badge?: number;
}

const NavItem: React.FC<NavItemProps> = ({ icon: Icon, label, isActive, onClick, badge }) => {
  const bg = useColorModeValue('gray.100', 'gray.700');
  const activeBg = useColorModeValue('brand.50', 'brand.900');
  const activeColor = useColorModeValue('brand.600', 'brand.200');
  const color = useColorModeValue('gray.600', 'gray.300');
  const hoverColor = useColorModeValue('gray.800', 'white');

  return (
    <Flex
      align="center"
      px={4}
      py={3}
      cursor="pointer"
      role="group"
      fontWeight="semibold"
      transition="all 0.2s"
      borderRadius="lg"
      bg={isActive ? activeBg : 'transparent'}
      color={isActive ? activeColor : color}
      _hover={{
        bg: isActive ? activeBg : bg,
        color: isActive ? activeColor : hoverColor,
      }}
      onClick={onClick}
      position="relative"
    >
      <Icon size={18} />
      <Text ml={3} fontSize="sm">
        {label}
      </Text>
      {badge && badge > 0 && (
        <Badge
          ml="auto"
          size="sm"
          colorScheme="red"
          variant="solid"
          borderRadius="full"
          minW={5}
          h={5}
          display="flex"
          alignItems="center"
          justifyContent="center"
          fontSize="xs"
        >
          {badge > 99 ? '99+' : badge}
        </Badge>
      )}
    </Flex>
  );
};

const DashboardLayout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const sidebarBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  return (
    <Flex h="100vh" bg={useColorModeValue('gray.50', 'gray.900')}>
      {/* Sidebar */}
      <Box
        w={64}
        bg={sidebarBg}
        borderRight="1px"
        borderColor={borderColor}
        pos="fixed"
        h="full"
        overflowY="auto"
      >
        <VStack spacing={0} align="stretch">
          {/* Logo/Brand */}
          <Flex align="center" px={6} py={4} borderBottom="1px" borderColor={borderColor}>
            <Box
              w={8}
              h={8}
              bg="brand.500"
              borderRadius="lg"
              display="flex"
              alignItems="center"
              justifyContent="center"
              mr={3}
            >
              <Text color="white" fontWeight="bold" fontSize="sm">
                Q
              </Text>
            </Box>
            <Text fontSize="lg" fontWeight="bold" color="brand.500">
              QuantMatrix
            </Text>
          </Flex>

          {/* Account Selector */}
          <Box px={4} py={4}>
            <HStack spacing={3}>
              <Avatar size="sm" name="Portfolio" bg="brand.500" />
              <Box flex={1}>
                <Text fontSize="sm" fontWeight="semibold">
                  Combined Portfolio
                </Text>
                <Text fontSize="xs" color="gray.500">
                  $1.69M • +52.4%
                </Text>
              </Box>
            </HStack>
          </Box>

          <Divider />

          {/* Navigation */}
          <VStack spacing={1} px={4} py={4} align="stretch">
            {navigationItems.map((item) => (
              <NavItem
                key={item.path}
                icon={item.icon}
                label={item.label}
                path={item.path}
                isActive={location.pathname === item.path}
                onClick={() => navigate(item.path)}
                badge={item.label === 'Notifications' ? 5 : undefined}
              />
            ))}
          </VStack>

          {/* Quick Stats */}
          <Box px={4} py={4} mt="auto">
            <VStack spacing={2} align="stretch">
              <Text fontSize="xs" fontWeight="semibold" color="gray.500" textTransform="uppercase">
                Quick Stats
              </Text>
              <HStack justify="space-between">
                <Text fontSize="xs" color="gray.500">Day P&L</Text>
                <Text fontSize="xs" fontWeight="semibold" color="green.400">
                  +$2,847
                </Text>
              </HStack>
              <HStack justify="space-between">
                <Text fontSize="xs" color="gray.500">Positions</Text>
                <Text fontSize="xs" fontWeight="semibold">
                  73
                </Text>
              </HStack>
              <HStack justify="space-between">
                <Text fontSize="xs" color="gray.500">Margin Used</Text>
                <Text fontSize="xs" fontWeight="semibold" color="orange.400">
                  23%
                </Text>
              </HStack>
            </VStack>
          </Box>
        </VStack>
      </Box>

      {/* Main Content */}
      <Box flex={1} ml={64}>
        {/* Header */}
        <Flex
          h={16}
          alignItems="center"
          justifyContent="space-between"
          px={6}
          bg={sidebarBg}
          borderBottom="1px"
          borderColor={borderColor}
        >
          <HStack spacing={4}>
            <IconButton
              size="md"
              variant="ghost"
              aria-label="Menu"
              icon={<FiMenu />}
            />
            {/* ADDED: Account Selection Dropdown */}
            <Select
              size="sm"
              w="200px"
              defaultValue="all"
              bg={useColorModeValue('white', 'gray.700')}
              borderColor={borderColor}
            >
              <option value="all">All Accounts</option>
              <option value="U19490886">Taxable Account</option>
              <option value="U15891532">Tax-Deferred Account</option>
            </Select>
            {/* REMOVED: Redundant page name display */}
          </HStack>

          <HStack spacing={4}>
            <IconButton
              size="md"
              variant="ghost"
              aria-label="Notifications"
              icon={<FiBell />}
              position="relative"
            >
              <Badge
                position="absolute"
                top="6px"
                right="6px"
                borderRadius="full"
                bg="red.500"
                w={2}
                h={2}
              />
            </IconButton>
            <Avatar size="sm" name="User" bg="brand.500" />
          </HStack>
        </Flex>

        {/* Page Content */}
        <Box p={6} h="calc(100vh - 4rem)" overflowY="auto">
          <Outlet />
        </Box>
      </Box>
    </Flex>
  );
};

export default DashboardLayout; 