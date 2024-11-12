import React, { useState } from 'react';
import type { MultiSelectOptions } from '@uikit/Select/Select.types';
import type { MultiSelectContextOptions } from './MultiSelect.context';
import { MultiSelectContext } from './MultiSelect.context';

export const MultiSelectContextProvider = <T,>({
  children,
  value,
}: {
  children: React.ReactNode;
  value: MultiSelectOptions<T>;
}) => {
  const originalOptions = value.options;
  const [options, setOptions] = useState(originalOptions);

  const contextValue = {
    ...value,
    options,
    setOptions,
    originalOptions,
  } as MultiSelectContextOptions<unknown>;

  return <MultiSelectContext.Provider value={contextValue}>{children}</MultiSelectContext.Provider>;
};
