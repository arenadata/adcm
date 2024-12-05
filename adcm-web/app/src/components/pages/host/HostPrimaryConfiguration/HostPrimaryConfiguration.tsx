import type React from 'react';
import ConfigurationHeader from '@commonComponents/configuration/ConfigurationHeader/ConfigurationHeader';
import ConfigurationFormContextProvider from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContextProvider';
import ConfigurationSubHeader from '@commonComponents/configuration/ConfigurationSubHeader/ConfigurationSubHeader';
import ConfigurationMain from '@commonComponents/configuration/ConfigurationMain/ConfigurationMain';
import { useHostsPrimaryConfiguration } from './useHostPrimaryConfiguration';
import { useHostsPrimaryConfigurationsCompare } from './useHostPrimaryConfigurationCompare';
import PermissionsChecker from '@commonComponents/PermissionsChecker/PermissionsChecker';

const HostPrimaryConfiguration: React.FC = () => {
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
    accessCheckStatus,
  } = useHostsPrimaryConfiguration();

  const compareOptions = useHostsPrimaryConfigurationsCompare();

  return (
    <PermissionsChecker requestState={accessCheckStatus}>
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
    </PermissionsChecker>
  );
};

export default HostPrimaryConfiguration;
