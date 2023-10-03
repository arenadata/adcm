import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { SelectOption } from '@uikit';
import { Steps, steps } from './AccessManagerPolicyAddDialog.constants';
import { cleanupActions, createPolicy } from '@store/adcm/policies/policiesActionsSlice';
import { AccessManagerPolicyAddDialogFormData } from './AccessManagerPolicyAddDialog.types';
import { getObjectsForSubmit } from '@pages/AccessManagerPage/AccessManagerPoliciesPage/Dialogs/AccessManagerPolicyAddDialog/AccessManagerPolicyAddDialog.utils';

const initialFormData: AccessManagerPolicyAddDialogFormData = {
  policyName: '',
  description: '',
  roleId: null,
  groupIds: [],
  clusterIds: [],
  serviceClusterIds: [],
  serviceName: '',
  hostIds: [],
  hostproviderIds: [],
  objectTypes: [],
};

export const useAccessManagerPolicyAddDialog = () => {
  const dispatch = useDispatch();

  const isOpen = useStore(({ adcm }) => adcm.policiesActions.isAddPolicyDialogOpen);
  const roles = useStore(({ adcm }) => adcm.roles.roles);
  const groups = useStore(({ adcm }) => adcm.groups.groups);
  const [formData, setFormData] = useState(initialFormData);
  const [currentStep, setCurrentStep] = useState<string>(Steps.MainInfo);

  useEffect(() => {
    setFormData(initialFormData);
  }, [isOpen]);

  const isValidFirstStep = useMemo(() => {
    const { policyName, roleId, groupIds } = formData;
    return policyName !== '' && roleId !== null && groupIds.length > 0;
  }, [formData]);

  const resetForm = useCallback(() => {
    setFormData(initialFormData);
    setCurrentStep(Steps.MainInfo);
  }, []);

  useEffect(() => {
    resetForm();
  }, [resetForm]);

  const submit = useCallback(() => {
    const { policyName, description, roleId, groupIds } = formData;
    const objectsForSubmit = getObjectsForSubmit(formData);

    dispatch(
      createPolicy({
        name: policyName,
        description,
        role: {
          id: roleId as number,
        },
        groups: groupIds,
        objects: objectsForSubmit,
      }),
    );

    setCurrentStep(Steps.MainInfo);
  }, [formData, dispatch]);

  const handleClose = () => {
    setCurrentStep(Steps.MainInfo);
    dispatch(cleanupActions());
  };

  const handleChangeFormData = (changes: Partial<AccessManagerPolicyAddDialogFormData>) => {
    setFormData({
      ...formData,
      ...changes,
    });
  };

  const groupsOptions: SelectOption<number>[] = useMemo(() => {
    return groups.map(({ displayName, id }) => ({ value: id, label: displayName }));
  }, [groups]);

  const rolesOptions: SelectOption<number>[] = useMemo(() => {
    return roles.map(({ displayName, id }) => ({ value: id, label: displayName }));
  }, [roles]);

  return {
    isOpen,
    isValidFirstStep,
    formData,
    resetForm,
    submit,
    currentStep,
    setCurrentStep,
    onClose: handleClose,
    onChangeFormData: handleChangeFormData,
    relatedData: { groupsOptions, rolesOptions, roles, steps },
  };
};
