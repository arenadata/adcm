import type { Context } from 'react';
import { createContext, useContext } from 'react';

export const createContextHelper = <T>(displayName: string) => {
  const context = createContext<T | undefined>(undefined);

  context.displayName = displayName;

  return context;
};

export const useContextHelper = <T>(context: Context<T | undefined>): T => {
  const value = useContext(context);

  if (value === undefined) {
    throw new Error(
      `Context "${context.displayName || 'Unknown'}" is not available. Make sure you're inside the corresponding Provider.`,
    );
  }

  return value;
};
