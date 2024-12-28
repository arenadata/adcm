import type React from 'react';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import { useDispatch, useStore } from '@hooks';
import type { AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import {
  runClusterServiceComponentDynamicAction,
  closeClusterServiceComponentsDynamicActionDialog,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsDynamicActionsSlice';

const ServiceComponentsDynamicActionDialog: React.FC = () => {
  const dispatch = useDispatch();
  const { component, actionDetails } = useStore((s) => s.adcm.serviceComponentsDynamicActions.dialog);

  if (!actionDetails || !component) return null;

  const handleCancel = () => {
    dispatch(closeClusterServiceComponentsDynamicActionDialog());
  };

  const handleSubmit = (actionRunConfig: AdcmDynamicActionRunConfig) => {
    dispatch(
      runClusterServiceComponentDynamicAction({
        component,
        actionId: actionDetails.id,
        actionRunConfig,
      }),
    );
  };

  return (
    <DynamicActionDialog
      clusterId={component.cluster.id}
      actionDetails={actionDetails}
      onCancel={handleCancel}
      onSubmit={handleSubmit}
    />
  );
};

export default ServiceComponentsDynamicActionDialog;
