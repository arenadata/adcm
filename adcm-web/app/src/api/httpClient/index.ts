import { AxiosBasedHttpClient } from './axiosBasedHttpClient';
export type { Response, RequestError } from './HttpClient';

export const httpClient = new AxiosBasedHttpClient();
