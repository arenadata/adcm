import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';
import {
  cleanupServiceConfigGroupConfiguration,
  createWithUpdateServiceConfigGroupConfigurations,
  getServiceConfigGroupConfiguration,
  getServiceConfigGroupConfigurationsVersions,
} from '@store/adcm/cluster/services/configGroupSingle/configuration/serviceConfigGroupConfigurationSlice';

export const useServiceConfigGroupSingleConfiguration = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const service = useStore(({ adcm }) => adcm.service.service);
  const serviceConfigGroup = useStore((s) => s.adcm.serviceConfigGroup.serviceConfigGroup);
  const configVersions = useStore(({ adcm }) => adcm.serviceConfigGroupConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.serviceConfigGroupConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.serviceConfigGroupConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.serviceConfigGroupConfiguration.isVersionsLoading);

  useEffect(() => {
    if (cluster && service && serviceConfigGroup) {
      // load all configurations for current Cluster
      dispatch(
        getServiceConfigGroupConfigurationsVersions({
          clusterId: cluster.id,
          serviceId: service.id,
          configGroupId: serviceConfigGroup.id,
        }),
      );
    }

    return () => {
      dispatch(cleanupServiceConfigGroupConfiguration());
    };
  }, [cluster, service, serviceConfigGroup, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (cluster && service && serviceConfigGroup && selectedConfigId) {
      // load full config for selected configuration
      dispatch(
        getServiceConfigGroupConfiguration({
          clusterId: cluster.id,
          serviceId: service.id,
          configGroupId: serviceConfigGroup.id,
          configId: selectedConfigId,
        }),
      );
    }
  }, [dispatch, cluster, service, serviceConfigGroup, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (cluster && service && serviceConfigGroup && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateServiceConfigGroupConfigurations({
            configurationData,
            attributes,
            clusterId: cluster.id,
            serviceId: service.id,
            configGroupId: serviceConfigGroup.id,
            description,
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
