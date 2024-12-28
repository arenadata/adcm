import type { RequestError } from '@api';
import { RequestState } from '@models/loadState';

export const processErrorResponse = (payload: RequestError) => {
  const response = payload?.response;

  if (response?.status === 403) {
    return RequestState.AccessDenied;
  }

  if (response?.status === 404) {
    return RequestState.NotFound;
  }

  return RequestState.Completed;
};
