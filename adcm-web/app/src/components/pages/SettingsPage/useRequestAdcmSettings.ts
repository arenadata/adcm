import { useEffect } from 'react';
import { useDispatch, useStore } from '@hooks';
import { getAdcmSettings } from '@store/adcm/settings/settingsSlice';
import {
  cleanupAdcmSettingsDynamicActions,
  loadAdcmSettingsDynamicActions,
} from '@store/adcm/settings/settingsDynamicActionsSlice';

export const useRequestAdcmSettings = () => {
  const dispatch = useDispatch();
  const configVersions = useStore(({ adcm }) => adcm.entityConfiguration.configVersions);

  useEffect(() => {
    dispatch(getAdcmSettings());

    return () => {
      dispatch(cleanupAdcmSettingsDynamicActions());
    };
  }, [dispatch]);

  useEffect(() => {
    dispatch(loadAdcmSettingsDynamicActions());
  }, [dispatch, configVersions]);
};
