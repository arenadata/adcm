export enum AdcmGroupType {
  Local = 'local',
  Ldap = 'ldap',
}

interface AdcmGroupUser {
  id: number;
  username: string;
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

export interface AdcmGroupUserPayload {
  id: number;
}

export interface CreateAdcmGroupPayload {
  name: string;
  description: string;
  displayName: string;
  users: number[];
}

export interface UpdateAdcmGroupPayload {
  name: string;
  description: string;
  users: AdcmGroupUserPayload[];
}
