import React, { useEffect } from 'react';
import { useDispatch } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import ConfigurationHeader from '@commonComponents/configuration/ConfigurationHeader/ConfigurationHeader';
import ConfigurationFormContextProvider from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContextProvider';
import ConfigurationSubHeader from '@commonComponents/configuration/ConfigurationSubHeader/ConfigurationSubHeader';
import ConfigurationMain from '@commonComponents/configuration/ConfigurationMain/ConfigurationMain';
import { useHostProviderPrimaryConfiguration } from '@pages/HostProviderPage/HostProviderPrimaryConfiguration/useHostProviderPrimaryConfiguration';
import { useHostProviderPrimaryConfigurationsCompare } from '@pages/HostProviderPage/HostProviderPrimaryConfiguration/useHostProviderPrimaryConfigurationsCompare';

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
  } = useHostProviderPrimaryConfiguration();

  const compareOptions = useHostProviderPrimaryConfigurationsCompare();

  useEffect(() => {
    if (hostProvider) {
      dispatch(
        setBreadcrumbs([
          { href: '/hostproviders', label: 'HostProviders' },
          { href: `/hostproviders/${hostProvider.id}`, label: hostProvider.name },
          { label: 'Primary configuration' },
        ]),
      );
    }
  }, [hostProvider, dispatch]);

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

export default HostProviderPrimaryConfiguration;
