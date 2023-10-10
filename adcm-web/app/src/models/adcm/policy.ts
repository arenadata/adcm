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
  type: string;
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

export type AdcmPolicyObjectPayload = Omit<AdcmPolicyObject, 'name' | 'displayName' | 'clusterName'> & {
  type: string;
};

export type AdcmPolicyObjectCandidate = Omit<AdcmPolicyObject, 'displayName' | 'clusterName'>;

export type AdcmPolicyObjectCandidateService = AdcmPolicyObjectCandidate & {
  displayName: string;
  clusters: {
    name: string;
    id: number;
  }[];
};

export interface AdcmPolicyPayload {
  name: string;
  description: string;
  role: {
    id: number;
  };
  groups: number[];
  objects: AdcmPolicyObjectPayload[];
}

export interface AdcmPolicyUpdatePayload {
  policyId: number;
  updatedValue: AdcmPolicyPayload;
}

export interface AdcmObjectCandidates {
  cluster: AdcmPolicyObjectCandidate[];
  provider: AdcmPolicyObjectCandidate[];
  service: AdcmPolicyObjectCandidateService[];
  host: AdcmPolicyObjectCandidate[];
}
