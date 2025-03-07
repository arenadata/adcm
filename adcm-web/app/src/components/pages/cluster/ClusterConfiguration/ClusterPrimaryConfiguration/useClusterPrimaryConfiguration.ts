import { useDispatch, useStore } from '@hooks';
import {
  cleanup,
  createWithUpdateConfigurations,
  getConfiguration,
  getConfigurationsVersions,
} from '@store/adcm/entityConfiguration/configurationSlice';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';

export const useClusterPrimaryConfiguration = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const configVersions = useStore(({ adcm }) => adcm.entityConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.entityConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.entityConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.entityConfiguration.isVersionsLoading);
  const accessCheckStatus = useStore(({ adcm }) => adcm.entityConfiguration.accessCheckStatus);
  const accessConfigCheckStatus = useStore(({ adcm }) => adcm.entityConfiguration.accessConfigCheckStatus);

  useEffect(() => {
    if (cluster?.id) {
      // load all configurations for current Cluster
      dispatch(getConfigurationsVersions({ entityType: 'cluster', args: { clusterId: cluster.id } }));
    }

    return () => {
      dispatch(cleanup());
    };
  }, [cluster?.id, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (cluster?.id && selectedConfigId) {
      // load full config for selected configuration
      dispatch(
        getConfiguration({ entityType: 'cluster', args: { clusterId: cluster.id, configId: selectedConfigId } }),
      );
    }
  }, [dispatch, cluster?.id, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (cluster?.id && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateConfigurations({
            entityType: 'cluster',
            args: { configurationData, attributes, clusterId: cluster.id, description },
          }),
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
    accessCheckStatus,
    accessConfigCheckStatus,
  };
};
