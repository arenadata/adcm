import { Injectable, InjectionToken } from '@angular/core';
import { Observable } from 'rxjs';
import { ParamMap } from '@angular/router';
import { EntityService } from '@app/abstract/entity-service';
import { ApiService } from '@app/core/api';
import { environment } from '@env/environment';
import { ConfigGroup } from '@app/config-groups/model/config-group.model';
import { IListService, ListInstance } from '@app/shared/components/list/list-service-token';
import { ListResult } from '@app/models/list-result';
import { ClusterService } from '@app/core/services/cluster.service';
import { Service } from '@app/core/types';
import { ICluster } from '@app/models/cluster';

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
    const current = this.cluster.Current as ICluster | Service;
    const listParamStr = localStorage.getItem('list:param');

    if (p?.keys.length) {
      const param = p.keys.reduce((a, c) => ({ ...a, [c]: p.get(c) }), {});
      delete param['page'];

      if (listParamStr) {
        const json = JSON.parse(listParamStr);
        json[`group_config_${current.typeName}`] = param;
        localStorage.setItem('list:param', JSON.stringify(json));
      } else localStorage.setItem('list:param', JSON.stringify({ [`group_config_${current.typeName}`]: param }));
    }

    return this.api.getList(current.group_config, p);
  }

  initInstance(): ListInstance {
    this.current = { typeName: 'group_config', columns: ['name', 'description', 'remove'] };
    return this.current;
  }

  get(
    id: number,
    params: { [key: string]: string } = {},
  ): Observable<ConfigGroup> {
    return this.api.get(`${environment.apiRoot}group-config/${id}/`, params);
  }

  delete(row: ConfigGroup): Observable<Object> {
    return this.api.delete(row.url);
  }

}
