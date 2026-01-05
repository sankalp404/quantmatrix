import React from 'react';
import { Box, HStack, Text } from '@chakra-ui/react';
import { useColorMode } from '../theme/colorMode';
import {
  PortfolioSummarySkeleton,
  HoldingsTableSkeleton,
  TransactionsSkeleton,
  LoadingSpinner,
  LoadingOverlay,
} from '../components/LoadingStates';

export default {
  title: 'DesignSystem/LoadingStates',
};

export const Skeletons_And_Spinners = () => {
  const { colorMode, toggleColorMode } = useColorMode();
  const [overlay, setOverlay] = React.useState(false);

  return (
    <Box p={6}>
      <HStack justify="space-between" mb={5}>
        <Box>
          <Text fontSize="lg" fontWeight="semibold" color="fg.default">Loading states</Text>
          <Text fontSize="sm" color="fg.muted">Mode: {colorMode}</Text>
        </Box>
        <HStack gap={2}>
          <Text
            as="button"
            onClick={toggleColorMode}
            style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.12)' }}
          >
            Toggle mode
          </Text>
          <Text
            as="button"
            onClick={() => setOverlay((v) => !v)}
            style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.12)' }}
          >
            Toggle overlay
          </Text>
        </HStack>
      </HStack>

      <Box display="flex" flexDirection="column" gap={6}>
        <Box>
          <Text fontSize="sm" fontWeight="semibold" color="fg.default" mb={3}>Portfolio summary</Text>
          <PortfolioSummarySkeleton />
        </Box>

        <Box>
          <Text fontSize="sm" fontWeight="semibold" color="fg.default" mb={3}>Holdings table</Text>
          <HoldingsTableSkeleton rows={7} />
        </Box>

        <Box>
          <Text fontSize="sm" fontWeight="semibold" color="fg.default" mb={3}>Transactions list</Text>
          <TransactionsSkeleton rows={8} />
        </Box>

        <Box borderWidth="1px" borderColor="border.subtle" borderRadius="xl" bg="bg.card" p={4}>
          <Text fontSize="sm" fontWeight="semibold" color="fg.default" mb={2}>Spinner</Text>
          <LoadingSpinner message="Syncing data…" showProgress progress={42} />
        </Box>
      </Box>

      <LoadingOverlay isVisible={overlay} message="Loading overlay…" />
    </Box>
  );
};


