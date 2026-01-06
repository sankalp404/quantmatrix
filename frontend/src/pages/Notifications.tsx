import React from 'react';
import { Box, Text, CardRoot, CardBody, VStack, Badge } from '@chakra-ui/react';

const Notifications: React.FC = () => {
  return (
    <Box>
      <Text fontSize="lg" fontWeight="semibold" mb={3} color="fg.default">
        Notifications
      </Text>

      <CardRoot bg="bg.card" borderWidth="1px" borderColor="border.subtle" borderRadius="xl">
        <CardBody>
          <VStack align="start" gap={2}>
            <Badge colorPalette="yellow">Under migration</Badge>
            <Text color="fg.muted">
              This page is being migrated to Chakra v3.
            </Text>
          </VStack>
        </CardBody>
      </CardRoot>
    </Box>
  );
};

export default Notifications;


