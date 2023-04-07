import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { CompareConfig, IConfig } from '../types';
import { map, switchMap } from 'rxjs/operators';
import { getRandomColor } from '@app/core/types';
import { ApiService } from '@app/core/api';

export interface IConfigResponse {
  current: string;
  history: string;
  previous: string;
}

export interface IConfigListResponse {
  count: 1;
  next: null;
  previous: null;
  results: IConfig[];
}


export interface IConfigService {
  getConfig(url: string): Observable<IConfig>;

  getHistoryList(url: string): Observable<CompareConfig[]>;

  send(url: string, data: any): Observable<IConfig>;

  changeVersion(id: number, url?: string): Observable<IConfig>;
}

@Injectable({
  providedIn: 'root'
})
export class ConfigService implements IConfigService {
  constructor(private api: ApiService) { }

  changeVersion(id: number, url: string): Observable<IConfig> {
    return this.api.get<IConfig>(`${url}history/${id}/`);
  }

  getConfig(url: string): Observable<IConfig> {
    return this.api.get<IConfig>(`${url}current/`);
  }

  getHistoryList(url: string): Observable<CompareConfig[]> {
    return this.api.get<IConfigResponse>(url).pipe(
      switchMap((config) => this.api.get<IConfigListResponse | IConfig[]>(config.history + '?fields=id,date,description')),
      // ToDo remove it when API will be consistent
      map((value) => Array.isArray(value) ? value as IConfig[] : value.results),
      map((h) => h.map((b) => ({
        ...b,
        color: getRandomColor()
      }))));
  }

  send(url: string, data: any): Observable<IConfig> {
    return this.api.post<IConfig>(`${url}history/`, data);
  }
}
