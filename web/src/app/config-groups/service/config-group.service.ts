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

  changeVersion(url: string, id: number): Observable<IConfig> {
        throw new Error('Method not implemented.');
    }

  getConfig(url: string): Observable<IConfig> {
    return this.api.get<IConfigResponse>(url).pipe(
      switchMap((config) => this.api.get<IConfig>(config.current))
    );
  }

  getHistoryList(url: string, currentVersionId: number): Observable<CompareConfig[]> {
    return this.api.get<IConfigResponse>(url).pipe(
      switchMap((config) => this.api.get<IConfigListResponse>(config.history)),
      map((value) => value.results),
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
