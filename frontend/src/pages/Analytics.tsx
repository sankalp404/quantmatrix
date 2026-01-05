import React from 'react';
import { Box, Text } from '@chakra-ui/react';
import AppCard from '../components/ui/AppCard';

const Analytics: React.FC = () => {
  return (
    <Box>
      <Text fontSize="2xl" fontWeight="bold" mb={6}>Analytics</Text>
      <AppCard>
        <Text color="fg.muted">Analytics dashboard coming soon...</Text>
      </AppCard>
    </Box>
  );
};

export default Analytics; 