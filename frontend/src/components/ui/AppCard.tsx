import React from "react";
import { CardRoot, CardBody, type CardRootProps, type CardBodyProps } from "@chakra-ui/react";

type Props = CardRootProps & {
  bodyProps?: CardBodyProps;
  children: React.ReactNode;
};

export default function AppCard({ children, bodyProps, ...props }: Props) {
  return (
    <CardRoot
      bg="bg.card"
      borderColor="border.subtle"
      borderWidth="1px"
      borderRadius="xl"
      boxShadow="0 18px 55px rgba(0,0,0,0.22)"
      {...props}
    >
      <CardBody {...bodyProps}>{children}</CardBody>
    </CardRoot>
  );
}


