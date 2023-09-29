import { useDispatch, useForm, useStore } from '@hooks';
import { closeUserUpdateDialog, updateUser } from '@store/adcm/users/usersActionsSlice';
import { RbacUserFormData } from '@pages/AccessManagerPage/AccessManagerUsersPage/RbacUserForm/RbacUserForm.types';
import { useEffect } from 'react';
import { isEmailValid, required } from '@utils/validationsUtils';

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
  const isUpdating = useStore((s) => s.adcm.usersActions.updateDialog.isUpdating);
  const groups = useStore((s) => s.adcm.usersActions.relatedData.groups);
  const isOpen = !!user;

  const { formData, handleChangeFormData, setFormData, errors, setErrors, isValid } =
    useForm<RbacUserFormData>(initialFormData);

  useEffect(() => {
    if (user) {
      setFormData({
        ...initialFormData,
        username: user.username,
        firstName: user.firstName,
        lastName: user.lastName,
        email: user.email,
        groups: user.groups.map(({ id }) => id),
        isSuperUser: user.isSuperuser,
      });
    }
  }, [user, setFormData]);

  useEffect(() => {
    setErrors({
      firstName: required(formData.firstName) ? undefined : 'First Name field is required',
      lastName: required(formData.lastName) ? undefined : 'Last Name field is required',
      confirmPassword:
        formData.confirmPassword === formData.password ? undefined : 'Confirm password must match password',
      email: isEmailValid(formData.email) ? undefined : 'Email is not correct',
    });
  }, [formData, setErrors]);

  useEffect(() => {
    setFormData(initialFormData);
  }, [isOpen, setFormData]);

  const handleClose = () => {
    setFormData(initialFormData);
    dispatch(closeUserUpdateDialog());
  };

  const handleCreate = () => {
    if (user) {
      dispatch(
        updateUser({
          id: user.id,
          userData: {
            firstName: formData.firstName,
            lastName: formData.lastName,
            email: formData.email,
            groups: formData.groups,
            password: formData.password === '' ? undefined : formData.password,
            isSuperUser: formData.isSuperUser,
          },
        }),
      );
    }
  };

  return {
    isOpen,
    groups,
    onChangeFormData: handleChangeFormData,
    isValid: isValid && !isUpdating,
    formData,
    onClose: handleClose,
    onSubmit: handleCreate,
    errors,
  };
};
