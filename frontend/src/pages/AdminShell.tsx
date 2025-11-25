import React from 'react';
import { Box, Flex, Text, VStack, Button, useColorModeValue } from '@chakra-ui/react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const MenuLink: React.FC<{ to: string; children: React.ReactNode }> = ({ to, children }) => {
  const activeBg = useColorModeValue('gray.100', 'gray.800');
  return (
    <NavLink to={to}>
      {({ isActive }) => (
        <Button
          justifyContent="flex-start"
          w="100%"
          variant={isActive ? 'solid' : 'ghost'}
          colorScheme={isActive ? 'brand' : 'gray'}
          bg={isActive ? activeBg : 'transparent'}
        >
          {children}
        </Button>
      )}
    </NavLink>
  );
};

const AdminShell: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  React.useEffect(() => {
    if (user?.role !== 'admin') {
      navigate('/', { replace: true });
      return;
    }
    if (location.pathname.endsWith('/admin')) {
      navigate('/admin/dashboard', { replace: true });
    }
  }, []);

  return (
    <Flex gap={6} p={4}>
      <Box minW="260px">
        <VStack align="stretch" spacing={1}>
          <Text fontSize="sm" color="gray.400" px={2}>ADMIN</Text>
          <MenuLink to="/admin/dashboard">Dashboard</MenuLink>
          <MenuLink to="/admin/jobs">Jobs</MenuLink>
          <MenuLink to="/admin/schedules">Schedules</MenuLink>
          <MenuLink to="/admin/coverage">Coverage</MenuLink>
          <MenuLink to="/admin/tracked">Tracked</MenuLink>
        </VStack>
      </Box>
      <Box flex="1">
        <Outlet />
      </Box>
    </Flex>
  );
};

export default AdminShell;



