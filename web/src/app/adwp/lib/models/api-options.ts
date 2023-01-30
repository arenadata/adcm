import { HttpHeaders, HttpParams } from '@angular/common/http';
import { ApiParams } from './api-params';

export interface ApiOptions {
  ignoreErrors?: number[];
  root?: string;
  params?: HttpParams | ApiParams;
  headers?: HttpHeaders | {
    [header: string]: string | string[];
  };
  reportProgress?: boolean;
  withCredentials?: boolean;
}
