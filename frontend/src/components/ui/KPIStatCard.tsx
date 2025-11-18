import React from 'react';
import { Stat, StatLabel, StatNumber, StatHelpText, StatArrow, HStack, Icon, Text } from '@chakra-ui/react';

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
    <Stat>
      <StatLabel>
        <HStack>
          {icon && <Icon as={icon} />}
          <Text>{label}</Text>
        </HStack>
      </StatLabel>
      <StatNumber color={color}>{value}</StatNumber>
      {helpText !== undefined && (
        <StatHelpText>
          {arrow && <StatArrow type={arrow} />}
          {helpText}
        </StatHelpText>
      )}
    </Stat>
  );
};

export default KPIStatCard;


