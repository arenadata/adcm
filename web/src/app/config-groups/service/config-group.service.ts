import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {
  IConfigListResponse,
  IConfigResponse,
  IConfigService
} from '@app/shared/configuration/services/config.service';
import { ApiService } from '@app/core/api';
import { CompareConfig, IConfig } from '@app/shared/configuration/types';
import { map, switchMap } from 'rxjs/operators';
import { getRandomColor } from '@app/core/types';
import { environment } from '@env/environment';


@Injectable({
  providedIn: 'root'
})
export class ConfigGroupService implements IConfigService {
  constructor(private api: ApiService) { }

  changeVersion(id: number): Observable<IConfig> {
    return this.api.get<IConfig>(`${environment.apiRoot}config-log/${id}`);
  }

  getConfig(url: string): Observable<IConfig> {
    return this.api.get<IConfigResponse>(url).pipe(
      switchMap((config) => this.api.get<IConfig>(config.current))
    );
  }

  getHistoryList(url: string): Observable<CompareConfig[]> {
    return this.api.get<IConfigResponse>(url).pipe(
      switchMap((config) => this.api.get<IConfigListResponse>(config.history)),
      map((value) => value.results),
      map((h) => h.map((b) => ({
        ...b,
        color: getRandomColor()
      }))));
  }

  send(url: string, data: any): Observable<IConfig> {
    return this.api.get<IConfigResponse>(url).pipe(
      switchMap((config) => this.api.post<IConfig>(config.history, data)),
    );
  }
}
