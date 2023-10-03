import { AccessManagerPolicyAddDialogFormData } from '@pages/AccessManagerPage/AccessManagerPoliciesPage/Dialogs/AccessManagerPolicyAddDialog/AccessManagerPolicyAddDialog.types.ts';

export const isValidStepItem = (step: string, formData: AccessManagerPolicyAddDialogFormData) => {
  switch (step) {
    case 'cluster':
      return formData.clusterIds.length > 0;
    case 'provider':
      return formData.hostproviderIds.length > 0;
    case 'service':
      return formData.serviceName !== '' && formData.serviceClusterIds.length > 0;
    case 'host':
      return formData.hostIds.length > 0;
    case '':
      return true;
    default:
      return false;
  }
};

export const getObjectsForSubmit = (formData: AccessManagerPolicyAddDialogFormData) => {
  if (formData.clusterIds.length > 0) {
    return formData.clusterIds.map((id) => ({ id: id, type: 'cluster' }));
  }
  if (formData.serviceName !== '' && formData.serviceClusterIds.length > 0) {
    return formData.serviceClusterIds.map((id) => ({ id: id, type: 'service' }));
  }
  if (formData.hostproviderIds.length > 0) {
    return formData.hostproviderIds.map((id) => ({ id: id, type: 'provider' }));
  }
  if (formData.hostIds.length > 0) {
    return formData.hostIds.map((id) => ({ id: id, type: 'host' }));
  }

  return [];
};

export const isValidSecondStep = (formData: AccessManagerPolicyAddDialogFormData) => {
  return formData.objectTypes.some((object) => isValidStepItem(object, formData));
};
