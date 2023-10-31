import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';
import {
  cleanupClusterConfigGroupConfiguration,
  createWithUpdateClusterConfigGroupConfigurations,
  getClusterConfigGroupConfiguration,
  getClusterConfigGroupConfigurationsVersions,
} from '@store/adcm/cluster/configGroupSingle/configuration/clusterConfigGroupConfigurationSlice';

export const useClusterConfigGroupConfiguration = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const clusterConfigGroup = useStore((s) => s.adcm.clusterConfigGroup.clusterConfigGroup);
  const configVersions = useStore(({ adcm }) => adcm.clusterConfigGroupConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.clusterConfigGroupConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.clusterConfigGroupConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.clusterConfigGroupConfiguration.isVersionsLoading);

  useEffect(() => {
    if (cluster && clusterConfigGroup) {
      // load all configurations for current Cluster
      dispatch(
        getClusterConfigGroupConfigurationsVersions({ clusterId: cluster.id, configGroupId: clusterConfigGroup.id }),
      );
    }

    return () => {
      dispatch(cleanupClusterConfigGroupConfiguration());
    };
  }, [cluster, clusterConfigGroup, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (cluster && clusterConfigGroup && selectedConfigId) {
      // load full config for selected configuration
      dispatch(
        getClusterConfigGroupConfiguration({
          clusterId: cluster.id,
          configGroupId: clusterConfigGroup.id,
          configId: selectedConfigId,
        }),
      );
    }
  }, [dispatch, cluster, clusterConfigGroup, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (cluster?.id && clusterConfigGroup?.id && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateClusterConfigGroupConfigurations({
            configurationData,
            attributes,
            clusterId: cluster.id,
            configGroupId: clusterConfigGroup.id,
            description,
          }),
        )
          .unwrap()
          .then(() => {
            onReset();
          });
      }
    },
    [onReset, selectedConfiguration, cluster, clusterConfigGroup, dispatch],
  );

  return {
    ...configurationsOptions,
    onSave,
    configVersions,
    selectedConfiguration,
    isConfigurationLoading,
    isVersionsLoading,
    cluster,
    clusterConfigGroup,
  };
};
