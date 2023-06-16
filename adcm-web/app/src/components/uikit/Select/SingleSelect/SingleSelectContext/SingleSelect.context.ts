import { SelectOption, SingleSelectOptions } from '@uikit/Select/Select.types';
import React, { useContext } from 'react';

export type SingleSelectContextOptions<T> = SingleSelectOptions<T> & {
  setOptions: (_list: SelectOption<T>[]) => void;
  originalOptions: SelectOption<T>[];
};

export const SingleSelectContext = React.createContext<SingleSelectContextOptions<unknown>>(
  {} as SingleSelectContextOptions<unknown>,
);

export const useSingleSelectContext = <T>() => {
  const ctx = useContext<SingleSelectContextOptions<T>>(
    SingleSelectContext as React.Context<SingleSelectContextOptions<T>>,
  );
  if (!ctx) {
    throw new Error('useContext must be inside a Provider with a value');
  }
  return ctx;
};
