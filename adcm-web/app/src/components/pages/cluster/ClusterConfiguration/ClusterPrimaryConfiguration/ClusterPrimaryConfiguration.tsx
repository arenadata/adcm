import React, { useEffect } from 'react';
import { useDispatch } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import ConfigurationMain from '@commonComponents/configuration/ConfigurationMain/ConfigurationMain';
import ConfigurationFormContextProvider from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContextProvider';
import ConfigurationSubHeader from '@commonComponents/configuration/ConfigurationSubHeader/ConfigurationSubHeader';
import { useClusterPrimaryConfigurationsCompare } from '@pages/cluster/ClusterConfiguration/ClusterPrimaryConfiguration/useClusterPrimaryConfigurationsCompare';
import ConfigurationHeader from '@commonComponents/configuration/ConfigurationHeader/ConfigurationHeader';
import { useClusterPrimaryConfiguration } from './useClusterPrimaryConfiguration';

const ClusterPrimaryConfiguration: React.FC = () => {
  const dispatch = useDispatch();
  const {
    cluster,
    configVersions,
    selectedConfigId,
    setSelectedConfigId,
    draftConfiguration,
    selectedConfiguration,
    onSave,
    onReset,
    setDraftConfiguration,
    isConfigurationLoading,
  } = useClusterPrimaryConfiguration();

  const compareOptions = useClusterPrimaryConfigurationsCompare();

  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Configuration' },
        ]),
      );
    }
  }, [cluster, dispatch]);

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

export default ClusterPrimaryConfiguration;
