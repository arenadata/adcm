import type React from 'react';
import { Dialog } from '@uikit';
import { AddServiceStepKey } from './AddClusterServiceDialog.types';
import SelectServicesStep from './SelectServicesStep/SelectServicesStep';
import { useAddClusterServiceDialog } from './useAddClusterServiceDialog';
import ServicesLicensesStep from './ServicesLicensesStep/ServicesLicensesStep';

const AddClusterServiceDialog: React.FC = () => {
  const {
    isOpen,
    onClose,
    onSubmit,
    formData,
    handleChangeFormData,
    currentStep,
    isValid,
    switchToLicenseStep,
    unacceptedSelectedServices,
  } = useAddClusterServiceDialog();

  const isNextLicenseStep = currentStep === AddServiceStepKey.SelectServices && unacceptedSelectedServices.length > 0;

  const handleAction = () => {
    isNextLicenseStep ? switchToLicenseStep() : onSubmit();
  };

  return (
    <Dialog
      isOpen={isOpen}
      title="Add services"
      onOpenChange={onClose}
      onCancel={onClose}
      onAction={handleAction}
      actionButtonLabel={isNextLicenseStep ? 'Next' : 'Add'}
      isActionDisabled={!isValid}
    >
      {currentStep === AddServiceStepKey.SelectServices && (
        <SelectServicesStep
          formData={formData}
          onChange={handleChangeFormData}
          unacceptedSelectedServices={unacceptedSelectedServices}
        />
      )}

      {currentStep === AddServiceStepKey.ServicesLicenses && (
        <ServicesLicensesStep
          formData={formData}
          onChange={handleChangeFormData}
          unacceptedSelectedServices={unacceptedSelectedServices}
        />
      )}
    </Dialog>
  );
};
export default AddClusterServiceDialog;
