import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';
import {
  cleanupServiceComponentConfiguration,
  createWithUpdateServiceComponentConfigurations,
  getServiceComponentConfiguration,
  getServiceComponentConfigurationsVersions,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponent/configuration/serviceComponentConfigurationSlice';
import { useServiceComponentParams } from '@pages/cluster/service/component/useServiceComponentParams';

export const useComponentPrimaryConfiguration = () => {
  const dispatch = useDispatch();
  const { clusterId, serviceId, componentId } = useServiceComponentParams();

  const component = useStore(({ adcm }) => adcm.serviceComponent.serviceComponent);
  const configVersions = useStore(({ adcm }) => adcm.serviceComponentConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.serviceComponentConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.serviceComponentConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.serviceComponentConfiguration.isVersionsLoading);

  useEffect(() => {
    if (componentId) {
      // load all configurations for current component
      dispatch(
        getServiceComponentConfigurationsVersions({
          clusterId: clusterId,
          serviceId: serviceId,
          componentId: componentId,
        }),
      );
    }

    return () => {
      dispatch(cleanupServiceComponentConfiguration());
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
        getServiceComponentConfiguration({
          clusterId: clusterId,
          serviceId: serviceId,
          componentId: componentId,
          configId: selectedConfigId,
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
          createWithUpdateServiceComponentConfigurations({
            configurationData,
            attributes,
            clusterId: clusterId,
            serviceId: serviceId,
            componentId: componentId,
            description,
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
  };
};
