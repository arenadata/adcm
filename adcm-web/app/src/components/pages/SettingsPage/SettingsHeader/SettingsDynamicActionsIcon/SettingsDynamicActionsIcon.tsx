import React, { useMemo } from 'react';
import { DynamicActionsIcon } from '@commonComponents/DynamicActionsButton/DynamicActionsButton';
import { useDispatch, useStore } from '@hooks';
import { openAdcmSettingsDynamicActionDialog } from '@store/adcm/settings/settingsDynamicActionsSlice';

const SettingsDynamicActionsButton: React.FC = () => {
  const dispatch = useDispatch();
  const adcmSettingsDynamicActions = useStore((s) => s.adcm.adcmSettingsDynamicActions.adcmSettingsDynamicActions);
  const adcmSettings = useStore((s) => s.adcm.adcmSettings.adcmSettings);
  const isDisabled = useMemo(
    () => !!adcmSettings && adcmSettings.concerns.some(({ isBlocking }) => isBlocking),
    [adcmSettings],
  );

  const handleSelectAction = (actionId: number) => {
    dispatch(openAdcmSettingsDynamicActionDialog(actionId));
  };

  return (
    <DynamicActionsIcon
      actions={adcmSettingsDynamicActions}
      onSelectAction={handleSelectAction}
      disabled={isDisabled}
    />
  );
};

export default SettingsDynamicActionsButton;
