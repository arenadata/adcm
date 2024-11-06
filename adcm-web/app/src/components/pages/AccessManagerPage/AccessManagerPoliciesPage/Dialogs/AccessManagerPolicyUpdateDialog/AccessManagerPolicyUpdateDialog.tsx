import React from 'react';
import { Dialog } from '@uikit';
import { useAccessManagerPolicyUpdateDialog } from './useAccessManagerPolicyUpdateDialog';
import { ChangeFormDataPayload } from '../common/AccessManagerPolicyFormDialog.types';
import { isValidSecondStep } from '../common/AccessManagerPolicyFormDialog.utils';
import PolicyFormDialogWizard from '../common/PolicyFormDialogWizard/PolicyFormDialogWizard/PolicyFormDialogWizard';
import { Steps } from '../common/PolicyFormDialogWizard/constants';
import {
  AccessManagerPolicyFormDialogWizardStepOne,
  AccessManagerPolicyFormDialogWizardStepTwo,
} from '../common/PolicyFormDialogWizard/wizardSteps';

const AccessManagerPolicyUpdateDialog: React.FC = () => {
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
  } = useAccessManagerPolicyUpdateDialog();

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
      title="Update policy"
      actionButtonLabel={isCurrentStepMainInfo ? 'Next' : 'Update'}
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
export default AccessManagerPolicyUpdateDialog;
