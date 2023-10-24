import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';
import {
  cleanupServiceComponentConfigGroupConfiguration,
  createWithUpdateServiceComponentConfigGroupConfigurations,
  getServiceComponentConfigGroupConfiguration,
  getServiceComponentConfigGroupConfigurationsVersions,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponent/configGroupSingle/serviceComponentConfigGroupConfigurationSlice';

export const useServiceComponentConfigGroupConfiguration = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const service = useStore(({ adcm }) => adcm.service.service);
  const component = useStore(({ adcm }) => adcm.serviceComponent.serviceComponent);
  const serviceComponentConfigGroup = useStore(
    (s) => s.adcm.serviceComponentConfigGroupSingle.serviceComponentConfigGroup,
  );
  const configVersions = useStore(({ adcm }) => adcm.serviceComponentConfigGroupConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.serviceComponentConfigGroupConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(
    ({ adcm }) => adcm.serviceComponentConfigGroupConfiguration.isConfigurationLoading,
  );
  const isVersionsLoading = useStore(({ adcm }) => adcm.serviceComponentConfigGroupConfiguration.isVersionsLoading);

  useEffect(() => {
    if (cluster && service && component && serviceComponentConfigGroup) {
      // load all configurations for current Cluster
      dispatch(
        getServiceComponentConfigGroupConfigurationsVersions({
          clusterId: cluster.id,
          serviceId: service.id,
          componentId: component.id,
          configGroupId: serviceComponentConfigGroup.id,
        }),
      );
    }

    return () => {
      dispatch(cleanupServiceComponentConfigGroupConfiguration());
    };
  }, [cluster, service, component, serviceComponentConfigGroup, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (cluster && service && component && serviceComponentConfigGroup && selectedConfigId) {
      // load full config for selected configuration
      dispatch(
        getServiceComponentConfigGroupConfiguration({
          clusterId: cluster.id,
          serviceId: service.id,
          componentId: component.id,
          configGroupId: serviceComponentConfigGroup.id,
          configId: selectedConfigId,
        }),
      );
    }
  }, [dispatch, cluster, service, component, serviceComponentConfigGroup, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (cluster && service && component && serviceComponentConfigGroup && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateServiceComponentConfigGroupConfigurations({
            configurationData,
            attributes,
            clusterId: cluster.id,
            serviceId: service.id,
            componentId: component.id,
            configGroupId: serviceComponentConfigGroup.id,
            description,
          }),
        )
          .unwrap()
          .then(() => {
            onReset();
          });
      }
    },
    [onReset, cluster, service, component, serviceComponentConfigGroup, selectedConfiguration, dispatch],
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
    component,
    serviceComponentConfigGroup,
  };
};
