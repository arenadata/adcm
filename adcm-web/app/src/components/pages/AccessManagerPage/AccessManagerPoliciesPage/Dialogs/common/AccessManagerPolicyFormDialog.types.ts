export interface AccessManagerPolicyDialogsFormData {
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

export type ChangeFormDataPayload = Partial<AccessManagerPolicyDialogsFormData>;

export interface AccessManagerPolicyDialogsStepsProps {
  formData: AccessManagerPolicyDialogsFormData;
  changeFormData: (value: ChangeFormDataPayload) => void;
  errors?: Partial<Record<keyof AccessManagerPolicyDialogsFormData, string | undefined>>;
}
