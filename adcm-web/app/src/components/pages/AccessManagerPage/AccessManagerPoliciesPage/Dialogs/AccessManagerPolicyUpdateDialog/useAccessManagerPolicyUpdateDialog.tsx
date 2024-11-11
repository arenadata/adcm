import { useDispatch, useForm, useStore } from '@hooks';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Steps, steps } from '../common/PolicyFormDialogWizard/constants';
import { closeUpdateDialog, loadRelatedData, updatePolicy } from '@store/adcm/policies/policiesActionsSlice';
import type { AccessManagerPolicyDialogsFormData } from '../common/AccessManagerPolicyFormDialog.types';
import {
  generateDialogData,
  getObjectsForSubmit,
  isValidSecondStep,
} from '../common/AccessManagerPolicyFormDialog.utils';
import { getObjectCandidates } from '@store/adcm/policies/policiesSlice';
import { required } from '@utils/validationsUtils';

const initialDialogData: AccessManagerPolicyDialogsFormData = {
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

export const useAccessManagerPolicyUpdateDialog = () => {
  const dispatch = useDispatch();
  const {
    formData,
    setFormData,
    errors,
    setErrors,
    isValid: areErrorsPresent,
  } = useForm<AccessManagerPolicyDialogsFormData>(initialDialogData);
  const [currentStep, setCurrentStep] = useState<string>(Steps.MainInfo);
  const policies = useStore(({ adcm }) => adcm.policies.policies);
  const policy = useStore(({ adcm }) => adcm.policiesActions.updateDialog.policy);
  const roles = useStore(({ adcm }) => adcm.policiesActions.relatedData.roles);
  const roleId = policy?.role.id;
  const isOpen = policy !== null;

  const objectTypes = useMemo(() => {
    return roles.find((role) => role.id === roleId)?.parametrizedByType ?? [];
  }, [roles, roleId]);

  const isValid = useMemo(() => {
    if (currentStep === Steps.MainInfo) {
      const { policyName, roleId, groupIds } = formData;
      return policyName !== '' && roleId !== null && groupIds.length > 0 && areErrorsPresent;
    }

    if (currentStep === Steps.Object) return isValidSecondStep(formData);

    return false;
  }, [currentStep, formData, areErrorsPresent]);

  useEffect(() => {
    if (policy && roleId) {
      if (objectTypes?.length > 0) {
        dispatch(getObjectCandidates(roleId));
      }
      setFormData(generateDialogData(policy, objectTypes));
    }
  }, [dispatch, policy, roleId, objectTypes, setFormData]);

  useEffect(() => {
    setErrors({
      policyName: required(formData.policyName) ? undefined : 'Policy name is required',
    });
  }, [policies, formData, currentStep, setErrors]);

  const resetForm = useCallback(() => {
    setFormData(initialDialogData);
    setCurrentStep(Steps.MainInfo);
  }, [setFormData, setCurrentStep]);

  useEffect(() => {
    if (isOpen) {
      dispatch(loadRelatedData());
    } else {
      resetForm();
    }
  }, [isOpen, dispatch, resetForm]);

  const handleSubmit = useCallback(() => {
    const { policyName, description, roleId, groupIds } = formData;

    if (policy) {
      const { id: policyId } = policy;
      const objectsForSubmit = getObjectsForSubmit(formData);
      const updatedValue = {
        name: policyName,
        description,
        role: {
          id: roleId as number,
        },
        groups: groupIds,
        objects: objectsForSubmit,
      };

      dispatch(updatePolicy({ policyId, updatedValue }));
    }
  }, [formData, dispatch, policy]);

  const handleClose = () => {
    dispatch(closeUpdateDialog());
  };

  const handleChangeFormData = (changes: Partial<AccessManagerPolicyDialogsFormData>) => {
    setFormData({
      ...formData,
      ...changes,
    });
  };

  return {
    isOpen,
    isValid,
    formData,
    currentStep,
    errors,
    resetForm,
    setCurrentStep,
    onSubmit: handleSubmit,
    onClose: handleClose,
    onChangeFormData: handleChangeFormData,
    relatedData: { roles, steps },
  };
};
