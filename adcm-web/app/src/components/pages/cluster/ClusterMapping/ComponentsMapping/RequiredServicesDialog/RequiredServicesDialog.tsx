import React from 'react';
import { Dialog } from '@uikit';
import { useRequiredServicesDialog } from './useRequiredServicesDialog';
import ShowServices from '@pages/cluster/ClusterMapping/ComponentsMapping/RequiredServicesDialog/ShowServices/ShowServices';
import { RequiredServicesStepKey } from './RequiredServicesDialog.types';
import ServicesLicensesStep from '@pages/cluster/ClusterMapping/ComponentsMapping/RequiredServicesDialog/ServicesLicensesStep/ServicesLicensesStep';

const RequiredServicesDialog: React.FC = () => {
  const {
    //
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
    <Dialog
      isOpen={isOpen}
      title="Required objects"
      actionButtonLabel={isNextLicenseStep ? 'Next' : 'Apply'}
      onAction={handleAction}
      onCancel={onClose}
      onOpenChange={onClose}
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
    </Dialog>
  );
};
export default RequiredServicesDialog;
