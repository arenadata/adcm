import { createClusterDynamicActionProcess } from '@store/adcm/clusters/clustersDynamicActionsSlice';
import { cleanupClustersWizard, getProcessOnActionClick } from '@store/adcm/clusters/clustersWizardSlice';
import { closeClusterWizardDialog, openClusterWizardDialog } from '@store/adcm/clusters/clustersWizardActionsSlice';
import { useDispatch, useStore } from '@hooks';
import { useEffect, useState } from 'react';

let wizardTitle = 'Manage install';

export const useClusterDynamicActionWizardDialog = () => {
  const dispatch = useDispatch();
  const actionDetails = useStore((s) => s.adcm.clustersDynamicActions.dialog.actionDetails);
  const cluster = useStore((s) => s.adcm.clustersDynamicActions.dialog.cluster);
  const processWithStages = useStore((s) => s.adcm.clustersWizard.process);

  const [savedActionData, setSavedActionData] = useState<{
    clusterId: number | null;
    actionId: number | null;
  }>({ clusterId: null, actionId: null });

  useEffect(() => {
    if (actionDetails && cluster) {
      setSavedActionData({
        clusterId: cluster.id,
        actionId: actionDetails.id,
      });
    }
  }, [actionDetails, cluster?.id]);

  useEffect(() => {
    if (!actionDetails || actionDetails.processes === null || !cluster) return;
    wizardTitle = actionDetails.displayName;

    if (actionDetails.processes.length === 0) {
      dispatch(createClusterDynamicActionProcess({ clusterId: cluster.id, actionId: actionDetails.id }));
    } else if (!processWithStages) {
      dispatch(
        getProcessOnActionClick({
          clusterId: cluster.id,
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
      savedActionData.actionId
    ) {
      dispatch(
        openClusterWizardDialog({
          processId: actionDetails?.processes[0].id,
          clusterId: savedActionData.clusterId,
          actionId: savedActionData.actionId,
        }),
      );
    }
  }, [dispatch, actionDetails?.processes, savedActionData]);

  const handleClose = () => {
    dispatch(closeClusterWizardDialog());
    dispatch(cleanupClustersWizard());
  };

  return {
    wizardTitle,
    onClose: handleClose,
  };
};
