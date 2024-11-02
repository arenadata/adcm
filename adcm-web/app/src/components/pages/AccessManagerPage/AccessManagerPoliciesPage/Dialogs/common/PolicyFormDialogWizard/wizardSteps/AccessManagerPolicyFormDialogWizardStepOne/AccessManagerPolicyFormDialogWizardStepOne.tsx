import React from 'react';
import { FormField, FormFieldsContainer, Input, Select } from '@uikit';
import MultiSelect from '@uikit/Select/MultiSelect/MultiSelect';
import { useAccessManagerPolicyFormDialogWizardStepOne } from './useAccessManagerPolicyFormDialogWizardStepOne';
import { useDispatch } from '@hooks';
import { getObjectCandidates } from '@store/adcm/policies/policiesSlice';
import { AccessManagerPolicyDialogsStepsProps } from '../../../AccessManagerPolicyFormDialog.types';

const AccessManagerPolicyFormDialogWizardStepOne: React.FC<AccessManagerPolicyDialogsStepsProps> = ({
  formData,
  errors,
  changeFormData,
}) => {
  const {
    roles,
    relatedData: { rolesOptions, groupsOptions },
  } = useAccessManagerPolicyFormDialogWizardStepOne();

  const dispatch = useDispatch();

  const handlePolicyNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    changeFormData({ policyName: event.target.value });
  };

  const handleDescriptionChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    changeFormData({ description: event.target.value });
  };

  const handleRoleChange = (roleId: number | null) => {
    const objectTypes = roles.find((role) => role.id === roleId)?.parametrizedByType ?? [];

    changeFormData({
      roleId,
      objectTypes,
      clusterIds: [],
      serviceClusterIds: [],
      serviceName: '',
      hostIds: [],
      hostproviderIds: [],
    });
    if (roleId && objectTypes.length > 0) {
      dispatch(getObjectCandidates(roleId));
    }
  };

  const handleGroupsChange = (groupIds: number[]) => {
    changeFormData({ groupIds });
  };

  return (
    <FormFieldsContainer>
      <FormField label="Policy name" error={errors?.policyName}>
        <Input
          value={formData.policyName}
          type="text"
          onChange={handlePolicyNameChange}
          placeholder="Enter unique name"
          autoFocus
        />
      </FormField>

      <FormField label="Description">
        <Input
          value={formData.description}
          type="text"
          onChange={handleDescriptionChange}
          placeholder="Enter description"
        />
      </FormField>

      <FormField label="Role">
        <Select
          placeholder="Select role"
          value={formData.roleId}
          onChange={handleRoleChange}
          options={rolesOptions}
          maxHeight={400}
        />
      </FormField>

      <FormField label="Groups">
        <MultiSelect
          placeholder="Select groups"
          checkAllLabel="All groups"
          value={formData.groupIds}
          onChange={handleGroupsChange}
          options={groupsOptions}
          maxHeight={310}
        />
      </FormField>
    </FormFieldsContainer>
  );
};

export default AccessManagerPolicyFormDialogWizardStepOne;
