import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '@app/core/api';
import { convertToParamMap, ParamMap } from '@angular/router';
import { IListService, ListInstance } from '@app/shared/components/list/list-service-token';
import { ListResult } from '@app/models/list-result';
import { of } from 'rxjs/internal/observable/of';
import { Host } from '@app/core/types';
import { ClusterService } from '@app/core/services/cluster.service';
import { environment } from '@env/environment';


@Injectable({
  providedIn: 'root'
})
export class ConfigGroupHostListService implements IListService<Host> {

  current: ListInstance;

  constructor(
    protected api: ApiService,
    protected cluster: ClusterService
  ) {
  }


  getList(p: ParamMap): Observable<ListResult<Host>> {
    const listParamStr = localStorage.getItem('list:param');
    if (p?.keys.length) {
      const param = p.keys.reduce((a, c) => ({ ...a, [c]: p.get(c) }), {});
      if (listParamStr) {
        const json = JSON.parse(listParamStr);
        json['group_config'] = param;
        localStorage.setItem('list:param', JSON.stringify(json));
      } else localStorage.setItem('list:param', JSON.stringify({ ['group_config']: param }));
    }

    const configGroupId = this.cluster.Current.id;
    const params = convertToParamMap({});

    return this.api.getList(`${environment.apiRoot}group-config/${configGroupId}/host/`, params);
  }

  initInstance(): ListInstance {
    this.current = { typeName: 'host2configgroup', columns: ['name', 'remove'] };
    return this.current;
  }

  delete(row: Host): Observable<Object> {
    // ToDo
    console.log('delete');

    return of(null);
  }

}
