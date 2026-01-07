import { useMemo } from "react";
import { useAuthOptional } from "../context/AuthContext";

export type TableDensity = "comfortable" | "compact";

export function useUserPreferences(): {
  currency: string;
  timezone: string;
  tableDensity: TableDensity;
} {
  const auth = useAuthOptional();
  const user = auth?.user ?? null;

  return useMemo(() => {
    const currency = (user?.currency_preference || "USD").toUpperCase();
    const timezone = user?.timezone || "UTC";
    const td = user?.ui_preferences?.table_density;
    const tableDensity: TableDensity = td === "compact" ? "compact" : "comfortable";
    return { currency, timezone, tableDensity };
  }, [user?.currency_preference, user?.timezone, user?.ui_preferences?.table_density]);
}


