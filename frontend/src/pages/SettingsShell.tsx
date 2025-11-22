import React from 'react';
import { Box, Flex, VStack, Button, Text } from '@chakra-ui/react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';

const MenuLink: React.FC<{ to: string; children: React.ReactNode }> = ({ to, children }) => {
  return (
    <NavLink to={to} style={({ isActive }) => ({ textDecoration: 'none' })}>
      {({ isActive }) => (
        <Button variant={isActive ? 'solid' : 'ghost'} justifyContent="flex-start" width="100%">
          {children}
        </Button>
      )}
    </NavLink>
  );
};

const SettingsShell: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  React.useEffect(() => {
    // Default to brokerages if hitting /settings without child
    if (location.pathname.endsWith('/settings')) {
      navigate('/settings/brokerages', { replace: true });
    }
  }, []);

  return (
    <Flex gap={6} p={4}>
      <Box minW="240px">
        <VStack align="stretch" spacing={1}>
          <Text fontSize="sm" color="gray.400" px={2}>ACCOUNT</Text>
          <MenuLink to="/settings/profile">Profile</MenuLink>
          <MenuLink to="/settings/preferences">Preferences</MenuLink>
          <MenuLink to="/settings/notifications">Notifications</MenuLink>
          <Text fontSize="sm" color="gray.400" px={2} mt={4}>WORKSPACE</Text>
          <MenuLink to="/settings/brokerages">Brokerages</MenuLink>
          <MenuLink to="/settings/security">Security</MenuLink>
        </VStack>
      </Box>
      <Box flex="1">
        <Outlet />
      </Box>
    </Flex>
  );
};

export default SettingsShell;




