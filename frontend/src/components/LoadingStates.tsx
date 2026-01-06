import React from 'react';
import {
  Box,
  Skeleton,
  SkeletonText,
  SkeletonCircle,
  VStack,
  HStack,
  Spinner,
  Text,
  CardRoot,
  CardBody,
  Grid,
  GridItem,
  Flex,
  Progress,
} from '@chakra-ui/react';

// Portfolio summary loading skeleton
export const PortfolioSummarySkeleton: React.FC = () => {
  return (
    <Grid templateColumns="repeat(auto-fit, minmax(250px, 1fr))" gap={6}>
      {[1, 2, 3, 4].map((i) => (
        <CardRoot key={i} bg="bg.card" borderWidth="1px" borderColor="border.subtle" borderRadius="xl">
          <CardBody>
            <VStack align="start" gap={3}>
              <Skeleton height="20px" width="60%" />
              <Skeleton height="32px" width="80%" />
              <HStack>
                <SkeletonCircle size="4" />
                <Skeleton height="16px" width="40%" />
              </HStack>
            </VStack>
          </CardBody>
        </CardRoot>
      ))}
    </Grid>
  );
};

// Holdings table loading skeleton
export const HoldingsTableSkeleton: React.FC<{ rows?: number }> = ({ rows = 10 }) => {
  return (
    <CardRoot bg="bg.card" borderWidth="1px" borderColor="border.subtle" borderRadius="xl">
      <CardBody>
        <VStack gap={4} align="stretch">
          {/* Header skeleton */}
          <HStack justify="space-between">
            <Skeleton height="24px" width="150px" />
            <Skeleton height="32px" width="200px" />
          </HStack>

          {/* Table header */}
          <HStack gap={4} py={2}>
            <Skeleton height="16px" width="80px" />
            <Skeleton height="16px" width="60px" />
            <Skeleton height="16px" width="80px" />
            <Skeleton height="16px" width="80px" />
            <Skeleton height="16px" width="60px" />
          </HStack>

          {/* Table rows */}
          {Array.from({ length: rows }).map((_, i) => (
            <HStack key={i} gap={4} py={3} borderBottom="1px" borderColor="border.subtle">
              <SkeletonCircle size="8" />
              <VStack align="start" flex={1} gap={1}>
                <Skeleton height="16px" width="60px" />
                <Skeleton height="12px" width="40px" />
              </VStack>
              <Skeleton height="16px" width="60px" />
              <Skeleton height="16px" width="80px" />
              <Skeleton height="16px" width="60px" />
            </HStack>
          ))}
        </VStack>
      </CardBody>
    </CardRoot>
  );
};

// Transaction list loading skeleton
export const TransactionsSkeleton: React.FC<{ rows?: number }> = ({ rows = 15 }) => {
  return (
    <CardRoot bg="bg.card" borderWidth="1px" borderColor="border.subtle" borderRadius="xl">
      <CardBody>
        <VStack gap={3} align="stretch">
          {/* Filter controls skeleton */}
          <HStack gap={4} mb={4}>
            <Skeleton height="32px" width="150px" />
            <Skeleton height="32px" width="120px" />
            <Skeleton height="32px" width="100px" />
          </HStack>

          {/* Transaction rows */}
          {Array.from({ length: rows }).map((_, i) => (
            <HStack key={i} justify="space-between" p={3} borderRadius="lg" border="1px" borderColor="border.subtle">
              <HStack gap={3}>
                <SkeletonCircle size="6" />
                <VStack align="start" gap={1}>
                  <Skeleton height="16px" width="80px" />
                  <Skeleton height="12px" width="120px" />
                </VStack>
              </HStack>
              <VStack align="end" gap={1}>
                <Skeleton height="16px" width="60px" />
                <Skeleton height="12px" width="40px" />
              </VStack>
            </HStack>
          ))}
        </VStack>
      </CardBody>
    </CardRoot>
  );
};

// Options portfolio loading skeleton
export const OptionsPortfolioSkeleton: React.FC = () => {
  return (
    <VStack gap={6} align="stretch">
      {/* Summary cards */}
      <PortfolioSummarySkeleton />

      {/* Options positions */}
      <CardRoot bg="bg.card" borderWidth="1px" borderColor="border.subtle" borderRadius="xl">
        <CardBody>
          <VStack gap={4} align="stretch">
            <Skeleton height="24px" width="200px" />

            {[1, 2, 3, 4, 5].map((i) => (
              <Box key={i} p={4} borderRadius="md" borderWidth="1px" borderColor="border.subtle" bg="bg.panel">
                <HStack justify="space-between" mb={3}>
                  <VStack align="start" gap={1}>
                    <Skeleton height="18px" width="100px" />
                    <Skeleton height="14px" width="150px" />
                  </VStack>
                  <VStack align="end" gap={1}>
                    <Skeleton height="16px" width="80px" />
                    <Skeleton height="14px" width="60px" />
                  </VStack>
                </HStack>

                <Grid templateColumns="repeat(4, 1fr)" gap={4}>
                  <Skeleton height="12px" />
                  <Skeleton height="12px" />
                  <Skeleton height="12px" />
                  <Skeleton height="12px" />
                </Grid>
              </Box>
            ))}
          </VStack>
        </CardBody>
      </CardRoot>
    </VStack>
  );
};

