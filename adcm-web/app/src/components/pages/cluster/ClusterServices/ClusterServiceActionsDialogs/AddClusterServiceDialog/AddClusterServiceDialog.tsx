import React, { useEffect } from 'react';
import { Dialog, FormFieldsContainer, MultiSelectPanel } from '@uikit';
import s from './AddClusterServiceDialog.module.scss';
import WarningMessage from '@uikit/WarningMessage/WarningMessage';
import { useAddClusterServiceForm } from '@pages/cluster/ClusterServices/ClusterServiceActionsDialogs/AddClusterServiceDialog/useAddClusterServiceDialog';
import LicenseAcceptanceDialog from '@commonComponents/Dialog/LicenseAcceptanceDialog/LicenseAcceptanceDialog';

const AddClusterServiceDialog: React.FC = () => {
  const {
    isOpen,
    isLicenseAcceptanceDialogOpen,
    formData,
    submit,
    getLicenses,
    resetForm,
    dialogControls,
    onClose,
    onCloseLicenseAcceptanceDialog,
    onOpenLicenseAcceptanceDialog,
    onAcceptServiceLicense,
    onChangeFormData,
    relatedData: { servicesWithDependencies, isServicesWithLicenseSelected, servicePrototypesOptions, serviceLicenses },
    isValid,
  } = useAddClusterServiceForm();

  useEffect(() => {
    resetForm();
  }, [resetForm]);

  const handleClusterServicesChange = (value: number[]) => {
    onChangeFormData({ serviceIds: value });
    getLicenses(value);
  };

  return (
    <>
      <Dialog
        isOpen={isOpen}
        onOpenChange={onClose}
        title={'Add services'}
        onAction={isServicesWithLicenseSelected ? onOpenLicenseAcceptanceDialog : submit}
        actionButtonLabel={isServicesWithLicenseSelected ? 'Next' : 'Add'}
        isActionDisabled={!isValid}
      >
        <FormFieldsContainer>
          {servicePrototypesOptions?.length > 0 && (
            <MultiSelectPanel
              options={servicePrototypesOptions}
              value={formData.serviceIds}
              onChange={handleClusterServicesChange}
              checkAllLabel="All services"
              searchPlaceholder="Search services"
              isSearchable={true}
              compactMode={true}
            />
          )}
        </FormFieldsContainer>
        {servicesWithDependencies?.length > 0 && (
          <WarningMessage className={s.warning}>
            {servicesWithDependencies.map((service) => {
              return (
                <div key={`${service.prototypeId}_${service.dependableService}_${service.name}`}>
                  {service.dependableService} requires installation of {service.name}
                </div>
              );
            })}
          </WarningMessage>
        )}
        {isServicesWithLicenseSelected && (
          <WarningMessage
            className={s.warning}
            children="Services you selected require you to accept Terms of Agreement"
          />
        )}
      </Dialog>
      {serviceLicenses.length > 0 && (
        <LicenseAcceptanceDialog
          dialogTitle="Add services"
          licensesRequiringAcceptanceList={serviceLicenses}
          isOpen={isLicenseAcceptanceDialogOpen}
          onCloseClick={onCloseLicenseAcceptanceDialog}
          onAcceptLicense={onAcceptServiceLicense}
          customControls={dialogControls}
        />
      )}
    </>
  );
};
export default AddClusterServiceDialog;
