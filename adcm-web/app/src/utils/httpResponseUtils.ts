import type { RequestError } from '@api';
import { HttpStatus } from '@constants';

export interface ResponseErrorData {
  code: string;
  level: 'error';
  desc?: string;
  detail?: string;
}

export const getErrorMessage = (requestError: RequestError) => {
  const data = (requestError.response?.data ?? {}) as ResponseErrorData;

  return data.desc ?? data.detail ?? requestError.message ?? 'Something wrong';
};

export const getErrorCode = (requestError: RequestError) => {
  const errorCode = requestError.response?.status;

  if (typeof errorCode === 'number') {
    return errorCode;
  }

  return null;
};

export const isErrorConflict = (error: RequestError) => {
  return getErrorCode(error) === HttpStatus.CONFLICT;
};
