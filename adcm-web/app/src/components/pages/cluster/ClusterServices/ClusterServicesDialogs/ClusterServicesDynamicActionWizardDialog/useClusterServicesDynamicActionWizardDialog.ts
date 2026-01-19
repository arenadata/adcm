import { useDispatch, useStore } from '@hooks';
import { useRemoveActionIdFromUrl } from '@hooks/useRemoveActionIdFromUrl/useRemoveActionIdFromUrl';
import { useEffect, useMemo, useState } from 'react';
import {
  cleanupClusterServiceActionDetails,
  createClusterServiceDynamicActionProcess,
} from '@store/adcm/cluster/services/servicesDynamicActionsSlice';
import {
  cleanupClusterServicesWizard,
  getProcessOnActionClick,
} from '@store/adcm/cluster/services/servicesWizardSlice';
import {
  closeClusterServiceWizardDialog,
  openClusterServiceWizardDialog,
  setIsContinueProcessModal,
} from '@store/adcm/cluster/services/servicesWizardActionsSlice';
import { defaultWizardTitle } from '@uikit/ActionWizard/ActionWizard.constants';

export const useClusterServicesDynamicActionWizardDialog = () => {
  const dispatch = useDispatch();
  const removeActionIdFromUrl = useRemoveActionIdFromUrl();
  const actionDetails = useStore((s) => s.adcm.servicesDynamicActions.dialog.actionDetails);
  const cluster = useStore((s) => s.adcm.cluster.cluster);
  const service = useStore((s) => s.adcm.servicesDynamicActions.dialog.service);
  const processWithStages = useStore((s) => s.adcm.clusterHostsWizard.process);

  const [savedActionData, setSavedActionData] = useState<{
    clusterId: number | null;
    serviceId: number | null;
    actionId: number | null;
  }>({ clusterId: null, serviceId: null, actionId: null });

  const wizardTitle = useMemo(() => {
    return actionDetails?.displayName || defaultWizardTitle;
  }, [actionDetails]);

  useEffect(() => {
    if (actionDetails && service && cluster) {
      setSavedActionData({
        clusterId: cluster.id,
        serviceId: service.id,
        actionId: actionDetails.id,
      });
    }
  }, [actionDetails, service?.id]);

  useEffect(() => {
    if (!actionDetails || actionDetails.processes === null || !service || !cluster) return;

    if (actionDetails.processes.length === 0) {
      dispatch(
        createClusterServiceDynamicActionProcess({
          clusterId: cluster.id,
          serviceId: service.id,
          actionId: actionDetails.id,
        }),
      );
    } else if (!processWithStages) {
      dispatch(
        getProcessOnActionClick({
          clusterId: cluster.id,
          serviceId: service.id,
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
      savedActionData.serviceId &&
      savedActionData.actionId
    ) {
      dispatch(
        openClusterServiceWizardDialog({
          processId: actionDetails?.processes[0].id,
          serviceId: savedActionData.serviceId,
          clusterId: savedActionData.clusterId,
          actionId: savedActionData.actionId,
        }),
      );
      removeActionIdFromUrl();
    }
  }, [dispatch, actionDetails?.processes, savedActionData, removeActionIdFromUrl]);

  const handleClose = () => {
    dispatch(closeClusterServiceWizardDialog());
    dispatch(cleanupClusterServicesWizard());
    dispatch(cleanupClusterServiceActionDetails());
    dispatch(setIsContinueProcessModal(false));
  };

  return {
    wizardTitle,
    onClose: handleClose,
  };
};
