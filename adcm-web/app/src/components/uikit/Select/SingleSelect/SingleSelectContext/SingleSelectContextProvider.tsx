import React, { useState } from 'react';
import { SingleSelectOptions } from '@uikit/Select/Select.types';
import { SingleSelectContext, SingleSelectContextOptions } from './SingleSelect.context';

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
