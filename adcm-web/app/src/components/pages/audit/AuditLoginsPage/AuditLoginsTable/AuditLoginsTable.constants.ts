import type { TableColumn } from '@uikit';
import { AdcmAuditLoginResultType } from '@models/adcm';
import { getOptionsFromEnum } from '@uikit/Select/Select.utils';

export const columns: TableColumn[] = [
  {
    label: 'Login',
    name: 'loginName',
    isSortable: false,
  },
  {
    label: 'Result',
    name: 'loginResult',
    isSortable: false,
  },
  {
    label: 'Login time',
    name: 'loginTime',
    isSortable: true,
  },
];

export const loginsResultOptions = getOptionsFromEnum(AdcmAuditLoginResultType);

export const loginsAuditInactiveResults = [
  AdcmAuditLoginResultType.UserNotFound,
  AdcmAuditLoginResultType.WrongPassword,
];
