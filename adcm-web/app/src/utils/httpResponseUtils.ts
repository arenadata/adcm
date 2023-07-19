import { RequestError } from '@api';

export interface ResponseErrorData {
  code: string;
  level: 'error';
  desc?: string;
  detail?: string;
}

export const getErrorMessage = (requestError: RequestError) => {
  const data = (requestError.response?.data ?? {}) as ResponseErrorData;

  return data.desc ?? data.detail ?? 'Something wrong';
};
