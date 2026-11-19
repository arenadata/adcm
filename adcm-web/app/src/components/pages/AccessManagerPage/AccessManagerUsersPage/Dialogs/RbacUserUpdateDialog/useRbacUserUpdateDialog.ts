import { useDispatch, useForm, useStore } from '@hooks';
import { closeUserUpdateDialog, loadGroups, updateUser } from '@store/adcm/users/usersActionsSlice';
import type { RbacUserFormData } from '@pages/AccessManagerPage/AccessManagerUsersPage/RbacUserForm/RbacUserForm.types';
import { useEffect } from 'react';
import { isEmailValid, required, stringLengthValidator } from '@utils/validationsUtils';
import { getProfile } from '@store/adcm/profile/profileSlice';

const initialFormData: RbacUserFormData = {
  username: '',
  firstName: '',
  lastName: '',
  email: '',
  groups: [],
  password: '',
  confirmPassword: '',
  isSuperUser: false,
};

export const useRbacUserUpdateDialog = () => {
  const dispatch = useDispatch();
  const user = useStore((s) => s.adcm.usersActions.updateDialog.user);
  const isUpdating = useStore((s) => s.adcm.usersActions.isActionInProgress);
  const groups = useStore((s) => s.adcm.usersActions.relatedData.groups);
  const isCurrentUserSuperUser = useStore((s) => s.auth.profile.isSuperUser);
  const authSettings = useStore((s) => s.auth.profile.authSettings);
  const isProfileLoading = useStore((s) => s.adcm.profile.isProfileLoading);
  const isOpen = !!user;
  const isPersonalDataEditForbidden = user?.type === 'ldap';
  const userGroups = groups.length > 0 ? groups : user ? user.groups : [];

  const { formData, handleChangeFormData, setFormData, errors, setErrors, isValid } =
    useForm<RbacUserFormData>(initialFormData);

  useEffect(() => {
    if (isOpen) {
      dispatch(getProfile());
      dispatch(loadGroups());
    } else {
      setFormData(initialFormData);
    }
  }, [dispatch, isOpen, setFormData]);

  useEffect(() => {
    if (user) {
      setFormData({
        ...initialFormData,
        username: user.username,
        firstName: user.firstName,
        lastName: user.lastName,
        email: user.email,
        groups: user.groups.map(({ id }) => id),
        isSuperUser: user.isSuperUser,
      });
    }
  }, [user, setFormData]);

  useEffect(() => {
    setErrors({
      password: formData.password
        ? stringLengthValidator(
            formData.password,
            'Password',
            authSettings?.minPasswordLength,
            authSettings?.maxPasswordLength,
          )
        : undefined,
      firstName: required(formData.firstName) ? undefined : 'First Name field is required',
      lastName: required(formData.lastName) ? undefined : 'Last Name field is required',
      confirmPassword:
        formData.confirmPassword === formData.password ? undefined : 'Confirm password must match password',
      email: isEmailValid(formData.email) ? undefined : 'Email is not correct',
    });
  }, [formData, authSettings, setErrors]);

  const handleClose = () => {
    setFormData(initialFormData);
    dispatch(closeUserUpdateDialog());
  };

  const handleCreate = () => {
    if (user) {
      const userData = {
        firstName: formData.firstName,
        lastName: formData.lastName,
        email: formData.email,
        groups: formData.groups,
        password: formData.password === '' ? undefined : formData.password,
      };

      dispatch(
        updateUser({
          id: user.id,
          userData: {
            ...userData,
            ...(isCurrentUserSuperUser && { isSuperUser: formData.isSuperUser }),
          },
        }),
      );
    }
  };

  return {
    isOpen,
    groups: userGroups,
    onChangeFormData: handleChangeFormData,
    isValid: isValid && !isUpdating && !isProfileLoading && !!authSettings,
    formData,
    onClose: handleClose,
    onSubmit: handleCreate,
    errors,
    isPersonalDataEditForbidden,
    isCurrentUserSuperUser,
  };
};
