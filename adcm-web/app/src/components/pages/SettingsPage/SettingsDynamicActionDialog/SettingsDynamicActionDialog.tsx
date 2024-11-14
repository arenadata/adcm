import React from 'react';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import { useDispatch, useStore } from '@hooks';
import type { AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import {
  closeAdcmSettingsDynamicActionDialog,
  runAdcmSettingsDynamicAction,
} from '@store/adcm/settings/settingsDynamicActionsSlice';

const SettingsDynamicActionDialog: React.FC = () => {
  const dispatch = useDispatch();
  const actionDetails = useStore((s) => s.adcm.adcmSettingsDynamicActions.dialog.actionDetails);
  const isOpen = useStore((s) => s.adcm.adcmSettingsDynamicActions.dialog.isOpen);

  if (!actionDetails || !isOpen) return null;

  const handleCancel = () => {
    dispatch(closeAdcmSettingsDynamicActionDialog());
  };

  const handleSubmit = (actionRunConfig: AdcmDynamicActionRunConfig) => {
    dispatch(
      runAdcmSettingsDynamicAction({
        actionId: actionDetails.id,
        actionRunConfig,
      }),
    );
  };

  return (
    <DynamicActionDialog
      clusterId={null}
      actionDetails={actionDetails}
      onCancel={handleCancel}
      onSubmit={handleSubmit}
    />
  );
};

export default SettingsDynamicActionDialog;
