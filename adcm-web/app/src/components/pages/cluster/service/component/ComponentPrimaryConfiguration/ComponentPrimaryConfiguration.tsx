import React, { useEffect } from 'react';
import { useDispatch } from '@hooks';
import { useComponentPrimaryConfiguration } from '@pages/cluster/service/component/ComponentPrimaryConfiguration/useComponentPrimaryConfiguration';
import { useHostProviderPrimaryConfigurationsCompare } from '@pages/HostProviderPage/HostProviderPrimaryConfiguration/useHostProviderPrimaryConfigurationsCompare';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import ConfigurationHeader from '@commonComponents/configuration/ConfigurationHeader/ConfigurationHeader';
import ConfigurationFormContextProvider from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContextProvider';
import ConfigurationSubHeader from '@commonComponents/configuration/ConfigurationSubHeader/ConfigurationSubHeader';
import ConfigurationMain from '@commonComponents/configuration/ConfigurationMain/ConfigurationMain';

const ComponentPrimaryConfiguration: React.FC = () => {
  const dispatch = useDispatch();
  const {
    component,
    configVersions,
    selectedConfigId,
    setSelectedConfigId,
    draftConfiguration,
    selectedConfiguration,
    onSave,
    onReset,
    setDraftConfiguration,
    isConfigurationLoading,
  } = useComponentPrimaryConfiguration();

  const compareOptions = useHostProviderPrimaryConfigurationsCompare();

  useEffect(() => {
    if (component) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${component.cluster.id}`, label: component.cluster.name },
          { href: `/clusters/${component.cluster.id}/services`, label: 'Services' },
          {
            href: `/clusters/${component.cluster.id}/services/${component.service.id}`,
            label: component.service.displayName,
          },
          {
            href: `/clusters/${component.cluster.id}/services/${component.service.id}/components`,
            label: 'Components',
          },
          {
            href: `/clusters/${component.cluster.id}/services/${component.service.id}/components/${component.id}`,
            label: component.displayName,
          },
          { label: 'Primary configuration' },
        ]),
      );
    }
  }, [component, dispatch]);

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

export default ComponentPrimaryConfiguration;
