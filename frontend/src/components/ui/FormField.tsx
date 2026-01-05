import React from "react";
import {
  FieldRoot,
  FieldLabel,
  FieldHelperText,
  FieldErrorText,
  type FieldRootProps,
} from "@chakra-ui/react";

type Props = Omit<FieldRootProps, "children"> & {
  label: string;
  helperText?: string;
  errorText?: string;
  children: React.ReactNode;
};

export default function FormField({ label, helperText, errorText, children, ...props }: Props) {
  const invalid = Boolean(errorText);
  return (
    <FieldRoot {...props} invalid={invalid}>
      <FieldLabel color="fg.muted">{label}</FieldLabel>
      {children}
      {helperText ? <FieldHelperText color="fg.subtle">{helperText}</FieldHelperText> : null}
      {errorText ? <FieldErrorText>{errorText}</FieldErrorText> : null}
    </FieldRoot>
  );
}


