import React from 'react';
import { Box, Text, Card, CardBody, useColorModeValue } from '@chakra-ui/react';

const Analytics: React.FC = () => {
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  return (
    <Box>
      <Text fontSize="2xl" fontWeight="bold" mb={6}>Analytics</Text>
      <Card bg={cardBg} border="1px" borderColor={borderColor}>
        <CardBody>
          <Text>Analytics dashboard coming soon...</Text>
        </CardBody>
      </Card>
    </Box>
  );
};

export default Analytics; 