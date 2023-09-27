import React from 'react';
import { SelectOption, SelectValue } from '@uikit/Select/Select.types';
import { Select } from '@uikit';

export interface FrequencySelectProps {
  value: number;
  options?: SelectOption<string | number>[];
  onChange: (frequency: number) => void;
}

const defaultOptions: SelectOption<string | number>[] = [
  { label: '1 sec', value: 1 },
  { label: '2 sec', value: 2 },
  { label: '5 sec', value: 5 },
  { label: '10 sec', value: 10 },
];

const FrequencySelect = ({ options = defaultOptions, onChange, value }: FrequencySelectProps) => {
  const handleChange = (value: SelectValue) => {
    onChange(value as number);
  };

  return <Select options={options} value={value} onChange={handleChange} variant="primary" />;
};

export default FrequencySelect;
