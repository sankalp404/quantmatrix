import React from 'react';
import { Separator, type SeparatorProps } from '@chakra-ui/react';

export type AppDividerProps = SeparatorProps & { orientation?: 'horizontal' | 'vertical' };

/**
 * Chakra v3 compatibility shim:
 * Chakra v3 exports `Separator` (not `Divider`) and does not export `useColorModeValue`.
 * This wrapper gives us a stable <AppDivider /> API across the codebase.
 */
const AppDivider: React.FC<AppDividerProps> = ({ orientation = 'horizontal', ...props }) => (
  <Separator orientation={orientation} {...props} />
);

export default AppDivider;


