import { Injectable } from '@angular/core';
import { forkJoin, Observable } from 'rxjs';
import { EntityService } from '../../abstract/entity-service';
import { ApiService } from '../../core/api';
import { environment } from '../../../environments/environment';
import { ConfigGroup } from '@app/config-groups/model/config-group.model';
import { Host } from '@app/core/types';
import { map } from 'rxjs/operators';
import { IListService, ListInstance } from '@app/shared/components/list/list-service-token';
import { ParamMap } from '@angular/router';
import { ListResult } from '@app/models/list-result';


@Injectable({
  providedIn: 'root'
})
export class ConfigGroupListService extends EntityService<ConfigGroup> implements IListService<ConfigGroup> {
  current: ListInstance;

  constructor(
    protected api: ApiService,
  ) {
    super(api);
  }

  getList(p: ParamMap): Observable<ListResult<ConfigGroup>> {
    // ToDo remove from here

    const listParamStr = localStorage.getItem('list:param');
    if (p?.keys.length) {
      const param = p.keys.reduce((a, c) => ({ ...a, [c]: p.get(c) }), {});
      if (listParamStr) {
        const json = JSON.parse(listParamStr);
        json['configgroup'] = param;
        localStorage.setItem('list:param', JSON.stringify(json));
      } else localStorage.setItem('list:param', JSON.stringify({ ['configgroup']: param }));
    }

    return this.api.getList(`${environment.apiRoot}config-group/`, p);
  }

  initInstance(): ListInstance {
    this.current = { typeName: 'configgroup', columns: ['name', 'description', 'remove'] };
    return this.current;
  }

  get(id: number): Observable<ConfigGroup> {
    return this.api.get<ConfigGroup>(`${environment.apiRoot}config-group/${id}`);
  }

  add(group: ConfigGroup): Observable<unknown> {
    const params = { ...group };

    return this.api.post<unknown>(`${environment.apiRoot}config-group/`, params);
  }

  delete(row: ConfigGroup): Observable<Object> {
    return this.api.delete(row.url);
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
