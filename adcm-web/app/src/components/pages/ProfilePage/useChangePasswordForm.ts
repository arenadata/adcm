import { useCallback, useEffect } from 'react';
import { useDispatch, useForm, useStore } from '@hooks';
import { changePassword } from '@store/adcm/profile/profileSlice';
import { required } from '@utils/validationsUtils';

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

const passwordMinMaxValidator = (passwordFieldLabel: string, password: string, minValue: number, maxValue: number) => {
  if (password.length === 0) return;

  return password.length >= minValue && password.length <= maxValue
    ? undefined
    : `The ${passwordFieldLabel} should be greater than ${minValue - 1} 
  and less than ${maxValue + 1}`;
};

export const useChangePasswordForm = () => {
  const dispatch = useDispatch();
  const minPasswordLength = useStore((s) => s.auth.profile.authSettings.minPasswordLength);
  const maxPasswordLength = useStore((s) => s.auth.profile.authSettings.maxPasswordLength);

  const { formData, setFormData, errors, setErrors, isValid } = useForm<ChangePasswordFormData>(initialFormData);

  useEffect(() => {
    setErrors({
      currentPassword:
        required(formData.newPassword) && !required(formData.currentPassword)
          ? 'Current password field is required'
          : undefined,
      newPassword:
        (required(formData.newPassword) ? undefined : 'New password field is required') ||
        passwordMinMaxValidator('new password', formData.newPassword, minPasswordLength, maxPasswordLength),
      confirmNewPassword:
        formData.newPassword === formData.confirmNewPassword
          ? undefined
          : 'The new and the confirm passwords should match',
    });
  }, [formData, minPasswordLength, maxPasswordLength, setErrors]);

  const submitForm = useCallback(() => {
    const { currentPassword, newPassword } = formData;
    dispatch(
      changePassword({
        currentPassword,
        newPassword,
      }),
    );
  }, [formData, dispatch]);

  const handleChangeFormData = (changes: Partial<ChangePasswordFormData>) => {
    setFormData({
      ...formData,
      ...changes,
    });
  };

  return {
    isValid,
    errors,
    formData,
    submitForm,
    onChangeFormData: handleChangeFormData,
  };
};
