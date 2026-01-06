import React from 'react';
import { Box, Text, CardRoot, CardBody, VStack, Badge } from '@chakra-ui/react';

const MultiPortfolio: React.FC = () => {
  return (
    <Box>
      <Text fontSize="lg" fontWeight="semibold" mb={3} color="fg.default">
        Multi-Portfolio
      </Text>

      <CardRoot bg="bg.card" borderWidth="1px" borderColor="border.subtle" borderRadius="xl">
        <CardBody>
          <VStack align="start" gap={2}>
            <Badge colorPalette="yellow">Under migration</Badge>
            <Text color="fg.muted">
              This page is being rebuilt on Chakra v3 (no v2-only alerts/tabs/modals/tables).
            </Text>
          </VStack>
        </CardBody>
      </CardRoot>
    </Box>
  );
};

export default MultiPortfolio;


