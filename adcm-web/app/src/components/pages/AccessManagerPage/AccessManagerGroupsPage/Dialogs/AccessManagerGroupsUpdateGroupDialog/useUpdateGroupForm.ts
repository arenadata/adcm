import { useMemo, useCallback, useEffect } from 'react';
import { useStore, useDispatch, useForm } from '@hooks';
import { getUsers } from '@store/adcm/users/usersSlice';
import { updateGroup } from '@store/adcm/groups/groupActionsSlice';
import { isNameUniq, required } from '@utils/validationsUtils';

interface UpdateGroupFormData {
  name: string;
  description: string;
  usersIds: number[];
}

const initialFormData: UpdateGroupFormData = {
  name: '',
  description: '',
  usersIds: [],
};

export const useUpdateGroupForm = () => {
  const dispatch = useDispatch();

  const updatedGroup = useStore((s) => s.adcm.groupsActions.updateDialog.group);

  const users = useStore(({ adcm }) => adcm.users.users);
  const groups = useStore((s) => s.adcm.groups.groups);

  const usersOptions = useMemo(() => {
    return users.map(({ username, id }) => ({ value: id, label: username }));
  }, [users]);

  const { formData, handleChangeFormData, setFormData, errors, setErrors, isValid } =
    useForm<UpdateGroupFormData>(initialFormData);

  const resetForm = useCallback(() => {
    setFormData({
      ...initialFormData,
      ...updatedGroup,
      name: updatedGroup?.displayName || '',
      usersIds: updatedGroup?.users.map(({ id }) => id) || [],
    });
  }, [updatedGroup, setFormData]);

  const submitForm = useCallback(() => {
    const { usersIds, description, name } = formData;
    if (updatedGroup) {
      dispatch(
        updateGroup({
          id: updatedGroup?.id,
          data: {
            name,
            displayName: name,
            description,
            users: usersIds,
          },
        }),
      );
    }
  }, [formData, updatedGroup, dispatch]);

  useEffect(() => {
    setErrors({
      name:
        (required(formData.name) ? undefined : 'Group field is required') ||
        (isNameUniq(
          formData.name,
          groups.filter(({ id }) => id !== updatedGroup?.id).map((group) => ({ ...group, name: group.displayName })),
        )
          ? undefined
          : 'Group with the same name already exists'),
    });
  }, [formData, updatedGroup, groups, setErrors]);

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
