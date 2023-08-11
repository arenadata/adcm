export enum AdcmGroupType {
  LOCAL = 'LOCAL',
  LDAP = 'LDAP',
}

interface AdcmGroupUser {
  id: number;
  name: string;
}

export interface AdcmGroup {
  id: number;
  name: string;
  displayName: string;
  description: string;
  users: AdcmGroupUser[];
  type: string;
}

export interface AdcmGroupFilter {
  name?: string;
  type?: string;
}

interface AdcmGroupUserPayload {
  id: number;
}

export interface CreateAdcmGroupPayload {
  name: string;
  description: string;
  users: AdcmGroupUserPayload[];
}

export interface UpdateAdcmGroupPayload {
  name: string;
  description: string;
  users: AdcmGroupUserPayload[];
}
