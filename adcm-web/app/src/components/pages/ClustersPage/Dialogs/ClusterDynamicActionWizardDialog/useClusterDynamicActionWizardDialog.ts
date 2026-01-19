import {
  cleanupClusterActionDetails,
  createClusterDynamicActionProcess,
} from '@store/adcm/clusters/clustersDynamicActionsSlice';
import { cleanupClustersWizard, getProcessOnActionClick } from '@store/adcm/clusters/clustersWizardSlice';
import {
  closeClusterWizardDialog,
  openClusterWizardDialog,
  setIsContinueProcessModal,
} from '@store/adcm/clusters/clustersWizardActionsSlice';
import { useDispatch, useStore } from '@hooks';
import { useRemoveActionIdFromUrl } from '@hooks/useRemoveActionIdFromUrl/useRemoveActionIdFromUrl';
import { useEffect, useMemo, useState } from 'react';
import { defaultWizardTitle } from '@uikit/ActionWizard/ActionWizard.constants';

export const useClusterDynamicActionWizardDialog = () => {
  const dispatch = useDispatch();
  const removeActionIdFromUrl = useRemoveActionIdFromUrl();
  const actionDetails = useStore((s) => s.adcm.clustersDynamicActions.dialog.actionDetails);
  const cluster = useStore((s) => s.adcm.clustersDynamicActions.dialog.cluster);
  const processWithStages = useStore((s) => s.adcm.clustersWizard.process);

  const [savedActionData, setSavedActionData] = useState<{
    clusterId: number | null;
    actionId: number | null;
  }>({ clusterId: null, actionId: null });

  const wizardTitle = useMemo(() => {
    return actionDetails?.displayName || defaultWizardTitle;
  }, [actionDetails]);

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
      removeActionIdFromUrl();
    }
  }, [dispatch, actionDetails?.processes, savedActionData, removeActionIdFromUrl]);

  const handleClose = () => {
    dispatch(closeClusterWizardDialog());
    dispatch(cleanupClustersWizard());
    dispatch(cleanupClusterActionDetails());
    dispatch(setIsContinueProcessModal(false));
  };

  return {
    wizardTitle,
    onClose: handleClose,
  };
};
