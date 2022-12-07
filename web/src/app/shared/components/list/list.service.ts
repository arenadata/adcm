// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { Injectable } from '@angular/core';
import { convertToParamMap, ParamMap, Params } from '@angular/router';
import { map, switchMap, tap } from 'rxjs/operators';
import { Observable } from 'rxjs';
import { environment } from '@env/environment';
import { ApiService } from '@app/core/api';
import { ClusterService } from '@app/core/services/cluster.service';
import { BaseEntity, Bundle, Entities, IAction, Service, TypeName } from '@app/core/types';
import { IListService, ListInstance } from '@app/shared/components/list/list-service-token';
import { ListResult } from '@app/models/list-result';
import { ICluster } from '@app/models/cluster';

const COLUMNS_SET = {
  cluster: ['name', 'prototype_version', 'description', 'state', 'status', 'actions', 'import', 'upgrade', 'config', 'controls'],
  host2cluster: ['fqdn', 'provider_name', 'state', 'status', 'actions', 'config', 'maintenance_mode', 'remove'],
  service2cluster: ['display_name', 'version_no_sort', 'state', 'status', 'actions', 'import', 'config'],
  host: ['fqdn', 'provider_name', 'host2cluster', 'state', 'status', 'actions', 'config', 'maintenance_mode', 'controls'],
  provider: ['name', 'prototype_version', 'state', 'actions', 'upgrade', 'config', 'controls'],
  job: ['action', 'objects', 'start_date', 'finish_date', 'status'],
  task: ['id', 'start_date', 'finish_date', 'status'],
  bundle: ['name', 'version', 'edition', 'description', 'controls'],
};

@Injectable({
  providedIn: 'root',
})
export class ListService implements IListService<Entities> {
  current: ListInstance;

  constructor(private api: ApiService, private detail: ClusterService) {}

  initInstance(typeName: TypeName): ListInstance {
    this.current = { typeName, columns: COLUMNS_SET[typeName] };
    return this.current;
  }

  getList(p: ParamMap, typeName: TypeName): Observable<ListResult<Entities>> {
    const listParamStr = localStorage.getItem('list:param');

    if (p?.keys?.length > 0) {
      const param = p.keys.reduce((a, c) => ({ ...a, [c]: p.get(c) }), {});
      delete param['page'];

      if (listParamStr) {
        const json = JSON.parse(listParamStr);
        json[typeName] = param;
        localStorage.setItem('list:param', JSON.stringify(json));
      } else localStorage.setItem('list:param', JSON.stringify({ [typeName]: param }));
    }

    let params = { ...(p || {}) };

    switch (typeName) {
      case 'host2cluster':
        return this.detail.getHosts(p);
      case 'service2cluster':
        return this.detail.getServices(p);
      case 'bundle':
        return this.api.getList<Bundle>(`${environment.apiRoot}stack/bundle/`, p);
      case 'servicecomponent':
        return this.api.getList(`${environment.apiRoot}cluster/${(this.detail.Current as Service).cluster_id}/service/${this.detail.Current.id}/component`, p);
      case 'user':
        params = { ...params['params'], 'expand': 'group' };
        return this.api.getList(`${environment.apiRoot}rbac/user/`, convertToParamMap(params));
      case 'group':
        params = { ...params['params'], 'expand': 'user' };
        return this.api.getList(`${environment.apiRoot}rbac/group/`, convertToParamMap(params));
      case 'role':
        params = { ...params['params'], 'expand': 'child' };
        return this.api.getList(`${environment.apiRoot}rbac/role/`, convertToParamMap(params), { type: 'role' });
      case 'policy':
        params = { ...params['params'], 'expand': 'child,role,user,group,object', 'built_in': 'false' };
        return this.api.getList(`${environment.apiRoot}rbac/policy/`, convertToParamMap(params));
      case 'audit_operations':
        params = { ...params['params'], 'expand': null };
        return this.api.getList(`${environment.apiRoot}audit/operation`, convertToParamMap(params));
      case 'audit_login':
        params = { ...params['params'], 'expand': null };
        return this.api.getList(`${environment.apiRoot}audit/login`, convertToParamMap(params));
      default:
        return this.api.root.pipe(switchMap((root) => this.api.getList<Entities>(root[this.current.typeName], p)));
    }
  }

  getCrumbs() {
    return [{ path: '/cluster', name: 'clusters' }];
  }

  getActions(row: Entities) {
    this.api
      .get<IAction[]>(row.action)
      .pipe(tap((actions) => (row.actions = actions)))
      .subscribe();
  }

  delete(row: Entities) {
    return this.api.delete(row.url);
  }

  // host
  getClustersForHost(param: Params): Observable<{ id: number; title: string }[]> {
    return this.api.root
      .pipe(switchMap((root) => this.api.getList<ICluster>(root.cluster, convertToParamMap(param))))
      .pipe(map((res) => res.results.map((a) => ({ id: a.id, title: a.name }))));
  }

  checkItem<T>(item: BaseEntity) {
    return this.api.get<T>(item.url);
  }

  acceptLicense(url: string) {
    return this.api.put(url, {});
  }

  getLicenseInfo(url: string) {
    return this.api.get<{ text: string }>(url);
  }

  setMaintenanceMode(row: Entities) {
    return this.api.post(`/api/v1/${row['type']}/${row.id}/maintenance-mode/`, { maintenance_mode: row['maintenance_mode'] });
  }

  renameHost(column: string, value: any, id: number) {
    return this.api.patch(`/api/v1/host/${id}/`, { [column]: value });
  }

  renameCluster(column: string, value: any, id: number) {
    return this.api.patch(`/api/v1/cluster/${id}/`, { [column]: value });
  }
}
