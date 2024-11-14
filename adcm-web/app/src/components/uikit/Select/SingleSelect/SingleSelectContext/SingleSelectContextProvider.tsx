import React, { useState } from 'react';
import type { SingleSelectOptions } from '@uikit/Select/Select.types';
import type { SingleSelectContextOptions } from './SingleSelect.context';
import { SingleSelectContext } from './SingleSelect.context';

export const SingleSelectContextProvider = <T,>({
  children,
  value,
}: {
  children: React.ReactNode;
  value: SingleSelectOptions<T>;
}) => {
  const originalOptions = value.options;
  const [options, setOptions] = useState(originalOptions);

  const contextValue = {
    ...value,
    options,
    setOptions,
    originalOptions,
  } as SingleSelectContextOptions<unknown>;

  return <SingleSelectContext.Provider value={contextValue}>{children}</SingleSelectContext.Provider>;
};
