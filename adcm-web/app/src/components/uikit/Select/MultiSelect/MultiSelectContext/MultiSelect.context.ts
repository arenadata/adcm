import type { MultiSelectOptions, SelectOption } from '@uikit/Select/Select.types';
import React, { useContext } from 'react';

export type MultiSelectContextOptions<T> = MultiSelectOptions<T> & {
  setOptions: (list: SelectOption<T>[]) => void;
  originalOptions: SelectOption<T>[];
};

export const MultiSelectContext = React.createContext<MultiSelectContextOptions<unknown>>(
  {} as MultiSelectContextOptions<unknown>,
);

export const useMultiSelectContext = <T>() => {
  const ctx = useContext<MultiSelectContextOptions<T>>(
    MultiSelectContext as React.Context<MultiSelectContextOptions<T>>,
  );
  if (!ctx) {
    throw new Error('useContext must be inside a Provider with a value');
  }
  return ctx;
};
