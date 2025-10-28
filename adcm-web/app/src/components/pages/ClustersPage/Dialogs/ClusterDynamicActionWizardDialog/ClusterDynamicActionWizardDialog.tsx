import type React from 'react';
import { useEffect, useMemo, useState } from 'react';
import { useDispatch, useStore } from '@hooks';
import { type AdcmWizardStage, AdcmWizardStepType } from '@models/adcm/wizard';
import { useClusterDynamicActionWizardDialog } from '@pages/ClustersPage/Dialogs/ClusterDynamicActionWizardDialog/useClusterDynamicActionWizardDialog';
import ActionWizard from '@uikit/ActionWizard/ActionWizard';
import { ActionWizardValidationContextProvider } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardValidationContextProvider/ActionWizardValidationContextProvider';
import Modal from '@uikit/Modal/Modal';
import { getStep, setBrokenStepError } from '@store/adcm/clusters/clustersWizardSlice';

const lastStepId = (stages: AdcmWizardStage[]) => {
  return stages.flatMap((stage) => stage.steps).find((step) => step.type === AdcmWizardStepType.LastStep)?.id || null;
};

const checkForBrokenStep = (stages: AdcmWizardStage[]) => {
  return stages.flatMap((stage) => stage.steps).find((step) => step.state === 'broken')?.id ?? undefined;
};

const ClusterActionWizardDialog: React.FC = () => {
  const dispatch = useDispatch();
  const [isOpen, setIsOpen] = useState(true);
  const clusterId = useStore(({ adcm }) => adcm.clustersWizardActions.wizardDialog.clusterId);
  const actionId = useStore(({ adcm }) => adcm.clustersWizardActions.wizardDialog.actionId);
  const process = useStore((s) => s.adcm.clustersWizardActions.wizardDialog.process);
  const processWithStages = useStore((s) => s.adcm.clustersWizard.process);
  const selectedStep = useStore((s) => s.adcm.clustersWizardActions.selectedStepId);
  const jobsData = useStore((s) => s.adcm.clustersWizard.jobsData);
  const brokenStepError = useStore((s) => s.adcm.clustersWizard.brokenStepError);

  const { onClose } = useClusterDynamicActionWizardDialog();

  const brokenStep = useMemo(
    () => (processWithStages?.stages ? checkForBrokenStep(processWithStages?.stages) : undefined),
    [processWithStages],
  );

  useEffect(() => {
    if (clusterId && actionId && process && brokenStep) {
      dispatch(setBrokenStepError('Error')); // mockup while waiting for real one and not allow to render WizardSteps
      dispatch(getStep({ clusterId, actionId, processId: process.id, stepId: brokenStep }));
    }
  }, [dispatch, clusterId, actionId, process?.id, brokenStep]);

  if (!process || !processWithStages) return null;

  const currentStep = processWithStages.currentStep ?? lastStepId(processWithStages.stages);

  return (
    <Modal isOpen={isOpen} onOpenChange={setIsOpen}>
      <ActionWizardValidationContextProvider>
        <ActionWizard
          stages={processWithStages.stages}
          selectedStep={selectedStep}
          brokenStepError={brokenStepError}
          currentStep={currentStep}
          process={process}
          jobsData={jobsData}
          onClose={onClose}
        />
      </ActionWizardValidationContextProvider>
    </Modal>
  );
};

export default ClusterActionWizardDialog;
