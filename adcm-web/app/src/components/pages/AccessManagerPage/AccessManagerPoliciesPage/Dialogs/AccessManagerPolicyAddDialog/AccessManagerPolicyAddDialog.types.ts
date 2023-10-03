export interface AccessManagerPolicyAddDialogFormData {
  policyName: string;
  description: string;
  roleId: number | null;
  groupIds: number[];
  clusterIds: number[];
  serviceClusterIds: number[];
  serviceName: string;
  hostIds: number[];
  hostproviderIds: number[];
  objectTypes: string[];
}

export interface ChangeFormDataPayload {
  [key: string]: number | number[] | string | null;
}
