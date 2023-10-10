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
  parametrizedByType: string[];
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
  displayName: string;
  description: string;
  children: number[];
}

export interface UpdateRolePayload {
  id: number;
  data: {
    displayName: string;
    description: string;
    children: number[];
  };
}
