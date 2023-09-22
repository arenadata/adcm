import React, { useMemo } from 'react';
import s from './RbacUserForm.module.scss';
import { Checkbox, FormField, FormFieldsContainer, Input } from '@uikit';
import InputPassword from '@uikit/InputPassword/InputPassword';
import MultiSelect from '@uikit/Select/MultiSelect/MultiSelect';
import { RbacUserFormData } from './RbacUserForm.types';
import { AdcmGroup } from '@models/adcm';
import TextFormField from '@commonComponents/Forms/TextFormField/TextFormField';

interface RbacUserFormProps {
  onChangeFormData: (prop: Partial<RbacUserFormData>) => void;
  formData: RbacUserFormData;
  groups: AdcmGroup[];
  errors: Partial<Record<keyof RbacUserFormData, string | undefined>>;
  isCreate?: boolean;
}

const RbacUserForm: React.FC<RbacUserFormProps> = ({
  formData,
  onChangeFormData,
  groups,
  errors,
  isCreate = false,
}) => {
  const groupsOptions = useMemo(() => {
    return groups.map(({ displayName, id }) => ({ value: id, label: displayName }));
  }, [groups]);

  const handleUsernameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ username: event.target.value });
  };

  const handlePasswordChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ password: event.target.value });
  };

  const handleConfirmPasswordChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ confirmPassword: event.target.value });
  };

  const handleFirstNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ firstName: event.target.value });
  };

  const handleLastNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ lastName: event.target.value });
  };

  const handleEmailChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ email: event.target.value });
  };

  const handleIsSuperUserChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ isSuperUser: event.target.checked });
  };

  const handleGroupsChange = (groups: number[]) => {
    onChangeFormData({ groups });
  };

  return (
    <FormFieldsContainer className={s.rbacUserForm}>
      <FormField label="Username" className={s.rbacUserForm__username} error={errors.username}>
        {isCreate ? (
          <Input
            value={formData.username}
            type="text"
            onChange={handleUsernameChange}
            placeholder="Enter unique name"
          />
        ) : (
          <TextFormField>{formData.username}</TextFormField>
        )}
      </FormField>

      <FormField label="Password" className={s.rbacUserForm__password} error={errors.password}>
        <InputPassword value={formData.password} onChange={handlePasswordChange} placeholder="Enter password" />
      </FormField>
      <FormField label="Confirm password" error={errors.confirmPassword} className={s.rbacUserForm__confirmPassword}>
        <InputPassword
          value={formData.confirmPassword}
          onChange={handleConfirmPasswordChange}
          placeholder="Enter password"
        />
      </FormField>

      <FormField label="First name" className={s.rbacUserForm__firstName} error={errors.firstName}>
        <Input
          value={formData.firstName}
          type="text"
          onChange={handleFirstNameChange}
          placeholder="Enter"
          autoComplete="off"
        />
      </FormField>
      <FormField label="Last name" className={s.rbacUserForm__lastName} error={errors.lastName}>
        <Input
          value={formData.lastName}
          type="text"
          onChange={handleLastNameChange}
          placeholder="Enter"
          autoComplete="off"
        />
      </FormField>
      <FormField label="" className={s.rbacUserForm__isSuperUser}>
        <Checkbox
          label="Grant ADCM Administrator’s rights"
          checked={formData.isSuperUser}
          onChange={handleIsSuperUserChange}
        />
      </FormField>

      <FormField
        //
        label="Email"
        error={errors.email}
        className={s.rbacUserForm__email}
      >
        <Input
          value={formData.email}
          type="text"
          onChange={handleEmailChange}
          placeholder="User’s email"
          autoComplete="email"
        />
      </FormField>
      <FormField label="Add groups" className={s.rbacUserForm__groups}>
        <MultiSelect
          placeholder="Select"
          value={formData.groups}
          onChange={handleGroupsChange}
          options={groupsOptions}
        />
      </FormField>
    </FormFieldsContainer>
  );
};
export default RbacUserForm;
