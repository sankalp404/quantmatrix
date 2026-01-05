import React from 'react';
import { Box, Text } from '@chakra-ui/react';
import { PageHeader } from '../components/ui/Page';
import AppCard from '../components/ui/AppCard';

const SettingsPreferences: React.FC = () => {
  return (
    <Box>
      <PageHeader title="Preferences" subtitle="UI and personal preferences (coming next)." />
      <AppCard>
        <Text color="fg.muted" fontSize="sm">
          This page is being migrated to Chakra v3. Preferences will live here.
        </Text>
      </AppCard>
    </Box>
  );
};

export default SettingsPreferences;


