import type React from 'react';
import { useState } from 'react';
import type { AdcmConfiguration } from '@models/adcm';
import { ActionWizardConfigurationEditorContext } from './ActionWizardConfigurationEditorContext.context';
import type { ConfigurationMap } from '@models/adcm/wizard';

interface ConfigurationContextProviderProps {
  children: React.ReactNode;
}

interface ConfigurationContextValue {
  configuration: ConfigurationMap;
  setConfigurationForStep: (stepId: number, config: AdcmConfiguration | null) => void;
}

const ActionWizardConfigurationEditorContextProvider: React.FC<ConfigurationContextProviderProps> = ({ children }) => {
  const [configuration, setConfiguration] = useState<ConfigurationMap>({});

  const setConfigurationForStep = (stepId: number, configuration: AdcmConfiguration | null) => {
    setConfiguration((prev: ConfigurationMap) => ({
      ...prev,
      [stepId]: configuration,
    }));
  };

  const contextValue: ConfigurationContextValue = {
    configuration,
    setConfigurationForStep,
  };

  return (
    <ActionWizardConfigurationEditorContext.Provider value={contextValue}>
      {children}
    </ActionWizardConfigurationEditorContext.Provider>
  );
};

export default ActionWizardConfigurationEditorContextProvider;
