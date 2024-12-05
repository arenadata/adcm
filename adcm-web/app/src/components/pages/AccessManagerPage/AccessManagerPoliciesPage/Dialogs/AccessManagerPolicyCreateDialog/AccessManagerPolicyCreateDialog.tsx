import type React from 'react';
import { Dialog } from '@uikit';
import { useAccessManagerPolicyCreateDialog } from './useAccessManagerPolicyCreateDialog';
import type { ChangeFormDataPayload } from '../common/AccessManagerPolicyFormDialog.types';
import { isValidSecondStep } from '../common/AccessManagerPolicyFormDialog.utils';
import PolicyFormDialogWizard from '../common/PolicyFormDialogWizard/PolicyFormDialogWizard/PolicyFormDialogWizard';
import { Steps } from '../common/PolicyFormDialogWizard/constants';
import {
  AccessManagerPolicyFormDialogWizardStepOne,
  AccessManagerPolicyFormDialogWizardStepTwo,
} from '../common/PolicyFormDialogWizard/wizardSteps';

const AccessManagerPolicyCreateDialog: React.FC = () => {
  const {
    //
    isOpen,
    formData,
    isValid,
    currentStep,
    errors,
    setCurrentStep,
    onSubmit,
    onClose,
    onChangeFormData,
  } = useAccessManagerPolicyCreateDialog();

  const isCurrentStepMainInfo = currentStep === Steps.MainInfo;
  const isCurrentStepObject = currentStep === Steps.Object;

  const changeFormData = (value: ChangeFormDataPayload) => {
    onChangeFormData(value);
  };

  const handleSwitchStep = () => {
    setCurrentStep(Steps.Object);
  };

  return (
    <Dialog
      isOpen={isOpen}
      onOpenChange={onClose}
      title="Create new policy"
      actionButtonLabel={isCurrentStepMainInfo ? 'Next' : 'Create'}
      isActionDisabled={isCurrentStepMainInfo ? !isValid : !isValidSecondStep(formData)}
      onAction={isCurrentStepMainInfo ? handleSwitchStep : onSubmit}
      onCancel={onClose}
    >
      <PolicyFormDialogWizard isValid={isValid} onChangeStep={setCurrentStep} currentStep={currentStep} />
      {isCurrentStepMainInfo && (
        <AccessManagerPolicyFormDialogWizardStepOne
          formData={formData}
          errors={errors}
          changeFormData={changeFormData}
        />
      )}
      {isCurrentStepObject && (
        <AccessManagerPolicyFormDialogWizardStepTwo formData={formData} changeFormData={changeFormData} />
      )}
    </Dialog>
  );
};
export default AccessManagerPolicyCreateDialog;
