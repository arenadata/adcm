import React from 'react';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import { useDispatch, useStore } from '@hooks';
import type { AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import {
  closeClusterServiceDynamicActionDialog,
  runClusterServiceDynamicAction,
} from '@store/adcm/cluster/services/servicesDynamicActionsSlice';

const ClusterServiceDynamicActionDialog: React.FC = () => {
  const dispatch = useDispatch();
  const { cluster, service, actionDetails } = useStore((s) => s.adcm.servicesDynamicActions.dialog);

  if (!actionDetails || !cluster || !service) return null;

  const handleCancel = () => {
    dispatch(closeClusterServiceDynamicActionDialog());
  };

  const handleSubmit = (actionRunConfig: AdcmDynamicActionRunConfig) => {
    dispatch(
      runClusterServiceDynamicAction({
        cluster,
        service,
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

export default ClusterServiceDynamicActionDialog;
