import React, { useEffect } from 'react';
import { Dialog, FormFieldsContainer, MultiSelectPanel } from '@uikit';
import s from './AddClusterServiceDialog.module.scss';
import WarningMessage from '@uikit/WarningMessage/WarningMessage';
import { useAddClusterServiceForm } from '@pages/cluster/ClusterServices/ClusterServicesDialogs/ClusterServiceActionsDialogs/AddClusterServiceDialog/useAddClusterServiceDialog';
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
    relatedData: {
      servicesWithDependenciesList,
      isServicesWithLicenseSelected,
      servicePrototypesOptions,
      serviceLicenses,
    },
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
          {servicePrototypesOptions?.length > 0 ? (
            <MultiSelectPanel
              options={servicePrototypesOptions}
              value={formData.serviceIds}
              onChange={handleClusterServicesChange}
              checkAllLabel="All services"
              searchPlaceholder="Search services"
              isSearchable={true}
              compactMode={true}
            />
          ) : (
            <div>There are no new services. Your cluster already has all of them.</div>
          )}
        </FormFieldsContainer>
        {servicesWithDependenciesList?.length > 0 && (
          <WarningMessage className={s.warning}>
            {servicesWithDependenciesList.map((service) => {
              return (
                <p key={`${service.id}_${service.displayName}`}>
                  {service.displayName} requires installation of{' '}
                  {service.dependencies.map(({ displayName }) => displayName).join(', ')}
                </p>
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
