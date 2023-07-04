import { RequestError } from '@api';

export interface ResponseErrorData {
  code: string;
  level: 'error';
  desc: string;
}

export const getErrorMessage = (requestError: RequestError) => {
  const data = (requestError.response?.data ?? {}) as ResponseErrorData;
  console.info('response error data = ', data);

  return data.desc;
};
