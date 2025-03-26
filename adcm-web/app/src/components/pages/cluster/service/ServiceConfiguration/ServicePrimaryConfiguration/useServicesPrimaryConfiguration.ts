import { useDispatch, useStore } from '@hooks';
import {
  cleanup,
  createWithUpdateConfigurations,
  getConfiguration,
  getConfigurationsVersions,
} from '@store/adcm/entityConfiguration/configurationSlice';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';

export const useServicesPrimaryConfiguration = () => {
  const dispatch = useDispatch();

  const service = useStore(({ adcm }) => adcm.service.service);
  const configVersions = useStore(({ adcm }) => adcm.entityConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.entityConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.entityConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.entityConfiguration.isVersionsLoading);
  const accessCheckStatus = useStore(({ adcm }) => adcm.entityConfiguration.accessCheckStatus);
  const accessConfigCheckStatus = useStore(({ adcm }) => adcm.entityConfiguration.accessConfigCheckStatus);

  useEffect(() => {
    if (service?.id) {
      // load all configurations for current HostProvider
      dispatch(
        getConfigurationsVersions({
          entityType: 'service',
          args: { clusterId: service.cluster.id, serviceId: service.id },
        }),
      );
    }

    return () => {
      dispatch(cleanup());
    };
  }, [service?.id, service?.cluster.id, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (service?.id && selectedConfigId) {
      // load full config for selected configuration
      dispatch(
        getConfiguration({
          entityType: 'service',
          args: {
            clusterId: service.cluster.id,
            serviceId: service.id,
            configId: selectedConfigId,
          },
        }),
      );
    }
  }, [service?.id, service?.cluster.id, dispatch, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (service?.id && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateConfigurations({
            entityType: 'service',
            args: {
              configurationData,
              attributes,
              clusterId: service.cluster.id,
              serviceId: service.id,
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
    [onReset, selectedConfiguration, service, dispatch],
  );

  return {
    ...configurationsOptions,
    onSave,
    configVersions,
    selectedConfiguration,
    isConfigurationLoading,
    isVersionsLoading,
    service,
    accessCheckStatus,
    accessConfigCheckStatus,
  };
};
