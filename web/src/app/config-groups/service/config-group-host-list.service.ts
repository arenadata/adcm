import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '@app/core/api';
import { ParamMap } from '@angular/router';
import { IListService, ListInstance } from '@app/shared/components/list/list-service-token';
import { ListResult } from '@app/models/list-result';
import { ApiFlat, Host } from '@app/core/types';
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
    const current = this.cluster.Current as unknown as ApiFlat;
    const listParamStr = localStorage.getItem('list:param');

    if (p?.keys.length) {
      const param = p.keys.reduce((a, c) => ({ ...a, [c]: p.get(c) }), {});
      delete param['page'];

      if (listParamStr) {
        const json = JSON.parse(listParamStr);
        json[`group_config_host_${current.object_type}`] = param;
        localStorage.setItem('list:param', JSON.stringify(json));
      } else localStorage.setItem('list:param', JSON.stringify({ [`group_config_host_${current.object_type}`]: param }));
    }

    const configGroupId = this.cluster.Current.id;

    return this.api.getList(`${environment.apiRoot}group-config/${configGroupId}/host/`, p);
  }

  initInstance(): ListInstance {
    this.current = { typeName: 'group_config_hosts', columns: ['name', 'remove'] };
    return this.current;
  }

  delete(row: Host): Observable<Object> {
    return this.api.delete(row.url);
  }

}
