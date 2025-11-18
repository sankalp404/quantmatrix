import { useCallback, useEffect, useState } from 'react';
import { flexqueryApi } from '../services/api';

export interface FlexQueryStatus {
  configured: boolean;
  status: string;
  token_configured?: boolean;
  query_id_configured?: boolean;
  setup_instructions?: any;
}

export function useFlexQuery() {
  const [status, setStatus] = useState<FlexQueryStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await flexqueryApi.getStatus();
      setStatus(res as unknown as FlexQueryStatus);
    } catch (e: any) {
      setError(e?.message || 'Failed to load FlexQuery status');
    } finally {
      setLoading(false);
    }
  }, []);

  const syncTaxLots = useCallback(async (accountId: string) => {
    try {
      setLoading(true);
      setError(null);
      const res = await flexqueryApi.syncTaxLots(accountId);
      return res;
    } catch (e: any) {
      setError(e?.message || 'Failed to sync tax lots');
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { status, loading, error, refresh, syncTaxLots };
}

export default useFlexQuery;


