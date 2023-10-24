import { useDispatch, useStore } from '@hooks';
import {
  cleanupClusterConfiguration,
  createWithUpdateClusterConfigurations,
  getClusterConfiguration,
  getClusterConfigurationsVersions,
} from '@store/adcm/cluster/configuration/clusterConfigurationSlice';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';

export const useClusterPrimaryConfiguration = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const configVersions = useStore(({ adcm }) => adcm.clusterConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.clusterConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.clusterConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.clusterConfiguration.isVersionsLoading);

  useEffect(() => {
    if (cluster) {
      // load all configurations for current Cluster
      dispatch(getClusterConfigurationsVersions({ clusterId: cluster.id }));
    }

    return () => {
      dispatch(cleanupClusterConfiguration());
    };
  }, [cluster, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (cluster && selectedConfigId) {
      // load full config for selected configuration
      dispatch(getClusterConfiguration({ clusterId: cluster.id, configId: selectedConfigId }));
    }
  }, [dispatch, cluster, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (cluster?.id && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateClusterConfigurations({ configurationData, attributes, clusterId: cluster.id, description }),
        )
          .unwrap()
          .then(() => {
            onReset();
          });
      }
    },
    [onReset, selectedConfiguration, cluster, dispatch],
  );

  return {
    ...configurationsOptions,
    onSave,
    configVersions,
    selectedConfiguration,
    isConfigurationLoading,
    isVersionsLoading,
    cluster,
  };
};
