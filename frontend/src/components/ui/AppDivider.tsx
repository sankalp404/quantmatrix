import React from 'react';
import { Box, BoxProps, useColorModeValue } from '@chakra-ui/react';

export type AppDividerProps = BoxProps & {
  orientation?: 'horizontal' | 'vertical';
};

/**
 * Chakra v3 compatibility shim:
 * Chakra v2 exported Divider from @chakra-ui/react; in v3 this can differ.
 * We implement a stable divider using Box borders.
 */
const AppDivider: React.FC<AppDividerProps> = ({ orientation = 'horizontal', ...props }) => {
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const resolved = (props as any).borderColor ?? borderColor;

  if (orientation === 'vertical') {
    return (
      <Box
        alignSelf="stretch"
        borderLeftWidth="1px"
        borderLeftColor={resolved}
        {...props}
      />
    );
  }

  return (
    <Box
      w="full"
      borderBottomWidth="1px"
      borderBottomColor={resolved}
      {...props}
    />
  );
};

export default AppDivider;


