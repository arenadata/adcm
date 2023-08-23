import React from 'react';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import { useDispatch, useStore } from '@hooks';
import {
  closeClusterDynamicActionDialog,
  runClusterDynamicAction,
} from '@store/adcm/clusters/clustersDynamicActionsSlice';
import { AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';

const ClusterDynamicActionDialog: React.FC = () => {
  const dispatch = useDispatch();
  const actionDetails = useStore((s) => s.adcm.clustersDynamicActions.dialog.actionDetails);
  const cluster = useStore((s) => s.adcm.clustersDynamicActions.dialog.cluster);

  if (!actionDetails || !cluster) return null;

  const handleCancel = () => {
    dispatch(closeClusterDynamicActionDialog());
  };

  const handleSubmit = (actionRunConfig: AdcmDynamicActionRunConfig) => {
    dispatch(
      runClusterDynamicAction({
        cluster,
        actionId: actionDetails.id,
        actionRunConfig,
      }),
    );
  };

  return (
    <DynamicActionDialog
      clusterId={cluster.id}
      actionDetails={actionDetails}
      onCancel={handleCancel}
      onSubmit={handleSubmit}
    />
  );
};

export default ClusterDynamicActionDialog;
