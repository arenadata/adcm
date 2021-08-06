import { Injectable } from '@angular/core';
import { forkJoin, Observable } from 'rxjs';
import { EntityService } from '../../abstract/entity-service';
import { ApiService } from '../../core/api';
import { environment } from '../../../environments/environment';
import { ConfigGroup } from '@app/config-groups/model/config-group.model';
import { Host } from '@app/core/types';
import { map } from 'rxjs/operators';


@Injectable({
  providedIn: 'root'
})
export class ConfigGroupListService extends EntityService<ConfigGroup> {

  constructor(
    protected api: ApiService,
  ) {
    super(api);
  }

  get(id: number): Observable<ConfigGroup> {
    return this.api.get<ConfigGroup>(`${environment.apiRoot}config-group/${id}`);
  }

  add(group: ConfigGroup): Observable<unknown> {
    const params = { ...group };

    return this.api.post<unknown>(`${environment.apiRoot}config-group/`, params);
  }

  addHosts(data: { host: number, group: number }[]): Observable<unknown> {
    return forkJoin(data.map((o) => this.api.post<unknown>(`${environment.apiRoot}host-group/`, o)));
  }

  getHostListForCurrentCluster(clusterUrl: string): Observable<Host[]> {
    return this.api.get<Host[]>(clusterUrl).pipe(
      map((hosts) =>
        hosts
          .map((host) => ({
            ...host,
            name: host.fqdn,
          }))
      )
    );
  }
}
