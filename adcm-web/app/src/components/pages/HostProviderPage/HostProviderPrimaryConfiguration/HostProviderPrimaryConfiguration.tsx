import type React from 'react';
import { useEffect } from 'react';
import { useDispatch } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import ConfigurationHeader from '@commonComponents/configuration/ConfigurationHeader/ConfigurationHeader';
import ConfigurationFormContextProvider from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContextProvider';
import ConfigurationSubHeader from '@commonComponents/configuration/ConfigurationSubHeader/ConfigurationSubHeader';
import ConfigurationMain from '@commonComponents/configuration/ConfigurationMain/ConfigurationMain';
import { useHostProviderPrimaryConfiguration } from '@pages/HostProviderPage/HostProviderPrimaryConfiguration/useHostProviderPrimaryConfiguration';
import { useHostProviderPrimaryConfigurationsCompare } from '@pages/HostProviderPage/HostProviderPrimaryConfiguration/useHostProviderPrimaryConfigurationsCompare';
import PermissionsChecker from '@commonComponents/PermissionsChecker/PermissionsChecker';

const HostProviderPrimaryConfiguration: React.FC = () => {
  const dispatch = useDispatch();
  const {
    hostProvider,
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
  } = useHostProviderPrimaryConfiguration();

  const compareOptions = useHostProviderPrimaryConfigurationsCompare();

  useEffect(() => {
    if (hostProvider) {
      dispatch(
        setBreadcrumbs([
          { href: '/hostproviders', label: 'Hostproviders' },
          { href: `/hostproviders/${hostProvider.id}`, label: hostProvider.name },
          { label: 'Primary configuration' },
        ]),
      );
    }
  }, [hostProvider, dispatch]);

  return (
    <>
      <PermissionsChecker requestState={accessCheckStatus}>
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
            <ConfigurationMain
              isLoading={isConfigurationLoading}
              configuration={selectedConfiguration}
              onChangeConfiguration={setDraftConfiguration}
            />
          </ConfigurationFormContextProvider>
        </PermissionsChecker>
      </PermissionsChecker>
    </>
  );
};

export default HostProviderPrimaryConfiguration;
