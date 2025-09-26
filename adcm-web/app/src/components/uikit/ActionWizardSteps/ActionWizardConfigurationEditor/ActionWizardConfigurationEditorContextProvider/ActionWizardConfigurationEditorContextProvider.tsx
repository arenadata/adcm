import type React from 'react';
import { useState } from 'react';
import type { AdcmConfiguration } from '@models/adcm';
import { ActionWizardConfigurationEditorContext } from './ActionWizardConfigurationEditorContext.context';

interface ConfigurationContextProviderProps {
  children: React.ReactNode;
}

const ActionWizardConfigurationEditorContextProvider: React.FC<ConfigurationContextProviderProps> = ({ children }) => {
  const [configuration, setConfiguration] = useState<AdcmConfiguration | null>(null);

  const contextValue = {
    configuration,
    setConfiguration,
  };

  return (
    <ActionWizardConfigurationEditorContext.Provider value={contextValue}>
      {children}
    </ActionWizardConfigurationEditorContext.Provider>
  );
};

export default ActionWizardConfigurationEditorContextProvider;
