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
  displayName?: string;
  type?: string;
}

export interface AdcmGroupUserPayload {
  id: number;
}

export interface AdcmCreateGroupPayload {
  name: string;
  description: string;
  displayName: string;
  users: number[];
}

export interface AdcmUpdateGroupPayload {
  name: string;
  displayName: string;
  description: string;
  users: number[];
}
