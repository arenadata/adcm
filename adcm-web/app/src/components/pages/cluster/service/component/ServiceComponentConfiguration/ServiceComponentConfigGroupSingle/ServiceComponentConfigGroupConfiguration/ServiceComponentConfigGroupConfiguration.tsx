import React from 'react';
import ConfigurationMain from '@commonComponents/configuration/ConfigurationMain/ConfigurationMain';
import ConfigurationFormContextProvider from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContextProvider';
import ConfigurationSubHeader from '@commonComponents/configuration/ConfigurationSubHeader/ConfigurationSubHeader';
import ConfigurationHeader from '@commonComponents/configuration/ConfigurationHeader/ConfigurationHeader';
import { useServiceComponentConfigGroupConfiguration } from './useServiceComponentConfigGroupConfiguration';
import { useServiceComponentConfigGroupConfigurationsCompare } from './useServiceComponentConfigGroupConfigurationsCompare';

const ServiceComponentConfigGroupConfiguration: React.FC = () => {
  const {
    configVersions,
    selectedConfigId,
    setSelectedConfigId,
    draftConfiguration,
    selectedConfiguration,
    onSave,
    onReset,
    setDraftConfiguration,
    isConfigurationLoading,
  } = useServiceComponentConfigGroupConfiguration();

  const compareOptions = useServiceComponentConfigGroupConfigurationsCompare();

  return (
    <div>
      <ConfigurationHeader
        configVersions={configVersions}
        selectedConfigId={selectedConfigId}
        setSelectedConfigId={setSelectedConfigId}
        draftConfiguration={draftConfiguration}
        compareOptions={compareOptions}
      />

      <ConfigurationFormContextProvider>
        <ConfigurationSubHeader onSave={onSave} onRevert={onReset} isViewDraft={selectedConfigId === 0} />
        <ConfigurationMain
          isLoading={isConfigurationLoading}
          configuration={selectedConfiguration}
          onChangeConfiguration={setDraftConfiguration}
        />
      </ConfigurationFormContextProvider>
    </div>
  );
};

export default ServiceComponentConfigGroupConfiguration;
