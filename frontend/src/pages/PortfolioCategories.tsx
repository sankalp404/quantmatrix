import React from 'react';
import { Box, Text, CardRoot, CardBody, VStack, Badge } from '@chakra-ui/react';

const PortfolioCategories: React.FC = () => {
  return (
    <Box>
      <Text fontSize="lg" fontWeight="semibold" mb={3} color="fg.default">
        Portfolio Categories
      </Text>

      <CardRoot bg="bg.card" borderWidth="1px" borderColor="border.subtle" borderRadius="xl">
        <CardBody>
          <VStack align="start" gap={2}>
            <Badge colorPalette="yellow">Under migration</Badge>
            <Text color="fg.muted">
              This page was still using Chakra v2-only components (dialogs/forms/table parts) and was crashing the app.
              It's now a v3-safe shell so the rest of the UI can load.
            </Text>
            <Text color="fg.muted">
              Next: reintroduce category CRUD using v3 dialogs, native selects, and the shared SortableTable.
            </Text>
          </VStack>
        </CardBody>
      </CardRoot>
    </Box>
  );
};

export default PortfolioCategories;


