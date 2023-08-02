export enum AdcmAuditOperationType {
  create = 'create',
  update = 'update',
  delete = 'delete',
}

export enum AdcmAuditOperationResult {
  success = 'success',
  fail = 'fail',
  denied = 'denied',
}

export enum AdcmAuditOperationObjectType {
  cluster = 'cluster',
  service = 'service',
  component = 'component',
  host = 'host',
  provider = 'provider',
  bundle = 'bundle',
  user = 'user',
  group = 'group',
  policy = 'policy',
  adcm = 'adcm',
  role = 'role',
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
  operationTimeAfter: number;
  operationTimeBefore: number;
}

export type AdcmAuditOperationRequestParam = Omit<
  AdcmAuditOperationFilter,
  'operationTimeAfter' | 'operationTimeBefore'
> & {
  operationTimeAfter: string;
  operationTimeBefore: string;
};
