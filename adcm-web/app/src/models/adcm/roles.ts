export enum AdcmRoleType {
  Role = 'role',
  Business = 'business',
}

export interface AdcmRole {
  id: number;
  name: string;
  displayName: string;
  description: string;
  isBuiltIn: boolean;
  isAnyCategory: boolean;
  categories: string[];
  type: AdcmRoleType;
  children: AdcmRole[] | null;
}

export interface AdcmRolesFilter {
  type: string;
  name?: string;
}

export interface AdcmRoleProduct {
  id: number;
  name: string;
}

export interface AdcmCreateRolePayload {
  displayName: string;
  description: string;
  children: number[];
}

export interface AdcmUpdateRolePayload {
  name: string;
}
