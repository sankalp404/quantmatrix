import React from 'react';
import { Box, Text } from '@chakra-ui/react';
import { PageHeader } from '../components/ui/Page';
import AppCard from '../components/ui/AppCard';

const SettingsSecurity: React.FC = () => {
  return (
    <Box>
      <PageHeader title="Security" subtitle="Security settings (coming next)." />
      <AppCard>
        <Text color="fg.muted" fontSize="sm">
          This page is being migrated to Chakra v3. Security settings will live here.
        </Text>
      </AppCard>
    </Box>
  );
};

export default SettingsSecurity;


