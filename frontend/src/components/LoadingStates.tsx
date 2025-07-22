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
  useColorModeValue,
  Card,
  CardBody,
  Grid,
  GridItem,
  Flex,
  Progress
} from '@chakra-ui/react';

// Portfolio summary loading skeleton
export const PortfolioSummarySkeleton: React.FC = () => {
  const cardBg = useColorModeValue('white', 'gray.800');

  return (
    <Grid templateColumns="repeat(auto-fit, minmax(250px, 1fr))" gap={6}>
      {[1, 2, 3, 4].map((i) => (
        <Card key={i} bg={cardBg}>
          <CardBody>
            <VStack align="start" spacing={3}>
              <Skeleton height="20px" width="60%" />
              <Skeleton height="32px" width="80%" />
              <HStack>
                <SkeletonCircle size="4" />
                <Skeleton height="16px" width="40%" />
              </HStack>
            </VStack>
          </CardBody>
        </Card>
      ))}
    </Grid>
  );
};

// Holdings table loading skeleton
export const HoldingsTableSkeleton: React.FC<{ rows?: number }> = ({ rows = 10 }) => {
  const cardBg = useColorModeValue('white', 'gray.800');

  return (
    <Card bg={cardBg}>
      <CardBody>
        <VStack spacing={4} align="stretch">
          {/* Header skeleton */}
          <HStack justify="space-between">
            <Skeleton height="24px" width="150px" />
            <Skeleton height="32px" width="200px" />
          </HStack>

          {/* Table header */}
          <HStack spacing={4} py={2}>
            <Skeleton height="16px" width="80px" />
            <Skeleton height="16px" width="60px" />
            <Skeleton height="16px" width="80px" />
            <Skeleton height="16px" width="80px" />
            <Skeleton height="16px" width="60px" />
          </HStack>

          {/* Table rows */}
          {Array.from({ length: rows }).map((_, i) => (
            <HStack key={i} spacing={4} py={3} borderBottom="1px" borderColor="gray.100">
              <SkeletonCircle size="8" />
              <VStack align="start" flex={1} spacing={1}>
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
    </Card>
  );
};

// Transaction list loading skeleton
export const TransactionsSkeleton: React.FC<{ rows?: number }> = ({ rows = 15 }) => {
  const cardBg = useColorModeValue('white', 'gray.800');

  return (
    <Card bg={cardBg}>
      <CardBody>
        <VStack spacing={3} align="stretch">
          {/* Filter controls skeleton */}
          <HStack spacing={4} mb={4}>
            <Skeleton height="32px" width="150px" />
            <Skeleton height="32px" width="120px" />
            <Skeleton height="32px" width="100px" />
          </HStack>

          {/* Transaction rows */}
          {Array.from({ length: rows }).map((_, i) => (
            <HStack key={i} justify="space-between" p={3} borderRadius="md" border="1px" borderColor="gray.100">
              <HStack spacing={3}>
                <SkeletonCircle size="6" />
                <VStack align="start" spacing={1}>
                  <Skeleton height="16px" width="80px" />
                  <Skeleton height="12px" width="120px" />
                </VStack>
              </HStack>
              <VStack align="end" spacing={1}>
                <Skeleton height="16px" width="60px" />
                <Skeleton height="12px" width="40px" />
              </VStack>
            </HStack>
          ))}
        </VStack>
      </CardBody>
    </Card>
  );
};

// Options portfolio loading skeleton
export const OptionsPortfolioSkeleton: React.FC = () => {
  const cardBg = useColorModeValue('white', 'gray.800');

  return (
    <VStack spacing={6} align="stretch">
      {/* Summary cards */}
      <PortfolioSummarySkeleton />

      {/* Options positions */}
      <Card bg={cardBg}>
        <CardBody>
          <VStack spacing={4} align="stretch">
            <Skeleton height="24px" width="200px" />

            {[1, 2, 3, 4, 5].map((i) => (
              <Box key={i} p={4} borderRadius="md" border="1px" borderColor="gray.100">
                <HStack justify="space-between" mb={3}>
                  <VStack align="start" spacing={1}>
                    <Skeleton height="18px" width="100px" />
                    <Skeleton height="14px" width="150px" />
                  </VStack>
                  <VStack align="end" spacing={1}>
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
      </Card>
    </VStack>
  );
};

// Tax lots loading skeleton
export const TaxLotsSkeleton: React.FC = () => {
  const cardBg = useColorModeValue('white', 'gray.800');

  return (
    <VStack spacing={6} align="stretch">
      {/* Summary */}
      <Card bg={cardBg}>
        <CardBody>
          <HStack justify="space-between">
            <VStack align="start" spacing={2}>
              <Skeleton height="20px" width="120px" />
              <Skeleton height="32px" width="100px" />
            </VStack>
            <VStack align="end" spacing={2}>
              <Skeleton height="20px" width="140px" />
              <Skeleton height="32px" width="120px" />
            </VStack>
          </HStack>
        </CardBody>
      </Card>

      {/* Tax lots list */}
      <Card bg={cardBg}>
        <CardBody>
          <VStack spacing={4} align="stretch">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Box key={i} p={4} borderRadius="md" border="1px" borderColor="gray.100">
                <HStack justify="space-between" mb={3}>
                  <HStack spacing={3}>
                    <SkeletonCircle size="10" />
                    <VStack align="start" spacing={1}>
                      <Skeleton height="18px" width="60px" />
                      <Skeleton height="14px" width="80px" />
                    </VStack>
                  </HStack>
                  <VStack align="end" spacing={1}>
                    <Skeleton height="16px" width="80px" />
                    <Skeleton height="14px" width="60px" />
                  </VStack>
                </HStack>

                <Grid templateColumns="repeat(5, 1fr)" gap={4}>
                  <VStack spacing={1}>
                    <Skeleton height="12px" width="40px" />
                    <Skeleton height="16px" width="60px" />
                  </VStack>
                  <VStack spacing={1}>
                    <Skeleton height="12px" width="40px" />
                    <Skeleton height="16px" width="60px" />
                  </VStack>
                  <VStack spacing={1}>
                    <Skeleton height="12px" width="40px" />
                    <Skeleton height="16px" width="60px" />
                  </VStack>
                  <VStack spacing={1}>
                    <Skeleton height="12px" width="40px" />
                    <Skeleton height="16px" width="60px" />
                  </VStack>
                  <VStack spacing={1}>
                    <Skeleton height="12px" width="40px" />
                    <Skeleton height="16px" width="60px" />
                  </VStack>
                </Grid>
              </Box>
            ))}
          </VStack>
        </CardBody>
      </Card>
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
      <VStack spacing={4}>
        <Spinner size={size} color="blue.500" thickness="3px" speed="0.8s" />
        <Text fontSize="lg" color="gray.600" textAlign="center">
          {message}
        </Text>
        {showProgress && (
          <Box w="200px">
            <Progress value={progress} colorScheme="blue" size="sm" borderRadius="full" />
            <Text fontSize="sm" color="gray.500" textAlign="center" mt={1}>
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
  const overlayBg = useColorModeValue('rgba(255, 255, 255, 0.9)', 'rgba(26, 32, 44, 0.9)');

  if (!isVisible) return null;

  return (
    <Box
      position="fixed"
      top={0}
      left={0}
      right={0}
      bottom={0}
      bg={overlayBg}
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
export const MiniSpinner: React.FC<{ size?: string }> = ({ size = '16px' }) => {
  return (
    <Spinner
      size={size}
      color="currentColor"
      thickness="2px"
      speed="0.8s"
    />
  );
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