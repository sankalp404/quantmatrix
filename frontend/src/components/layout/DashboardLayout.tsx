import React, { useEffect, useState } from 'react';
import {
  Box,
  Flex,
  HStack,
  VStack,
  IconButton,
  Text,
  Badge,
  DialogRoot,
  DialogBackdrop,
  DialogPositioner,
  DialogContent,
  MenuRoot,
  MenuTrigger,
  MenuContent,
  MenuItem,
  Button,
  useMediaQuery,
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
  FiSun,
  FiMoon,
} from 'react-icons/fi';
import { BsGraphUp } from 'react-icons/bs';
import { FaBrain } from 'react-icons/fa';
import { FaChartPie } from 'react-icons/fa';
import { portfolioApi } from '../../services/api';
import { useAccountContext } from '../../context/AccountContext';
import { useAuth } from '../../context/AuthContext';
import AppDivider from '../ui/AppDivider';

// Navigation items inspired by Snowball Analytics
const navigationItems = [
  { label: 'Dashboard', icon: FiHome, path: '/' },
  { label: 'Portfolio', icon: FiPieChart, path: '/portfolio' },
  { label: 'Categories', icon: FaChartPie, path: '/portfolio-categories' },
  { label: 'Stocks', icon: BsGraphUp, path: '/stocks' },
  { label: 'Options', icon: FiTarget, path: '/options-portfolio' }, // Options Portfolio with target icon
  { label: 'Workspace', icon: FiActivity, path: '/workspace' },
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
  showLabel?: boolean;
}

