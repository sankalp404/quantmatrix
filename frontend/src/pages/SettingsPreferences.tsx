import React from 'react';
import { Box, HStack, VStack, Text, Button, Input } from '@chakra-ui/react';
import { PageHeader } from '../components/ui/Page';
import AppCard from '../components/ui/AppCard';
import hotToast from 'react-hot-toast';
import { authApi, handleApiError } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useColorMode } from '../theme/colorMode';

const SettingsPreferences: React.FC = () => {
  const { user, refreshMe } = useAuth();
  const { colorModePreference, setColorModePreference } = useColorMode();

  const [themePref, setThemePref] = React.useState<'system' | 'light' | 'dark'>('system');
  const [tableDensity, setTableDensity] = React.useState<'comfortable' | 'compact'>('comfortable');
  const [timezone, setTimezone] = React.useState<string>(user?.timezone || 'UTC');
  const [currency, setCurrency] = React.useState<string>((user?.currency_preference || 'USD').toUpperCase());
  const [saving, setSaving] = React.useState(false);

  const timezones = React.useMemo<string[]>(() => {
    try {
      const tzs = (Intl as any)?.supportedValuesOf?.('timeZone');
      if (Array.isArray(tzs) && tzs.length) return tzs;
    } catch { /* ignore */ }
    return ['UTC', 'America/New_York', 'America/Chicago', 'America/Los_Angeles', 'Europe/London'];
  }, []);

  React.useEffect(() => {
    const pref = user?.ui_preferences?.color_mode_preference;
    if (pref === 'system' || pref === 'light' || pref === 'dark') {
      setThemePref(pref);
    } else {
      // Fall back to local preference if user doesn't have a server-side value yet.
      setThemePref(colorModePreference);
    }
    const td = user?.ui_preferences?.table_density;
    if (td === 'comfortable' || td === 'compact') setTableDensity(td);
    setTimezone(user?.timezone || 'UTC');
    setCurrency((user?.currency_preference || 'USD').toUpperCase());
  }, [
    user?.timezone,
    user?.currency_preference,
    user?.ui_preferences?.color_mode_preference,
    user?.ui_preferences?.table_density,
    colorModePreference,
  ]);

  const save = async () => {
    try {
      setSaving(true);
      const payload = {
        timezone,
        currency_preference: currency.toUpperCase(),
        ui_preferences: {
          color_mode_preference: themePref,
          table_density: tableDensity,
        },
      };
      await authApi.updateMe(payload);
      setColorModePreference(themePref);
      await refreshMe();
      hotToast.success('Preferences saved');
    } catch (e) {
      hotToast.error(handleApiError(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box>
      <PageHeader title="Preferences" subtitle="Customize the UI and your personal defaults." />
      <VStack align="stretch" gap={4}>
        <AppCard>
          <VStack align="stretch" gap={4}>
            <Text fontWeight="semibold">Appearance</Text>
            <Box>
              <Text fontSize="sm" color="fg.muted" mb={2}>Theme</Text>
              <select
                value={themePref}
                onChange={(e) => setThemePref(e.target.value as any)}
                style={{
                  width: 280,
                  fontSize: 12,
                  padding: '8px 10px',
                  borderRadius: 10,
                  border: '1px solid rgba(255,255,255,0.14)',
                  background: 'var(--chakra-colors-bg-input, #0b1220)',
                  color: 'var(--chakra-colors-fg-default, #e5e7eb)',
                }}
              >
                <option value="system">Use system preference</option>
                <option value="light">Light</option>
                <option value="dark">Dark</option>
              </select>
            </Box>

            <Box>
              <Text fontSize="sm" color="fg.muted" mb={2}>Table density</Text>
              <select
                value={tableDensity}
                onChange={(e) => setTableDensity(e.target.value as any)}
                style={{
                  width: 280,
                  fontSize: 12,
                  padding: '8px 10px',
                  borderRadius: 10,
                  border: '1px solid rgba(255,255,255,0.14)',
                  background: 'var(--chakra-colors-bg-input, #0b1220)',
                  color: 'var(--chakra-colors-fg-default, #e5e7eb)',
                }}
              >
                <option value="comfortable">Comfortable</option>
                <option value="compact">Compact</option>
              </select>
            </Box>
          </VStack>
        </AppCard>

        <AppCard>
          <VStack align="stretch" gap={4}>
            <Text fontWeight="semibold">Locale</Text>
            <HStack gap={4} align="start" flexWrap="wrap">
              <Box flex="1" minW={{ base: "100%", md: "320px" }}>
                <Text fontSize="sm" color="fg.muted" mb={1}>Timezone</Text>
                <select
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  style={{
                    width: 280,
                    fontSize: 12,
                    padding: '8px 10px',
                    borderRadius: 10,
                    border: '1px solid rgba(255,255,255,0.14)',
                    background: 'var(--chakra-colors-bg-input, #0b1220)',
                    color: 'var(--chakra-colors-fg-default, #e5e7eb)',
                  }}
                >
                  {timezones.map((tz) => (
                    <option key={tz} value={tz}>{tz}</option>
                  ))}
                </select>
              </Box>
              <Box minW={{ base: "100%", md: "200px" }}>
                <Text fontSize="sm" color="fg.muted" mb={1}>Currency</Text>
                <Input value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} placeholder="USD" />
                <Text fontSize="xs" color="fg.muted" mt={1}>3-letter code (e.g. USD)</Text>
              </Box>
            </HStack>
          </VStack>
        </AppCard>

        <HStack justify="flex-end">
          <Button loading={saving} onClick={save}>Save preferences</Button>
        </HStack>
      </VStack>
    </Box>
  );
};

export default SettingsPreferences;


