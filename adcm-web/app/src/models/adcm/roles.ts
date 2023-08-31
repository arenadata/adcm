export enum AdcmRoleType {
  ROLE = 'ROLE',
  BUSINESS = 'BUSINESS',
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
  name?: string;
}

export interface AdcmRoleProduct {
  id: number;
  name: string;
}

export interface AdcmCreateRolePayload {
  name: string;
}

export interface AdcmUpdateRolePayload {
  name: string;
}
