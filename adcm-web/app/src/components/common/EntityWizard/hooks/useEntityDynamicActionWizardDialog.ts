import { useDispatch, useStore } from '@hooks';
import { useRemoveActionIdFromUrl } from '@hooks/useRemoveActionIdFromUrl/useRemoveActionIdFromUrl';
import { useEffect, useMemo, useState } from 'react';
import { defaultWizardTitle } from '@uikit/ActionWizard/ActionWizard.constants';
import {
  cleanupEntityWizard,
  getProcess,
  getProcessOnActionClick,
  getStep,
  setBrokenStepError,
} from '@store/adcm/entityWizard/wizardSlice';
import type { EntityArgs } from '@store/adcm/entityActionHostGroups/actionHostGroups.types';
import type { WizardOwner } from '@store/adcm/entityWizard/types/wizardSlice.types';
import {
  cleanupWizardActions,
  closeWizardDialog,
  createProcess,
  openWizardDialog,
  setHasConflictError,
  setIsContinueProcessModal,
  setSelectedStepId,
  startNewProcess,
} from '@store/adcm/entityWizard/wizardActionsSlice';
import { createWizardProcess } from '@store/adcm/entityDynamicActions/dynamicActionsSlice';
import { checkForBrokenStep, lastStepId } from '@uikit/ActionWizardSteps/ActionWizardSteps.utils';

