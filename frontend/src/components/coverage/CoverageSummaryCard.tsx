import React from 'react';
import { Box, Heading, Stack, Text } from '@chakra-ui/react';
import type {
  CoverageAction,
  CoverageBucketGroup,
  CoverageHeroMeta,
  CoverageKpi,
  CoverageSparkline,
} from '../../utils/coverage';

export interface CoverageSummaryCardProps {
  hero: CoverageHeroMeta;
  status?: any;
  children?: React.ReactNode;
}

/**
 * Lightweight, read-only coverage summary container.
 * (Kept intentionally dependency-light to avoid charting/DOM issues in CI.)
 */
export const CoverageSummaryCard: React.FC<CoverageSummaryCardProps> = ({ hero, children }) => {
  return (
    <Box borderWidth="1px" borderRadius="md" p={4}>
      <Stack gap={3}>
        <Box>
          <Heading size="sm">Coverage Status</Heading>
          <Text fontSize="sm" color="gray.400">
            {hero.statusLabel} · Updated {hero.updatedRelative} ({hero.updatedDisplay})
          </Text>
          <Text mt={1}>{hero.summary}</Text>
          {hero.warningBanner ? (
            <Box mt={2} borderWidth="1px" borderRadius="md" p={3}>
              <Text fontWeight="semibold">{hero.warningBanner.title}</Text>
              {hero.warningBanner.description ? (
                <Text fontSize="sm" color="gray.400">
                  {hero.warningBanner.description}
                </Text>
              ) : null}
            </Box>
          ) : null}
        </Box>

        {children ? <Box>{children}</Box> : null}
      </Stack>
    </Box>
  );
};

export interface CoverageKpiGridProps {
  kpis: CoverageKpi[];
  variant?: 'compact' | 'stat' | string;
}

