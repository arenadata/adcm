import { getStatusLabel } from '@utils/humanisationUtils';
import { SelectOption } from './Select.types';

export const getOptionsFromEnum = <T extends string, TEnumValue extends string>(someEnum: {
  [key in T]: TEnumValue;
}): SelectOption<TEnumValue>[] => {
  const options = Object.values(someEnum).map((value) => ({
    label: getStatusLabel(value as string),
    value: value as TEnumValue,
  }));

  return options;
};

export const getOptionsFromArray = (s: string[]): SelectOption<string>[] => {
  const options = s.map((value) => ({
    label: getStatusLabel(value),
    value: value,
  }));

  return options;
};