export const useEntityDynamicActionWizardDialog = <T extends WizardOwner>(entityType: T, entityArgs: EntityArgs<T>) => {
  const dispatch = useDispatch();
  const removeActionIdFromUrl = useRemoveActionIdFromUrl();
  const actionDetails = useStore(({ adcm }) => adcm.dynamicActions.actionDetails);
  const processWithStages = useStore(({ adcm }) => adcm.entityWizard.process);

  const actionId = useStore(({ adcm }) => adcm.entityWizardActions.wizardDialog.actionId);
  const processId = useStore(({ adcm }) => adcm.entityWizardActions.wizardDialog.processId);
  const process = useStore(({ adcm }) => adcm.entityWizardActions.wizardDialog.process);
  const selectedStep = useStore(({ adcm }) => adcm.entityWizardActions.selectedStepId);
  const jobsData = useStore(({ adcm }) => adcm.entityWizard.jobsData);
  const brokenStepError = useStore(({ adcm }) => adcm.entityWizard.brokenStepError);
  const hasConflictError = useStore(({ adcm }) => adcm.entityWizardActions.wizardDialog.hasConflictError);
  const isContinueProcessModal = useStore(({ adcm }) => adcm.entityWizardActions.wizardDialog.isContinueProcessModal);
  const actionHostGroup = useStore(({ adcm }) => adcm.dynamicActions.actionHostGroup);

  const [savedActionData, setSavedActionData] = useState<{
    actionId: number | null;
    [arg: string]: number | null;
  }>({ actionId: null, ...entityArgs });

  const wizardTitle = useMemo(() => {
    return actionDetails?.displayName || defaultWizardTitle;
  }, [actionDetails]);

  useEffect(() => {
    if (actionDetails) {
      setSavedActionData({
        actionId: actionDetails.id,
        ...entityArgs,
      });
    }
  }, [actionDetails]);

  useEffect(() => {
    if (!actionDetails || actionDetails.processes === null || !actionHostGroup) return;

    if (actionDetails.processes.length === 0) {
      dispatch(
        createWizardProcess({
          entityType,
          entityArgs,
          actionId: actionDetails.id,
          actionHostGroupId: actionHostGroup.id,
        }),
      );
    } else if (!processWithStages) {
      dispatch(
        getProcessOnActionClick({
          entityType,
          entityArgs,
          actionId: actionDetails.id,
          processId: actionDetails.processes[0].id,
          actionHostGroupId: actionHostGroup.id,
        }),
      );
    }
  }, [dispatch, actionDetails, actionDetails?.processes]);

  useEffect(() => {
    if (actionDetails?.processes && actionDetails.processes.length > 0 && savedActionData.actionId) {
      dispatch(
        openWizardDialog({
          processId: actionDetails.processes[0].id,
          actionId: savedActionData.actionId,
          entityArgs,
        }),
      );
      removeActionIdFromUrl();
    }
  }, [dispatch, actionDetails?.processes, savedActionData, removeActionIdFromUrl]);

  const brokenStep = useMemo(
    () => (processWithStages?.stages ? checkForBrokenStep(processWithStages?.stages) : undefined),
    [processWithStages],
  );

  const currentStep = useMemo(
    () => processWithStages && (processWithStages.currentStep ?? lastStepId(processWithStages.stages)),
    [processWithStages],
  );

  useEffect(() => {
    if (actionId && processId && brokenStep && actionHostGroup) {
      dispatch(setBrokenStepError('Error')); // mockup while waiting for real one and not allow to render WizardSteps
      dispatch(
        getStep({
          entityType,
          entityArgs,
          actionId,
          processId,
          stepId: brokenStep,
          actionHostGroupId: actionHostGroup.id,
        }),
      );
    }
  }, [dispatch, actionId, processId, brokenStep]);

  const handleClose = () => {
    dispatch(closeWizardDialog());
    dispatch(cleanupEntityWizard());
    dispatch(cleanupWizardActions());
    dispatch(setIsContinueProcessModal(false));
  };

  const handleSetBrokenStepError = (error?: string) => {
    dispatch(setBrokenStepError(error));
  };

  const handleSetSelectedStepId = (id: number) => {
    dispatch(setSelectedStepId(id));
  };

  const handleCloseConflictDialog = () => {
    dispatch(setHasConflictError(false));
    handleClose();
  };

  const handleContinueConflictDialog = () => {
    if (actionId && processId && actionHostGroup) {
      dispatch(getProcess({ entityType, entityArgs, actionId, processId, actionHostGroupId: actionHostGroup.id }));
      dispatch(setHasConflictError(false));
    }
  };

  const handleStartNewConflictDialog = () => {
    if (actionId && actionHostGroup) {
      dispatch(createProcess({ entityType, entityArgs, actionId, actionHostGroupId: actionHostGroup.id }));
      dispatch(setHasConflictError(false));
    }
  };

  const handleCloseChangedProcessDialog = () => {
    dispatch(setIsContinueProcessModal(false));
    handleClose();
  };

  const handleContinueChangedProcessDialog = () => {
    if (actionId && processId && actionHostGroup) {
      dispatch(getProcess({ entityType, entityArgs, actionId, processId, actionHostGroupId: actionHostGroup.id }));
      dispatch(setIsContinueProcessModal(false));
    }
  };

  const handleStartNewChangedProcessDialog = () => {
    if (actionId && actionHostGroup) {
      dispatch(startNewProcess({ entityType, entityArgs, actionId, actionHostGroupId: actionHostGroup.id }));
      dispatch(setBrokenStepError(undefined));
    }
  };

  return {
    wizardTitle,
    process,
    currentStep,
    selectedStep,
    jobsData,
    brokenStepError,
    hasConflictError,
    isContinueProcessModal,
    processWithStages,
    onSetBrokenStepError: handleSetBrokenStepError,
    onSetSelectedStepId: handleSetSelectedStepId,
    onCloseConfictDialog: handleCloseConflictDialog,
    onContinueConflictDialog: handleContinueConflictDialog,
    onStartNewConfictDialog: handleStartNewConflictDialog,
    onCloseChangedProcessDialog: handleCloseChangedProcessDialog,
    onContinueChangedProcessDialog: handleContinueChangedProcessDialog,
    onStartNewChangedProcessDialog: handleStartNewChangedProcessDialog,
    onClose: handleClose,
  };
};
