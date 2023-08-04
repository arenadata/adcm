import React, { useEffect } from 'react';
import { Dialog, FormFieldsContainer, FormField, Input, Select } from '@uikit';
import { useCreateHostForm } from './useCreateHostForm';
import { useDispatch, useStore } from '@hooks';
import { closeCreateDialog } from '@store/adcm/hosts/hostsActionsSlice';

const CreateHostDialog = () => {
  const dispatch = useDispatch();

  const isOpenDialog = useStore(({ adcm }) => adcm.hostsActions.createDialog.isOpen);

  const {
    formData,
    submit,
    reset,
    onChangeFormData,
    loadRelatedData,
    relatedData: { clustersOptions, hostProvidersOptions },
    isValid,
  } = useCreateHostForm();

  useEffect(() => {
    reset();
    if (isOpenDialog) {
      loadRelatedData();
    }
  }, [isOpenDialog, reset, loadRelatedData]);

  const handleHostNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ hostName: event.target.value });
  };

  const handleHostProviderChange = (value: number | null) => {
    onChangeFormData({ hostproviderId: value });
  };

  const handleClusterNameChange = (value: number | null) => {
    onChangeFormData({ clusterId: value });
  };

  const handleCloseDialog = () => {
    dispatch(closeCreateDialog());
  };

  return (
    <Dialog
      title="Create host"
      isOpen={isOpenDialog}
      onOpenChange={handleCloseDialog}
      onAction={submit}
      isActionDisabled={!isValid}
    >
      <FormFieldsContainer>
        <FormField label="Hostprovider">
          <Select
            placeholder="Select hostprovider"
            value={formData.hostproviderId}
            onChange={handleHostProviderChange}
            options={hostProvidersOptions}
          />
        </FormField>
        <FormField label="Name">
          <Input
            value={formData.hostName}
            type="text"
            onChange={handleHostNameChange}
            placeholder="Enter unique host name"
          />
        </FormField>
        <FormField label="Cluster">
          <Select
            placeholder="Select cluster"
            value={formData.clusterId}
            onChange={handleClusterNameChange}
            options={clustersOptions}
          />
        </FormField>
      </FormFieldsContainer>
    </Dialog>
  );
};

export default CreateHostDialog;
