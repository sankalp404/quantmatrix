import React from 'react';
import { Box, Text, Card, CardBody, useColorModeValue } from '@chakra-ui/react';

const Settings: React.FC = () => {
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  return (
    <Box>
      <Text fontSize="2xl" fontWeight="bold" mb={6}>Settings</Text>
      <Card bg={cardBg} border="1px" borderColor={borderColor}>
        <CardBody>
          <Text>Application settings coming soon...</Text>
        </CardBody>
      </Card>
    </Box>
  );
};

export default Settings; 