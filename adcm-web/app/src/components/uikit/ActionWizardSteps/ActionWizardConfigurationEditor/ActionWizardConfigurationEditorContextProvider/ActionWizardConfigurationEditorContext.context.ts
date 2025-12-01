import React, { useContext } from 'react';
import type { AdcmConfiguration } from '@models/adcm';
import type { ConfigurationMap } from '@models/adcm/wizard';

export type ConfigurationFormContextOptions = {
  configuration: ConfigurationMap;
  setConfigurationForStep: (stepId: number, config: AdcmConfiguration | null) => void;
};

export const ActionWizardConfigurationEditorContext = React.createContext<ConfigurationFormContextOptions>(
  {} as ConfigurationFormContextOptions,
);

export const useActionWizardConfigurationEditorContext = () => {
  const ctx = useContext<ConfigurationFormContextOptions>(
    ActionWizardConfigurationEditorContext as React.Context<ConfigurationFormContextOptions>,
  );
  if (!ctx) {
    throw new Error('useContext must be inside a Provider with a value');
  }
  return ctx;
};
