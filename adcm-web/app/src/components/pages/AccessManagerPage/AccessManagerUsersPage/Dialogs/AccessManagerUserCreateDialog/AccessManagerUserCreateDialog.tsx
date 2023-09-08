import { useMemo } from 'react';
import { Dialog, Checkbox, FormField, FormFieldsContainer, Input } from '@uikit';
import InputPassword from '@uikit/InputPassword/InputPassword';
import MultiSelect from '@uikit/Select/MultiSelect/MultiSelect';
import { getOptionsFromArray } from '@uikit/Select/Select.utils';
import { useAccessManagerUserCreateDialog } from './useAccessManagerUserCreateDialog';
import CustomDialogControls from '@commonComponents/Dialog/CustomDialogControls/CustomDialogControls';
import s from './AccessManagerUserCreateDialog.module.scss';

const AccessManagerUserCreateDialog = () => {
  const { isOpen, relatedData, formData, isValid, errorMessages, onCreate, onClose, onChangeFormData } =
    useAccessManagerUserCreateDialog();

  const groupOptions = useMemo(
    () =>
      getOptionsFromArray(
        relatedData.groups,
        (x) => x.displayName,
        (x) => x.id,
      ),
    [relatedData.groups],
  );

  const dialogControls = (
    <CustomDialogControls
      actionButtonLabel="Create"
      onCancel={onClose}
      onAction={onCreate}
      isActionDisabled={!isValid}
    />
  );

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
    <Dialog title="Create new user" isOpen={isOpen} onOpenChange={onClose} dialogControls={dialogControls}>
      <FormFieldsContainer className={s.userCreateDialog}>
        <FormField label="Username" className={s.userCreateDialog__username}>
          <Input
            value={formData.username}
            type="text"
            onChange={handleUsernameChange}
            placeholder="Enter unique name"
            autoComplete="username"
          />
        </FormField>

        <FormField label="Password" className={s.userCreateDialog__password}>
          <InputPassword
            value={formData.password}
            onChange={handlePasswordChange}
            placeholder="Enter password"
            autoComplete="password"
          />
        </FormField>
        <FormField
          label="Confirm password"
          error={errorMessages.confirmPassword}
          className={s.userCreateDialog__confirmPassword}
        >
          <InputPassword
            value={formData.confirmPassword}
            onChange={handleConfirmPasswordChange}
            placeholder="Enter password"
            autoComplete="password"
          />
        </FormField>

        <FormField label="First name" className={s.userCreateDialog__firstName}>
          <Input
            value={formData.firstName}
            type="text"
            onChange={handleFirstNameChange}
            placeholder="Enter"
            autoComplete="off"
          />
        </FormField>
        <FormField label="Last name" className={s.userCreateDialog__lastName}>
          <Input
            value={formData.lastName}
            type="text"
            onChange={handleLastNameChange}
            placeholder="Enter"
            autoComplete="off"
          />
        </FormField>
        <FormField label="" className={s.userCreateDialog__isSuperUser}>
          <Checkbox
            label="Grant ADCM Administrator’s rights"
            checked={formData.isSuperUser}
            onChange={handleIsSuperUserChange}
          />
        </FormField>

        <FormField label="Email" error={errorMessages.email} className={s.userCreateDialog__email}>
          <Input
            value={formData.email}
            type="text"
            onChange={handleEmailChange}
            placeholder="User’s email"
            autoComplete="email"
          />
        </FormField>
        <FormField label="Add groups" className={s.userCreateDialog__groups}>
          <MultiSelect
            placeholder="Select"
            value={formData.groups}
            onChange={handleGroupsChange}
            options={groupOptions}
          />
        </FormField>
      </FormFieldsContainer>
    </Dialog>
  );
};

export default AccessManagerUserCreateDialog;
