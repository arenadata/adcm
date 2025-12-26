import type React from 'react';
import ConfigurationHeader from '@commonComponents/configuration/ConfigurationHeader/ConfigurationHeader';
import ConfigurationFormContextProvider from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContextProvider';
import ConfigurationSubHeader from '@commonComponents/configuration/ConfigurationSubHeader/ConfigurationSubHeader';
import ConfigurationMain from '@commonComponents/configuration/ConfigurationMain/ConfigurationMain';
import ConfigurationEmptyState from '@commonComponents/configuration/ConfigurationEmptyState/ConfigurationEmptyState';
import { useHostsPrimaryConfiguration } from './useHostPrimaryConfiguration';
import { useHostsPrimaryConfigurationsCompare } from './useHostPrimaryConfigurationCompare';
import PermissionsChecker from '@commonComponents/PermissionsChecker/PermissionsChecker';
import ConfigurationMinimap from '@commonComponents/configuration/ConfigurationMinimap/ConfigurationMinimap';

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
    accessConfigCheckStatus,
  } = useHostsPrimaryConfiguration();

  const compareOptions = useHostsPrimaryConfigurationsCompare();

  const hasNoConfiguration = configVersions.length === 0;

  return (
    <PermissionsChecker requestState={accessCheckStatus}>
      {hasNoConfiguration ? (
        <ConfigurationEmptyState />
      ) : (
        <>
          <ConfigurationHeader
            configVersions={configVersions}
            selectedConfigId={selectedConfigId}
            setSelectedConfigId={setSelectedConfigId}
            draftConfiguration={draftConfiguration}
            compareOptions={compareOptions}
          />
          <PermissionsChecker requestState={accessConfigCheckStatus}>
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
          </PermissionsChecker>
        </>
      )}
    </PermissionsChecker>
  );
};

export default HostPrimaryConfiguration;
