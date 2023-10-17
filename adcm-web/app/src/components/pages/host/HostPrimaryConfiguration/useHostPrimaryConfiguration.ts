import { useDispatch, useStore } from '@hooks';
import {
  cleanupHostsConfiguration,
  createWithUpdateHostsConfigurations,
  getHostsConfiguration,
  getHostsConfigurationsVersions,
} from '@store/adcm/host/configuration/hostsConfigurationSlice';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';
import { useParams } from 'react-router-dom';

export const useHostsPrimaryConfiguration = () => {
  const dispatch = useDispatch();
  const { hostId: hostIdFromUrl } = useParams();
  const hostId = Number(hostIdFromUrl);
  const configVersions = useStore(({ adcm }) => adcm.hostsConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.hostsConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.hostsConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.hostsConfiguration.isVersionsLoading);

  useEffect(() => {
    // load all configurations for current Host
    dispatch(getHostsConfigurationsVersions(hostId));

    return () => {
      dispatch(cleanupHostsConfiguration());
    };
  }, [hostId, dispatch]);

  const configurationsOptions = useConfigurations({
    configVersions,
  });
  const { selectedConfigId, onReset } = configurationsOptions;

  useEffect(() => {
    if (selectedConfigId) {
      // load full config for selected configuration
      dispatch(
        getHostsConfiguration({
          hostId,
          configId: selectedConfigId,
        }),
      );
    }
  }, [dispatch, hostId, selectedConfigId]);

  const selectedConfiguration = selectedConfigId === 0 ? configurationsOptions.draftConfiguration : loadedConfiguration;

  const onSave = useCallback(
    (description: string) => {
      if (selectedConfiguration) {
        const { configurationData, attributes } = selectedConfiguration;
        dispatch(
          createWithUpdateHostsConfigurations({
            configurationData,
            attributes,
            hostId,
            description,
          }),
        )
          .unwrap()
          .then(() => {
            onReset();
          });
      }
    },
    [onReset, selectedConfiguration, hostId, dispatch],
  );

  return {
    ...configurationsOptions,
    onSave,
    configVersions,
    selectedConfiguration,
    isConfigurationLoading,
    isVersionsLoading,
  };
};
