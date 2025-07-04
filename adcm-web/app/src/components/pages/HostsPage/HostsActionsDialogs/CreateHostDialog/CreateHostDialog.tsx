import type React from 'react';
import { useEffect } from 'react';
import { FormFieldsContainer, FormField, Input, Select, DialogV2 } from '@uikit';
import { useCreateHostForm } from './useCreateHostForm';
import { useDispatch, useStore } from '@hooks';
import { closeCreateDialog } from '@store/adcm/hosts/hostsActionsSlice';

const CreateHostDialog = () => {
  const dispatch = useDispatch();

  const isOpenDialog = useStore(({ adcm }) => adcm.hostsActions.createDialog.isOpen);
  const isCreating = useStore(({ adcm }) => adcm.hostsActions.isActionInProgress);

  const {
    formData,
    submit,
    reset,
    onChangeFormData,
    loadRelatedData,
    relatedData: { clustersOptions, hostProvidersOptions },
    isValid,
    errors,
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
    isOpenDialog && (
      <DialogV2
        title="Create host"
        onAction={submit}
        onCancel={handleCloseDialog}
        isActionDisabled={!isValid || isCreating}
        actionButtonLabel="Create"
        isActionButtonLoaderShown={isCreating}
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
          <FormField label="Name" error={errors.hostName}>
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
      </DialogV2>
    )
  );
};

export default CreateHostDialog;
