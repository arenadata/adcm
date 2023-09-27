import { getStatusLabel } from '@utils/humanizationUtils';
import type { SelectOption } from './Select.types';

export const getOptionsFromEnum = <T extends string, TEnumValue extends string>(someEnum: {
  [key in T]: TEnumValue;
}): SelectOption<TEnumValue>[] => {
  const options = Object.values(someEnum).map((value) => ({
    label: getStatusLabel(value as string),
    value: value as TEnumValue,
  }));

  return options;
};

type LabelAccessor<T> = (item: T, index: number) => string;
type ValueAccessor<T, V> = (item: T, index: number) => V;

export const getOptionsFromArray = <T, V = T>(
  items: T[],
  labelAccessor: LabelAccessor<T>,
  valueAccessor?: ValueAccessor<T, V>,
): SelectOption<T | V>[] => {
  const options = items.map((item, index) => ({
    label: getStatusLabel(labelAccessor(item, index)),
    value: valueAccessor ? valueAccessor(item, index) : item,
  }));

  return options;
};
