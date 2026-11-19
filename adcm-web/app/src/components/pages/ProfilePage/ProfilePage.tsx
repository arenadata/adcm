import PageSection from '@commonComponents/PageSection/PageSection';
import type React from 'react';
import { useEffect } from 'react';
import s from './ProfilePage.module.scss';
import { Button, Checkbox, FormField, InputPassword, LabeledField, Text } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { getProfile } from '@store/adcm/profile/profileSlice';
import { useChangePasswordForm } from './useChangePasswordForm';

const ProfilePage = () => {
  const dispatch = useDispatch();

  const profile = useStore(({ adcm }) => adcm.profile.profile);
  useEffect(() => {
    dispatch(getProfile());
  }, [dispatch]);

  const { formData, submitForm, onChangeFormData, canSubmit, errors } = useChangePasswordForm();

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
    <div>
      <PageSection title="User information" isExpandDefault>
        <div className={`${s.profilePageGrid} ${s.profilePageInformation}`}>
          <LabeledField label="User Name">
            <Text variant="h4" className={s.profilePageValue}>
              {profile.username}
            </Text>
          </LabeledField>

          <LabeledField label="E-mail">
            <Text variant="h4" className={s.profilePageValue}>
              {profile.email}
            </Text>
          </LabeledField>

          <LabeledField label="First Name">
            <Text variant="h4" className={s.profilePageValue}>
              {profile.firstName}
            </Text>
          </LabeledField>

          <LabeledField label="Last Name">
            <Text variant="h4" className={s.profilePageValue}>
              {profile.lastName}
            </Text>
          </LabeledField>
        </div>

        {!!profile.id && (
          <Checkbox
            className={s.profilePageAdministrator}
            label="ADCM administrator"
            checked={profile.isSuperUser}
            readOnly
          />
        )}
      </PageSection>

      <PageSection
        title="Password"
        isExpandDefault
        headerActions={
          <Button onClick={submitForm} disabled={!canSubmit}>
            Save
          </Button>
        }
      >
        <div className={s.profilePageGrid}>
          <FormField label="Current password" error={errors.currentPassword}>
            <InputPassword
              value={formData.currentPassword}
              onChange={handleCurrentPasswordChange}
              placeholder="Type password"
            />
          </FormField>

          <FormField className={s.profilePageNewPassword} label="New password" error={errors.newPassword}>
            <InputPassword
              value={formData.newPassword}
              onChange={handleNewPasswordChange}
              placeholder="Type new password"
            />
          </FormField>

          <FormField
            className={s.profilePageConfirmPassword}
            label="Confirm new password"
            error={errors.confirmNewPassword}
          >
            <InputPassword
              value={formData.confirmNewPassword}
              onChange={handleConfirmNewPasswordChange}
              placeholder="Type new password"
            />
          </FormField>
        </div>
      </PageSection>
    </div>
  );
};

export default ProfilePage;
