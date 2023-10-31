import { useMemo, useCallback, useEffect } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import { getUsers } from '@store/adcm/users/usersSlice';
import { createGroup } from '@store/adcm/groups/groupActionsSlice';
import { isNameUniq, required } from '@utils/validationsUtils';

interface CreateGroupFormData {
  name: string;
  description: string;
  usersIds: number[];
}

const initialFormData: CreateGroupFormData = {
  name: '',
  description: '',
  usersIds: [],
};

export const useCreateGroupForm = () => {
  const dispatch = useDispatch();

  const users = useStore(({ adcm }) => adcm.users.users);
  const groups = useStore((s) => s.adcm.groups.groups);

  const usersOptions = useMemo(() => {
    return users.map(({ username, id }) => ({ value: id, label: username }));
  }, [users]);

  const { formData, handleChangeFormData, setFormData, errors, setErrors, isValid } =
    useForm<CreateGroupFormData>(initialFormData);

  const resetForm = useCallback(() => {
    setFormData(initialFormData);
  }, [setFormData]);

  const submitForm = useCallback(() => {
    const { usersIds, description, name } = formData;
    if (name) {
      dispatch(
        createGroup({
          name,
          displayName: name,
          description,
          users: usersIds,
        }),
      );
    }
  }, [formData, dispatch]);

  useEffect(() => {
    setErrors({
      name:
        (required(formData.name) ? undefined : 'Group field is required') ||
        (isNameUniq(
          formData.name,
          groups.map((group) => ({ ...group, name: group.displayName })),
        )
          ? undefined
          : 'Group with the same name already exists'),
    });
  }, [formData, groups, setErrors]);

  const loadRelatedData = useCallback(() => {
    dispatch(getUsers());
  }, [dispatch]);

  return {
    isValid,
    formData,
    errors,
    resetForm,
    submitForm,
    onChangeFormData: handleChangeFormData,
    loadRelatedData,
    relatedData: {
      usersOptions,
    },
  };
};
