// Audit Operations

export enum AdcmAuditOperationType {
  Create = 'create',
  Update = 'update',
  Delete = 'delete',
}

export enum AdcmAuditOperationResult {
  Success = 'success',
  Fail = 'fail',
  Denied = 'denied',
}

export enum AdcmAuditOperationObjectType {
  Cluster = 'cluster',
  Service = 'service',
  Component = 'component',
  Host = 'host',
  Provider = 'provider',
  Bundle = 'bundle',
  User = 'user',
  Group = 'group',
  Policy = 'policy',
  Adcm = 'adcm',
  Role = 'role',
}

export interface AdcmAuditOperationObject {
  id: number;
  type: AdcmAuditOperationObjectType;
  name: string;
}

export interface AdcmAuditOperationObjectChanges {
  previous: { [key: string]: string };
  current: { [key: string]: string };
}

export interface AdcmAuditOperationUser {
  name: string;
}

export interface AdcmAuditOperation {
  id: number;
  name: string;
  type: AdcmAuditOperationType;
  result: AdcmAuditOperationResult;
  time: string;
  object: AdcmAuditOperationObject;
  user: AdcmAuditOperationUser;
  objectChanges: AdcmAuditOperationObjectChanges;
}

export interface AdcmAuditOperationFilter {
  operationType?: AdcmAuditOperationType;
  operationResult?: AdcmAuditOperationResult;
  objectName?: string;
  objectType?: AdcmAuditOperationObjectType;
  username?: string;
  timeFrom: number;
  timeTo: number;
}

export type AdcmAuditOperationRequestParam = Omit<AdcmAuditOperationFilter, 'timeFrom' | 'timeTo'> & {
  timeFrom: string;
  timeTo: string;
};

// Audit Logins

export interface AdcmAuditLogin {
  id: number;
  user: AdcmAuditLoginUser;
  result: AdcmAuditLoginResultType;
  time: string;
}

export enum AdcmAuditLoginResultType {
  Success = 'success',
  WrongPassword = 'wrong password',
  UserNotFound = 'user not found',
  AccountDisabled = 'account disabled',
}

export interface AdcmAuditLoginUser {
  name: string;
}

export interface AdcmAuditLoginFilter {
  username?: string;
  loginResult?: AdcmAuditLoginResultType;
  timeFrom: number;
  timeTo: number;
}

export type AdcmAuditLoginRequestParam = Omit<AdcmAuditLoginFilter, 'timeFrom' | 'timeTo'> & {
  timeFrom: string;
  timeTo: string;
};
