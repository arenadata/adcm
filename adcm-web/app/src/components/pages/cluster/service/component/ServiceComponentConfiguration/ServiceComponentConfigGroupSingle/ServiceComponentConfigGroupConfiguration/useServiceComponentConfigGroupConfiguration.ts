import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';
import {
  cleanup,
  createWithUpdateConfigurations,
  getConfiguration,
  getConfigurationsVersions,
} from '@store/adcm/entityConfiguration/configurationSlice';

export const useServiceComponentConfigGroupConfiguration = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const service = useStore(({ adcm }) => adcm.service.service);
  const component = useStore(({ adcm }) => adcm.serviceComponent.serviceComponent);
  const serviceComponentConfigGroup = useStore(
    (s) => s.adcm.serviceComponentConfigGroupSingle.serviceComponentConfigGroup,
  );
  const configVersions = useStore(({ adcm }) => adcm.entityConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.entityConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.entityConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.entityConfiguration.isVersionsLoading);

  useEffect(() => {
    if (cluster?.id && service?.id && component?.id && serviceComponentConfigGroup?.id) {
      // load all configurations for current Cluster
      dispatch(
        getConfigurationsVersions({
          entityType: 'service-component-config-group',
          args: {
            clusterId: cluster.id,
            serviceId: service.id,
            componentId: component.id,
            configGroupId: serviceComponentConfigGroup.id,
          },
        }),
      );
    }

    return () => {
      dispatch(cleanup());
    };
  }, [cluster?.id, service?.id, component?.id, serviceComponentConfigGroup?.id, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (cluster?.id && service?.id && component?.id && serviceComponentConfigGroup?.id && selectedConfigId) {
      // load full config for selected configuration
      dispatch(
        getConfiguration({
          entityType: 'service-component-config-group',
          args: {
            clusterId: cluster.id,
            serviceId: service.id,
            componentId: component.id,
            configGroupId: serviceComponentConfigGroup.id,
            configId: selectedConfigId,
          },
        }),
      );
    }
  }, [dispatch, cluster?.id, service?.id, component?.id, serviceComponentConfigGroup?.id, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (cluster && service && component && serviceComponentConfigGroup && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateConfigurations({
            entityType: 'service-component-config-group',
            args: {
              configurationData,
              attributes,
              clusterId: cluster.id,
              serviceId: service.id,
              componentId: component.id,
              configGroupId: serviceComponentConfigGroup.id,
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
