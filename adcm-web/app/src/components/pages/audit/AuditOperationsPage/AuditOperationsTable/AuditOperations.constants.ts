import { TableColumn } from '@uikit';
import { AdcmAuditOperationObjectType, AdcmAuditOperationResult, AdcmAuditOperationType } from '@models/adcm';
import { getOptionsFromEnum } from '@uikit/Select/Select.utils';

export const columns: TableColumn[] = [
  {
    label: 'Object type',
    name: 'objectType',
    isSortable: true,
  },
  {
    label: 'Object name',
    name: 'objectName',
    isSortable: true,
  },
  {
    label: 'Operation name',
    name: 'name',
    isSortable: true,
  },
  {
    label: 'Operation type',
    name: 'type',
    isSortable: true,
  },
  {
    label: 'Result',
    name: 'result',
    isSortable: true,
  },
  {
    label: 'Time',
    name: 'time',
    isSortable: true,
  },
  {
    label: 'Username',
    name: 'userName',
    isSortable: true,
  },
  {
    label: '',
    name: '',
    isSortable: false,
  },
];

export const objectTypeOptions = getOptionsFromEnum(AdcmAuditOperationObjectType);
export const operationTypeOptions = getOptionsFromEnum(AdcmAuditOperationType);
export const operationResultOptions = getOptionsFromEnum(AdcmAuditOperationResult);

export const operationAuditInactiveResults = [AdcmAuditOperationResult.Denied, AdcmAuditOperationResult.Fail];
