import { useDispatch, useForm, useStore } from '@hooks';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Steps, steps } from '../common/PolicyFormDialogWizard/constants';
import { closeCreateDialog, createPolicy, loadRelatedData } from '@store/adcm/policies/policiesActionsSlice';
import type { AccessManagerPolicyDialogsFormData } from '../common/AccessManagerPolicyFormDialog.types';
import { getObjectsForSubmit, isValidSecondStep } from '../common/AccessManagerPolicyFormDialog.utils';
import { isNameUniq, required } from '@utils/validationsUtils';

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

export const useAccessManagerPolicyCreateDialog = () => {
  const dispatch = useDispatch();

  const isOpen = useStore(({ adcm }) => adcm.policiesActions.createDialog.isOpen);
  const roles = useStore(({ adcm }) => adcm.policiesActions.relatedData.roles);
  const policies = useStore(({ adcm }) => adcm.policies.policies);

  const { formData, setFormData, setErrors, errors, isValid: areErrorsPresent } = useForm(initialDialogData);
  const [currentStep, setCurrentStep] = useState<string>(Steps.MainInfo);

  const isValid = useMemo(() => {
    if (currentStep === Steps.MainInfo) {
      const { policyName, roleId, groupIds } = formData;
      return policyName !== '' && roleId !== null && groupIds.length > 0 && areErrorsPresent;
    }

    if (currentStep === Steps.Object) return isValidSecondStep(formData);

    return false;
  }, [currentStep, formData, areErrorsPresent]);

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

  useEffect(() => {
    setErrors({
      policyName:
        (required(formData.policyName) ? undefined : 'Policy name is required') ||
        (isNameUniq(formData.policyName, policies) ? undefined : 'Similarly named policy already exists'),
    });
  }, [policies, formData, currentStep, setErrors]);

  const handleSubmit = useCallback(() => {
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

    dispatch(createPolicy(data));
  }, [formData, dispatch]);

  const handleClose = () => {
    dispatch(closeCreateDialog());
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
    resetForm,
    currentStep,
    errors,
    setCurrentStep,
    onSubmit: handleSubmit,
    onClose: handleClose,
    onChangeFormData: handleChangeFormData,
    relatedData: { roles, steps },
  };
};
