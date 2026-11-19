import { useCallback, useEffect } from 'react';
import { useDispatch, useForm, useStore } from '@hooks';
import { changePassword } from '@store/adcm/profile/profileSlice';
import { required, stringLengthValidator } from '@utils/validationsUtils';

interface ChangePasswordFormData {
  currentPassword: string;
  newPassword: string;
  confirmNewPassword: string;
}

const initialFormData: ChangePasswordFormData = {
  currentPassword: '',
  newPassword: '',
  confirmNewPassword: '',
};

export const useChangePasswordForm = () => {
  const dispatch = useDispatch();
  const authSettings = useStore((s) => s.auth.profile.authSettings);
  const isProfileLoading = useStore((s) => s.adcm.profile.isProfileLoading);
  const minPasswordLength = authSettings?.minPasswordLength;
  const maxPasswordLength = authSettings?.maxPasswordLength;

  const { formData, setFormData, errors, setErrors, isValid } = useForm<ChangePasswordFormData>(initialFormData);
  const isFormEmpty = !formData.currentPassword && !formData.newPassword && !formData.confirmNewPassword;

  useEffect(() => {
    if (isFormEmpty) {
      setErrors({});
      return;
    }

    setErrors({
      currentPassword:
        required(formData.newPassword) && !required(formData.currentPassword)
          ? 'Current password field is required'
          : undefined,
      newPassword:
        (required(formData.newPassword) ? undefined : 'New password field is required') ||
        stringLengthValidator(formData.newPassword, 'New password', minPasswordLength, maxPasswordLength),
      confirmNewPassword:
        formData.newPassword === formData.confirmNewPassword
          ? undefined
          : 'The new and the confirm passwords should match',
    });
  }, [formData, isFormEmpty, minPasswordLength, maxPasswordLength, setErrors]);

  const submitForm = useCallback(() => {
    const { currentPassword, newPassword, confirmNewPassword } = formData;

    if (isFormEmpty || !required(currentPassword) || !required(newPassword) || newPassword !== confirmNewPassword) {
      return;
    }

    dispatch(
      changePassword({
        currentPassword,
        newPassword,
      }),
    );
  }, [formData, isFormEmpty, dispatch]);

  const handleChangeFormData = (changes: Partial<ChangePasswordFormData>) => {
    setFormData({
      ...formData,
      ...changes,
    });
  };

  return {
    canSubmit: !!authSettings && !isProfileLoading && !isFormEmpty && isValid,
    errors,
    formData,
    submitForm,
    onChangeFormData: handleChangeFormData,
  };
};
