import type React from 'react';
import { DialogV2 } from '@uikit';
import { useAccessManagerPolicyUpdateDialog } from './useAccessManagerPolicyUpdateDialog';
import type { ChangeFormDataPayload } from '../common/AccessManagerPolicyFormDialog.types';
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
    isOpen && (
      <DialogV2
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
      </DialogV2>
    )
  );
};
export default AccessManagerPolicyUpdateDialog;
