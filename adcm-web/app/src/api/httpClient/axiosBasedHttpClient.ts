import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import { RequestOptions, Response, RequestError } from './HttpClient';
import { apiHost } from '@constants';
import '@utils/objectUtils';
import type { HttpClient } from './HttpClient';

export class AxiosBasedHttpClient implements HttpClient {
  protected axiosInstance: AxiosInstance;

  constructor() {
    this.axiosInstance = axios.create({
      baseURL: apiHost,
      withCredentials: true,
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
      xsrfCookieName: 'csrftoken',
      xsrfHeaderName: 'X-CSRFToken',
    });
  }

  public async get<T>(url: string, options?: RequestOptions): Promise<Response<T>> {
    try {
      const axiosResponse = await this.axiosInstance.get<T>(url, options || {});
      const response = this.mapResponse<T>(axiosResponse);
      return response;
    } catch (axiosError) {
      const error = this.mapError(axiosError as AxiosError);
      throw error;
    }
  }

  public async post<T, D = unknown>(url: string, data?: D, options?: RequestOptions): Promise<Response<T>> {
    try {
      const axiosResponse = await this.axiosInstance.post<T>(url, data, options || {});
      const response = this.mapResponse<T>(axiosResponse);
      return response;
    } catch (axiosError) {
      const error = this.mapError(axiosError as AxiosError);
      throw error;
    }
  }

  public async put<T, D = unknown>(url: string, data: D, options?: RequestOptions): Promise<Response<T>> {
    try {
      const axiosResponse = await this.axiosInstance.put<T>(url, data, options || {});
      const response = this.mapResponse<T>(axiosResponse);
      return response;
    } catch (axiosError) {
      const error = this.mapError(axiosError as AxiosError);
      throw error;
    }
  }

  public async patch<T, D = unknown>(url: string, data?: D, options?: RequestOptions): Promise<Response<T>> {
    try {
      const axiosResponse = await this.axiosInstance.patch<T>(url, data, options || {});
      const response = this.mapResponse<T>(axiosResponse);
      return response;
    } catch (axiosError) {
      const error = this.mapError(axiosError as AxiosError);
      throw error;
    }
  }

  public async delete<T>(url: string, options?: RequestOptions): Promise<Response<T>> {
    try {
      const axiosResponse = await this.axiosInstance.delete(url, options || {});
      const response = this.mapResponse<T>(axiosResponse);
      return response;
    } catch (axiosError) {
      const error = this.mapError(axiosError as AxiosError);
      throw error;
    }
  }

  protected mapResponse<T>(axiosResponse: AxiosResponse): Response<T> {
    return {
      data: axiosResponse.data as T,
      headers: axiosResponse.headers as Response<T>['headers'],
      status: axiosResponse.status,
      statusText: axiosResponse.statusText,
    };
  }

  protected mapError(axiosError: AxiosError) {
    const response = axiosError.response ? this.mapResponse<unknown>(axiosError.response) : undefined;
    const error = new RequestError(axiosError.message, response);
    return error;
  }
}
