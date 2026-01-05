import React from 'react';
import { Box, Text } from '@chakra-ui/react';
import { PageHeader } from '../components/ui/Page';
import AppCard from '../components/ui/AppCard';

const SettingsProfile: React.FC = () => {
  return (
    <Box>
      <PageHeader title="Profile" subtitle="Account profile settings (coming next)." />
      <AppCard>
        <Text color="fg.muted" fontSize="sm">
          This page is being migrated to Chakra v3. Profile management will land here.
        </Text>
      </AppCard>
    </Box>
  );
};

export default SettingsProfile;


