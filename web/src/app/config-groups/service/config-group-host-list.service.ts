import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { EntityService } from '../../abstract/entity-service';
import { ApiService } from '../../core/api';
import { ParamMap } from '@angular/router';
import { ConfigGroup } from '../model/config-group.model';
import { IListService, ListInstance } from '../../shared/components/list/list-service-token';
import { ListResult } from '../../models/list-result';
import { of } from 'rxjs/internal/observable/of';


@Injectable({
  providedIn: 'root'
})
export class ConfigGroupHostListService extends EntityService<ConfigGroup>
  implements IListService<ConfigGroup> {

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

    console.log('getList p: ', p);
    console.log(this.current);

    return of(null);
  }

  initInstance(): ListInstance {
    this.current = { typeName: 'configgroup', columns: ['name', 'description', 'remove'] };
    return this.current;
  }

  get(id: number): Observable<ConfigGroup> {
    // ToDo

    return of(null);
  }

  delete(row: ConfigGroup): Observable<Object> {
    // ToDo
    
    return of(null);
  }


  // addHosts(data: { host: number, group: number }[]): Observable<unknown> {
  //   return forkJoin(data.map((o) => this.api.post<unknown>(`${environment.apiRoot}host-group/`, o)));
  // }

  // getHostListForCurrentCluster(clusterUrl: string): Observable<Host[]> {
  //   return this.api.get<Host[]>(clusterUrl).pipe(
  //     map((hosts) =>
  //       hosts
  //         .map((host) => ({
  //           ...host,
  //           name: host.fqdn,
  //         }))
  //     )
  //   );
  // }


}
