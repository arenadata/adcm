import type { AdcmWizardOperationSettings } from '@models/adcm/wizard';

interface OperationSettingItem {
  key: keyof AdcmWizardOperationSettings;
  label: string;
  hint: string;
}

export const operationSettingItems: OperationSettingItem[] = [
  {
    key: 'shouldBlockObject',
    label: 'Raise blocking concern',
    hint: 'Disable object blocking after action runs feature allows users to run parallel processes on an object and its children and parents.',
  },
  {
    key: 'isVerbose',
    label: 'Verbose',
    hint: 'Shows detailed debug output. May slow down execution.',
  },
];
