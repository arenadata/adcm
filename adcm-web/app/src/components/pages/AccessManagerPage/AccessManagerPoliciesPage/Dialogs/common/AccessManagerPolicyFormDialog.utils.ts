import type { AdcmPolicy } from '@models/adcm';
import type { AccessManagerPolicyDialogsFormData } from './AccessManagerPolicyFormDialog.types';

export const isValidStepItem = (step: string, formData: AccessManagerPolicyDialogsFormData) => {
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

const getPreparedObjectsArray = (entityIds: number[], type: string) => {
  return entityIds.map((id) => ({ id, type }));
};

export const getObjectsForSubmit = (formData: AccessManagerPolicyDialogsFormData) => {
  const objectsForSubmit = [];

  if (formData.clusterIds.length > 0) {
    objectsForSubmit.push(...getPreparedObjectsArray(formData.clusterIds, 'cluster'));
  }
  if (formData.serviceName !== '' && formData.serviceClusterIds.length > 0) {
    objectsForSubmit.push(...getPreparedObjectsArray(formData.serviceClusterIds, 'service'));
  }
  if (formData.hostproviderIds.length > 0) {
    objectsForSubmit.push(...getPreparedObjectsArray(formData.hostproviderIds, 'provider'));
  }
  if (formData.hostIds.length > 0) {
    objectsForSubmit.push(...getPreparedObjectsArray(formData.hostIds, 'host'));
  }

  return objectsForSubmit;
};

export const generateDialogData = (policy: AdcmPolicy, objectTypes: string[]) => {
  const objectTypesForUpdateAction = new Set(objectTypes);
  const dialogData: AccessManagerPolicyDialogsFormData = {
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

  // we need to additionally check for data that conflicts with available objectTypes for update action
  for (const object of policy.objects) {
    switch (object.type) {
      case 'cluster':
        if (objectTypesForUpdateAction.has('cluster')) {
          dialogData.clusterIds.push(object.id);
        }
        break;
      case 'service':
        if (objectTypesForUpdateAction.has('service')) {
          dialogData.serviceClusterIds.push(object.id);
          dialogData.serviceName = object.name;
        }
        break;
      case 'host':
        if (objectTypesForUpdateAction.has('host')) {
          dialogData.hostIds.push(object.id);
        }
        break;
      case 'provider':
        if (objectTypesForUpdateAction.has('provider')) {
          dialogData.hostproviderIds.push(object.id);
        }
        break;
    }
  }

  return dialogData;
};

export const isValidSecondStep = (formData: AccessManagerPolicyDialogsFormData) => {
  if (formData.objectTypes.length > 0) {
    return formData.objectTypes.some((object) => isValidStepItem(object, formData));
  }

  return true;
};