const NavItem: React.FC<NavItemProps> = ({ icon: Icon, label, isActive, onClick, badge, showLabel = true }) => {
  const bg = 'gray.800';
  const activeBg = 'gray.700';
  const activeColor = 'white';
  const color = 'gray.300';
  const hoverColor = 'white';

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
      justifyContent={showLabel ? 'flex-start' : 'center'}
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
      {showLabel && (
        <Text ml={3} fontSize="sm">
          {label}
        </Text>
      )}
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
  const sidebarBg = 'gray.900';
  const headerBg = 'gray.950';
  const borderColor = 'gray.800';
  const appBg = 'gray.950';
  const { accounts, loading: accountsLoading, selected, setSelected } = useAccountContext();
  const { user, logout } = useAuth();
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const [isDesktop] = useMediaQuery(['(min-width: 48em)']);
  const [totals, setTotals] = useState<{ value: number; dayPnL: number; positions: number }>({ value: 0, dayPnL: 0, positions: 0 });
  const [headerStats, setHeaderStats] = useState<{ label: string; sublabel: string }>({ label: 'Combined Portfolio', sublabel: '' });

  useEffect(() => {
    const load = async () => {
      try {
        const res = await portfolioApi.getLive();
        const data = (res as any)?.data || res;
        const accounts = Object.values<any>(data?.accounts || {});
        const value = accounts.reduce((sum, a: any) => sum + (a.account_summary?.net_liquidation || 0), 0);
        const dayPnL = accounts.reduce((sum, a: any) => sum + (a.account_summary?.day_change || 0), 0);
        const positions = accounts.reduce((sum, a: any) => sum + ((a.all_positions || []).length || 0), 0);
        setTotals({ value, dayPnL, positions });
        setHeaderStats({
          label: 'Combined Portfolio',
          sublabel: `${formatCurrency(value)} • ${formatSignedCurrency(dayPnL)}`,
        });
      } catch (e) {
        // leave defaults
      }
    };
    load();
  }, []);

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount || 0);
  const formatSignedCurrency = (amount: number) => {
    const f = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Math.abs(amount || 0));
    return `${(amount || 0) >= 0 ? '+' : '-'}${f}`;
  };

  const sidebarWidth = isSidebarOpen ? 64 : 16;

  const renderNav = (opts: { showLabel: boolean; px: any }) => (
    <VStack gap={1} px={opts.px} py={4} align="stretch">
      {navigationItems.map((item) => (
        <NavItem
          key={item.path}
          icon={item.icon}
          label={item.label}
          path={item.path}
          isActive={location.pathname === item.path}
          onClick={() => {
            navigate(item.path);
            setIsMobileNavOpen(false);
          }}
          badge={item.label === 'Notifications' ? 5 : undefined}
          showLabel={opts.showLabel}
        />
      ))}
    </VStack>
  );

  return (
    <Flex h="100vh" w="100vw" bg={appBg} overflow="hidden">
      {/* Desktop rail */}
      {isDesktop ? (
        <Box
          w={sidebarWidth}
          flexShrink={0}
          bg={sidebarBg}
          borderRight="1px"
          borderColor={borderColor}
          h="100vh"
          overflowY="auto"
          transition="width 0.2s ease"
        >
          <VStack gap={0} align="stretch">
            {/* Logo/Brand */}
            <Flex align="center" px={isSidebarOpen ? 6 : 3} py={4} borderBottom="1px" borderColor={borderColor}>
              <Box
                w={8}
                h={8}
                bg="brand.500"
                borderRadius="lg"
                display="flex"
                alignItems="center"
                justifyContent="center"
                mr={isSidebarOpen ? 3 : 0}
              >
                <Text color="white" fontWeight="bold" fontSize="sm">
                  Q
                </Text>
              </Box>
              {isSidebarOpen ? (
                <Text fontSize="lg" fontWeight="bold" color="brand.500">
                  QuantMatrix
                </Text>
              ) : null}
            </Flex>

            {isSidebarOpen ? <AppDivider /> : null}

            {/* Navigation */}
            {renderNav({ showLabel: isSidebarOpen, px: isSidebarOpen ? 4 : 2 })}

            {/* Quick Stats */}
            {isSidebarOpen && (
              <Box px={4} py={4} mt="auto">
                <VStack gap={2} align="stretch">
                  <HStack justify="space-between">
                    <Text fontSize="xs" fontWeight="semibold" color="gray.500">
                      {headerStats.label}
                    </Text>
                    <Text fontSize="xs" fontWeight="semibold" color="gray.200">
                      {headerStats.sublabel || formatSignedCurrency(totals.dayPnL)}
                    </Text>
                  </HStack>
                  <AppDivider />
                  <Text fontSize="xs" fontWeight="semibold" color="gray.500" textTransform="uppercase">
                    Quick Stats
                  </Text>
                  <HStack justify="space-between">
                    <Text fontSize="xs" color="gray.500">Day P&L</Text>
                    <Text fontSize="xs" fontWeight="semibold" color={totals.dayPnL >= 0 ? 'green.400' : 'red.400'}>
                      {formatSignedCurrency(totals.dayPnL)}
                    </Text>
                  </HStack>
                  <HStack justify="space-between">
                    <Text fontSize="xs" color="gray.500">Positions</Text>
                    <Text fontSize="xs" fontWeight="semibold">
                      {totals.positions}
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
            )}
          </VStack>
        </Box>
      ) : null}

      {/* Mobile overlay nav */}
      {!isDesktop ? (
        <DialogRoot open={isMobileNavOpen} onOpenChange={(d) => setIsMobileNavOpen(Boolean(d.open))}>
          <DialogBackdrop />
          <DialogPositioner inset={0} justifyContent="flex-start" alignItems="stretch" p={0} m={0}>
            <DialogContent
              position="fixed"
              top={0}
              left={0}
              w="280px"
              maxW="80vw"
              h="100vh"
              borderRadius={0}
              bg={sidebarBg}
              borderRight="1px"
              borderColor={borderColor}
              m={0}
            >
              <VStack gap={0} align="stretch" h="full">
                <Flex align="center" px={6} py={4} borderBottom="1px" borderColor={borderColor}>
                  <Box w={8} h={8} bg="brand.500" borderRadius="lg" display="flex" alignItems="center" justifyContent="center" mr={3}>
                    <Text color="white" fontWeight="bold" fontSize="sm">
                      Q
                    </Text>
                  </Box>
                  <Text fontSize="lg" fontWeight="bold" color="brand.500">
                    QuantMatrix
                  </Text>
                </Flex>
                <AppDivider />
                <Box flex={1} overflowY="auto">
                  {renderNav({ showLabel: true, px: 4 })}
                </Box>
              </VStack>
            </DialogContent>
          </DialogPositioner>
        </DialogRoot>
      ) : null}

      {/* Main Content */}
      <Box flex={1} minW={0} overflowX="hidden">
        {/* Header */}
        <Flex
          h={16}
          alignItems="center"
          justifyContent="space-between"
          px={6}
          bg={headerBg}
          borderBottom="1px"
          borderColor={borderColor}
        >
          <HStack gap={4}>
            <IconButton
              size="md"
              variant="ghost"
              aria-label="Menu"
              position="relative"
              zIndex={2}
              onClick={() => {
                if (isDesktop) {
                  setIsSidebarOpen((v) => !v);
                } else {
                  setIsMobileNavOpen(true);
                }
              }}
            >
              <FiMenu />
            </IconButton>
            {/* Global Account Selection */}
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              disabled={accountsLoading}
              style={{
                width: 260,
                fontSize: 12,
                padding: '6px 8px',
                borderRadius: 8,
                border: '1px solid #2d3748',
                background: '#111827',
                color: '#e5e7eb',
              }}
            >
              <option value="all">All Accounts</option>
              <option value="taxable">Taxable</option>
              <option value="ira">Tax-Deferred (IRA)</option>
              {accounts.map((a) => (
                <option key={a.account_number} value={a.account_number}>
                  {a.account_name || a.account_number}
                </option>
              ))}
            </select>
            {/* REMOVED: Redundant page name display */}
          </HStack>

          <HStack gap={4}>
            <IconButton size="md" variant="ghost" aria-label="Notifications" position="relative">
              <FiBell />
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
            <MenuRoot>
              <MenuTrigger asChild>
                <Button size="sm" variant="ghost">
                  <HStack gap={2}>
                    <Box w={8} h={8} borderRadius="full" bg="brand.500" display="flex" alignItems="center" justifyContent="center">
                      <Text fontSize="xs" fontWeight="bold" color="white">
                        {(user?.username || 'U').slice(0, 1).toUpperCase()}
                      </Text>
                    </Box>
                    <Text fontSize="sm">{user?.username || 'Account'}</Text>
                  </HStack>
                </Button>
              </MenuTrigger>
              <MenuContent>
                <MenuItem value="settings" onClick={() => navigate('/settings')}>Account Settings</MenuItem>
                <MenuItem value="portfolio" onClick={() => navigate('/portfolio')}>Portfolio</MenuItem>
                <MenuItem value="workspace" onClick={() => navigate('/workspace')}>Workspace</MenuItem>
                <MenuItem value="logout" onClick={() => { logout(); navigate('/login'); }}>Logout</MenuItem>
              </MenuContent>
            </MenuRoot>
          </HStack>
        </Flex>

        {/* Page Content */}
        <Box p={4} h="calc(100vh - 4rem)" overflowY="auto" overflowX="hidden" minW={0}>
          <Outlet />
        </Box>
      </Box>
    </Flex>
  );
};

export default DashboardLayout; 