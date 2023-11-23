import React, { useEffect } from 'react';
import { Dialog, FormFieldsContainer, FormField, Input } from '@uikit';
import { useUpdateGroupForm } from './useUpdateGroupForm';
import { useDispatch, useStore } from '@hooks';
import { closeUpdateDialog } from '@store/adcm/groups/groupActionsSlice';
import MultiSelect from '@uikit/Select/MultiSelect/MultiSelect';

const AccessManagerGroupsUpdateGroupDialog = () => {
  const dispatch = useDispatch();

  const isOpenDialog = useStore(({ adcm }) => !!adcm.groupsActions.updateDialog.group);

  const {
    formData,
    submitForm,
    resetForm,
    onChangeFormData,
    loadRelatedData,
    relatedData: { usersOptions },
    isValid,
    errors,
  } = useUpdateGroupForm();

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
    dispatch(closeUpdateDialog());
  };

  return (
    <Dialog
      title="Edit users group"
      isOpen={isOpenDialog}
      onOpenChange={handleCloseDialog}
      onAction={submitForm}
      isActionDisabled={!isValid}
      actionButtonLabel="Save"
    >
      <FormFieldsContainer>
        <FormField label="Group name" error={errors.name}>
          <Input
            //
            value={formData.name}
            type="text"
            onChange={handleGroupNameChange}
            placeholder="Enter unique name"
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
          />
        </FormField>
      </FormFieldsContainer>
    </Dialog>
  );
};

export default AccessManagerGroupsUpdateGroupDialog;
