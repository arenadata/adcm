import PageSection from '@commonComponents/PageSection/PageSection';
import React, { useEffect } from 'react';
import s from './ProfilePage.module.scss';
import { Button, FormField, FormFieldsContainer, LabeledField, Text } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { getProfile } from '@store/adcm/profile/profileSlice';
import { useChangePasswordForm } from './useChangePasswordForm';
import InputPassword from '@uikit/InputPassword/InputPassword';

const ProfilePage = () => {
  const dispatch = useDispatch();

  const profile = useStore(({ adcm }) => adcm.profile.profile);
  useEffect(() => {
    dispatch(getProfile());
  }, [dispatch]);

  const { formData, submitForm, onChangeFormData, isValid, errors } = useChangePasswordForm();

  const handleCurrentPasswordChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ currentPassword: event.target.value });
  };

  const handleNewPasswordChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ newPassword: event.target.value });
  };

  const handleConfirmNewPasswordChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChangeFormData({ confirmNewPassword: event.target.value });
  };

  return (
    <div className={s.profilePage}>
      <PageSection title={'User information'} isExpandDefault={true}>
        <div className={s.profilePageInformation}>
          <LabeledField label="User">
            <Text variant="h4">{profile.username}</Text>
          </LabeledField>

          <LabeledField label="Email">
            <Text variant="h4">{profile.email}</Text>
          </LabeledField>
        </div>
      </PageSection>

      <PageSection title={'Password'} isExpandDefault={true}>
        <FormFieldsContainer className={s.profilePagePassword}>
          <FormField label="Current password" error={errors.currentPassword}>
            <InputPassword
              value={formData.currentPassword}
              onChange={handleCurrentPasswordChange}
              placeholder="Password"
              areAsterisksShown={true}
            />
          </FormField>
          <FormField label="New password" error={errors.newPassword}>
            <InputPassword
              value={formData.newPassword}
              onChange={handleNewPasswordChange}
              placeholder="Type new password"
            />
          </FormField>
          <FormField
            className={s.profilePageConfirmPassword}
            label="Confirm password"
            error={errors.confirmNewPassword}
          >
            <InputPassword
              value={formData.confirmNewPassword}
              onChange={handleConfirmNewPasswordChange}
              placeholder="Type new password"
            />
          </FormField>
        </FormFieldsContainer>

        <Button className={s.buttonChangePassword} onClick={submitForm} disabled={!isValid}>
          Save
        </Button>
      </PageSection>
    </div>
  );
};

export default ProfilePage;
