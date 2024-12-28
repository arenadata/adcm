import type React from 'react';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import { useDispatch, useStore } from '@hooks';
import type { AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import {
  closeHostProviderDynamicActionDialog,
  runHostProviderDynamicAction,
} from '@store/adcm/hostProviders/hostProvidersDynamicActionsSlice';

const HostProviderDynamicActionDialog: React.FC = () => {
  const dispatch = useDispatch();
  const { hostProvider, actionDetails } = useStore((s) => s.adcm.hostProvidersDynamicActions.dialog);

  if (!actionDetails || !hostProvider) return null;

  const handleCancel = () => {
    dispatch(closeHostProviderDynamicActionDialog());
  };

  const handleSubmit = (actionRunConfig: AdcmDynamicActionRunConfig) => {
    dispatch(
      runHostProviderDynamicAction({
        hostProvider,
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

export default HostProviderDynamicActionDialog;
