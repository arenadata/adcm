import { SelectOption } from '@uikit/Select/Select.types';

const defaultCompare = (label: string, search: string) => label.toLowerCase().includes(search.toLowerCase());

export const getFilteredOptions = <T>(options: SelectOption<T>[], search: string, comparator = defaultCompare) => {
  if (search === '') {
    return options;
  }

  return options.filter(({ label }) => comparator(label, search));
};
