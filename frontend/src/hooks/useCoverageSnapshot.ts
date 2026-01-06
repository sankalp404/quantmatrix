import { useCallback, useEffect, useMemo, useState } from 'react';
import api from '../services/api';
import {
  buildCoverageActions,
  buildCoverageKpis,
  CoverageAction,
  CoverageHeroMeta,
  CoverageKpi,
  CoverageSparkline,
  deriveSparklineSeries,
  formatCoverageHero,
} from '../utils/coverage';

interface UseCoverageSnapshotResult {
  snapshot: any | null;
  loading: boolean;
  refresh: () => Promise<void>;
  sparkline: CoverageSparkline;
  kpis: CoverageKpi[];
  actions: CoverageAction[];
  hero: CoverageHeroMeta;
}

const defaultSparkline = deriveSparklineSeries();

const useCoverageSnapshot = (): UseCoverageSnapshotResult => {
  const [snapshot, setSnapshot] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchSnapshot = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/market-data/coverage');
      setSnapshot(response.data || null);
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('Failed to load coverage snapshot', error);
      }
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSnapshot();
  }, [fetchSnapshot]);

  const sparkline = useMemo(
    () =>
      deriveSparklineSeries(snapshot?.meta?.sparkline, snapshot?.history || snapshot?.meta?.history),
    [snapshot],
  );

  const kpis = useMemo(
    () => buildCoverageKpis(snapshot?.meta?.kpis, snapshot, snapshot?.status),
    [snapshot],
  );

  const actions = useMemo(
    () => buildCoverageActions(snapshot?.meta?.actions),
    [snapshot],
  );

  const hero = useMemo(() => formatCoverageHero(snapshot), [snapshot]);

  return {
    snapshot,
    loading,
    refresh: fetchSnapshot,
    sparkline: sparkline || defaultSparkline,
    kpis,
    actions,
    hero,
  };
};

export default useCoverageSnapshot;