// Tax lots loading skeleton
export const TaxLotsSkeleton: React.FC = () => {
  return (
    <VStack gap={6} align="stretch">
      {/* Summary */}
      <CardRoot bg="bg.card" borderWidth="1px" borderColor="border.subtle" borderRadius="xl">
        <CardBody>
          <HStack justify="space-between">
            <VStack align="start" gap={2}>
              <Skeleton height="20px" width="120px" />
              <Skeleton height="32px" width="100px" />
            </VStack>
            <VStack align="end" gap={2}>
              <Skeleton height="20px" width="140px" />
              <Skeleton height="32px" width="120px" />
            </VStack>
          </HStack>
        </CardBody>
      </CardRoot>

      {/* Tax lots list */}
      <CardRoot bg="bg.card" borderWidth="1px" borderColor="border.subtle" borderRadius="xl">
        <CardBody>
          <VStack gap={4} align="stretch">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Box key={i} p={4} borderRadius="md" borderWidth="1px" borderColor="border.subtle" bg="bg.panel">
                <HStack justify="space-between" mb={3}>
                  <HStack gap={3}>
                    <SkeletonCircle size="10" />
                    <VStack align="start" gap={1}>
                      <Skeleton height="18px" width="60px" />
                      <Skeleton height="14px" width="80px" />
                    </VStack>
                  </HStack>
                  <VStack align="end" gap={1}>
                    <Skeleton height="16px" width="80px" />
                    <Skeleton height="14px" width="60px" />
                  </VStack>
                </HStack>

                <Grid templateColumns="repeat(5, 1fr)" gap={4}>
                  <VStack gap={1}>
                    <Skeleton height="12px" width="40px" />
                    <Skeleton height="16px" width="60px" />
                  </VStack>
                  <VStack gap={1}>
                    <Skeleton height="12px" width="40px" />
                    <Skeleton height="16px" width="60px" />
                  </VStack>
                  <VStack gap={1}>
                    <Skeleton height="12px" width="40px" />
                    <Skeleton height="16px" width="60px" />
                  </VStack>
                  <VStack gap={1}>
                    <Skeleton height="12px" width="40px" />
                    <Skeleton height="16px" width="60px" />
                  </VStack>
                  <VStack gap={1}>
                    <Skeleton height="12px" width="40px" />
                    <Skeleton height="16px" width="60px" />
                  </VStack>
                </Grid>
              </Box>
            ))}
          </VStack>
        </CardBody>
      </CardRoot>
    </VStack>
  );
};

// Loading spinner with message
export const LoadingSpinner: React.FC<{
  message?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showProgress?: boolean;
  progress?: number;
}> = ({ message = 'Loading...', size = 'lg', showProgress = false, progress = 0 }) => {
  return (
    <Flex direction="column" align="center" justify="center" py={12} px={6} minH="200px">
      <VStack gap={4}>
        <Spinner size={size} color="brand.500" />
        <Text fontSize="lg" color="fg.muted" textAlign="center">
          {message}
        </Text>
        {showProgress && (
          <Box w="200px">
            <Progress.Root value={progress} max={100}>
              <Progress.Track borderRadius="full">
                <Progress.Range />
              </Progress.Track>
            </Progress.Root>
            <Text fontSize="sm" color="fg.muted" textAlign="center" mt={1}>
              {progress}%
            </Text>
          </Box>
        )}
      </VStack>
    </Flex>
  );
};

// Full page loading overlay
export const LoadingOverlay: React.FC<{
  message?: string;
  isVisible: boolean;
}> = ({ message = 'Loading...', isVisible }) => {
  if (!isVisible) return null;

  return (
    <Box
      position="fixed"
      top={0}
      left={0}
      right={0}
      bottom={0}
      bg="bg.canvas"
      opacity={0.92}
      display="flex"
      alignItems="center"
      justifyContent="center"
      zIndex={9999}
      backdropFilter="blur(2px)"
    >
      <LoadingSpinner message={message} size="xl" />
    </Box>
  );
};

// Mini loading indicator for buttons
export const MiniSpinner: React.FC<{ size?: 'sm' | 'md' | 'lg' | 'xl' }> = ({ size = 'sm' }) => {
  return <Spinner size={size} color="currentColor" />;
};

export default {
  PortfolioSummarySkeleton,
  HoldingsTableSkeleton,
  TransactionsSkeleton,
  OptionsPortfolioSkeleton,
  TaxLotsSkeleton,
  LoadingSpinner,
  LoadingOverlay,
  MiniSpinner
}; 