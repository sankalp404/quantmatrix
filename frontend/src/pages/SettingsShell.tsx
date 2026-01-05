import React from 'react';
import { Box, Flex, VStack, Button, Text, IconButton, TooltipRoot, TooltipTrigger, TooltipPositioner, TooltipContent, useMediaQuery } from '@chakra-ui/react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { FiBell, FiGrid, FiLock, FiSliders, FiUser, FiShield, FiActivity } from 'react-icons/fi';

const MenuLink: React.FC<{ to: string; children: React.ReactNode }> = ({ to, children }) => {
  const activeBg = 'bg.muted';
  const hoverBg = 'bg.subtle';
  const activeColor = 'fg.default';
  const textColor = 'fg.muted';
  return (
    <NavLink to={to} style={({ isActive }) => ({ textDecoration: 'none' })}>
      {({ isActive }) => (
        <Button
          variant="ghost"
          justifyContent="flex-start"
          width="100%"
          bg={isActive ? activeBg : 'transparent'}
          color={isActive ? activeColor : textColor}
          _hover={{ bg: hoverBg, color: 'fg.default' }}
        >
          {children}
        </Button>
      )}
    </NavLink>
  );
};

const SettingsShell: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const sectionColor = 'fg.muted';
  const [marketDataPublic, setMarketDataPublic] = React.useState(false);
  const [isDesktop] = useMediaQuery(['(min-width: 48em)']);

  React.useEffect(() => {
    // Default to brokerages if hitting /settings without child
    if (location.pathname.endsWith('/settings')) {
      navigate('/settings/brokerages', { replace: true });
    }
  }, []);

  React.useEffect(() => {
    const checkVisibility = async () => {
      try {
        const res = await api.get('/market-data/coverage');
        setMarketDataPublic(Boolean(res.data?.meta?.exposed_to_all));
      } catch {
        setMarketDataPublic(false);
      }
    };
    checkVisibility();
  }, []);

  const showMarketDataLinks = marketDataPublic || user?.role === 'admin';

  const iconNav = (to: string, label: string, icon: React.ReactNode) => (
    <NavLink to={to} style={{ textDecoration: 'none' }}>
      {({ isActive }) => (
        <TooltipRoot>
          <TooltipTrigger asChild>
            <IconButton
              aria-label={label}
              variant={isActive ? 'solid' : 'ghost'}
              colorScheme={isActive ? 'brand' : undefined}
              size="md"
            >
              {icon}
            </IconButton>
          </TooltipTrigger>
          <TooltipPositioner>
            <TooltipContent>{label}</TooltipContent>
          </TooltipPositioner>
        </TooltipRoot>
      )}
    </NavLink>
  );

  return (
    <Flex gap={6} p={4} w="full" minW={0} overflowX="hidden">
      {isDesktop ? (
        <Box w="260px" flexShrink={0}>
          <VStack align="stretch" gap={1}>
            <Text fontSize="sm" color={sectionColor} px={2}>ACCOUNT</Text>
            <MenuLink to="/settings/profile">Profile</MenuLink>
            <MenuLink to="/settings/preferences">Preferences</MenuLink>
            <MenuLink to="/settings/notifications">Notifications</MenuLink>
            {showMarketDataLinks && (
              <>
                <Text fontSize="sm" color={sectionColor} px={2} mt={4}>MARKET DATA</Text>
                <MenuLink to="/settings/market/coverage">Coverage</MenuLink>
                <MenuLink to="/settings/market/tracked">Tracked</MenuLink>
              </>
            )}
            <Text fontSize="sm" color={sectionColor} px={2} mt={4}>WORKSPACE</Text>
            <MenuLink to="/settings/brokerages">Brokerages</MenuLink>
            <MenuLink to="/settings/security">Security</MenuLink>
            {user?.role === 'admin' && (
              <>
                <Text fontSize="sm" color={sectionColor} px={2} mt={4}>ADMIN</Text>
                <MenuLink to="/settings/admin/dashboard">Dashboard</MenuLink>
                <MenuLink to="/settings/admin/jobs">Jobs</MenuLink>
                <MenuLink to="/settings/admin/schedules">Schedules</MenuLink>
                <MenuLink to="/settings/admin/runbook">Runbook</MenuLink>
              </>
            )}
          </VStack>
        </Box>
      ) : (
        <Box w="56px" flexShrink={0}>
          <VStack align="stretch" gap={2}>
            {iconNav('/settings/profile', 'Profile', <FiUser />)}
            {iconNav('/settings/preferences', 'Preferences', <FiSliders />)}
            {iconNav('/settings/notifications', 'Notifications', <FiBell />)}
            {showMarketDataLinks ? (
              <>
                {iconNav('/settings/market/coverage', 'Market Coverage', <FiActivity />)}
                {iconNav('/settings/market/tracked', 'Tracked Symbols', <FiGrid />)}
              </>
            ) : null}
            {iconNav('/settings/brokerages', 'Brokerages', <FiShield />)}
            {iconNav('/settings/security', 'Security', <FiLock />)}
            {user?.role === 'admin' ? (
              <>
                {iconNav('/settings/admin/dashboard', 'Admin Dashboard', <FiGrid />)}
                {iconNav('/settings/admin/jobs', 'Admin Jobs', <FiActivity />)}
                {iconNav('/settings/admin/schedules', 'Admin Schedules', <FiGrid />)}
                {iconNav('/settings/admin/runbook', 'Admin Runbook', <FiShield />)}
              </>
            ) : null}
          </VStack>
        </Box>
      )}
      <Box flex="1" minW={0} overflowX="hidden">
        <Outlet />
      </Box>
    </Flex>
  );
};

export default SettingsShell;




