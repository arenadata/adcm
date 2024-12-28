import type React from 'react';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import { useDispatch, useStore } from '@hooks';
import type { AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import { closeHostDynamicActionDialog, runHostDynamicAction } from '@store/adcm/hosts/hostsDynamicActionsSlice';

const HostDynamicActionDialog: React.FC = () => {
  const dispatch = useDispatch();
  const { host, actionDetails } = useStore((s) => s.adcm.hostsDynamicActions.dialog);

  if (!actionDetails || !host) return null;

  const handleCancel = () => {
    dispatch(closeHostDynamicActionDialog());
  };

  const handleSubmit = (actionRunConfig: AdcmDynamicActionRunConfig) => {
    dispatch(
      runHostDynamicAction({
        host,
        actionId: actionDetails.id,
        actionRunConfig,
      }),
    );
  };

  return (
    <DynamicActionDialog
      clusterId={host.cluster ? host.cluster.id : null}
      actionDetails={actionDetails}
      onCancel={handleCancel}
      onSubmit={handleSubmit}
    />
  );
};

export default HostDynamicActionDialog;
