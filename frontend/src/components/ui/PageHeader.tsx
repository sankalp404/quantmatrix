import React from 'react';
import { Box, HStack, VStack, Heading, Text } from '@chakra-ui/react';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  rightContent?: React.ReactNode;
}

const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle, actions, rightContent }) => {
  return (
    <Box>
      <HStack justify="space-between" align="start" spacing={4} mb={2}>
        <VStack align="start" spacing={1}>
          <Heading size="lg">{title}</Heading>
          {subtitle && (
            <Text color="gray.500" fontSize="sm">
              {subtitle}
            </Text>
          )}
        </VStack>
        {rightContent}
      </HStack>
      {actions && <Box>{actions}</Box>}
    </Box>
  );
};

export default PageHeader;


