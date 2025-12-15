import { useDispatch, useStore } from '@hooks';
import { useEffect, useMemo, useState } from 'react';
import { cleanupClusterHostsWizard, getProcessOnActionClick } from '@store/adcm/cluster/hosts/hostsWizardSlice';
import {
  closeClusterHostsWizardDialog,
  openClusterHostsWizardDialog,
  setIsContinueProcessModal,
} from '@store/adcm/cluster/hosts/hostsWizardActionsSlice';
import {
  createClusterHostDynamicActionProcess,
  cleanupClusterHostActionDetails,
} from '@store/adcm/cluster/hosts/hostsDynamicActionsSlice';
import { defaultWizardTitle } from '@uikit/ActionWizard/ActionWizard.constants';

export const useClusterHostsDynamicActionWizardDialog = () => {
  const dispatch = useDispatch();
  const actionDetails = useStore((s) => s.adcm.hostsDynamicActions.dialog.actionDetails);
  const cluster = useStore((s) => s.adcm.cluster.cluster);
  const host = useStore((s) => s.adcm.hostsDynamicActions.dialog.host);
  const processWithStages = useStore((s) => s.adcm.clusterHostsWizard.process);

  const [savedActionData, setSavedActionData] = useState<{
    clusterId: number | null;
    hostId: number | null;
    actionId: number | null;
  }>({ clusterId: null, hostId: null, actionId: null });

  const wizardTitle = useMemo(() => {
    return actionDetails?.displayName || defaultWizardTitle;
  }, [actionDetails]);

  useEffect(() => {
    if (actionDetails && host && cluster) {
      setSavedActionData({
        clusterId: cluster.id,
        hostId: host.id,
        actionId: actionDetails.id,
      });
    }
  }, [actionDetails, host?.id]);

  useEffect(() => {
    if (!actionDetails || actionDetails.processes === null || !host || !cluster) return;

    if (actionDetails.processes.length === 0) {
      dispatch(
        createClusterHostDynamicActionProcess({ clusterId: cluster.id, hostId: host.id, actionId: actionDetails.id }),
      );
    } else if (!processWithStages) {
      dispatch(
        getProcessOnActionClick({
          clusterId: cluster.id,
          hostId: host.id,
          actionId: actionDetails.id,
          processId: actionDetails.processes[0].id,
        }),
      );
    }
  }, [dispatch, actionDetails, cluster?.id]);

  useEffect(() => {
    if (
      actionDetails?.processes &&
      actionDetails?.processes.length > 0 &&
      savedActionData.clusterId &&
      savedActionData.hostId &&
      savedActionData.actionId
    ) {
      dispatch(
        openClusterHostsWizardDialog({
          processId: actionDetails?.processes[0].id,
          hostId: savedActionData.hostId,
          clusterId: savedActionData.clusterId,
          actionId: savedActionData.actionId,
        }),
      );
    }
  }, [dispatch, actionDetails?.processes, savedActionData]);

  const handleClose = () => {
    dispatch(closeClusterHostsWizardDialog());
    dispatch(cleanupClusterHostsWizard());
    dispatch(cleanupClusterHostActionDetails());
    dispatch(setIsContinueProcessModal(false));
  };

  return {
    wizardTitle,
    onClose: handleClose,
  };
};
