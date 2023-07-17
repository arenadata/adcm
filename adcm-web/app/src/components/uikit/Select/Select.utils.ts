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

type LabelAccessor<T> = (item: T) => string;

export const getOptionsFromArray = <T>(s: T[], labelAccessor: LabelAccessor<T>): SelectOption<T>[] => {
  const options = s.map((item) => ({
    label: getStatusLabel(labelAccessor(item)),
    value: item,
  }));

  return options;
};
