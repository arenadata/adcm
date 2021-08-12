import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { CompareConfig, IConfig } from '@app/shared/configuration/types';
import { map, switchMap } from 'rxjs/operators';
import { getRandomColor } from '@app/core/types';
import { ApiService } from '@app/core/api';
import { ClusterService } from '@app/core/services/cluster.service';

export interface IConfigResponse {
  current: string;
  history: string;
  previous: string;
}

export interface IConfigService {
  getConfig(url: string): Observable<IConfig>;

  getHistoryList(url: string, currentVersionId: number): Observable<CompareConfig[]>

  send(url: string, data: any): Observable<IConfig>
}

@Injectable({
  providedIn: 'root'
})
export class ConfigService implements IConfigService {

  constructor(private api: ApiService, public cluster: ClusterService) { }

  getConfig(url: string): Observable<IConfig> {
    return this.api.get<IConfigResponse>(url).pipe(
      switchMap((config) => this.api.get<IConfig>(config.current))
    );
  }

  getHistoryList(url: string, currentVersionId: number): Observable<CompareConfig[]> {
    return this.api.get<IConfigResponse>(url).pipe(
      switchMap((config) => this.api.get<IConfig[]>(config.history)),
      map((h) => h.filter((a) => a.id !== currentVersionId).map((b) => ({
        ...b,
        color: getRandomColor()
      }))));
  }

  send(url: string, data: any): Observable<IConfig> {
    return this.api.post<IConfig>(url, data);
  }
}
