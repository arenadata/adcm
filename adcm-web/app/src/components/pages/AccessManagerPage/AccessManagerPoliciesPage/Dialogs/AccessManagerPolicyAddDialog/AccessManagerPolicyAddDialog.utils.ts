import { AccessManagerPolicyAddDialogFormData } from '@pages/AccessManagerPage/AccessManagerPoliciesPage/Dialogs/AccessManagerPolicyAddDialog/AccessManagerPolicyAddDialog.types';
import { AdcmPolicy } from '@models/adcm';

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

export const generateDialogData = (policy: AdcmPolicy, objectTypes: string[]) => {
  const dialogData: AccessManagerPolicyAddDialogFormData = {
    policyName: policy.name,
    description: policy.description,
    roleId: policy.role.id,
    groupIds: policy.groups.map((group) => group.id),
    clusterIds: [],
    serviceClusterIds: [],
    serviceName: '',
    hostIds: [],
    hostproviderIds: [],
    objectTypes: objectTypes,
  };

  for (const object of policy.objects) {
    switch (object.type) {
      case 'cluster':
        dialogData.clusterIds.push(object.id);
        break;
      case 'service':
        dialogData.serviceClusterIds.push(object.id);
        dialogData.serviceName = object.name;
        break;
      case 'host':
        dialogData.hostIds.push(object.id);
        break;
      case 'provider':
        dialogData.hostproviderIds.push(object.id);
        break;
    }
  }

  return dialogData;
};

export const isValidSecondStep = (formData: AccessManagerPolicyAddDialogFormData) => {
  if (formData.objectTypes.length > 0) {
    return formData.objectTypes.some((object) => isValidStepItem(object, formData));
  }

  return true;
};
