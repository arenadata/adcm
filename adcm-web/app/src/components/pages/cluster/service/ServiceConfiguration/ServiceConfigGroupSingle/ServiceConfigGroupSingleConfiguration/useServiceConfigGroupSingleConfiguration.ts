import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';
import {
  cleanup,
  createWithUpdateConfigurations,
  getConfiguration,
  getConfigurationsVersions,
} from '@store/adcm/entityConfiguration/configurationSlice';

export const useServiceConfigGroupSingleConfiguration = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const service = useStore(({ adcm }) => adcm.service.service);
  const serviceConfigGroup = useStore((s) => s.adcm.serviceConfigGroup.serviceConfigGroup);
  const configVersions = useStore(({ adcm }) => adcm.entityConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.entityConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.entityConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.entityConfiguration.isVersionsLoading);

  useEffect(() => {
    if (cluster?.id && service?.id && serviceConfigGroup?.id) {
      // load all configurations for current Cluster
      dispatch(
        getConfigurationsVersions({
          entityType: 'service-config-group',
          args: {
            clusterId: cluster.id,
            serviceId: service.id,
            configGroupId: serviceConfigGroup.id,
          },
        }),
      );
    }

    return () => {
      dispatch(cleanup());
    };
  }, [cluster?.id, service?.id, serviceConfigGroup?.id, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (cluster?.id && service?.id && serviceConfigGroup?.id && selectedConfigId) {
      // load full config for selected configuration
      dispatch(
        getConfiguration({
          entityType: 'service-config-group',
          args: {
            clusterId: cluster.id,
            serviceId: service.id,
            configGroupId: serviceConfigGroup.id,
            configId: selectedConfigId,
          },
        }),
      );
    }
  }, [dispatch, cluster?.id, service?.id, serviceConfigGroup?.id, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (cluster && service && serviceConfigGroup && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateConfigurations({
            entityType: 'service-config-group',
            args: {
              configurationData,
              attributes,
              clusterId: cluster.id,
              serviceId: service.id,
              configGroupId: serviceConfigGroup.id,
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
    [onReset, cluster, service, serviceConfigGroup, selectedConfiguration, dispatch],
  );

  return {
    ...configurationsOptions,
    onSave,
    configVersions,
    selectedConfiguration,
    isConfigurationLoading,
    isVersionsLoading,
    cluster,
    service,
    serviceConfigGroup,
  };
};
