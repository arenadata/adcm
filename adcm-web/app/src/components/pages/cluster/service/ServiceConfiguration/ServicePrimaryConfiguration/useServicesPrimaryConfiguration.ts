import { useDispatch, useStore } from '@hooks';
import {
  cleanupClusterServicesConfiguration,
  createWithUpdateClusterServicesConfigurations,
  getClusterServicesConfiguration,
  getClusterServicesConfigurationsVersions,
} from '@store/adcm/cluster/services/servicesPrymaryConfiguration/servicesConfigurationSlice';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';

export const useServicesPrimaryConfiguration = () => {
  const dispatch = useDispatch();
  const service = useStore(({ adcm }) => adcm.service.service);
  const configVersions = useStore(({ adcm }) => adcm.clusterServicesConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.clusterServicesConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.clusterServicesConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.clusterServicesConfiguration.isVersionsLoading);

  useEffect(() => {
    if (service) {
      // load all configurations for current HostProvider
      dispatch(getClusterServicesConfigurationsVersions({ clusterId: service.cluster.id, serviceId: service.id }));
    }

    return () => {
      dispatch(cleanupClusterServicesConfiguration());
    };
  }, [service, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (service && selectedConfigId) {
      // load full config for selected configuration
      dispatch(
        getClusterServicesConfiguration({
          clusterId: service.cluster.id,
          serviceId: service.id,
          configId: selectedConfigId,
        }),
      );
    }
  }, [dispatch, service, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (service?.id && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateClusterServicesConfigurations({
            configurationData,
            attributes,
            clusterId: service.cluster.id,
            serviceId: service.id,
            description,
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
  };
};
