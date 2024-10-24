import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';
import {
  cleanup,
  createWithUpdateConfigurations,
  getConfiguration,
  getConfigurationsVersions,
} from '@store/adcm/entityConfiguration/configurationSlice';

export const useClusterConfigGroupConfiguration = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const clusterConfigGroup = useStore((s) => s.adcm.clusterConfigGroup.clusterConfigGroup);
  const configVersions = useStore(({ adcm }) => adcm.entityConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.entityConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.entityConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.entityConfiguration.isVersionsLoading);

  useEffect(() => {
    if (cluster?.id && clusterConfigGroup?.id) {
      // load all configurations for current Cluster
      dispatch(
        getConfigurationsVersions({
          entityType: 'cluster-config-group',
          args: { clusterId: cluster.id, configGroupId: clusterConfigGroup.id },
        }),
      );
    }

    return () => {
      dispatch(cleanup());
    };
  }, [cluster?.id, clusterConfigGroup?.id, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (cluster?.id && clusterConfigGroup?.id && selectedConfigId) {
      // load full config for selected configuration
      dispatch(
        getConfiguration({
          entityType: 'cluster-config-group',
          args: {
            clusterId: cluster.id,
            configGroupId: clusterConfigGroup.id,
            configId: selectedConfigId,
          },
        }),
      );
    }
  }, [dispatch, cluster?.id, clusterConfigGroup?.id, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (cluster?.id && clusterConfigGroup?.id && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateConfigurations({
            entityType: 'cluster-config-group',
            args: {
              configurationData,
              attributes,
              clusterId: cluster.id,
              configGroupId: clusterConfigGroup.id,
              description,
            },
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
