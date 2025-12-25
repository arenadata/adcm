import type React from 'react';
import { useEffect, useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import { useClusterDynamicActionWizardDialog } from '@pages/ClustersPage/Dialogs/ClusterDynamicActionWizardDialog/useClusterDynamicActionWizardDialog';
import ActionWizard from '@uikit/ActionWizard/ActionWizard';
import { ActionWizardValidationContextProvider } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardValidationContextProvider/ActionWizardValidationContextProvider';
import Modal from '@uikit/Modal/Modal';
import { getProcess, getStep, setBrokenStepError } from '@store/adcm/clusters/clustersWizardSlice';
import ActionWizardConflictProcessDialog from '@commonComponents/ActionWizardConflictProcessDialog/ActionWizardConflictProcessDialog';
import {
  createProcess,
  setHasConflictError,
  setIsContinueProcessModal,
  setSelectedStepId,
  startNewProcess,
} from '@store/adcm/clusters/clustersWizardActionsSlice';
import { checkForBrokenStep, lastStepId } from '@uikit/ActionWizardSteps/ActionWizardSteps.utils';
import ClusterDynamicActionWizardStep from '@pages/ClustersPage/Dialogs/ClusterDynamicActionWizardDialog/ClusterDynamicActionWizardStep/ClusterDynamicActionWizardStep';

const ClusterActionWizardDialog: React.FC = () => {
  const dispatch = useDispatch();
  const clusterId = useStore(({ adcm }) => adcm.clustersWizardActions.wizardDialog.clusterId);
  const actionId = useStore(({ adcm }) => adcm.clustersWizardActions.wizardDialog.actionId);

  const processId = useStore((s) => s.adcm.clustersWizardActions.wizardDialog.processId);
  const process = useStore((s) => s.adcm.clustersWizardActions.wizardDialog.process);
  const processWithStages = useStore((s) => s.adcm.clustersWizard.process);

  const selectedStep = useStore((s) => s.adcm.clustersWizardActions.selectedStepId);
  const jobsData = useStore((s) => s.adcm.clustersWizard.jobsData);
  const brokenStepError = useStore((s) => s.adcm.clustersWizard.brokenStepError);
  const hasConflictError = useStore((s) => s.adcm.clustersWizardActions.wizardDialog.hasConflictError);
  const isContinueProcessModal = useStore((s) => s.adcm.clustersWizardActions.wizardDialog.isContinueProcessModal);

  const { wizardTitle, onClose } = useClusterDynamicActionWizardDialog();

  const brokenStep = useMemo(
    () => (processWithStages?.stages ? checkForBrokenStep(processWithStages?.stages) : undefined),
    [processWithStages],
  );

  const currentStep = useMemo(
    () => processWithStages && (processWithStages.currentStep ?? lastStepId(processWithStages.stages)),
    [processWithStages],
  );

  useEffect(() => {
    if (clusterId && actionId && processId && brokenStep) {
      dispatch(setBrokenStepError('Error')); // mockup while waiting for real one and not allow to render WizardSteps
      dispatch(getStep({ clusterId, actionId, processId, stepId: brokenStep }));
    }
  }, [dispatch, clusterId, actionId, processId, brokenStep]);

  const handleSetBrokenStepError = (error?: string) => {
    dispatch(setBrokenStepError(error));
  };

  const handleSetSelectedStepId = (id: number) => {
    dispatch(setSelectedStepId(id));
  };

  const handleCloseConflictDialog = () => {
    dispatch(setHasConflictError(false));
    onClose();
  };

  const handleContinueConflictDialog = () => {
    if (clusterId && actionId && processId) {
      dispatch(getProcess({ clusterId, actionId, processId }));
      dispatch(setHasConflictError(false));
    }
  };

  const handleStartNewConflictDialog = () => {
    if (clusterId && actionId) {
      dispatch(createProcess({ clusterId, actionId }));
      dispatch(setHasConflictError(false));
    }
  };

  const handleCloseChangedProcessDialog = () => {
    dispatch(setIsContinueProcessModal(false));
    onClose();
  };

  const handleContinueChangedProcessDialog = () => {
    if (clusterId && actionId && processId) {
      dispatch(getProcess({ clusterId, actionId, processId }));
      dispatch(setIsContinueProcessModal(false));
    }
  };

  const handleStartNewChangedProcessDialog = () => {
    if (clusterId && actionId) {
      dispatch(startNewProcess({ clusterId, actionId }));
      dispatch(setBrokenStepError(undefined));
    }
  };

  return (
    <>
      {!isContinueProcessModal && processWithStages && currentStep && (
        <Modal isOpen={true}>
          <ActionWizardValidationContextProvider>
            <ActionWizard
              wizardTitle={wizardTitle}
              stages={processWithStages.stages}
              selectedStep={selectedStep}
              brokenStepError={brokenStepError}
              currentStep={currentStep}
              process={processWithStages ?? process}
              jobsData={jobsData}
              onClose={onClose}
              onSetSelectedStepId={handleSetSelectedStepId}
              onSetBrokenStepError={handleSetBrokenStepError}
              entityDynamicActionWizardStepComponent={ClusterDynamicActionWizardStep}
            />
          </ActionWizardValidationContextProvider>
        </Modal>
      )}
      {hasConflictError && (
        <ActionWizardConflictProcessDialog
          title="Process has been changed"
          description="Changes have been made to the current process. Do you wish to start a new process or continue the current one?"
          onCancel={handleCloseConflictDialog}
          onContinue={handleContinueConflictDialog}
          onStartNew={handleStartNewConflictDialog}
        />
      )}
      {isContinueProcessModal && (
        <ActionWizardConflictProcessDialog
          title="Continue process"
          description="Do you wish to continue or discard previous data and start new process?"
          onCancel={handleCloseChangedProcessDialog}
          onContinue={handleContinueChangedProcessDialog}
          onStartNew={handleStartNewChangedProcessDialog}
        />
      )}
    </>
  );
};

export default ClusterActionWizardDialog;
