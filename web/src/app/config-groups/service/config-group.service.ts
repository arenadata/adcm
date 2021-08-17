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


@Injectable({
  providedIn: 'root'
})
export class ConfigGroupService implements IConfigService {
  constructor(private api: ApiService) { }

  getConfig(url: string): Observable<IConfig> {
    return this.api.get<IConfigResponse>(url).pipe(
      switchMap((config) => this.api.get<IConfig>(config.current))
    );
  }

  getHistoryList(url: string, currentVersionId: number): Observable<CompareConfig[]> {
    return this.api.get<IConfigResponse>(url).pipe(
      switchMap((config) => this.api.get<IConfigListResponse | IConfig[]>(config.history)),
      // ToDo remove it when API will be consistent
      map((value) => Array.isArray(value) ? value as IConfig[] : value.results),
      map((h) => h.filter((a) => a.id !== currentVersionId).map((b) => ({
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
