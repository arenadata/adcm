import type React from 'react';
import { useEffect } from 'react';
import { DialogV2, FormFieldsContainer, FormField, Input } from '@uikit';
import { useCreateGroupForm } from './useCreateGroupForm';
import { useDispatch, useStore } from '@hooks';
import { closeCreateDialog } from '@store/adcm/groups/groupsActionsSlice';
import MultiSelect from '@uikit/Select/MultiSelect/MultiSelect';

const AccessManagerGroupsCreateDialog = () => {
  const dispatch = useDispatch();

  const isOpenDialog = useStore(({ adcm }) => adcm.groupsActions.createDialog.isOpen);

  const {
    formData,
    submitForm,
    resetForm,
    onChangeFormData,
    loadRelatedData,
    relatedData: { usersOptions },
    isValid,
    errors,
  } = useCreateGroupForm();

  useEffect(() => {
    resetForm();
    if (isOpenDialog) {
      loadRelatedData();
    }
  }, [isOpenDialog, resetForm, loadRelatedData]);

  const handleGroupNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ name: event.target.value });
  };

  const handleGroupDescriptionChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ description: event.target.value });
  };

  const handleGroupUsersChange = (value: number[]) => {
    onChangeFormData({ usersIds: value });
  };

  const handleCloseDialog = () => {
    dispatch(closeCreateDialog());
  };

  return (
    isOpenDialog && (
      <DialogV2
        title="Create new users group"
        onAction={submitForm}
        onCancel={handleCloseDialog}
        isActionDisabled={!isValid}
        actionButtonLabel="Create"
      >
        <FormFieldsContainer>
          <FormField label="Group name" error={errors.name}>
            <Input
              //
              value={formData.name}
              type="text"
              onChange={handleGroupNameChange}
              placeholder="Enter unique name"
              autoFocus
            />
          </FormField>
          <FormField label="Description">
            <Input
              value={formData.description}
              type="text"
              onChange={handleGroupDescriptionChange}
              placeholder="Enter description"
            />
          </FormField>
          <FormField label="Users">
            <MultiSelect
              checkAllLabel="All users"
              value={formData.usersIds}
              onChange={handleGroupUsersChange}
              options={usersOptions}
              maxHeight={400}
              placeholder="Select"
            />
          </FormField>
        </FormFieldsContainer>
      </DialogV2>
    )
  );
};

export default AccessManagerGroupsCreateDialog;
