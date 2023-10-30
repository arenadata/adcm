import React from 'react';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import { useDispatch, useStore } from '@hooks';
import { AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import {
  closeClusterHostComponentsDynamicActionDialog,
  runClusterHostComponentDynamicAction,
} from '@store/adcm/cluster/hosts/host/hostComponentsDynamicActionsSlice';

const HostComponentsDynamicActionDialog: React.FC = () => {
  const dispatch = useDispatch();
  const { clusterId, hostId, actionDetails } = useStore((s) => s.adcm.hostComponentsDynamicActions.dialog);

  if (!actionDetails || !clusterId || !hostId) return null;

  const handleCancel = () => {
    dispatch(closeClusterHostComponentsDynamicActionDialog());
  };

  const handleSubmit = (actionRunConfig: AdcmDynamicActionRunConfig) => {
    dispatch(
      runClusterHostComponentDynamicAction({
        clusterId,
        hostId,
        actionId: actionDetails.id,
        actionRunConfig,
      }),
    );
  };

  return (
    <DynamicActionDialog
      clusterId={clusterId}
      actionDetails={actionDetails}
      onCancel={handleCancel}
      onSubmit={handleSubmit}
    />
  );
};

export default HostComponentsDynamicActionDialog;
