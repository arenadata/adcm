import { Injectable, InjectionToken } from '@angular/core';
import { Observable } from 'rxjs';
import { EntityService } from '../../abstract/entity-service';
import { ApiService } from '../../core/api';
import { environment } from '../../../environments/environment';
import { ConfigGroup } from '@app/config-groups/model/config-group.model';
import { IListService, ListInstance } from '@app/shared/components/list/list-service-token';
import { ParamMap } from '@angular/router';
import { ListResult } from '@app/models/list-result';
import { ClusterService } from '@app/core/services/cluster.service';

export const CONFIG_GROUP_LIST_SERVICE = new InjectionToken<EntityService<ConfigGroup>>('EntityService');


@Injectable({
  providedIn: 'root'
})
export class ConfigGroupListService extends EntityService<ConfigGroup> implements IListService<ConfigGroup> {

  current: ListInstance;

  constructor(
    protected api: ApiService,
    private cluster: ClusterService
  ) {
    super(api);
  }

  getList(p: ParamMap): Observable<ListResult<ConfigGroup>> {
    console.log(this.cluster.Current);

    const listParamStr = localStorage.getItem('list:param');
    if (p?.keys.length) {
      const param = p.keys.reduce((a, c) => ({ ...a, [c]: p.get(c) }), {});
      if (listParamStr) {
        const json = JSON.parse(listParamStr);
        json['group_configs'] = param;
        localStorage.setItem('list:param', JSON.stringify(json));
      } else localStorage.setItem('list:param', JSON.stringify({ ['group_configs']: param }));
    }

    return this.api.getList(`${environment.apiRoot}group-config/`, p);
  }

  initInstance(): ListInstance {
    this.current = { typeName: 'group_configs', columns: ['name', 'description', 'remove'] };
    return this.current;
  }

  get(id: number): Observable<ConfigGroup> {
    return this.api.get<ConfigGroup>(`${environment.apiRoot}group-config/${id}`);
  }

  delete(row: ConfigGroup): Observable<Object> {
    return this.api.delete(row.url);
  }

}
