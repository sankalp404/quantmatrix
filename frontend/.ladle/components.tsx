import React from "react";
import { ChakraProvider } from "@chakra-ui/react";
import { system } from "../src/theme/system";
import { ColorModeProvider } from "../src/theme/colorMode";

export const Provider = ({ children }: { children: React.ReactNode }) => {
  return (
    <ColorModeProvider>
      <ChakraProvider value={system}>{children}</ChakraProvider>
    </ColorModeProvider>
  );
};


