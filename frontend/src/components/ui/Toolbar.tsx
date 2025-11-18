import React from 'react';
import { Box, Flex } from '@chakra-ui/react';

interface ToolbarProps {
  children: React.ReactNode;
}

const Toolbar: React.FC<ToolbarProps> = ({ children }) => {
  return (
    <Box border="1px" borderColor="gray.600" borderRadius="md" p={3} bg="gray.800">
      <Flex wrap="wrap" gap={4} align="center">
        {children}
      </Flex>
    </Box>
  );
};

export default Toolbar;


