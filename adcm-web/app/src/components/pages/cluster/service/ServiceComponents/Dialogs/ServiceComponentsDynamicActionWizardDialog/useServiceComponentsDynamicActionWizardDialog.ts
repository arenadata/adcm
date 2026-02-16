import { useDispatch, useStore } from '@hooks';
import { useRemoveActionIdFromUrl } from '@hooks/useRemoveActionIdFromUrl/useRemoveActionIdFromUrl';
import { useEffect, useMemo, useState } from 'react';
import {
  cleanupClusterServiceComponentsWizard,
  getProcessOnActionClick,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsWizardSlice';
import {
  closeClusterServiceComponentsWizardDialog,
  openClusterServiceComponentsWizardDialog,
  setIsContinueProcessModal,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsWizardActionsSlice';
import {
  cleanupClusterServiceComponentsActionDetails,
  createClusterServiceComponentsDynamicActionProcess,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsDynamicActionsSlice';
import { defaultWizardTitle } from '@uikit/ActionWizard/ActionWizard.constants';

export const useServiceComponentsDynamicActionWizardDialog = () => {
  const dispatch = useDispatch();
  const removeActionIdFromUrl = useRemoveActionIdFromUrl();
  const actionDetails = useStore((s) => s.adcm.serviceComponentsDynamicActions.dialog.actionDetails);
  const component = useStore((s) => s.adcm.serviceComponentsDynamicActions.dialog.component);

  const processWithStages = useStore((s) => s.adcm.clusterServiceComponentsWizard.process);

  const [savedActionData, setSavedActionData] = useState<{
    clusterId: number | null;
    serviceId: number | null;
    componentId: number | null;
    actionId: number | null;
  }>({ clusterId: null, serviceId: null, componentId: null, actionId: null });

  const wizardTitle = useMemo(() => {
    return actionDetails?.displayName || defaultWizardTitle;
  }, [actionDetails]);

  useEffect(() => {
    if (actionDetails && component) {
      setSavedActionData({
        clusterId: component.cluster.id,
        serviceId: component.service.id,
        componentId: component.id,
        actionId: actionDetails.id,
      });
    }
  }, [actionDetails, component]);

  useEffect(() => {
    if (!actionDetails || actionDetails.processes === null || !component) return;

    if (actionDetails.processes.length === 0) {
      dispatch(
        createClusterServiceComponentsDynamicActionProcess({
          clusterId: component.cluster.id,
          serviceId: component.service.id,
          componentId: component.id,
          actionId: actionDetails.id,
        }),
      );
    } else if (!processWithStages) {
      dispatch(
        getProcessOnActionClick({
          clusterId: component.cluster.id,
          serviceId: component.service.id,
          componentId: component.id,
          actionId: actionDetails.id,
          processId: actionDetails.processes[0].id,
        }),
      );
    }
  }, [dispatch, actionDetails, component]);

  useEffect(() => {
    if (
      actionDetails?.processes &&
      actionDetails?.processes.length > 0 &&
      savedActionData.clusterId &&
      savedActionData.serviceId &&
      savedActionData.componentId &&
      savedActionData.actionId
    ) {
      dispatch(
        openClusterServiceComponentsWizardDialog({
          processId: actionDetails?.processes[0].id,
          serviceId: savedActionData.serviceId,
          componentId: savedActionData.componentId,
          clusterId: savedActionData.clusterId,
          actionId: savedActionData.actionId,
        }),
      );
      removeActionIdFromUrl();
    }
  }, [dispatch, actionDetails?.processes, savedActionData, removeActionIdFromUrl]);

  const handleClose = () => {
    dispatch(closeClusterServiceComponentsWizardDialog());
    dispatch(cleanupClusterServiceComponentsWizard());
    dispatch(cleanupClusterServiceComponentsActionDetails());
    dispatch(setIsContinueProcessModal(false));
  };

  return {
    wizardTitle,
    onClose: handleClose,
  };
};
