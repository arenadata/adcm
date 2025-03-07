import { useDispatch, useStore } from '@hooks';
import {
  cleanup,
  createWithUpdateConfigurations,
  getConfiguration,
  getConfigurationsVersions,
} from '@store/adcm/entityConfiguration/configurationSlice';
import { useCallback, useEffect } from 'react';
import { useConfigurations } from '@commonComponents/configuration/useConfigurations';
import { useParams } from 'react-router-dom';

export const useHostsPrimaryConfiguration = () => {
  const dispatch = useDispatch();
  const { hostId: hostIdFromUrl } = useParams();
  const hostId = Number(hostIdFromUrl);
  const configVersions = useStore(({ adcm }) => adcm.entityConfiguration.configVersions);
  const loadedConfiguration = useStore(({ adcm }) => adcm.entityConfiguration.loadedConfiguration);
  const isConfigurationLoading = useStore(({ adcm }) => adcm.entityConfiguration.isConfigurationLoading);
  const isVersionsLoading = useStore(({ adcm }) => adcm.entityConfiguration.isVersionsLoading);
  const accessCheckStatus = useStore(({ adcm }) => adcm.entityConfiguration.accessCheckStatus);
  const accessConfigCheckStatus = useStore(({ adcm }) => adcm.entityConfiguration.accessConfigCheckStatus);

  useEffect(() => {
    // load all configurations for current Host
    dispatch(getConfigurationsVersions({ entityType: 'host', args: { hostId } }));

    return () => {
      dispatch(cleanup());
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
        getConfiguration({
          entityType: 'host',
          args: {
            hostId,
            configId: selectedConfigId,
          },
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
          createWithUpdateConfigurations({
            entityType: 'host',
            args: {
              configurationData,
              attributes,
              hostId,
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
    [onReset, selectedConfiguration, hostId, dispatch],
  );

  return {
    ...configurationsOptions,
    onSave,
    configVersions,
    selectedConfiguration,
    isConfigurationLoading,
    isVersionsLoading,
    accessCheckStatus,
    accessConfigCheckStatus,
  };
};