export const CoverageKpiGrid: React.FC<CoverageKpiGridProps> = ({ kpis }) => {
  return (
    <Box>
      <Heading size="xs" mb={2}>
        KPIs
      </Heading>
      <Box display="grid" gridTemplateColumns="repeat(auto-fit, minmax(160px, 1fr))" gap={3}>
        {kpis.map((kpi) => (
          <Box key={kpi.id} borderWidth="1px" borderRadius="md" p={3}>
            <Text fontSize="xs" color="gray.400">
              {kpi.label}
            </Text>
            <Text fontSize="lg" fontWeight="semibold">
              {kpi.value ?? '—'}
              {kpi.unit ? ` ${kpi.unit}` : ''}
            </Text>
            {kpi.help ? (
              <Text fontSize="xs" color="gray.500">
                {kpi.help}
              </Text>
            ) : null}
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export interface CoverageTrendGridProps {
  sparkline: CoverageSparkline;
}

export const CoverageTrendGrid: React.FC<CoverageTrendGridProps> = ({ sparkline }) => {
  const daily = sparkline.daily_pct?.[sparkline.daily_pct.length - 1];
  const m5 = sparkline.m5_pct?.[sparkline.m5_pct.length - 1];

  return (
    <Box mt={4}>
      <Heading size="xs" mb={2}>
        Trend (latest)
      </Heading>
      <Box display="grid" gridTemplateColumns="repeat(auto-fit, minmax(160px, 1fr))" gap={3}>
        <Box borderWidth="1px" borderRadius="md" p={3}>
          <Text fontSize="xs" color="gray.400">
            Daily coverage %
          </Text>
          <Text fontSize="lg" fontWeight="semibold">
            {typeof daily === 'number' ? daily.toFixed(1) : '—'}%
          </Text>
        </Box>
        <Box borderWidth="1px" borderRadius="md" p={3}>
          <Text fontSize="xs" color="gray.400">
            5m coverage %
          </Text>
          <Text fontSize="lg" fontWeight="semibold">
            {typeof m5 === 'number' ? m5.toFixed(1) : '—'}%
          </Text>
        </Box>
      </Box>
    </Box>
  );
};

export interface CoverageBucketsGridProps {
  groups: CoverageBucketGroup[];
}

export const CoverageBucketsGrid: React.FC<CoverageBucketsGridProps> = ({ groups }) => {
  return (
    <Box mt={4}>
      <Heading size="xs" mb={2}>
        Freshness Buckets
      </Heading>
      <Box display="grid" gridTemplateColumns="repeat(auto-fit, minmax(240px, 1fr))" gap={3}>
        {groups.map((group) => (
          <Box key={group.interval} borderWidth="1px" borderRadius="md" p={3}>
            <Text fontWeight="semibold" mb={2}>
              {group.title}
            </Text>
            <Stack gap={1}>
              {group.buckets.map((b) => (
                <Box key={b.label} display="flex" justifyContent="space-between">
                  <Text fontSize="sm" color="gray.400">
                    {b.label}
                  </Text>
                  <Text fontSize="sm" fontWeight="semibold">
                    {b.count}
                  </Text>
                </Box>
              ))}
            </Stack>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export interface CoverageActionsListProps {
  actions: CoverageAction[];
  onRun: (taskName: string, label?: string) => Promise<void> | void;
  buttonRenderer?: (action: CoverageAction, handleClick: () => void) => React.ReactNode;
}

export const CoverageActionsList: React.FC<CoverageActionsListProps> = ({
  actions,
  onRun,
  buttonRenderer,
}) => {
  return (
    <Stack gap={2}>
      {actions.map((action) => {
        const handleClick = () => void onRun(action.task_name, action.label);
        return (
          <Box
            key={action.task_name}
            borderWidth="1px"
            borderRadius="md"
            p={3}
            display="flex"
            alignItems="center"
            justifyContent="space-between"
            gap={3}
          >
            <Box>
              <Text fontWeight="semibold">{action.label}</Text>
              {action.description ? (
                <Text fontSize="sm" color="gray.400">
                  {action.description}
                </Text>
              ) : null}
            </Box>
            <Box>
              {buttonRenderer ? (
                buttonRenderer(action, handleClick)
              ) : (
                <button disabled={Boolean(action.disabled)} onClick={handleClick}>
                  Run
                </button>
              )}
            </Box>
          </Box>
        );
      })}
    </Stack>
  );
};

import React from 'react';
import {
  Badge,
  BadgeProps,
  Box,
  HStack,
  SimpleGrid,
  Stack,
  AlertRoot,
  AlertIndicator,
  AlertTitle,
  AlertDescription,
  Separator,
  StatRoot,
  StatLabel,
  StatValueText,
  StatHelpText,
  Text,
} from '@chakra-ui/react';
import Sparkline from '../charts/Sparkline';
import {
  CoverageBucketGroup,
  CoverageHeroMeta,
  CoverageKpi,
  CoverageSparkline,
} from '../../utils/coverage';

type CoverageSummaryCardProps = {
  hero?: CoverageHeroMeta | null;
  status?: Record<string, any> | null;
  children?: React.ReactNode;
};

export const CoverageSummaryCard: React.FC<CoverageSummaryCardProps> = ({
  hero,
  status,
  children,
}) => {
  if (!hero) return null;

  const statusLabel = hero.statusLabel || status?.label || 'UNKNOWN';
  const summary = hero.summary || status?.summary || 'No summary yet.';
  const source = hero.source || status?.source || 'db';
  const staleCounts = hero.staleCounts || { daily: 0, m5: 0 };
  const badgeColor = hero.statusColor || 'gray';
  const timeline = hero.updatedDisplay
    ? `Updated ${hero.updatedDisplay} (${source}) • ${hero.updatedRelative}`
    : null;

  const pills = [
    { label: 'Tracked', value: hero.trackedCount?.toLocaleString() ?? '0', colorScheme: 'cyan' as const },
    {
      label: 'Universe',
      value: hero.totalSymbols?.toLocaleString() ?? '0',
      colorScheme: 'purple' as const,
    },
    {
      label: 'History samples',
      value: hero.historySamples ?? 0,
      colorScheme: 'teal' as const,
      hidden: (hero.historySamples ?? 0) === 0,
    },
    { label: 'Stale daily', value: staleCounts.daily ?? 0, colorScheme: 'orange' as const },
    { label: 'Stale 5m', value: staleCounts.m5 ?? 0, colorScheme: 'orange' as const },
    { label: 'Source', value: (source || 'db').toUpperCase(), colorScheme: 'gray' as const },
    { label: 'Snapshot age', value: hero.updatedRelative || '—', colorScheme: 'gray' as const },
  ].filter((pill) => !pill.hidden);

  const warningBanner = hero.warningBanner;
  const sla = hero.sla;

  return (
    <Box border="1px solid" borderColor="surface.border" bg="surface.card" borderRadius="lg" p={4} mb={6}>
      <HStack justify="space-between" align="flex-start" flexWrap="wrap" gap={3}>
        <Stack gap={1} flex="1 1 300px">
          <Text fontSize="xs" textTransform="uppercase" letterSpacing="wide" color="gray.500">
            Coverage status
          </Text>
          <Text fontSize="lg" fontWeight="semibold">{summary}</Text>
          {timeline && (
            <Text fontSize="xs" color="gray.500">
              {timeline}
            </Text>
          )}
          <Text fontSize="xs" color="gray.500">
            Stale daily: {staleCounts.daily} • Stale 5m: {staleCounts.m5}
          </Text>
        </Stack>
        <Badge colorScheme={badgeColor} fontSize="sm" px={3} py={1} borderRadius="md">
          {statusLabel}
        </Badge>
      </HStack>
      <HStack gap={2} flexWrap="wrap" mt={2}>
        {pills.map((pill) => (
          <HeroPill key={`${pill.label}-${pill.value}`} label={pill.label} value={pill.value} colorScheme={pill.colorScheme} />
        ))}
      </HStack>
      <Separator my={4} />
      {warningBanner && (
        <AlertRoot status={warningBanner.status} borderRadius="md" mb={4} bg="surface.muted">
          <AlertIndicator />
          <Stack gap={0}>
            <AlertTitle fontSize="sm">{warningBanner.title}</AlertTitle>
            {warningBanner.description ? (
              <AlertDescription fontSize="xs">{warningBanner.description}</AlertDescription>
            ) : null}
          </Stack>
        </AlertRoot>
      )}
      {sla && (
        <AlertRoot status="info" borderRadius="md" mb={4} bg="surface.muted">
          <AlertIndicator />
          <Stack gap={0}>
            <AlertTitle fontSize="sm">Coverage SLA</AlertTitle>
            <AlertDescription fontSize="xs">
              Daily ≥ {sla.daily_pct ?? 0}% • 5m refresh expectation: {sla.m5_expectation || '≥1 refresh/day'}
            </AlertDescription>
          </Stack>
        </AlertRoot>
      )}
      {children}
    </Box>
  );
};

type HeroPillProps = {
  label: string;
  value: React.ReactNode;
  colorScheme?: BadgeProps['colorScheme'];
};

const HeroPill: React.FC<HeroPillProps> = ({ label, value, colorScheme = 'gray' }) => (
  <Badge
    colorScheme={colorScheme}
    variant="subtle"
    fontSize="xs"
    px={3}
    py={1}
    borderRadius="full"
  >
    {label}: {value}
  </Badge>
);

type CoverageKpiGridProps = {
  kpis?: CoverageKpi[];
  variant?: 'stat' | 'compact';
};

const formatKpiValue = (value: any, unit?: string) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  if (unit === '%' && typeof value === 'number') {
    return `${value}%`;
  }
  return value;
};

export const CoverageKpiGrid: React.FC<CoverageKpiGridProps> = ({ kpis = [], variant = 'stat' }) => {
  if (!kpis.length) return null;
  const columns = variant === 'stat' ? [1, 2, 4] : [1, 2, 2, 4];

  return (
    <SimpleGrid columns={columns} gap={4}>
      {kpis.map((card) =>
        variant === 'stat' ? (
          <StatRoot key={card.id} p={4} border="1px solid" borderColor="surface.border" borderRadius="lg" bg="surface.card">
            <StatLabel>{card.label}</StatLabel>
            <StatValueText>{formatKpiValue(card.value, card.unit)}</StatValueText>
            {card.help ? <StatHelpText>{card.help}</StatHelpText> : null}
          </StatRoot>
        ) : (
          <Box
            key={card.id}
            p={4}
            border="1px solid"
            borderColor="surface.border"
            borderRadius="lg"
            bg="surface.card"
          >
            <Text fontSize="sm" color="gray.400">{card.label}</Text>
            <Text fontSize="2xl" fontWeight="bold">{formatKpiValue(card.value, card.unit)}</Text>
            {card.help ? <Text fontSize="xs" color="gray.500">{card.help}</Text> : null}
          </Box>
        ),
      )}
    </SimpleGrid>
  );
};

type CoverageTrendGridProps = {
  sparkline?: CoverageSparkline | null;
  limit?: number;
};

export const CoverageTrendGrid: React.FC<CoverageTrendGridProps> = ({ sparkline, limit = 24 }) => {
  if (!sparkline) return null;
  const daily = (sparkline.daily_pct || []).slice(-limit);
  const m5 = (sparkline.m5_pct || []).slice(-limit);
  const dailyMax = Math.max(...daily, 100);
  const m5Max = Math.max(...m5, 100);

  return (
    <SimpleGrid columns={[1, 2]} gap={4} mt={4}>
      <Box>
        <Text fontSize="sm" color="gray.400" mb={1}>Daily coverage trend</Text>
        <Sparkline values={daily} color="green.400" max={dailyMax} />
      </Box>
      <Box>
        <Text fontSize="sm" color="gray.400" mb={1}>5m coverage trend</Text>
        <Sparkline values={m5} color="blue.300" max={m5Max} />
      </Box>
    </SimpleGrid>
  );
};

type CoverageBucketsGridProps = {
  groups?: CoverageBucketGroup[] | null;
};

export const CoverageBucketsGrid: React.FC<CoverageBucketsGridProps> = ({ groups }) => {
  if (!groups || groups.length === 0) return null;
  const bgMuted = 'surface.muted';

  return (
    <SimpleGrid columns={[1, 2]} gap={4} mt={4}>
      {groups.map((group) => (
        <Box
          key={group.interval}
          p={3}
          border="1px solid"
          borderColor="surface.border"
          borderRadius="lg"
          bg={bgMuted}
        >
          <Text fontSize="sm" color="gray.400" mb={2}>{group.title}</Text>
          <HStack gap={4} flexWrap="wrap">
            {group.buckets.map((bucket) => (
              <Stack key={`${group.interval}-${bucket.label}`} gap={0}>
                <Text fontSize="xs" color="gray.500">{bucket.label}</Text>
                <Text fontWeight="semibold">{bucket.count}</Text>
              </Stack>
            ))}
          </HStack>
        </Box>
      ))}
    </SimpleGrid>
  );
};

type CoverageActionsListProps = {
  actions?: Array<{ task_name: string; label: string; description?: string; disabled?: boolean }>;
  onRun: (taskName: string, label: string) => Promise<void> | void;
  buttonRenderer: (action: { task_name: string; label: string; description?: string; disabled?: boolean }, onClick: () => void) => React.ReactNode;
};

export const CoverageActionsList: React.FC<CoverageActionsListProps> = ({ actions = [], onRun, buttonRenderer }) => {
  if (!actions.length) return null;

  return (
    <HStack gap={4} align="flex-start" flexWrap="wrap">
      {actions.map((action) => {
        const handleClick = () => onRun(action.task_name, action.label);
        return (
          <Stack key={action.task_name} gap={1} maxW="260px">
            {buttonRenderer(action, handleClick)}
            {action.description ? (
              <Text
                fontSize="xs"
                color="gray.400"
                whiteSpace="nowrap"
                overflowX="auto"
                px={1}
              >
                {action.description}
              </Text>
            ) : null}
          </Stack>
        );
      })}
    </HStack>
  );
};


