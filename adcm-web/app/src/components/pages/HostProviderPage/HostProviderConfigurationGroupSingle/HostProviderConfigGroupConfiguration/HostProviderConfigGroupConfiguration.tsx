import { useDispatch } from '@hooks';
import React, { useEffect } from 'react';
import { useHostProviderConfigGroupConfiguration } from '@pages/HostProviderPage/HostProviderConfigurationGroupSingle/HostProviderConfigGroupConfiguration/useHostProviderConfigGroupConfiguration';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import ConfigurationHeader from '@commonComponents/configuration/ConfigurationHeader/ConfigurationHeader';
import ConfigurationFormContextProvider from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContextProvider';
import ConfigurationMain from '@commonComponents/configuration/ConfigurationMain/ConfigurationMain';
import { useHostProviderConfigGroupConfigurationsCompare } from '@pages/HostProviderPage/HostProviderConfigurationGroupSingle/HostProviderConfigGroupConfiguration/useHostProviderConfigGroupConfigurationsCompare';
import ConfigurationSubHeader from '@commonComponents/configuration/ConfigurationSubHeader/ConfigurationSubHeader';

const HostProviderConfigGroupConfiguration: React.FC = () => {
  const dispatch = useDispatch();
  const {
    hostProvider,
    hostProviderConfigGroup,
    configVersions,
    selectedConfigId,
    setSelectedConfigId,
    draftConfiguration,
    selectedConfiguration,
    onSave,
    onReset,
    setDraftConfiguration,
    isConfigurationLoading,
  } = useHostProviderConfigGroupConfiguration();

  const compareOptions = useHostProviderConfigGroupConfigurationsCompare();

  useEffect(() => {
    if (hostProvider && hostProviderConfigGroup) {
      dispatch(
        setBreadcrumbs([
          { href: '/hostproviders', label: 'Hostproviders' },
          { href: `/hostproviders/${hostProvider.id}`, label: hostProvider.name },
          {
            href: `/hostproviders/${hostProvider.id}/configuration-groups/${hostProviderConfigGroup.id}/`,
            label: hostProviderConfigGroup.name,
          },
          { label: 'Configuration' },
        ]),
      );
    }
  }, [hostProvider, hostProviderConfigGroup, dispatch]);

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

export default HostProviderConfigGroupConfiguration;
