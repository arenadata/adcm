export interface RequestOptions {
  headers?: { [key: string]: string };
  withCredentials?: boolean;
  signal?: AbortSignal;
}

export interface Response<T> {
  data: T;
  headers?: { [key: string]: string };
  status: number;
  statusText: string;
}

export interface HttpClient {
  get<T>(url: string, options: RequestOptions): Promise<Response<T>>;
  post<T>(url: string, payload: object, options: RequestOptions): Promise<Response<T>>;
  put<T>(url: string, payload: object, options: RequestOptions): Promise<Response<T>>;
  delete<T>(url: string, options: RequestOptions): Promise<Response<T>>;
}

export class RequestError extends Error {
  public response?: Response<unknown>;

  constructor(message: string, response?: Response<unknown>) {
    super(message);
    this.response = response;
  }
}

export const isCancelledError = (requestError: RequestError): boolean => requestError.message === 'canceled';
