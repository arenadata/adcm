import type React from 'react';
import { useState } from 'react';
import { useStore } from '@hooks';
import { type AdcmWizardStage, AdcmWizardStepType } from '@models/adcm/wizard';
import { useClusterDynamicActionWizardDialog } from '@pages/ClustersPage/Dialogs/ClusterDynamicActionWizardDialog/useClusterDynamicActionWizardDialog';
import ActionWizard from '@uikit/ActionWizard/ActionWizard';
import { ActionWizardValidationContextProvider } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardValidationContextProvider/ActionWizardValidationContextProvider';
import Modal from '@uikit/Modal/Modal';

const lastStepId = (stages: AdcmWizardStage[]) => {
  return stages.flatMap((stage) => stage.steps).find((step) => step.type === AdcmWizardStepType.LastStep)?.id || null;
};

const ClusterActionWizardDialog: React.FC = () => {
  const [isOpen, setIsOpen] = useState(true);
  const process = useStore((s) => s.adcm.clustersWizardActions.wizardDialog.process);
  const processWithStages = useStore((s) => s.adcm.clustersWizard.process);

  const { onClose } = useClusterDynamicActionWizardDialog();

  if (!process || !processWithStages) return null;

  const currentStep = processWithStages.currentStep ?? lastStepId(processWithStages.stages);

  return (
    <Modal isOpen={isOpen} onOpenChange={setIsOpen}>
      <ActionWizardValidationContextProvider>
        <ActionWizard stages={processWithStages.stages} currentStep={currentStep} process={process} onClose={onClose} />
      </ActionWizardValidationContextProvider>
    </Modal>
  );
};

export default ClusterActionWizardDialog;
