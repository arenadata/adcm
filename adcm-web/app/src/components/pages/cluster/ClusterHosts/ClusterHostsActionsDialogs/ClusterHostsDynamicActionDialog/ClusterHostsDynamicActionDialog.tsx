import React from 'react';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import { useDispatch, useStore } from '@hooks';
import { AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import {
  runClusterHostDynamicAction,
  closeClusterHostDynamicActionDialog,
} from '@store/adcm/cluster/hosts/hostsDynamicActionsSlice';

const ClusterHostsDynamicActionDialog: React.FC = () => {
  const dispatch = useDispatch();
  const { cluster, clusterHost, actionDetails } = useStore((s) => s.adcm.clusterHostsDynamicActions.dialog);

  if (!actionDetails || !cluster || !clusterHost) return null;

  const handleCancel = () => {
    dispatch(closeClusterHostDynamicActionDialog());
  };

  const handleSubmit = (actionRunConfig: AdcmDynamicActionRunConfig) => {
    dispatch(
      runClusterHostDynamicAction({
        cluster,
        clusterHost,
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

export default ClusterHostsDynamicActionDialog;
