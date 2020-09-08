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
import { ParamMap, Params, convertToParamMap } from '@angular/router';
import { ApiService } from '@app/core/api';
import { ClusterService } from '@app/core/services';
import { Bundle, Cluster, Entities, Host, IAction, TypeName } from '@app/core/types';
import { environment } from '@env/environment';
import { switchMap, tap, map } from 'rxjs/operators';
import { Observable } from 'rxjs';

const COLUMNS_SET = {
  cluster: ['name', 'prototype_version', 'description', 'state', 'status', 'actions', 'import', 'upgrade', 'config', 'controls'],
  host2cluster: ['fqdn', 'provider_name', 'state', 'status', 'actions', 'config', 'remove'],
  service2cluster: ['display_name', 'version_no_sort', 'state', 'status', 'actions', 'import', 'config'],
  host: ['fqdn', 'provider_name', 'host2cluster', 'state', 'status', 'actions', 'config', 'controls'],
  provider: ['name', 'prototype_version', 'state', 'actions', 'upgrade', 'config', 'controls'],
  job: ['action', 'objects', 'start_date', 'finish_date', 'status'],
  task: ['id', 'start_date', 'finish_date', 'status'],
  bundle: ['name', 'version', 'edition', 'description', 'controls'],
};


export interface ListInstance {
  typeName: TypeName;
  columns: string[];
}

@Injectable({
  providedIn: 'root',
})
export class ListService {
  current: ListInstance;

  constructor(private api: ApiService, private detail: ClusterService) {}

  initInstance(typeName: TypeName): ListInstance {
    this.current = { typeName, columns: COLUMNS_SET[typeName] };
    return this.current;
  }

  getList(p: ParamMap, typeName: string) {
    const listParamStr = localStorage.getItem('list:param');
    if (p?.keys.length) {
      const param = p.keys.reduce((a, c) => ({ ...a, [c]: p.get(c) }), {});
      if (listParamStr) {
        const json = JSON.parse(listParamStr);
        json[typeName] = param;
        localStorage.setItem('list:param', JSON.stringify(json));
      } else localStorage.setItem('list:param', JSON.stringify({ [typeName]: param }));
    }

    switch (typeName) {
      case 'host2cluster':
        return this.detail.getHosts(p);
      case 'service2cluster':
        return this.detail.getServices(p);
      case 'bundle':
        return this.api.getList<Bundle>(`${environment.apiRoot}stack/bundle/`, p);
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
      .pipe(switchMap((root) => this.api.getList<Cluster>(root.cluster, convertToParamMap(param))))
      .pipe(map((res) => res.results.map((a) => ({ id: a.id, title: a.name }))));
  }

  addClusterToHost(cluster_id: number, row: Host) {
    this.api
      .post<Host>(`${environment.apiRoot}cluster/${cluster_id}/host/`, { host_id: row.id })
      .subscribe((host) => {
        row.cluster_id = host.cluster_id;
        row.cluster_name = host.cluster;
      });
  }

  checkItem<T>(item: Entities) {
    return this.api.get<T>(item.url);
  }

  acceptLicense(url: string) {
    return this.api.put(url, {});
  }

  getLicenseInfo(url: string) {
    return this.api.get<{ text: string }>(url);
  }
}
