import React from 'react';
import {
  StatRoot,
  StatLabel,
  StatValueText,
  StatHelpText,
  StatUpIndicator,
  StatDownIndicator,
  HStack,
  Icon,
  Text,
} from '@chakra-ui/react';

interface KPIStatCardProps {
  label: string;
  value: string | number;
  helpText?: string;
  arrow?: 'increase' | 'decrease';
  icon?: React.ElementType;
  color?: string;
}

const KPIStatCard: React.FC<KPIStatCardProps> = ({ label, value, helpText, arrow, icon, color }) => {
  return (
    <StatRoot>
      <StatLabel>
        <HStack>
          {icon && <Icon as={icon} />}
          <Text>{label}</Text>
        </HStack>
      </StatLabel>
      <StatValueText color={color}>{value}</StatValueText>
      {helpText !== undefined && (
        <StatHelpText>
          {arrow === 'increase' ? <StatUpIndicator /> : null}
          {arrow === 'decrease' ? <StatDownIndicator /> : null}
          {helpText}
        </StatHelpText>
      )}
    </StatRoot>
  );
};

export default KPIStatCard;


