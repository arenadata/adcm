export interface AdcmPolicyRole {
  id: number;
  name: string;
  displayName: string;
}

export interface AdcmPolicyGroup {
  id: number;
  name: string;
  displayName: string;
}

export interface AdcmPolicyObject {
  id: number;
  name: string;
  displayName: string;
  clusterName: string;
}

export interface AdcmPoliciesFilter {
  name?: string;
}

export interface AdcmPolicy {
  id: number;
  name: string;
  description: string;
  role: AdcmPolicyRole;
  groups: AdcmPolicyGroup[];
  objects: AdcmPolicyObject[];
  isBuiltIn: boolean;
}

export type AdcmPolicyGroupPayload = Omit<AdcmPolicyGroup, 'name' | 'displayName'>;

export type AdcmPolicyObjectPayload = Omit<AdcmPolicyObject, 'name' | 'displayName' | 'clusterName'>;

export interface AdcmPolicyPayload {
  name: string;
  description: string;
  role: {
    id: number;
  };
  groups: AdcmPolicyGroupPayload[];
  objects: AdcmPolicyGroupPayload[];
}
