import React from 'react';
import { Box, type BoxProps } from '@chakra-ui/react';

type Props = BoxProps & { children: React.ReactNode };

/**
 *  auth shell:
 * - full-viewport center
 * - soft gradient background
 * - subtle border + glow
 */
export default function AuthLayout({ children, ...props }: Props) {
  return (
    <Box
      minH="100vh"
      display="flex"
      alignItems="center"
      justifyContent="center"
      px={{ base: 4, md: 8 }}
      py={{ base: 10, md: 14 }}
      bg="radial-gradient(1200px 600px at 20% 10%, rgba(42,121,240,0.22), transparent 55%), radial-gradient(900px 500px at 90% 20%, rgba(34,197,94,0.16), transparent 55%), #070B12"
      color="white"
      {...props}
    >
      {/* subtle vignette */}
      <Box
        position="absolute"
        inset={0}
        pointerEvents="none"
        bg="radial-gradient(900px 500px at 50% 20%, rgba(255,255,255,0.06), transparent 60%)"
      />
      <Box position="relative" w="full" maxW={{ base: '420px', md: '440px' }}>
        {children}
      </Box>
    </Box>
  );
}


