import React from 'react';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import { useDispatch, useStore } from '@hooks';
import { AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import {
  runClusterServiceComponentDynamicAction,
  closeClusterServiceComponentsDynamicActionDialog,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsDynamicActionsSlice';

const ServiceComponentsDynamicActionDialog: React.FC = () => {
  const dispatch = useDispatch();
  const { cluster, service, component, actionDetails } = useStore((s) => s.adcm.serviceComponentsDynamicActions.dialog);

  if (!actionDetails || !cluster || !service || !component) return null;

  const handleCancel = () => {
    dispatch(closeClusterServiceComponentsDynamicActionDialog());
  };

  const handleSubmit = (actionRunConfig: AdcmDynamicActionRunConfig) => {
    dispatch(
      runClusterServiceComponentDynamicAction({
        cluster,
        service,
        component,
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

export default ServiceComponentsDynamicActionDialog;
