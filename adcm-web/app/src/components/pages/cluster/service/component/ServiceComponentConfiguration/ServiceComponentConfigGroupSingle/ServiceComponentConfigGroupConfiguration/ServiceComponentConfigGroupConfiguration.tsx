import type React from 'react';
import ConfigurationMain from '@commonComponents/configuration/ConfigurationMain/ConfigurationMain';
import ConfigurationFormContextProvider from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContextProvider';
import ConfigurationSubHeader from '@commonComponents/configuration/ConfigurationSubHeader/ConfigurationSubHeader';
import ConfigurationHeader from '@commonComponents/configuration/ConfigurationHeader/ConfigurationHeader';
import { useServiceComponentConfigGroupConfiguration } from './useServiceComponentConfigGroupConfiguration';
import { useServiceComponentConfigGroupConfigurationsCompare } from './useServiceComponentConfigGroupConfigurationsCompare';
import ConfigurationMinimap from '@commonComponents/configuration/ConfigurationMinimap/ConfigurationMinimap';

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
        <ConfigurationMinimap>
          <ConfigurationMain
            isLoading={isConfigurationLoading}
            configuration={selectedConfiguration}
            onChangeConfiguration={setDraftConfiguration}
          />
        </ConfigurationMinimap>
      </ConfigurationFormContextProvider>
    </div>
  );
};

export default ServiceComponentConfigGroupConfiguration;
