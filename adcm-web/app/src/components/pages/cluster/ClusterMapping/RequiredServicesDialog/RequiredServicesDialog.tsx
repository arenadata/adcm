import type React from 'react';
import { DialogV2 } from '@uikit';
import { useRequiredServicesDialog } from './useRequiredServicesDialog';
import ShowServices from './ShowServices/ShowServices';
import ServicesLicensesStep from './ServicesLicensesStep/ServicesLicensesStep';
import { RequiredServicesStepKey } from './RequiredServicesDialog.types';

const RequiredServicesDialog: React.FC = () => {
  const {
    isOpen,
    onClose,
    onSubmit,
    currentStep,
    formData,
    handleChangeFormData,
    unacceptedDependsServices,
    dependsServices,
    switchToLicenseStep,
    isValid,
  } = useRequiredServicesDialog();

  const isNextLicenseStep =
    currentStep === RequiredServicesStepKey.ShowServices && unacceptedDependsServices.length > 0;

  const handleAction = () => {
    isNextLicenseStep ? switchToLicenseStep() : onSubmit();
  };

  return (
    isOpen && (
      <DialogV2
        title="Required objects"
        actionButtonLabel={isNextLicenseStep ? 'Next' : 'Apply'}
        onAction={handleAction}
        onCancel={onClose}
        isActionDisabled={!isValid}
      >
        {currentStep === RequiredServicesStepKey.ShowServices && (
          <ShowServices dependsServices={dependsServices} unacceptedSelectedServices={unacceptedDependsServices} />
        )}
        {currentStep === RequiredServicesStepKey.ServicesLicenses && (
          <ServicesLicensesStep
            formData={formData}
            onChange={handleChangeFormData}
            unacceptedSelectedServices={unacceptedDependsServices}
          />
        )}
      </DialogV2>
    )
  );
};
export default RequiredServicesDialog;
