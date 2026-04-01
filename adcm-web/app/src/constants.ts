import { getEnv } from '@utils/envVarsUtils';

export const apiHost = getEnv('ADCM_API_HOST') ?? '';
export const adcmVersion = getEnv('ADCM_VERSION') ?? '';

const defaultSocketSchema = window.location.protocol === 'https:' ? 'wss' : 'ws';
export const wsHost = getEnv('ADCM_WS_HOST') ?? `${defaultSocketSchema}://${window.location.host}`;
const isDevMode = import.meta.env.DEV;
export const apiRedocHost = isDevMode ? 'http://localhost:8000' : '';

export const defaultPerPagesList = [
  { value: 10, label: '10 per page' },
  { value: 30, label: '30 per page' },
  { value: 50, label: '50 per page' },
  { value: 100, label: '100 per page' },
];

export const defaultDebounceDelay = 300;
export const defaultSpinnerDelay = 300;

export const queryParamSortBy = 'ordering';
export const searchParamActionId = 'actionId';

export const emailRegexp = new RegExp(/^[^@ ]+@[^@ ]+\.[a-zA-Z]+$/);

export enum ActionStatuses {
  SuccessRun = 'Action was launched successfully',
}

export const unlimitedRequestItems = 10000;

export enum HelperLinkActions {
  Help = 'https://t.me/arenadata_cm',
  Documentation = 'https://docs.arenadata.io/en/ADCM/current/introduction/intro.html',
}

export const wizardProcessConflictErrorCode = 'ACTION_PROCESS_UPDATE_CONFLICT';
export enum HttpStatus {
  // 2xx - Successful responses
  OK = 200,
  CREATED = 201,

  // 4xx - Client errors
  BAD_REQUEST = 400,
  UNAUTHORIZED = 401,
  FORBIDDEN = 403,
  NOT_FOUND = 404,
  METHOD_NOT_ALLOWED = 405,
  REQUEST_TIMEOUT = 408,
  CONFLICT = 409,

  // 5xx - Server errors
  INTERNAL_SERVER_ERROR = 500,
}

export const AbortPayload = 'aborted';
