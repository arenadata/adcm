import type React from 'react';
import ActionWizard from '@uikit/ActionWizard/ActionWizard';
import { ActionWizardValidationContextProvider } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardValidationContextProvider/ActionWizardValidationContextProvider';
import Modal from '@uikit/Modal/Modal';
import ActionWizardConflictProcessDialog from '@commonComponents/ActionWizardConflictProcessDialog/ActionWizardConflictProcessDialog';
import EntityDynamicActionWizardStep from './EntityDynamicActionWizardStep/EntityDynamicActionWizardStep';
import type { AdcmActionWizardProcess, AdcmWizardJobsData } from '@models/adcm/wizard';
import type { WizardOwner, SomeEntityArgs } from '@store/adcm/entityWizard/types/wizardSlice.types';
import { EntityWizardDataContextProvider } from './EntityWizardContextProvider/EntityWizardDataContextProvider';

export interface EntityDynamicActionWizardDialogProps {
  entityType: WizardOwner;
  entityArgs: SomeEntityArgs;
  wizardTitle: string;
  process: AdcmActionWizardProcess | null;
  processWithStages: AdcmActionWizardProcess | null;
  currentStep: number | null;
  selectedStep?: number;
  jobsData: AdcmWizardJobsData;
  brokenStepError?: string;
  hasConflictError: boolean;
  isContinueProcessModal: boolean;
  onSetBrokenStepError: (error?: string) => void;
  onSetSelectedStepId: (id: number) => void;
  onCloseConfictDialog: () => void;
  onContinueConflictDialog: () => void;
  onStartNewConfictDialog: () => void;
  onCloseChangedProcessDialog: () => void;
  onContinueChangedProcessDialog: () => void;
  onStartNewChangedProcessDialog: () => void;
  onClose: () => void;
}

const EntityDynamicActionWizardDialog: React.FC<EntityDynamicActionWizardDialogProps> = ({
  entityType,
  entityArgs,
  wizardTitle,
  process,
  processWithStages,
  currentStep,
  selectedStep,
  jobsData,
  brokenStepError,
  hasConflictError,
  isContinueProcessModal,
  onSetBrokenStepError,
  onSetSelectedStepId,
  onCloseConfictDialog,
  onContinueConflictDialog,
  onStartNewConfictDialog,
  onCloseChangedProcessDialog,
  onContinueChangedProcessDialog,
  onStartNewChangedProcessDialog,
  onClose,
}) => {
  return (
    <>
      {!isContinueProcessModal && processWithStages && currentStep && (
        <Modal isOpen={true}>
          <ActionWizardValidationContextProvider>
            <EntityWizardDataContextProvider entityType={entityType} entityArgs={entityArgs}>
              <ActionWizard
                wizardTitle={wizardTitle}
                stages={processWithStages.stages}
                selectedStep={selectedStep}
                brokenStepError={brokenStepError}
                currentStep={currentStep}
                process={processWithStages ?? process}
                jobsData={jobsData}
                onClose={onClose}
                onSetSelectedStepId={onSetSelectedStepId}
                onSetBrokenStepError={onSetBrokenStepError}
                entityDynamicActionWizardStepComponent={EntityDynamicActionWizardStep}
              />
            </EntityWizardDataContextProvider>
          </ActionWizardValidationContextProvider>
        </Modal>
      )}
      {hasConflictError && (
        <ActionWizardConflictProcessDialog
          title="Process has been changed"
          description="Changes have been made to the current process. Do you wish to start a new process or continue the current one?"
          onCancel={onCloseConfictDialog}
          onContinue={onContinueConflictDialog}
          onStartNew={onStartNewConfictDialog}
        />
      )}
      {isContinueProcessModal && (
        <ActionWizardConflictProcessDialog
          title="Continue process"
          description="Do you wish to continue or discard previous data and start new process?"
          onCancel={onCloseChangedProcessDialog}
          onContinue={onContinueChangedProcessDialog}
          onStartNew={onStartNewChangedProcessDialog}
        />
      )}
    </>
  );
};

export default EntityDynamicActionWizardDialog;
