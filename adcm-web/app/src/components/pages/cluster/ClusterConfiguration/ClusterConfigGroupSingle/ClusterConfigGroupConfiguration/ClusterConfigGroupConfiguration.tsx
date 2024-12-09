import type React from 'react';
import { useEffect } from 'react';
import { useDispatch } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import ConfigurationMain from '@commonComponents/configuration/ConfigurationMain/ConfigurationMain';
import ConfigurationFormContextProvider from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContextProvider';
import ConfigurationSubHeader from '@commonComponents/configuration/ConfigurationSubHeader/ConfigurationSubHeader';
import ConfigurationHeader from '@commonComponents/configuration/ConfigurationHeader/ConfigurationHeader';
import { useClusterConfigGroupConfiguration } from './useClusterConfigGroupConfiguration';
import { useClusterConfigGroupConfigurationsCompare } from './useClusterConfigGroupConfigurationsCompare';

const ClusterConfigGroupConfiguration: React.FC = () => {
  const dispatch = useDispatch();
  const {
    cluster,
    clusterConfigGroup,
    configVersions,
    selectedConfigId,
    setSelectedConfigId,
    draftConfiguration,
    selectedConfiguration,
    onSave,
    onReset,
    setDraftConfiguration,
    isConfigurationLoading,
  } = useClusterConfigGroupConfiguration();

  const compareOptions = useClusterConfigGroupConfigurationsCompare();

  useEffect(() => {
    if (cluster && clusterConfigGroup) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Configuration' },
          { href: `/clusters/${cluster.id}/configuration/config-groups`, label: 'Configuration groups' },
          { label: clusterConfigGroup.name },
        ]),
      );
    }
  }, [cluster, clusterConfigGroup, dispatch]);

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

export default ClusterConfigGroupConfiguration;
