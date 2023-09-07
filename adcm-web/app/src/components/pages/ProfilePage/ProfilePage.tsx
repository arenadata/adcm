import PageSection from '@commonComponents/PageSection/PageSection';
import React, { useEffect, useState } from 'react';
import s from './ProfilePage.module.scss';
import { Button, FormField, FormFieldsContainer, Input, LabeledField, Text } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { getProfile } from '@store/adcm/profile/profileSlice';
import { useChangePasswordForm } from './useChangePasswordForm';
import InputPassword from '@uikit/InputPassword/InputPassword';
import { useNavigate } from 'react-router-dom';

const ProfilePage = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const profile = useStore(({ adcm }) => adcm.profile.profile);
  useEffect(() => {
    dispatch(getProfile());
  }, []);

  const { formData, submitForm, onChangeFormData, isValid } = useChangePasswordForm();

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
          <FormField label="Current password">
            <InputPassword
              value={formData.currentPassword}
              onChange={handleCurrentPasswordChange}
              placeholder="Password"
            />
          </FormField>
          <FormField label="New password">
            <InputPassword
              value={formData.newPassword}
              onChange={handleNewPasswordChange}
              placeholder="Type new password"
            />
          </FormField>
          <FormField className={s.profilePageConfirmPassword} label="Confirm password">
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
