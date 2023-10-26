import { useEffect } from 'react';
import { useDispatch, useStore } from '@hooks';
import { cleanupAdcmSettings, getAdcmSettings } from '@store/adcm/settings/settingsSlice';
import {
  cleanupAdcmSettingsDynamicActions,
  loadAdcmSettingsDynamicActions,
} from '@store/adcm/settings/settingsDynamicActionsSlice';

export const useRequestAdcmSettings = () => {
  const dispatch = useDispatch();
  const configVersions = useStore(({ adcm }) => adcm.settingsConfigurations.configVersions);

  useEffect(() => {
    dispatch(getAdcmSettings());

    return () => {
      dispatch(cleanupAdcmSettings());
      dispatch(cleanupAdcmSettingsDynamicActions());
    };
  }, [dispatch]);

  useEffect(() => {
    dispatch(loadAdcmSettingsDynamicActions());
  }, [dispatch, configVersions]);
};
