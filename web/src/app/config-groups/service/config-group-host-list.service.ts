import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { EntityService } from '../../abstract/entity-service';
import { ApiService } from '../../core/api';
import { ParamMap } from '@angular/router';
import { IListService, ListInstance } from '../../shared/components/list/list-service-token';
import { ListResult } from '../../models/list-result';
import { of } from 'rxjs/internal/observable/of';
import { Host } from '../../core/types';


@Injectable({
  providedIn: 'root'
})
export class ConfigGroupHostListService extends EntityService<Host> implements IListService<Host> {

  current: ListInstance;

  constructor(
    protected api: ApiService,
  ) {
    super(api);
  }


  getList(p: ParamMap): Observable<ListResult<Host>> {
    const listParamStr = localStorage.getItem('list:param');
    if (p?.keys.length) {
      const param = p.keys.reduce((a, c) => ({ ...a, [c]: p.get(c) }), {});
      if (listParamStr) {
        const json = JSON.parse(listParamStr);
        json['configgroup'] = param;
        localStorage.setItem('list:param', JSON.stringify(json));
      } else localStorage.setItem('list:param', JSON.stringify({ ['configgroup']: param }));
    }

    return of({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          typeName: 'host',
          id: 1,
          name: 'MOCK host1',
          url: 'MOCK host1_url',
          config: 'string',
          fqdn: 'MOCK  host1_fqdn',
          provider_id: 1,
          cluster: 'cluster'
        }
      ]
    });
  }

  initInstance(): ListInstance {
    this.current = { typeName: 'configgroup', columns: ['name', 'remove'] };
    return this.current;
  }

  get(id: number): Observable<Host> {
    return of(null);
  }

  delete(row: Host): Observable<Object> {
    return of(null);
  }

}
