import React from 'react';
import { Box, Heading, Stack, Text } from '@chakra-ui/react';
import useCoverageSnapshot from '../hooks/useCoverageSnapshot';
import {
  CoverageBucketsGrid,
  CoverageKpiGrid,
  CoverageSummaryCard,
  CoverageTrendGrid,
} from '../components/coverage/CoverageSummaryCard';

/**
 * Market Data Coverage page (read-only).
 * Shows concise status/KPIs only; admin controls and raw tables live on Admin Dashboard.
 */
const MarketCoverage: React.FC = () => {
  const { snapshot: coverage, loading, sparkline, kpis, hero } = useCoverageSnapshot();

  return (
    <Box p={4}>
      <Stack gap={6}>
        <Stack gap={2}>
          <Heading size="md">Market Coverage</Heading>
          <Text color="gray.400">
            Shows how many tracked symbols have fresh prices. Daily should stay above 95%, and 5m bars should refresh at least once per trading day.
          </Text>
        </Stack>

        {coverage && (
          <CoverageSummaryCard hero={hero} status={coverage.status}>
            <CoverageKpiGrid kpis={kpis} variant="compact" />
            <CoverageTrendGrid sparkline={sparkline} />
            <CoverageBucketsGrid groups={hero?.buckets || []} />
          </CoverageSummaryCard>
        )}

        {!coverage && !loading && <Text color="gray.400">No coverage yet.</Text>}
      </Stack>
    </Box>
  );
};

export default MarketCoverage;

