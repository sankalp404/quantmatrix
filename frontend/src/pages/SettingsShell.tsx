import React from 'react';
import { Box, Flex, VStack, Button, Text, useColorModeValue } from '@chakra-ui/react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const MenuLink: React.FC<{ to: string; children: React.ReactNode }> = ({ to, children }) => {
  const activeBg = useColorModeValue('white', 'rgba(255,255,255,0.08)');
  const hoverBg = useColorModeValue('rgba(74, 118, 255, 0.12)', 'rgba(255,255,255,0.05)');
  const activeColor = useColorModeValue('brand.600', 'brand.200');
  const textColor = useColorModeValue('gray.800', 'gray.100');
  return (
    <NavLink to={to} style={({ isActive }) => ({ textDecoration: 'none' })}>
      {({ isActive }) => (
        <Button
          variant="ghost"
          justifyContent="flex-start"
          width="100%"
          bg={isActive ? activeBg : 'transparent'}
          color={isActive ? activeColor : textColor}
          _hover={{ bg: hoverBg, color: activeColor }}
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
  const sectionColor = useColorModeValue('gray.600', 'gray.400');
  const [marketDataPublic, setMarketDataPublic] = React.useState(false);

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

  return (
    <Flex gap={6} p={4}>
      <Box minW="240px">
        <VStack align="stretch" spacing={1}>
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
      <Box flex="1">
        <Outlet />
      </Box>
    </Flex>
  );
};

export default SettingsShell;




