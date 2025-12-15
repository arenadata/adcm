import type React from 'react';
import { useEffect, useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import ActionWizard from '@uikit/ActionWizard/ActionWizard';
import { ActionWizardValidationContextProvider } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardValidationContextProvider/ActionWizardValidationContextProvider';
import Modal from '@uikit/Modal/Modal';
import ActionWizardConflictProcessDialog from '@commonComponents/ActionWizardConflictProcessDialog/ActionWizardConflictProcessDialog';
import { checkForBrokenStep, lastStepId } from '@uikit/ActionWizardSteps/ActionWizardSteps.utils';
import { useServiceComponentsDynamicActionWizardDialog } from '@pages/cluster/service/ServiceComponents/Dialogs/ServiceComponentsDynamicActionWizardDialog/useServiceComponentsDynamicActionWizardDialog';
import {
  getProcess,
  getStep,
  setBrokenStepError,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsWizardSlice';
import {
  createProcess,
  setHasConflictError,
  setIsContinueProcessModal,
  setSelectedStepId,
  startNewProcess,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsWizardActionsSlice';
import ServiceComponentsDynamicActionWizardStep from './ServiceComponentsDynamicActionWizardStep/ServiceComponentsDynamicActionWizardStep';

const ServiceComponentsActionWizardDialog: React.FC = () => {
  const dispatch = useDispatch();
  const clusterId = useStore(({ adcm }) => adcm.clusterServiceComponentsWizardActions.wizardDialog.clusterId);
  const serviceId = useStore(({ adcm }) => adcm.clusterServiceComponentsWizardActions.wizardDialog.serviceId);
  const componentId = useStore(({ adcm }) => adcm.clusterServiceComponentsWizardActions.wizardDialog.componentId);
  const actionId = useStore(({ adcm }) => adcm.clusterServiceComponentsWizardActions.wizardDialog.actionId);

  const processId = useStore((s) => s.adcm.clusterServiceComponentsWizardActions.wizardDialog.processId);
  const process = useStore((s) => s.adcm.clusterServiceComponentsWizardActions.wizardDialog.process);
  const processWithStages = useStore((s) => s.adcm.clusterServiceComponentsWizard.process);

  const selectedStep = useStore((s) => s.adcm.clusterServiceComponentsWizardActions.selectedStepId);
  const jobsData = useStore((s) => s.adcm.clusterServiceComponentsWizard.jobsData);
  const brokenStepError = useStore((s) => s.adcm.clusterServiceComponentsWizard.brokenStepError);
  const hasConflictError = useStore((s) => s.adcm.clusterServiceComponentsWizardActions.wizardDialog.hasConflictError);
  const isContinueProcessModal = useStore(
    (s) => s.adcm.clusterServiceComponentsWizardActions.wizardDialog.isContinueProcessModal,
  );

  const { wizardTitle, onClose } = useServiceComponentsDynamicActionWizardDialog();

  const brokenStep = useMemo(
    () => (processWithStages?.stages ? checkForBrokenStep(processWithStages?.stages) : undefined),
    [processWithStages],
  );

  const currentStep = useMemo(
    () => processWithStages && (processWithStages.currentStep ?? lastStepId(processWithStages.stages)),
    [processWithStages],
  );

  useEffect(() => {
    if (clusterId && serviceId && componentId && actionId && processId && brokenStep) {
      dispatch(setBrokenStepError('Error')); // mockup while waiting for real one and not allow to render WizardSteps
      dispatch(getStep({ clusterId, serviceId, componentId, actionId, processId, stepId: brokenStep }));
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
    if (clusterId && serviceId && componentId && actionId && processId) {
      dispatch(getProcess({ clusterId, serviceId, componentId, actionId, processId }));
      dispatch(setHasConflictError(false));
    }
  };

  const handleStartNewConflictDialog = () => {
    if (clusterId && serviceId && componentId && actionId) {
      dispatch(createProcess({ clusterId, serviceId, componentId, actionId }));
      dispatch(setHasConflictError(false));
    }
  };

  const handleCloseChangedProcessDialog = () => {
    dispatch(setIsContinueProcessModal(false));
    onClose();
  };

  const handleContinueChangedProcessDialog = () => {
    if (clusterId && serviceId && componentId && actionId && processId) {
      dispatch(getProcess({ clusterId, serviceId, componentId, actionId, processId }));
      dispatch(setIsContinueProcessModal(false));
    }
  };

  const handleStartNewChangedProcessDialog = () => {
    if (clusterId && serviceId && componentId && actionId) {
      dispatch(startNewProcess({ clusterId, serviceId, componentId, actionId }));
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
              entityDynamicActionWizardStepComponent={ServiceComponentsDynamicActionWizardStep}
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

export default ServiceComponentsActionWizardDialog;
