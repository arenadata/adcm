import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';
import {
  cleanup,
  createWithUpdateConfigurations,
  getConfiguration,
  getConfigurationsVersions,
} from '@store/adcm/entityConfiguration/configurationSlice';
import { useServiceComponentParams } from '@pages/cluster/service/component/useServiceComponentParams';

export const useComponentPrimaryConfiguration = () => {
  const dispatch = useDispatch();
  const { clusterId, serviceId, componentId } = useServiceComponentParams();

  const component = useStore(({ adcm }) => adcm.serviceComponent.serviceComponent);
  const configVersions = useStore(({ adcm }) => adcm.entityConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.entityConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.entityConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.entityConfiguration.isVersionsLoading);
  const accessCheckStatus = useStore(({ adcm }) => adcm.entityConfiguration.accessCheckStatus);

  useEffect(() => {
    if (componentId) {
      // load all configurations for current component
      dispatch(
        getConfigurationsVersions({
          entityType: 'service-component',
          args: {
            clusterId: clusterId,
            serviceId: serviceId,
            componentId: componentId,
          },
        }),
      );
    }

    return () => {
      dispatch(cleanup());
    };
  }, [clusterId, componentId, dispatch, serviceId]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (componentId && selectedConfigId) {
      // load full config for selected configuration
      dispatch(
        getConfiguration({
          entityType: 'service-component',
          args: {
            clusterId: clusterId,
            serviceId: serviceId,
            componentId: componentId,
            configId: selectedConfigId,
          },
        }),
      );
    }
  }, [dispatch, componentId, selectedConfigId, clusterId, serviceId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (componentId && selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateConfigurations({
            entityType: 'service-component',
            args: {
              configurationData,
              attributes,
              clusterId: clusterId,
              serviceId: serviceId,
              componentId: componentId,
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
    [componentId, selectedConfiguration, dispatch, clusterId, serviceId, onReset],
  );

  return {
    ...configurationsOptions,
    onSave,
    configVersions,
    selectedConfiguration,
    isConfigurationLoading,
    isVersionsLoading,
    component,
    accessCheckStatus,
  };
};
