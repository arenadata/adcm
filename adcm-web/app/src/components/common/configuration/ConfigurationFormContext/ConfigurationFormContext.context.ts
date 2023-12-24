import React, { useContext } from 'react';
import { ConfigurationNodeFilter } from '@uikit/ConfigurationEditor/ConfigurationEditor.types';

export type ConfigurationFormContextOptions = {
  filter: ConfigurationNodeFilter;
  onFilterChange: (changes: Partial<ConfigurationNodeFilter>) => void;
  areExpandedAll: boolean;
  isValid: boolean;
  onChangeIsValid: (isValid: boolean) => void;
  handleChangeExpandedAll: () => void;
};

export const ConfigurationFormContextContext = React.createContext<ConfigurationFormContextOptions>(
  {} as ConfigurationFormContextOptions,
);

export const useConfigurationFormContext = () => {
  const ctx = useContext<ConfigurationFormContextOptions>(
    ConfigurationFormContextContext as React.Context<ConfigurationFormContextOptions>,
  );
  if (!ctx) {
    throw new Error('useContext must be inside a Provider with a value');
  }
  return ctx;
};
