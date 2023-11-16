import { useDispatch, useStore } from '@hooks';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { SelectOption } from '@uikit';
import { Steps, steps } from './AccessManagerPolicyAddDialog.constants';
import { cleanupActions, createPolicy, updatePolicy } from '@store/adcm/policies/policiesActionsSlice';
import { AccessManagerPolicyAddDialogFormData } from './AccessManagerPolicyAddDialog.types';
import {
  generateDialogData,
  getObjectsForSubmit,
} from '@pages/AccessManagerPage/AccessManagerPoliciesPage/Dialogs/AccessManagerPolicyAddDialog/AccessManagerPolicyAddDialog.utils';
import { getObjectCandidates } from '@store/adcm/policies/policiesSlice';

const initialDialogData: AccessManagerPolicyAddDialogFormData = {
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
  const { policy, roleId } = useStore(({ adcm }) => adcm.policiesActions.editDialog);
  const roles = useStore(({ adcm }) => adcm.policiesActions.relatedData.roles);
  const groups = useStore(({ adcm }) => adcm.policiesActions.relatedData.groups);

  const [formData, setFormData] = useState(initialDialogData);
  const [currentStep, setCurrentStep] = useState<string>(Steps.MainInfo);

  const objectTypes = useMemo(() => {
    return roles.find((role) => role.id === roleId)?.parametrizedByType ?? [];
  }, [roles, roleId]);

  useEffect(() => {
    if (roleId && policy && roles.length > 0 && objectTypes?.length > 0) {
      dispatch(getObjectCandidates(roleId));
      setFormData(generateDialogData(policy, objectTypes));
    }
  }, [dispatch, objectTypes, policy, roleId, roles]);

  const isValidFirstStep = useMemo(() => {
    const { policyName, roleId, groupIds } = formData;
    return policyName !== '' && roleId !== null && groupIds.length > 0;
  }, [formData]);

  const resetForm = useCallback(() => {
    setFormData(initialDialogData);
    setCurrentStep(Steps.MainInfo);
  }, []);

  useEffect(() => {
    if (!isOpen) {
      resetForm();
    }
  }, [isOpen, resetForm]);

  const submit = useCallback(() => {
    const { policyName, description, roleId, groupIds } = formData;
    const objectsForSubmit = getObjectsForSubmit(formData);
    const data = {
      name: policyName,
      description,
      role: {
        id: roleId as number,
      },
      groups: groupIds,
      objects: objectsForSubmit,
    };

    if (policy?.id) {
      dispatch(updatePolicy({ policyId: policy.id as number, updatedValue: data }));
    } else {
      dispatch(createPolicy(data));
    }
  }, [formData, dispatch, policy]);

  const handleClose = () => {
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
    isEdit: !!roleId,
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
