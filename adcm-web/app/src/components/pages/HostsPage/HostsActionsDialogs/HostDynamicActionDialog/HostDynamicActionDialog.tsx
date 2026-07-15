import type React from 'react';
import { useCallback } from 'react';
import DynamicActionDialog from '@commonComponents/DynamicActionDialog/DynamicActionDialog';
import { useDispatch, useStore } from '@hooks';
import type { AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import { closeHostDynamicActionDialog, runBulkHostDynamicAction } from '@store/adcm/hosts/hostsDynamicActionsSlice';

const HostDynamicActionDialog: React.FC = () => {
  const dispatch = useDispatch();
  const { host, hosts, actionDetails, actionIdsByHostId } = useStore((s) => s.adcm.hostsDynamicActions.dialog);

  const handleCancel = useCallback(() => {
    dispatch(closeHostDynamicActionDialog());
  }, [dispatch]);

  const handleSubmit = useCallback(
    (actionRunConfig: AdcmDynamicActionRunConfig) => {
      if (!actionDetails || !host) {
        return;
      }

      const actionHosts = hosts.length > 0 ? hosts : [host];
      const actionIds = hosts.length > 0 ? actionIdsByHostId : { [host.id]: actionDetails.id };

      dispatch(
        runBulkHostDynamicAction({
          hosts: actionHosts,
          actionIdsByHostId: actionIds,
          actionRunConfig,
        }),
      );
    },
    [actionDetails, actionIdsByHostId, dispatch, host, hosts],
  );

  if (!actionDetails || !host) {
    return null;
  }

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
