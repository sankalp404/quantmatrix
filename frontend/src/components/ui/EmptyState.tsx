import React from 'react';
import { Box, VStack, Heading, Text, Icon, Button } from '@chakra-ui/react';

interface EmptyStateProps {
  icon?: React.ElementType;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
  secondaryAction?: { label: string; onClick: () => void };
}

const EmptyState: React.FC<EmptyStateProps> = ({ icon, title, description, action, secondaryAction }) => {
  return (
    <Box textAlign="center" py={12}>
      <VStack gap={3}>
        {icon && <Icon as={icon} boxSize={10} color="fg.muted" />}
        <Heading size="md" color="fg.default">{title}</Heading>
        {description && (
          <Text color="fg.muted" maxW="3xl">
            {description}
          </Text>
        )}
        <VStack gap={2}>
          {action && (
            <Button bg="brand.500" _hover={{ bg: "brand.400" }} onClick={action.onClick}>
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <Button variant="ghost" onClick={secondaryAction.onClick}>
              {secondaryAction.label}
            </Button>
          )}
        </VStack>
      </VStack>
    </Box>
  );
};

export default EmptyState;


