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
  const component = useStore((s) => s.adcm.serviceComponentsDynamicActions.dialog.component);
  const actionDetails = useStore((s) => s.adcm.serviceComponentsDynamicActions.dialog.actionDetails);

  if (!actionDetails || !component || actionDetails.processes !== null) return null;

  const handleCancel = () => {
    dispatch(closeClusterServiceComponentsDynamicActionDialog());
  };

  const handleSubmit = (actionRunConfig: AdcmDynamicActionRunConfig) => {
    dispatch(
      runClusterServiceComponentDynamicAction({
        clusterId: component.cluster.id,
        serviceId: component.service.id,
        componentId: component.id,
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
