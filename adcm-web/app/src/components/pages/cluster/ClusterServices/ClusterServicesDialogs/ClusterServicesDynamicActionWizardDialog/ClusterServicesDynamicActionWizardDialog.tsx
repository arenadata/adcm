import type React from 'react';
import { useEffect, useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import ActionWizard from '@uikit/ActionWizard/ActionWizard';
import { ActionWizardValidationContextProvider } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardValidationContextProvider/ActionWizardValidationContextProvider';
import Modal from '@uikit/Modal/Modal';
import ActionWizardConflictProcessDialog from '@commonComponents/ActionWizardConflictProcessDialog/ActionWizardConflictProcessDialog';
import { checkForBrokenStep, lastStepId } from '@uikit/ActionWizardSteps/ActionWizardSteps.utils';
import { useClusterServicesDynamicActionWizardDialog } from './useClusterServicesDynamicActionWizardDialog';
import { getProcess, getStep, setBrokenStepError } from '@store/adcm/cluster/services/servicesWizardSlice';
import {
  createProcess,
  setHasConflictError,
  setIsContinueProcessModal,
  setSelectedStepId,
  startNewProcess,
} from '@store/adcm/cluster/services/servicesWizardActionsSlice';
import ClusterServicesDynamicActionWizardStep from '@pages/cluster/ClusterServices/ClusterServicesDialogs/ClusterServicesDynamicActionWizardDialog/ClusterServicesDynamicActionWizardStep/ClusterServicesDynamicActionWizardStep';

const ClusterServicesActionWizardDialog: React.FC = () => {
  const dispatch = useDispatch();
  const clusterId = useStore(({ adcm }) => adcm.clusterServicesWizardActions.wizardDialog.clusterId);
  const serviceId = useStore(({ adcm }) => adcm.clusterServicesWizardActions.wizardDialog.serviceId);
  const actionId = useStore(({ adcm }) => adcm.clusterServicesWizardActions.wizardDialog.actionId);

  const processId = useStore((s) => s.adcm.clusterServicesWizardActions.wizardDialog.processId);
  const process = useStore((s) => s.adcm.clusterServicesWizardActions.wizardDialog.process);
  const processWithStages = useStore((s) => s.adcm.clusterServicesWizard.process);

  const selectedStep = useStore((s) => s.adcm.clusterServicesWizardActions.selectedStepId);
  const jobsData = useStore((s) => s.adcm.clusterServicesWizard.jobsData);
  const brokenStepError = useStore((s) => s.adcm.clusterServicesWizard.brokenStepError);
  const hasConflictError = useStore((s) => s.adcm.clusterServicesWizardActions.wizardDialog.hasConflictError);
  const isContinueProcessModal = useStore(
    (s) => s.adcm.clusterServicesWizardActions.wizardDialog.isContinueProcessModal,
  );

  const { wizardTitle, onClose } = useClusterServicesDynamicActionWizardDialog();

  const brokenStep = useMemo(
    () => (processWithStages?.stages ? checkForBrokenStep(processWithStages?.stages) : undefined),
    [processWithStages],
  );

  const currentStep = useMemo(
    () => processWithStages && (processWithStages.currentStep ?? lastStepId(processWithStages.stages)),
    [processWithStages],
  );

  useEffect(() => {
    if (clusterId && serviceId && actionId && processId && brokenStep) {
      dispatch(setBrokenStepError('Error')); // mockup while waiting for real one and not allow to render WizardSteps
      dispatch(getStep({ clusterId, serviceId, actionId, processId, stepId: brokenStep }));
    }
  }, [dispatch, clusterId, serviceId, actionId, processId, brokenStep]);

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
    if (clusterId && serviceId && actionId && processId) {
      dispatch(getProcess({ clusterId, serviceId, actionId, processId }));
      dispatch(setHasConflictError(false));
    }
  };

  const handleStartNewConflictDialog = () => {
    if (clusterId && serviceId && actionId) {
      dispatch(createProcess({ clusterId, serviceId, actionId }));
      dispatch(setHasConflictError(false));
    }
  };

  const handleCloseChangedProcessDialog = () => {
    dispatch(setIsContinueProcessModal(false));
    onClose();
  };

  const handleContinueChangedProcessDialog = () => {
    if (clusterId && serviceId && actionId && processId) {
      dispatch(getProcess({ clusterId, serviceId, actionId, processId }));
      dispatch(setIsContinueProcessModal(false));
    }
  };

  const handleStartNewChangedProcessDialog = () => {
    if (clusterId && serviceId && actionId) {
      dispatch(startNewProcess({ clusterId, serviceId, actionId }));
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
              entityDynamicActionWizardStepComponent={ClusterServicesDynamicActionWizardStep}
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

export default ClusterServicesActionWizardDialog;
