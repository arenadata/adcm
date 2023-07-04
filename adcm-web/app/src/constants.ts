import { getEnv } from '@utils/envVarsUtils';

export const apiHost = getEnv('ADCM_API_HOST');

export const defaultPerPagesList = [
  { value: 10, label: '10 per page' },
  { value: 30, label: '30 per page' },
  { value: 50, label: '50 per page' },
  { value: 100, label: '100 per page' },
];

export const defaultDebounceDelay = 300;
export const defaultSpinnerDelay = 300;
